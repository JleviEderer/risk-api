"""Flask application with x402 payment middleware."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from flask import Flask, Response, jsonify, request

from risk_api.analysis.engine import analyze_contract
from risk_api.chain.rpc import RPCError
from risk_api.config import Config, load_config

logger = logging.getLogger(__name__)

# Ethereum address pattern: 0x followed by 40 hex chars
ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")

# Routes that require x402 payment
PROTECTED_ROUTES = {"/analyze"}


class FlaskHTTPAdapter:
    """Adapts Flask request to x402 HTTPAdapter protocol."""

    def get_header(self, name: str) -> str | None:
        return request.headers.get(name)

    def get_method(self) -> str:
        return request.method

    def get_path(self) -> str:
        return request.path

    def get_accept_header(self) -> str:
        return request.headers.get("Accept", "")

    def get_query_param(self, name: str) -> str | list[str] | None:
        return request.args.get(name)

    def get_query_params(self) -> dict[str, str | list[str]] | None:
        return dict(request.args)

    def get_url(self) -> str:
        return request.url

    def get_user_agent(self) -> str:
        return request.headers.get("User-Agent", "")

    def get_body(self) -> Any:
        return request.get_json(silent=True)


def _setup_x402_middleware(app: Flask, config: Config) -> bool:
    """Set up x402 payment middleware. Returns True if successful."""
    try:
        from x402 import x402ResourceServerSync
        from x402.http import (
            FacilitatorConfig,
            HTTPFacilitatorClientSync,
            HTTPRequestContext,
            PaymentOption,
            RouteConfig,
            x402HTTPResourceServerSync,
        )
        from x402.mechanisms.evm.exact import ExactEvmServerScheme
    except ImportError:
        logger.warning("x402 SDK not available — payment middleware disabled")
        return False

    fac_config = FacilitatorConfig(url=config.facilitator_url)
    facilitator = HTTPFacilitatorClientSync(fac_config)
    resource_server = x402ResourceServerSync(facilitator)
    resource_server.register(config.network, ExactEvmServerScheme())  # type: ignore[arg-type]  # x402 SDK parameter name mismatch

    routes = {
        "GET /analyze": RouteConfig(
            accepts=PaymentOption(
                scheme="exact",
                pay_to=config.wallet_address,
                price=config.price,
                network=config.network,
            ),
            description="Smart contract risk scoring",
        ),
    }

    http_server = x402HTTPResourceServerSync(resource_server, routes)

    try:
        http_server.initialize()
    except Exception:
        logger.warning(
            "x402 middleware initialization failed (facilitator unreachable?) "
            "— payment middleware disabled",
            exc_info=True,
        )
        return False

    @app.before_request
    def x402_payment_gate():
        if request.path not in PROTECTED_ROUTES:
            return None

        adapter = FlaskHTTPAdapter()
        payment_header = request.headers.get("X-PAYMENT")
        context = HTTPRequestContext(
            adapter=adapter,
            path=request.path,
            method=request.method,
            payment_header=payment_header,
        )
        result = http_server.process_http_request(context)

        if result.type == "no-payment-required":
            return None
        elif result.type == "payment-verified":
            # Store payment info for potential settlement after response
            request.environ["x402_payload"] = result.payment_payload
            request.environ["x402_requirements"] = result.payment_requirements
            return None
        else:
            # payment-error: return 402 with payment requirements
            resp = result.response
            if resp is None:
                return Response("Payment Required", status=402)
            body = resp.body
            if not isinstance(body, str):
                body = json.dumps(body)
            return Response(
                body,
                status=resp.status,
                headers=resp.headers,
            )

    @app.after_request
    def x402_settle(response: Response) -> Response:
        if response.status_code == 200 and request.path in PROTECTED_ROUTES:
            payload = request.environ.get("x402_payload")
            requirements = request.environ.get("x402_requirements")
            if payload and requirements:
                try:
                    http_server.process_settlement(payload, requirements)
                except Exception:
                    logger.exception("x402 settlement failed")
        return response

    logger.info("x402 payment middleware enabled for %s", PROTECTED_ROUTES)
    return True


def create_app(
    config: Config | None = None,
    *,
    enable_x402: bool = True,
) -> Flask:
    """Flask application factory.

    Pass a Config object for testing; defaults to loading from environment.
    Set enable_x402=False to skip payment middleware (useful for testing).
    """
    if config is None:
        config = load_config()

    app = Flask(__name__)
    app.config["RISK_API_CONFIG"] = config
    if config.erc8004_agent_id is not None:
        app.config["ERC8004_AGENT_ID"] = config.erc8004_agent_id

    if enable_x402:
        _setup_x402_middleware(app, config)

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.route("/agent-metadata.json")
    def agent_metadata():
        """ERC-8004 agent registration metadata."""
        metadata = {
            "type": "https://eips.ethereum.org/EIPS/eip-8004#registration-v1",
            "name": "Smart Contract Risk Scorer",
            "description": (
                "EVM smart contract risk scoring API on Base. "
                "Analyzes bytecode patterns (proxy detection, reentrancy, "
                "selfdestruct, honeypot, hidden mint, fee manipulation, "
                "delegatecall) and returns a composite 0-100 risk score. "
                "Pay $0.10/call via x402 in USDC on Base. "
                "Endpoint: GET /analyze?address={contract_address}"
            ),
            "services": [
                {
                    "name": "web",
                    "endpoint": request.url_root.rstrip("/") + "/",
                }
            ],
            "x402Support": True,
            "active": True,
            "supportedTrust": ["reputation"],
        }

        agent_id = app.config.get("ERC8004_AGENT_ID")
        if agent_id is not None:
            metadata["registrations"] = [
                {
                    "agentId": agent_id,
                    "agentRegistry": (
                        "eip155:8453:"
                        "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
                    ),
                }
            ]

        return jsonify(metadata)

    @app.route("/analyze")
    def analyze():
        address = request.args.get("address", "").strip()

        if not address:
            return jsonify({"error": "Missing 'address' query parameter"}), 422

        if not ADDRESS_RE.match(address):
            return (
                jsonify({"error": f"Invalid Ethereum address: {address}"}),
                422,
            )

        try:
            result = analyze_contract(
                address, config.base_rpc_url, config.basescan_api_key
            )
        except RPCError as e:
            return jsonify({"error": f"RPC error: {e}"}), 502

        response_data: dict[str, object] = {
            "address": result.address,
            "score": result.score,
            "level": result.level.value,
            "bytecode_size": result.bytecode_size,
            "findings": [
                {
                    "detector": f.detector,
                    "severity": f.severity.value,
                    "title": f.title,
                    "description": f.description,
                    "points": f.points,
                }
                for f in result.findings
            ],
            "category_scores": result.category_scores,
        }

        if result.implementation is not None:
            impl = result.implementation
            response_data["implementation"] = {
                "address": impl.address,
                "bytecode_size": impl.bytecode_size,
                "findings": [
                    {
                        "detector": f.detector,
                        "severity": f.severity.value,
                        "title": f.title,
                        "description": f.description,
                        "points": f.points,
                    }
                    for f in impl.findings
                ],
                "category_scores": impl.category_scores,
            }

        return jsonify(response_data)

    return app
