import base64
import json
from unittest.mock import patch

import pytest
from flask import Response, request

from risk_api.app import PROTECTED_ROUTES, create_app
from risk_api.config import Config

# Bazaar extension data matching what _setup_x402_middleware registers.
# Kept here so x402 gate tests don't need the real (slow) SDK imports.
_EXAMPLE_OUTPUT = {
    "address": "0x4200000000000000000000000000000000000006",
    "score": 0,
    "level": "safe",
    "bytecode_size": 4632,
    "findings": [],
    "category_scores": {},
}

_ADDRESS_SCHEMA = {
    "properties": {
        "address": {
            "type": "string",
            "pattern": "^0x[0-9a-fA-F]{40}$",
            "description": "EVM contract address (0x-prefixed, 40 hex chars)",
        },
    },
    "required": ["address"],
}


def _build_payment_required(method: str, config: Config) -> dict:
    """Build a Payment-Required payload matching x402 SDK output."""
    bazaar: dict = {}

    if method == "GET":
        bazaar = {
            "info": {
                "input": {
                    "type": "http",
                    "queryParams": {
                        "address": "0x4200000000000000000000000000000000000006"
                    },
                },
                "output": {"example": _EXAMPLE_OUTPUT},
            },
            "schema": {
                "properties": {
                    "input": {
                        "properties": {
                            "queryParams": _ADDRESS_SCHEMA,
                        },
                    },
                },
            },
        }
    else:  # POST
        bazaar = {
            "info": {
                "input": {
                    "type": "http",
                    "bodyType": "json",
                    "body": {
                        "address": "0x4200000000000000000000000000000000000006"
                    },
                },
                "output": {"example": _EXAMPLE_OUTPUT},
            },
            "schema": {
                "properties": {
                    "input": {
                        "properties": {
                            "body": _ADDRESS_SCHEMA,
                        },
                    },
                },
            },
        }

    return {
        "x402Version": 2,
        "accepts": [
            {
                "scheme": "exact",
                "network": config.network,
                "maxAmountRequired": "100000",
                "resource": "/analyze",
                "payTo": config.wallet_address,
            }
        ],
        "extensions": {"bazaar": bazaar},
    }


def _fake_x402_middleware_setup(app, config: Config) -> bool:
    """Register a lightweight fake x402 payment gate for testing.

    Returns 402 with proper Payment-Required headers for protected routes,
    without importing the heavy x402 EVM SDK.
    """

    @app.before_request
    def x402_payment_gate():
        if request.path not in PROTECTED_ROUTES:
            return None

        method = "GET" if request.method == "HEAD" else request.method
        pr_data = _build_payment_required(method, config)
        pr_encoded = base64.b64encode(
            json.dumps(pr_data).encode()
        ).decode()

        return Response(
            json.dumps({"error": "Payment Required"}),
            status=402,
            content_type="application/json",
            headers={"Payment-Required": pr_encoded},
        )

    return True


@pytest.fixture()
def test_config():
    return Config(
        wallet_address="0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891",
        base_rpc_url="https://mainnet.base.org",
        facilitator_url="https://x402.org/facilitator",
        network="eip155:84532",
        price="$0.10",
        erc8004_agent_id=None,
        basescan_api_key="",
    )


@pytest.fixture()
def app(test_config):
    """App without x402 middleware — for testing route logic."""
    app = create_app(config=test_config, enable_x402=False)
    app.config["TESTING"] = True
    return app


@pytest.fixture()
def app_with_x402(test_config):
    """App with x402 payment gate — lightweight fake, no SDK imports.

    Registers a fake before_request hook that returns 402 with proper
    Payment-Required headers for protected routes, matching the real
    x402 SDK's response structure including Bazaar extensions.
    """
    with patch(
        "risk_api.app._setup_x402_middleware",
        side_effect=lambda app, config: _fake_x402_middleware_setup(app, config),
    ), patch("risk_api.app.get_code", return_value="0x60006000"):
        app = create_app(config=test_config, enable_x402=True)
        app.config["TESTING"] = True
        yield app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def client_with_x402(app_with_x402):
    return app_with_x402.test_client()
