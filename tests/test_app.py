import pytest
import responses

from risk_api.analysis.engine import clear_analysis_cache
from risk_api.chain.rpc import clear_cache


RPC_URL = "https://mainnet.base.org"


def setup_function():
    clear_cache()
    clear_analysis_cache()


def teardown_function():
    clear_cache()
    clear_analysis_cache()


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_x402_verification_endpoint(client):
    resp = client.get("/.well-known/x402-verification.json")
    assert resp.status_code == 200
    assert resp.get_json() == {"x402": "64cb3a6a29bb"}


def test_x402_verification_not_behind_paywall(client_with_x402):
    resp = client_with_x402.get("/.well-known/x402-verification.json")
    assert resp.status_code == 200
    assert resp.get_json()["x402"] == "64cb3a6a29bb"


def test_missing_address(client):
    resp = client.get("/analyze")
    assert resp.status_code == 422
    data = resp.get_json()
    assert "Missing" in data["error"]


def test_invalid_address_too_short(client):
    resp = client.get("/analyze?address=0x1234")
    assert resp.status_code == 422
    data = resp.get_json()
    assert "Invalid" in data["error"]


def test_invalid_address_no_prefix(client):
    resp = client.get(f"/analyze?address={'ab' * 20}")
    assert resp.status_code == 422


def test_invalid_address_bad_chars(client):
    resp = client.get(f"/analyze?address=0x{'zz' * 20}")
    assert resp.status_code == 422


@responses.activate
def test_analyze_success(client):
    bytecode = "0x" + "6080604052" + "00" * 200
    responses.post(
        RPC_URL,
        json={"jsonrpc": "2.0", "id": 1, "result": bytecode},
    )
    addr = "0x" + "ab" * 20
    resp = client.get(f"/analyze?address={addr}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["address"] == addr
    assert data["score"] == 0
    assert data["level"] == "safe"
    assert isinstance(data["findings"], list)
    assert isinstance(data["category_scores"], dict)


@responses.activate
def test_analyze_rpc_error(client):
    responses.post(
        RPC_URL,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32000, "message": "server busy"},
        },
    )
    addr = "0x" + "cd" * 20
    resp = client.get(f"/analyze?address={addr}")
    assert resp.status_code == 502
    data = resp.get_json()
    assert "RPC error" in data["error"]


@responses.activate
def test_analyze_with_findings(client):
    # Bytecode with SELFDESTRUCT
    bytecode = "0x" + "ff" + "00" * 200
    responses.post(
        RPC_URL,
        json={"jsonrpc": "2.0", "id": 1, "result": bytecode},
    )
    addr = "0x" + "ef" * 20
    resp = client.get(f"/analyze?address={addr}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["score"] >= 30
    assert len(data["findings"]) > 0
    assert data["findings"][0]["detector"] == "selfdestruct"


def test_x402_returns_402_without_payment(client_with_x402):
    """With x402 middleware enabled, /analyze should return 402 without payment."""
    addr = "0x" + "ab" * 20
    resp = client_with_x402.get(f"/analyze?address={addr}")
    assert resp.status_code == 402


def test_x402_health_not_gated(client_with_x402):
    """/health should NOT be behind the payment gate."""
    resp = client_with_x402.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_agent_metadata_endpoint(client):
    resp = client.get("/agent-metadata.json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["type"] == "https://eips.ethereum.org/EIPS/eip-8004#registration-v1"
    assert data["name"] == "Smart Contract Risk Scorer"
    assert data["x402Support"] is True
    assert data["active"] is True
    assert len(data["services"]) == 1
    assert data["services"][0]["name"] == "web"
    assert "registrations" not in data
    # New discovery fields
    assert "/avatar.png" in data["image"]
    assert isinstance(data["updatedAt"], int)
    assert data["updatedAt"] > 0
    assert data["pricing"] == {
        "amount": "0.10",
        "currency": "USDC",
        "network": "eip155:8453",
    }
    assert "/openapi.json" in data["openapi_url"]
    assert isinstance(data["capabilities"], list)
    assert "contract risk scoring" in data["capabilities"]
    assert "proxy detection" in data["capabilities"]


def test_agent_metadata_uses_public_url(app):
    app.config["PUBLIC_URL"] = "https://risk-api.life.conway.tech"
    with app.test_client() as c:
        resp = c.get("/agent-metadata.json")
        data = resp.get_json()
        assert data["services"][0]["endpoint"] == "https://risk-api.life.conway.tech/"


def test_agent_metadata_falls_back_to_request_url(client):
    resp = client.get("/agent-metadata.json")
    data = resp.get_json()
    endpoint = data["services"][0]["endpoint"]
    assert "localhost" in endpoint or "127.0.0.1" in endpoint


def test_agent_metadata_with_agent_id(app):
    app.config["ERC8004_AGENT_ID"] = 12345
    with app.test_client() as c:
        resp = c.get("/agent-metadata.json")
        data = resp.get_json()
        assert "registrations" in data
        assert data["registrations"][0]["agentId"] == 12345


def test_agent_metadata_not_behind_paywall(client_with_x402):
    resp = client_with_x402.get("/agent-metadata.json")
    assert resp.status_code == 200
    assert resp.get_json()["x402Support"] is True


@responses.activate
def test_analyze_proxy_response_includes_implementation(client):
    """API response includes implementation object for proxy contracts."""
    eip1967 = "360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
    proxy_bytecode = "0x7f" + eip1967 + "f4" + "00" * 200

    impl_addr_hex = "ab" * 20
    impl_addr_padded = "0x" + "0" * 24 + impl_addr_hex
    impl_bytecode = "0x" + "ff" + "00" * 200  # SELFDESTRUCT

    # get_code for proxy
    responses.post(RPC_URL, json={"jsonrpc": "2.0", "id": 1, "result": proxy_bytecode})
    # storage slot returns impl address
    responses.post(RPC_URL, json={"jsonrpc": "2.0", "id": 1, "result": impl_addr_padded})
    # get_code for implementation
    responses.post(RPC_URL, json={"jsonrpc": "2.0", "id": 1, "result": impl_bytecode})

    addr = "0x" + "ee" * 20
    resp = client.get(f"/analyze?address={addr}")
    assert resp.status_code == 200
    data = resp.get_json()

    assert "implementation" in data
    impl = data["implementation"]
    assert impl["address"] == "0x" + impl_addr_hex
    assert impl["bytecode_size"] > 0
    assert isinstance(impl["findings"], list)
    assert isinstance(impl["category_scores"], dict)


@responses.activate
def test_analyze_non_proxy_no_implementation_key(client):
    """Non-proxy contracts should NOT have implementation key."""
    bytecode = "0x" + "6080604052" + "00" * 200
    responses.post(RPC_URL, json={"jsonrpc": "2.0", "id": 1, "result": bytecode})

    addr = "0x" + "dd" * 20
    resp = client.get(f"/analyze?address={addr}")
    assert resp.status_code == 200
    data = resp.get_json()

    assert "implementation" not in data


@responses.activate
def test_analyze_post_with_json_body(client):
    """POST /analyze with address in JSON body should work."""
    bytecode = "0x" + "6080604052" + "00" * 200
    responses.post(
        RPC_URL,
        json={"jsonrpc": "2.0", "id": 1, "result": bytecode},
    )
    addr = "0x" + "ab" * 20
    resp = client.post("/analyze", json={"address": addr})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["address"] == addr
    assert data["score"] == 0


@responses.activate
def test_analyze_post_with_query_param(client):
    """POST /analyze with address in query param should also work."""
    bytecode = "0x" + "6080604052" + "00" * 200
    responses.post(
        RPC_URL,
        json={"jsonrpc": "2.0", "id": 1, "result": bytecode},
    )
    addr = "0x" + "ab" * 20
    resp = client.post(f"/analyze?address={addr}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["address"] == addr


def test_analyze_post_missing_address(client):
    """POST /analyze with no address should return 422."""
    resp = client.post("/analyze", json={})
    assert resp.status_code == 422


def test_x402_post_returns_402_without_payment(client_with_x402):
    """POST /analyze should also be behind x402 paywall."""
    addr = "0x" + "ab" * 20
    resp = client_with_x402.post("/analyze", json={"address": addr})
    assert resp.status_code == 402


def test_dashboard_returns_html(client):
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert resp.content_type.startswith("text/html")
    assert b"risk-api" in resp.data
    assert b"<canvas" in resp.data


def test_dashboard_not_behind_paywall(client_with_x402):
    resp = client_with_x402.get("/dashboard")
    assert resp.status_code == 200
    assert resp.content_type.startswith("text/html")


def test_avatar_returns_png(client):
    resp = client.get("/avatar.png")
    assert resp.status_code == 200
    assert resp.content_type == "image/png"
    # PNG magic bytes
    assert resp.data[:4] == b"\x89PNG"


def test_avatar_not_behind_paywall(client_with_x402):
    resp = client_with_x402.get("/avatar.png")
    assert resp.status_code == 200
    assert resp.content_type == "image/png"


def test_openapi_returns_valid_json(client):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["openapi"] == "3.0.3"
    assert data["info"]["title"] == "Smart Contract Risk Scorer"
    assert "/analyze" in data["paths"]
    assert "servers" in data
    assert "get" in data["paths"]["/analyze"]
    assert "post" in data["paths"]["/analyze"]


def test_openapi_uses_public_url(app):
    app.config["PUBLIC_URL"] = "https://risk-api.life.conway.tech"
    with app.test_client() as c:
        resp = c.get("/openapi.json")
        data = resp.get_json()
        assert data["servers"][0]["url"] == "https://risk-api.life.conway.tech"


def test_openapi_not_behind_paywall(client_with_x402):
    resp = client_with_x402.get("/openapi.json")
    assert resp.status_code == 200
    assert "openapi" in resp.get_json()


def test_ai_plugin_json_endpoint(client):
    resp = client.get("/.well-known/ai-plugin.json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["schema_version"] == "v1"
    assert data["name_for_model"] == "smart_contract_risk_scorer"
    assert data["auth"] == {"type": "none"}
    assert data["api"]["type"] == "openapi"
    assert "/openapi.json" in data["api"]["url"]


def test_ai_plugin_uses_public_url(app):
    app.config["PUBLIC_URL"] = "https://risk-api.life.conway.tech"
    with app.test_client() as c:
        resp = c.get("/.well-known/ai-plugin.json")
        data = resp.get_json()
        assert data["api"]["url"] == "https://risk-api.life.conway.tech/openapi.json"


def test_ai_plugin_not_behind_paywall(client_with_x402):
    resp = client_with_x402.get("/.well-known/ai-plugin.json")
    assert resp.status_code == 200
    assert resp.get_json()["schema_version"] == "v1"
