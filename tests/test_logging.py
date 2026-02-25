import json
import logging
import os
import tempfile

import pytest
import responses

from risk_api.app import create_app
from risk_api.chain.rpc import clear_cache
from risk_api.config import Config

RPC_URL = "https://mainnet.base.org"


def setup_function():
    clear_cache()


def teardown_function():
    clear_cache()


@pytest.fixture()
def log_dir():
    d = tempfile.mkdtemp()
    yield d
    # Clean up logger file handlers before deleting temp dir
    req_logger = logging.getLogger("risk_api.requests")
    for h in list(req_logger.handlers):
        if isinstance(h, logging.FileHandler):
            h.close()
            req_logger.removeHandler(h)
    # Now safe to delete on Windows
    for f in os.listdir(d):
        try:
            os.unlink(os.path.join(d, f))
        except OSError:
            pass
    try:
        os.rmdir(d)
    except OSError:
        pass


@pytest.fixture()
def test_config():
    return Config(
        wallet_address="0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891",
        base_rpc_url=RPC_URL,
        facilitator_url="https://x402.org/facilitator",
        network="eip155:84532",
        price="$0.10",
    )


@pytest.fixture()
def app_with_logging(test_config, log_dir, monkeypatch):
    log_path = os.path.join(log_dir, "requests.jsonl")
    monkeypatch.setenv("REQUEST_LOG_PATH", log_path)
    app = create_app(config=test_config, enable_x402=False)
    app.config["TESTING"] = True
    return app


@pytest.fixture()
def client_logged(app_with_logging):
    return app_with_logging.test_client()


@responses.activate
def test_analyze_request_is_logged(client_logged, app_with_logging):
    bytecode = "0x" + "6080604052" + "00" * 200
    responses.post(RPC_URL, json={"jsonrpc": "2.0", "id": 1, "result": bytecode})

    addr = "0x" + "ab" * 20
    resp = client_logged.get(f"/analyze?address={addr}")
    assert resp.status_code == 200

    log_path = app_with_logging.config["REQUEST_LOG_PATH"]
    with open(log_path) as f:
        lines = [l.strip() for l in f if l.strip()]

    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["address"] == addr
    assert entry["status"] == 200
    assert entry["paid"] is False
    assert entry["score"] == 0
    assert entry["level"] == "safe"
    assert entry["method"] == "GET"
    assert "ts" in entry
    assert isinstance(entry["duration_ms"], int)


@responses.activate
def test_failed_request_is_logged(client_logged, app_with_logging):
    resp = client_logged.get("/analyze?address=0xinvalid")
    assert resp.status_code == 422

    log_path = app_with_logging.config["REQUEST_LOG_PATH"]
    with open(log_path) as f:
        lines = [l.strip() for l in f if l.strip()]

    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["status"] == 422
    assert "score" not in entry


def test_health_not_logged(client_logged, app_with_logging):
    client_logged.get("/health")
    log_path = app_with_logging.config["REQUEST_LOG_PATH"]
    if os.path.exists(log_path):
        with open(log_path) as f:
            assert f.read().strip() == ""


@responses.activate
def test_stats_endpoint(client_logged, app_with_logging):
    bytecode = "0x" + "6080604052" + "00" * 200
    responses.post(RPC_URL, json={"jsonrpc": "2.0", "id": 1, "result": bytecode})
    responses.post(RPC_URL, json={"jsonrpc": "2.0", "id": 1, "result": bytecode})

    addr = "0x" + "ab" * 20
    client_logged.get(f"/analyze?address={addr}")
    client_logged.get(f"/analyze?address={addr}")

    resp = client_logged.get("/stats")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total_requests"] == 2
    assert data["paid_requests"] == 0
    assert len(data["recent"]) == 2


def test_stats_empty_when_no_requests(client_logged):
    resp = client_logged.get("/stats")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total_requests"] == 0


def test_stats_returns_501_without_log_path(test_config):
    app = create_app(config=test_config, enable_x402=False)
    app.config["TESTING"] = True
    client = app.test_client()
    resp = client.get("/stats")
    assert resp.status_code == 501


@responses.activate
def test_stats_includes_hourly_and_avg_duration(client_logged, app_with_logging):
    """Stats response includes avg_duration_ms and hourly buckets."""
    bytecode = "0x" + "6080604052" + "00" * 200
    responses.post(RPC_URL, json={"jsonrpc": "2.0", "id": 1, "result": bytecode})
    responses.post(RPC_URL, json={"jsonrpc": "2.0", "id": 1, "result": bytecode})

    addr = "0x" + "ab" * 20
    client_logged.get(f"/analyze?address={addr}")
    client_logged.get(f"/analyze?address={addr}")

    resp = client_logged.get("/stats")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "avg_duration_ms" in data
    assert isinstance(data["avg_duration_ms"], int)
    assert data["avg_duration_ms"] >= 0
    assert "hourly" in data
    assert isinstance(data["hourly"], list)
    assert len(data["hourly"]) >= 1
    bucket = data["hourly"][0]
    assert "hour" in bucket
    assert bucket["count"] == 2
    assert "avg_duration_ms" in bucket
