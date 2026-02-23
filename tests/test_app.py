import pytest
import responses

from risk_api.chain.rpc import clear_cache


RPC_URL = "https://mainnet.base.org"


def setup_function():
    clear_cache()


def teardown_function():
    clear_cache()


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


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
