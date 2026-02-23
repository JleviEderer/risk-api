"""Tests for deployer wallet reputation detector."""

import time

import responses

from risk_api.analysis.patterns import Severity
from risk_api.analysis.reputation import (
    BASESCAN_API,
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


def setup_function():
    clear_reputation_cache()


def teardown_function():
    clear_reputation_cache()


# --- get_contract_creator ---


@responses.activate
def test_get_contract_creator_success():
    responses.get(
        BASESCAN_API,
        json={
            "status": "1",
            "result": [
                {
                    "contractCreator": FAKE_DEPLOYER,
                    "txHash": FAKE_TX_HASH,
                }
            ],
        },
    )
    result = get_contract_creator(FAKE_ADDRESS, API_KEY)
    assert result == (FAKE_DEPLOYER, FAKE_TX_HASH)


@responses.activate
def test_get_contract_creator_not_found():
    responses.get(
        BASESCAN_API,
        json={"status": "0", "result": []},
    )
    assert get_contract_creator(FAKE_ADDRESS, API_KEY) is None


@responses.activate
def test_get_contract_creator_api_error():
    responses.get(BASESCAN_API, status=500)
    assert get_contract_creator(FAKE_ADDRESS, API_KEY) is None


# --- get_first_tx_timestamp ---


@responses.activate
def test_get_first_tx_timestamp_success():
    responses.get(
        BASESCAN_API,
        json={
            "status": "1",
            "result": [{"timeStamp": "1700000000"}],
        },
    )
    assert get_first_tx_timestamp(FAKE_DEPLOYER, API_KEY) == 1700000000


@responses.activate
def test_get_first_tx_timestamp_no_txs():
    responses.get(
        BASESCAN_API,
        json={"status": "0", "result": []},
    )
    assert get_first_tx_timestamp(FAKE_DEPLOYER, API_KEY) is None


# --- get_tx_count ---


@responses.activate
def test_get_tx_count_success():
    responses.get(
        BASESCAN_API,
        json={"result": "0x1a"},  # 26 in hex
    )
    assert get_tx_count(FAKE_DEPLOYER, API_KEY) == 26


@responses.activate
def test_get_tx_count_zero():
    responses.get(
        BASESCAN_API,
        json={"result": "0x0"},
    )
    assert get_tx_count(FAKE_DEPLOYER, API_KEY) == 0


@responses.activate
def test_get_tx_count_api_error():
    responses.get(BASESCAN_API, status=500)
    assert get_tx_count(FAKE_DEPLOYER, API_KEY) is None


# --- detect_deployer_reputation ---


def test_missing_api_key_returns_empty():
    """No API key → graceful skip, no findings."""
    findings = detect_deployer_reputation(FAKE_ADDRESS, "")
    assert findings == []


@responses.activate
def test_contract_not_found_returns_info():
    """Contract creator not found → 3pt INFO finding."""
    responses.get(
        BASESCAN_API,
        json={"status": "0", "result": []},
    )
    findings = detect_deployer_reputation(FAKE_ADDRESS, API_KEY)
    assert len(findings) == 1
    assert findings[0].detector == "deployer_reputation"
    assert findings[0].points == 3
    assert findings[0].severity == Severity.INFO


@responses.activate
def test_fresh_deployer_scores_points():
    """New wallet (<7 days) with few txs → two findings stacking up."""
    # get_contract_creator
    responses.get(
        BASESCAN_API,
        json={
            "status": "1",
            "result": [
                {"contractCreator": FAKE_DEPLOYER, "txHash": FAKE_TX_HASH}
            ],
        },
    )
    # get_first_tx_timestamp — 1 day ago
    responses.get(
        BASESCAN_API,
        json={
            "status": "1",
            "result": [{"timeStamp": str(int(time.time()) - 86400)}],
        },
    )
    # get_tx_count — 2 txs
    responses.get(
        BASESCAN_API,
        json={"result": "0x2"},
    )

    findings = detect_deployer_reputation(FAKE_ADDRESS, API_KEY)
    assert len(findings) == 2
    total_points = sum(f.points for f in findings)
    assert total_points == 10  # 5 (young) + 5 (low tx)
    assert all(f.detector == "deployer_reputation" for f in findings)


@responses.activate
def test_established_deployer_scores_zero():
    """Well-established deployer (>30 days, >20 txs) → no findings."""
    # get_contract_creator
    responses.get(
        BASESCAN_API,
        json={
            "status": "1",
            "result": [
                {"contractCreator": FAKE_DEPLOYER, "txHash": FAKE_TX_HASH}
            ],
        },
    )
    # get_first_tx_timestamp — 60 days ago
    responses.get(
        BASESCAN_API,
        json={
            "status": "1",
            "result": [{"timeStamp": str(int(time.time()) - 86400 * 60)}],
        },
    )
    # get_tx_count — 100 txs
    responses.get(
        BASESCAN_API,
        json={"result": "0x64"},
    )

    findings = detect_deployer_reputation(FAKE_ADDRESS, API_KEY)
    assert findings == []


@responses.activate
def test_api_failure_graceful():
    """All API calls fail → returns empty (no crash, no score impact)."""
    responses.get(BASESCAN_API, status=500)

    findings = detect_deployer_reputation(FAKE_ADDRESS, API_KEY)
    # Contract creator lookup fails → "not found" finding
    assert len(findings) == 1
    assert findings[0].points == 3


@responses.activate
def test_caching_works():
    """Second call with same args should use cache, not hit API again."""
    responses.get(
        BASESCAN_API,
        json={
            "status": "1",
            "result": [
                {"contractCreator": FAKE_DEPLOYER, "txHash": FAKE_TX_HASH}
            ],
        },
    )

    result1 = get_contract_creator(FAKE_ADDRESS, API_KEY)
    result2 = get_contract_creator(FAKE_ADDRESS, API_KEY)
    assert result1 == result2
    # Only 1 HTTP call should have been made
    assert len(responses.calls) == 1
