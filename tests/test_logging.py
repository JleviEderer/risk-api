import json
import logging
import os
import sqlite3
import tempfile
from unittest.mock import patch

import pytest
import responses
from flask import request

from risk_api.analytics import PAID_RESPONSE_SNAPSHOT_MAX_BYTES, append_sqlite_entry
from risk_api.api_contract import analysis_result_from_snapshot
from risk_api.app import create_app
from risk_api.analysis.engine import clear_analysis_cache
from risk_api.analysis.reputation import BLOCKSCOUT_API, clear_reputation_cache
from risk_api.chain.rpc import clear_cache
from risk_api.config import Config

RPC_URL = "https://mainnet.base.org"


def setup_function():
    clear_cache()
    clear_analysis_cache()
    clear_reputation_cache()


def teardown_function():
    clear_cache()
    clear_analysis_cache()
    clear_reputation_cache()


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
    monkeypatch.delenv("ANALYTICS_DB_PATH", raising=False)
    monkeypatch.setenv("REQUEST_LOG_PATH", log_path)
    app = create_app(config=test_config, enable_x402=False)
    app.config["TESTING"] = True
    return app


@pytest.fixture()
def client_logged(app_with_logging):
    return app_with_logging.test_client()


@pytest.fixture()
def app_with_analytics_db(test_config, log_dir, monkeypatch):
    db_path = os.path.join(log_dir, "analytics.sqlite3")
    monkeypatch.delenv("REQUEST_LOG_PATH", raising=False)
    monkeypatch.setenv("ANALYTICS_DB_PATH", db_path)
    app = create_app(config=test_config, enable_x402=False)
    app.config["TESTING"] = True
    return app


@pytest.fixture()
def client_analytics(app_with_analytics_db):
    return app_with_analytics_db.test_client()


@responses.activate
def test_analyze_request_is_logged(client_logged, app_with_logging):
    bytecode = "0x" + "6080604052" + "00" * 200
    responses.post(RPC_URL, json={"jsonrpc": "2.0", "id": 1, "result": bytecode})
    responses.get(BLOCKSCOUT_API, status=500)
    responses.get(BLOCKSCOUT_API, status=500)

    addr = "0x" + "ab" * 20
    resp = client_logged.get(f"/analyze?address={addr}")
    assert resp.status_code == 200

    log_path = app_with_logging.config["REQUEST_LOG_PATH"]
    with open(log_path) as f:
        lines = [l.strip() for l in f if l.strip()]

    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["path"] == "/analyze"
    assert entry["address"] == addr
    assert entry["status"] == 200
    assert entry["paid"] is False
    assert entry["score"] == 0
    assert entry["level"] == "safe"
    assert entry["method"] == "GET"
    assert entry["funnel_stage"] == "analyze_success"
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
    assert entry["path"] == "/analyze"
    assert entry["status"] == 422
    assert entry["funnel_stage"] == "invalid_address"
    assert entry["error_type"] == "invalid_address"
    assert entry["traffic_class"] == "malformed_probe"
    assert "score" not in entry


def test_health_is_logged_as_health_check(client_logged, app_with_logging):
    client_logged.get("/health")
    log_path = app_with_logging.config["REQUEST_LOG_PATH"]
    with open(log_path) as f:
        lines = [l.strip() for l in f if l.strip()]

    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["path"] == "/health"
    assert entry["funnel_stage"] == "health_check"
    assert entry["traffic_class"] == "known_health_check"


def test_landing_view_is_logged(client_logged, app_with_logging):
    resp = client_logged.get("/")
    assert resp.status_code == 200

    log_path = app_with_logging.config["REQUEST_LOG_PATH"]
    with open(log_path) as f:
        lines = [l.strip() for l in f if l.strip()]

    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["path"] == "/"
    assert entry["status"] == 200
    assert entry["funnel_stage"] == "landing_view"
    assert "address" not in entry


@responses.activate
def test_no_bytecode_request_is_logged(client_logged, app_with_logging):
    responses.post(RPC_URL, json={"jsonrpc": "2.0", "id": 1, "result": "0x"})

    addr = "0x" + "cd" * 20
    resp = client_logged.get(f"/analyze?address={addr}")
    assert resp.status_code == 422

    log_path = app_with_logging.config["REQUEST_LOG_PATH"]
    with open(log_path) as f:
        lines = [l.strip() for l in f if l.strip()]

    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["status"] == 422
    assert entry["funnel_stage"] == "no_bytecode"
    assert entry["error_type"] == "no_bytecode"


def test_action_approve_logs_allowlisted_spender_trust(
    test_config, log_dir, monkeypatch
):
    log_path = os.path.join(log_dir, "requests.jsonl")
    monkeypatch.delenv("ANALYTICS_DB_PATH", raising=False)
    monkeypatch.setenv("REQUEST_LOG_PATH", log_path)

    addr = "0x" + "ab" * 20
    spender = "0x" + "12" * 20
    app = create_app(
        config=Config(
            wallet_address=test_config.wallet_address,
            base_rpc_url=test_config.base_rpc_url,
            facilitator_url=test_config.facilitator_url,
            network=test_config.network,
            price=test_config.price,
            approve_spender_allowlist=(spender.lower(),),
        ),
        enable_x402=False,
    )
    app.config["TESTING"] = True
    client = app.test_client()
    clean_result = analysis_result_from_snapshot(
        {
            "address": addr,
            "score": 0,
            "level": "safe",
            "decision": "allow",
            "recommended_policy": {
                "action": "allow",
                "summary": "Allow by default.",
                "reason_codes": [],
            },
            "bytecode_size": 4,
            "findings": [],
            "category_scores": {},
        }
    )

    with patch("risk_api.app.get_code", return_value="0x60006000"), patch(
        "risk_api.app.analyze_contract",
        return_value=clean_result,
    ):
        resp = client.get(f"/analyze?address={addr}&action=approve&spender={spender}")

    assert resp.status_code == 200

    with open(log_path, encoding="utf-8") as handle:
        lines = [line.strip() for line in handle if line.strip()]

    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["action"] == "approve"
    assert entry["spender"] == spender
    assert entry["action_spender_trust"] == "allowlisted"
    assert entry["action_decision"] == "allow"


def test_action_approve_logs_unchecked_spender_trust_without_allowlist(
    test_config, log_dir, monkeypatch
):
    log_path = os.path.join(log_dir, "requests.jsonl")
    monkeypatch.delenv("ANALYTICS_DB_PATH", raising=False)
    monkeypatch.setenv("REQUEST_LOG_PATH", log_path)

    addr = "0x" + "ab" * 20
    spender = "0x" + "12" * 20
    app = create_app(config=test_config, enable_x402=False)
    app.config["TESTING"] = True
    client = app.test_client()
    clean_result = analysis_result_from_snapshot(
        {
            "address": addr,
            "score": 0,
            "level": "safe",
            "decision": "allow",
            "recommended_policy": {
                "action": "allow",
                "summary": "Allow by default.",
                "reason_codes": [],
            },
            "bytecode_size": 4,
            "findings": [],
            "category_scores": {},
        }
    )

    with patch("risk_api.app.get_code", return_value="0x60006000"), patch(
        "risk_api.app.analyze_contract",
        return_value=clean_result,
    ):
        resp = client.get(f"/analyze?address={addr}&action=approve&spender={spender}")

    assert resp.status_code == 200

    with open(log_path, encoding="utf-8") as handle:
        lines = [line.strip() for line in handle if line.strip()]

    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["action"] == "approve"
    assert entry["spender"] == spender
    assert entry["action_spender_trust"] == "unchecked"
    assert entry["action_decision"] == "warn"


@responses.activate
def test_stats_endpoint(client_logged, app_with_logging):
    bytecode = "0x" + "6080604052" + "00" * 200
    responses.post(RPC_URL, json={"jsonrpc": "2.0", "id": 1, "result": bytecode})
    responses.post(RPC_URL, json={"jsonrpc": "2.0", "id": 1, "result": bytecode})

    addr = "0x" + "ab" * 20
    client_logged.get("/")
    client_logged.get(f"/analyze?address={addr}")
    client_logged.get(f"/analyze?address={addr}")

    resp = client_logged.get("/stats")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total_requests"] == 3
    assert data["paid_requests"] == 0
    assert data["storage_backend"] == "jsonl"
    assert data["storage_durable"] is False
    assert data["funnel"]["landing_views"] == 1
    assert data["funnel"]["paid_requests"] == 0
    assert data["traffic_classes"]["other_traffic"] == 3
    assert len(data["recent"]) == 3


def test_stats_empty_when_no_requests(client_logged):
    resp = client_logged.get("/stats")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total_requests"] == 0
    assert data["storage_backend"] == "jsonl"
    assert data["storage_durable"] is False
    assert data["funnel"]["landing_views"] == 0


def test_stats_ignores_malformed_jsonl_lines(test_config, monkeypatch, tmp_path):
    log_path = tmp_path / "requests.jsonl"
    monkeypatch.delenv("ANALYTICS_DB_PATH", raising=False)
    monkeypatch.setenv("REQUEST_LOG_PATH", str(log_path))
    log_path.write_text(
        '\n'.join(
            [
                'not-json',
                json.dumps(
                    {
                        "ts": "2026-03-30T12:00:00Z",
                        "path": "/",
                        "status": 200,
                        "paid": False,
                        "duration_ms": 12,
                        "user_agent": "pytest-agent",
                        "method": "GET",
                        "host": "augurrisk.com",
                        "referer": "",
                        "request_id": "req-stats-malformed",
                        "funnel_stage": "landing_view",
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    app = create_app(config=test_config, enable_x402=False)
    app.config["TESTING"] = True
    client = app.test_client()

    resp = client.get("/stats")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total_requests"] == 1
    assert data["funnel"]["landing_views"] == 1
    assert data["top_paths"] == [{"path": "/", "count": 1}]


def test_stats_returns_501_without_log_path(test_config, monkeypatch):
    monkeypatch.delenv("REQUEST_LOG_PATH", raising=False)
    monkeypatch.delenv("ANALYTICS_DB_PATH", raising=False)
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
    assert "landing_views" in bucket
    assert "valid_unpaid_402_attempts" in bucket
    assert "invalid_address_requests" in bucket
    assert "no_bytecode_requests" in bucket
    assert "paid_requests" in bucket
    assert "avg_duration_ms" in bucket


@responses.activate
def test_durable_analytics_db_persists_request_events(
    client_analytics, app_with_analytics_db
):
    bytecode = "0x" + "6080604052" + "00" * 200
    responses.post(RPC_URL, json={"jsonrpc": "2.0", "id": 1, "result": bytecode})

    addr = "0x" + "ab" * 20
    client_analytics.get("/")
    client_analytics.get(f"/analyze?address={addr}")

    db_path = app_with_analytics_db.config["ANALYTICS_DB_PATH"]
    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM request_events").fetchone()[0]

    assert count == 2

    data = client_analytics.get("/stats").get_json()
    assert data["total_requests"] == 2
    assert data["storage_backend"] == "sqlite"
    assert data["storage_durable"] is True
    assert data["funnel"]["landing_views"] == 1
    assert data["stage_counts"]["analyze_success"] == 1
    assert data["traffic_classes"]["other_traffic"] == 2
    assert data["recent"][-1]["path"] == "/analyze"


def test_paid_analyze_response_snapshot_is_persisted(app_with_analytics_db):
    addr = "0x" + "ab" * 20
    clean_result = analysis_result_from_snapshot(
        {
            "address": addr,
            "score": 0,
            "level": "safe",
            "decision": "allow",
            "recommended_policy": {
                "action": "allow",
                "summary": "Allow by default.",
                "reason_codes": [],
            },
            "bytecode_size": 4,
            "findings": [],
            "category_scores": {},
        }
    )

    @app_with_analytics_db.before_request
    def _mark_paid_for_test() -> None:
        if request.path == "/analyze":
            request.environ["x402_payload"] = {"test": "paid"}

    client = app_with_analytics_db.test_client()
    with patch("risk_api.app.get_code", return_value="0x60006000"), patch(
        "risk_api.app.analyze_contract",
        return_value=clean_result,
    ):
        resp = client.get(f"/analyze?address={addr}")

    assert resp.status_code == 200
    assert resp.get_json()["decision"] == "allow"

    db_path = app_with_analytics_db.config["ANALYTICS_DB_PATH"]
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT e.paid, e.funnel_stage, s.address, s.truncated, s.snapshot_json
            FROM request_events e
            JOIN paid_response_snapshots s ON s.request_event_id = e.id
            """
        ).fetchone()

    assert row is not None
    paid, funnel_stage, stored_address, truncated, snapshot_json = row
    assert paid == 1
    assert funnel_stage == "paid_request"
    assert stored_address == addr
    assert truncated == 0
    snapshot = json.loads(snapshot_json)
    assert snapshot["address"] == addr
    assert snapshot["score"] == 0
    assert snapshot["recommended_policy"]["action"] == "allow"
    assert "payment" not in snapshot


def test_non_paid_analyze_response_does_not_create_snapshot(
    client_analytics, app_with_analytics_db
):
    addr = "0x" + "ab" * 20
    clean_result = analysis_result_from_snapshot(
        {
            "address": addr,
            "score": 0,
            "level": "safe",
            "decision": "allow",
            "recommended_policy": {
                "action": "allow",
                "summary": "Allow by default.",
                "reason_codes": [],
            },
            "bytecode_size": 4,
            "findings": [],
            "category_scores": {},
        }
    )

    with patch("risk_api.app.get_code", return_value="0x60006000"), patch(
        "risk_api.app.analyze_contract",
        return_value=clean_result,
    ):
        resp = client_analytics.get(f"/analyze?address={addr}")

    assert resp.status_code == 200

    db_path = app_with_analytics_db.config["ANALYTICS_DB_PATH"]
    with sqlite3.connect(db_path) as conn:
        snapshot_count = conn.execute(
            "SELECT COUNT(*) FROM paid_response_snapshots"
        ).fetchone()[0]

    assert snapshot_count == 0


def test_sqlite_paid_response_snapshot_is_paid_only(app_with_analytics_db):
    db_path = app_with_analytics_db.config["ANALYTICS_DB_PATH"]
    entry = {
        "ts": "2026-07-07T12:00:00Z",
        "path": "/analyze",
        "status": 200,
        "paid": False,
        "duration_ms": 12,
        "user_agent": "pytest-agent",
        "method": "GET",
        "host": "augurrisk.com",
        "referer": "",
        "request_id": "req-unpaid-snapshot-test",
        "funnel_stage": "analyze_success",
        "address": "0x" + "ab" * 20,
    }

    assert append_sqlite_entry(
        db_path,
        entry,
        paid_response_snapshot={
            "address": entry["address"],
            "score": 0,
            "level": "safe",
        },
    ) is True

    with sqlite3.connect(db_path) as conn:
        snapshot_count = conn.execute(
            "SELECT COUNT(*) FROM paid_response_snapshots"
        ).fetchone()[0]

    assert snapshot_count == 0


def test_sqlite_paid_response_snapshot_is_bounded_and_redacted(
    app_with_analytics_db,
):
    db_path = app_with_analytics_db.config["ANALYTICS_DB_PATH"]
    addr = "0x" + "ab" * 20
    entry = {
        "ts": "2026-07-07T12:00:00Z",
        "path": "/analyze",
        "status": 200,
        "paid": True,
        "duration_ms": 12,
        "user_agent": "pytest-agent",
        "method": "GET",
        "host": "augurrisk.com",
        "referer": "",
        "request_id": "req-paid-snapshot-bound-test",
        "funnel_stage": "paid_request",
        "address": addr,
    }
    max_bytes = 512
    secret = "secret-payment-signature"

    assert append_sqlite_entry(
        db_path,
        entry,
        paid_response_snapshot={
            "address": addr,
            "score": 0,
            "level": "safe",
            "payment_signature": secret,
            "payer_wallet": "0x" + "12" * 20,
            "findings": [{"description": "x" * PAID_RESPONSE_SNAPSHOT_MAX_BYTES}],
        },
        paid_response_max_bytes=max_bytes,
    ) is True

    with sqlite3.connect(db_path) as conn:
        response_bytes, truncated, snapshot_json = conn.execute(
            """
            SELECT response_bytes, truncated, snapshot_json
            FROM paid_response_snapshots
            """
        ).fetchone()

    assert response_bytes > max_bytes
    assert truncated == 1
    assert len(snapshot_json.encode("utf-8")) <= max_bytes
    assert secret not in snapshot_json
    assert "secret" not in snapshot_json
    snapshot = json.loads(snapshot_json)
    assert snapshot["truncated"] is True
    assert snapshot["original_size_bytes"] == response_bytes


def test_sqlite_stats_remains_compatible_with_paid_response_snapshots(
    client_analytics, app_with_analytics_db
):
    db_path = app_with_analytics_db.config["ANALYTICS_DB_PATH"]
    addr = "0x" + "ab" * 20
    entry = {
        "ts": "2026-07-07T12:00:00Z",
        "path": "/analyze",
        "status": 200,
        "paid": True,
        "duration_ms": 12,
        "user_agent": "pytest-agent",
        "method": "GET",
        "host": "augurrisk.com",
        "referer": "",
        "request_id": "req-paid-snapshot-stats-test",
        "funnel_stage": "paid_request",
        "address": addr,
    }

    assert append_sqlite_entry(
        db_path,
        entry,
        paid_response_snapshot={
            "address": addr,
            "score": 0,
            "level": "safe",
        },
    ) is True

    data = client_analytics.get("/stats").get_json()

    assert data["total_requests"] == 1
    assert data["paid_requests"] == 1
    assert data["funnel"]["paid_requests"] == 1
    assert data["traffic_classes"]["paid_request"] == 1
    assert "paid_response_snapshot" not in data["recent"][0]
    assert "snapshot_json" not in data["recent"][0]


def test_stats_empty_when_only_durable_analytics_is_configured(client_analytics):
    resp = client_analytics.get("/stats")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total_requests"] == 0
    assert data["storage_backend"] == "sqlite"
    assert data["storage_durable"] is True
    assert data["funnel"]["landing_views"] == 0


def test_sqlite_analytics_persists_traffic_class(app_with_analytics_db):
    db_path = app_with_analytics_db.config["ANALYTICS_DB_PATH"]
    entry = {
        "ts": "2026-04-10T12:00:00Z",
        "path": "/analyze",
        "status": 422,
        "paid": False,
        "duration_ms": 12,
        "user_agent": "pytest-agent",
        "method": "GET",
        "host": "augurrisk.com",
        "referer": "",
        "request_id": "req-traffic-class-test",
        "funnel_stage": "invalid_address",
    }

    assert append_sqlite_entry(db_path, entry) is True

    with sqlite3.connect(db_path) as conn:
        traffic_class = conn.execute(
            "SELECT traffic_class FROM request_events"
        ).fetchone()[0]

    assert traffic_class == "malformed_probe"


def test_sqlite_stats_classifies_rows_without_stored_traffic_class(
    client_analytics, app_with_analytics_db
):
    db_path = app_with_analytics_db.config["ANALYTICS_DB_PATH"]
    entry = {
        "ts": "2026-04-10T12:00:00Z",
        "path": "/health",
        "status": 200,
        "paid": False,
        "duration_ms": 8,
        "user_agent": "Better Stack",
        "method": "GET",
        "host": "augurrisk.com",
        "referer": "",
        "request_id": "req-old-traffic-class-test",
        "funnel_stage": "health_check",
    }
    assert append_sqlite_entry(db_path, entry) is True

    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE request_events SET traffic_class = NULL")

    data = client_analytics.get("/stats").get_json()

    assert data["total_requests"] == 1
    assert data["traffic_classes"]["known_health_check"] == 1
    assert data["recent"][0]["traffic_class"] == "known_health_check"


def test_sqlite_analytics_ignores_duplicate_entries(app_with_analytics_db):
    db_path = app_with_analytics_db.config["ANALYTICS_DB_PATH"]
    entry = {
        "ts": "2026-03-09T12:00:00Z",
        "path": "/",
        "status": 200,
        "paid": False,
        "duration_ms": 12,
        "user_agent": "pytest-agent",
        "method": "GET",
        "host": "augurrisk.com",
        "referer": "",
        "request_id": "req-duplicate-test",
        "funnel_stage": "landing_view",
    }

    assert append_sqlite_entry(db_path, entry) is True
    assert append_sqlite_entry(db_path, entry) is False

    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM request_events").fetchone()[0]

    assert count == 1
