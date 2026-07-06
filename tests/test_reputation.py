"""Tests for deployer wallet reputation detector."""

import time
from typing import cast
from urllib.parse import parse_qs, urlparse

import pytest
import responses

import risk_api.analysis.reputation as reputation
from risk_api.analysis.patterns import Severity
from risk_api.analysis.reputation import (
    BLOCKSCOUT_API,
    CreatorLookupStatus,
    LOW_TX_COUNT,
    clear_reputation_cache,
    detect_deployer_reputation,
    get_contract_creator,
    get_first_tx_timestamp,
    get_tx_count,
)

FAKE_ADDRESS = "0x" + "ab" * 20
FAKE_DEPLOYER = "0x" + "cd" * 20
FAKE_TX_HASH = "0x" + "ee" * 32
API_KEY = "test-api-key"


@pytest.fixture(autouse=True)
def _clear_caches_and_disable_sleep(monkeypatch):
    clear_reputation_cache()
    monkeypatch.setattr(reputation, "REQUEST_INTERVAL_SECONDS", 0.0)
    monkeypatch.setattr(reputation, "RETRY_BACKOFF_SECONDS", 0.0)
    yield
    clear_reputation_cache()


def _last_call_params() -> dict[str, list[str]]:
    request_url = cast(str, responses.calls[-1].request.url)
    return parse_qs(urlparse(request_url).query)


# --- get_contract_creator ---


@responses.activate
def test_get_contract_creator_success():
    responses.get(
        BLOCKSCOUT_API,
        json={
            "status": "1",
            "message": "OK",
            "result": [
                {
                    "contractCreator": FAKE_DEPLOYER,
                    "txHash": FAKE_TX_HASH,
                }
            ],
        },
    )
    result = get_contract_creator(FAKE_ADDRESS, API_KEY)
    params = _last_call_params()
    assert result.status == CreatorLookupStatus.FOUND
    assert result.deployer == FAKE_DEPLOYER
    assert result.tx_hash == FAKE_TX_HASH
    assert params["module"] == ["contract"]
    assert params["action"] == ["getcontractcreation"]
    assert params["contractaddresses"] == [FAKE_ADDRESS]
    assert params["apikey"] == [API_KEY]


@responses.activate
def test_get_contract_creator_without_api_key_omits_key_param():
    responses.get(
        BLOCKSCOUT_API,
        json={
            "status": "1",
            "message": "OK",
            "result": [
                {
                    "contractCreator": FAKE_DEPLOYER,
                    "txHash": FAKE_TX_HASH,
                }
            ],
        },
    )
    result = get_contract_creator(FAKE_ADDRESS, "")
    params = _last_call_params()
    assert result.status == CreatorLookupStatus.FOUND
    assert "apikey" not in params


@responses.activate
def test_get_contract_creator_not_found():
    responses.get(
        BLOCKSCOUT_API,
        json={"status": "0", "message": "No data found", "result": []},
    )
    result = get_contract_creator(FAKE_ADDRESS, API_KEY)
    assert result.status == CreatorLookupStatus.NOT_FOUND


@responses.activate
def test_get_contract_creator_api_error():
    responses.get(BLOCKSCOUT_API, status=500)
    responses.get(BLOCKSCOUT_API, status=500)
    result = get_contract_creator(FAKE_ADDRESS, API_KEY)
    assert result.status == CreatorLookupStatus.ERROR
    assert len(responses.calls) == 2


@responses.activate
def test_get_contract_creator_soft_error_is_error():
    responses.get(
        BLOCKSCOUT_API,
        json={
            "status": "0",
            "message": "NOTOK",
            "result": "Invalid API Key",
        },
    )
    result = get_contract_creator(FAKE_ADDRESS, API_KEY)
    assert result.status == CreatorLookupStatus.ERROR


@responses.activate
def test_get_contract_creator_retries_on_rate_limit_then_succeeds():
    responses.get(
        BLOCKSCOUT_API,
        json={
            "status": "0",
            "message": "NOTOK",
            "result": "Rate limit exceeded",
        },
    )
    responses.get(
        BLOCKSCOUT_API,
        json={
            "status": "1",
            "message": "OK",
            "result": [
                {
                    "contractCreator": FAKE_DEPLOYER,
                    "txHash": FAKE_TX_HASH,
                }
            ],
        },
    )

    result = get_contract_creator(FAKE_ADDRESS, API_KEY)

    assert result.status == CreatorLookupStatus.FOUND
    assert result.deployer == FAKE_DEPLOYER
    assert len(responses.calls) == 2


@responses.activate
def test_get_contract_creator_soft_error_is_not_cached():
    responses.get(
        BLOCKSCOUT_API,
        json={
            "status": "0",
            "message": "NOTOK",
            "result": "Invalid API Key",
        },
    )
    responses.get(
        BLOCKSCOUT_API,
        json={
            "status": "1",
            "message": "OK",
            "result": [
                {
                    "contractCreator": FAKE_DEPLOYER,
                    "txHash": FAKE_TX_HASH,
                }
            ],
        },
    )

    result1 = get_contract_creator(FAKE_ADDRESS, API_KEY)
    result2 = get_contract_creator(FAKE_ADDRESS, API_KEY)

    assert result1.status == CreatorLookupStatus.ERROR
    assert result2.status == CreatorLookupStatus.FOUND
    assert len(responses.calls) == 2


# --- get_first_tx_timestamp ---


@responses.activate
def test_get_first_tx_timestamp_success():
    responses.get(
        BLOCKSCOUT_API,
        json={
            "status": "1",
            "message": "OK",
            "result": [{"timeStamp": "1700000000"}],
        },
    )
    assert get_first_tx_timestamp(FAKE_DEPLOYER, API_KEY) == 1700000000
    params = _last_call_params()
    assert params["module"] == ["account"]
    assert params["action"] == ["txlist"]
    assert params["sort"] == ["asc"]
    assert params["offset"] == ["1"]


@responses.activate
def test_get_first_tx_timestamp_no_txs():
    responses.get(
        BLOCKSCOUT_API,
        json={"status": "0", "message": "No transactions found", "result": []},
    )
    assert get_first_tx_timestamp(FAKE_DEPLOYER, API_KEY) is None


@responses.activate
def test_get_first_tx_timestamp_empty_ok_result():
    responses.get(
        BLOCKSCOUT_API,
        json={"status": "1", "message": "OK", "result": []},
    )
    assert get_first_tx_timestamp(FAKE_DEPLOYER, API_KEY) is None


@responses.activate
def test_get_first_tx_timestamp_retryable_soft_error_returns_none_after_retry():
    responses.get(
        BLOCKSCOUT_API,
        json={
            "status": "0",
            "message": "NOTOK",
            "result": "Timeout while processing request",
        },
    )
    responses.get(
        BLOCKSCOUT_API,
        json={
            "status": "0",
            "message": "NOTOK",
            "result": "Timeout while processing request",
        },
    )
    assert get_first_tx_timestamp(FAKE_DEPLOYER, API_KEY) is None
    assert len(responses.calls) == 2


# --- get_tx_count ---


@responses.activate
def test_get_tx_count_exact_low_count():
    responses.get(
        BLOCKSCOUT_API,
        json={
            "status": "1",
            "message": "OK",
            "result": [{"hash": f"0x{i}"} for i in range(4)],
        },
    )
    assert get_tx_count(FAKE_DEPLOYER, API_KEY) == 4
    params = _last_call_params()
    assert params["module"] == ["account"]
    assert params["action"] == ["txlist"]
    assert params["sort"] == ["desc"]
    assert params["offset"] == [str(LOW_TX_COUNT)]


@responses.activate
def test_get_tx_count_busy_wallet_clamps_at_threshold():
    responses.get(
        BLOCKSCOUT_API,
        json={
            "status": "1",
            "message": "OK",
            "result": [{"hash": f"0x{i}"} for i in range(LOW_TX_COUNT)],
        },
    )
    assert get_tx_count(FAKE_DEPLOYER, API_KEY) == LOW_TX_COUNT


@responses.activate
def test_get_tx_count_api_error():
    responses.get(BLOCKSCOUT_API, status=500)
    responses.get(BLOCKSCOUT_API, status=500)
    assert get_tx_count(FAKE_DEPLOYER, API_KEY) is None
    assert len(responses.calls) == 2


@responses.activate
def test_get_tx_count_soft_error_returns_none():
    responses.get(
        BLOCKSCOUT_API,
        json={
            "status": "0",
            "message": "Unknown module",
            "result": None,
        },
    )
    assert get_tx_count(FAKE_DEPLOYER, API_KEY) is None


# --- detect_deployer_reputation ---


@responses.activate
def test_missing_api_key_still_uses_public_blockscout():
    responses.get(
        BLOCKSCOUT_API,
        json={
            "status": "0",
            "message": "No data found",
            "result": [],
        },
    )
    findings = detect_deployer_reputation(FAKE_ADDRESS, "")
    assert len(findings) == 1
    assert findings[0].detector == "deployer_reputation"


@responses.activate
def test_contract_not_found_returns_info():
    responses.get(
        BLOCKSCOUT_API,
        json={"status": "0", "message": "No data found", "result": []},
    )
    findings = detect_deployer_reputation(FAKE_ADDRESS, API_KEY)
    assert len(findings) == 1
    assert findings[0].detector == "deployer_reputation"
    assert findings[0].points == 3
    assert findings[0].severity == Severity.INFO


@responses.activate
def test_fresh_deployer_scores_points():
    responses.get(
        BLOCKSCOUT_API,
        json={
            "status": "1",
            "message": "OK",
            "result": [
                {"contractCreator": FAKE_DEPLOYER, "txHash": FAKE_TX_HASH}
            ],
        },
    )
    responses.get(
        BLOCKSCOUT_API,
        json={
            "status": "1",
            "message": "OK",
            "result": [{"timeStamp": str(int(time.time()) - 86400)}],
        },
    )
    responses.get(
        BLOCKSCOUT_API,
        json={
            "status": "1",
            "message": "OK",
            "result": [{"hash": f"0x{i}"} for i in range(2)],
        },
    )

    findings = detect_deployer_reputation(FAKE_ADDRESS, API_KEY)
    assert len(findings) == 2
    total_points = sum(f.points for f in findings)
    assert total_points == 10
    assert all(f.detector == "deployer_reputation" for f in findings)


@responses.activate
def test_established_deployer_scores_zero():
    responses.get(
        BLOCKSCOUT_API,
        json={
            "status": "1",
            "message": "OK",
            "result": [
                {"contractCreator": FAKE_DEPLOYER, "txHash": FAKE_TX_HASH}
            ],
        },
    )
    responses.get(
        BLOCKSCOUT_API,
        json={
            "status": "1",
            "message": "OK",
            "result": [{"timeStamp": str(int(time.time()) - 86400 * 60)}],
        },
    )
    responses.get(
        BLOCKSCOUT_API,
        json={
            "status": "1",
            "message": "OK",
            "result": [{"hash": f"0x{i}"} for i in range(LOW_TX_COUNT)],
        },
    )

    findings = detect_deployer_reputation(FAKE_ADDRESS, API_KEY)
    assert findings == []


@responses.activate
def test_api_failure_graceful():
    responses.get(BLOCKSCOUT_API, status=500)
    responses.get(BLOCKSCOUT_API, status=500)

    findings = detect_deployer_reputation(FAKE_ADDRESS, API_KEY)
    assert findings == []


@responses.activate
def test_caching_works():
    responses.get(
        BLOCKSCOUT_API,
        json={
            "status": "1",
            "message": "OK",
            "result": [
                {"contractCreator": FAKE_DEPLOYER, "txHash": FAKE_TX_HASH}
            ],
        },
    )

    result1 = get_contract_creator(FAKE_ADDRESS, API_KEY)
    result2 = get_contract_creator(FAKE_ADDRESS, API_KEY)
    assert result1 == result2
    assert len(responses.calls) == 1
