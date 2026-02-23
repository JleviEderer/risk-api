import pytest

from risk_api.app import create_app
from risk_api.config import Config


@pytest.fixture()
def test_config():
    return Config(
        wallet_address="0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891",
        base_rpc_url="https://mainnet.base.org",
        facilitator_url="https://x402.org/facilitator",
        network="eip155:84532",
        price="$0.01",
    )


@pytest.fixture()
def app(test_config):
    """App without x402 middleware — for testing route logic."""
    app = create_app(config=test_config, enable_x402=False)
    app.config["TESTING"] = True
    return app


@pytest.fixture()
def app_with_x402(test_config):
    """App with x402 middleware enabled — for testing payment gate."""
    app = create_app(config=test_config, enable_x402=True)
    app.config["TESTING"] = True
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def client_with_x402(app_with_x402):
    return app_with_x402.test_client()
