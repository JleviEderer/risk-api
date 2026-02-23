"""Deployer wallet reputation scoring via Basescan API.

Checks deployer wallet age and transaction count. Fresh/inactive deployers
are a risk signal — scammers often use burner wallets.

Graceful degradation: if no API key or API fails, returns empty findings.
"""

from __future__ import annotations

import functools
import logging
import time

import requests

from risk_api.analysis.patterns import Finding, Severity

logger = logging.getLogger(__name__)

BASESCAN_API = "https://api.basescan.org/api"

# Thresholds
YOUNG_WALLET_DAYS = 7
LOW_TX_COUNT = 5


@functools.lru_cache(maxsize=256)
def get_contract_creator(
    address: str, api_key: str
) -> tuple[str, str] | None:
    """Get contract deployer address and creation tx hash from Basescan.

    Returns (deployer_address, tx_hash) or None on failure.
    """
    params = {
        "module": "contract",
        "action": "getcontractcreation",
        "contractaddresses": address,
        "apikey": api_key,
    }
    try:
        resp = requests.get(BASESCAN_API, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        logger.debug("Basescan contract creator lookup failed: %s", e)
        return None

    if data.get("status") != "1" or not data.get("result"):
        return None

    entry = data["result"][0]
    return (entry["contractCreator"], entry["txHash"])


@functools.lru_cache(maxsize=256)
def get_first_tx_timestamp(
    deployer: str, api_key: str
) -> int | None:
    """Get timestamp of deployer's first transaction (account age proxy).

    Returns Unix timestamp or None on failure.
    """
    params = {
        "module": "account",
        "action": "txlist",
        "address": deployer,
        "startblock": 0,
        "endblock": 99999999,
        "page": 1,
        "offset": 1,
        "sort": "asc",
        "apikey": api_key,
    }
    try:
        resp = requests.get(BASESCAN_API, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        logger.debug("Basescan txlist lookup failed: %s", e)
        return None

    if data.get("status") != "1" or not data.get("result"):
        return None

    return int(data["result"][0]["timeStamp"])


@functools.lru_cache(maxsize=256)
def get_tx_count(deployer: str, api_key: str) -> int | None:
    """Get total transaction count for deployer via eth_getTransactionCount.

    Returns count or None on failure.
    """
    params = {
        "module": "proxy",
        "action": "eth_getTransactionCount",
        "address": deployer,
        "tag": "latest",
        "apikey": api_key,
    }
    try:
        resp = requests.get(BASESCAN_API, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        logger.debug("Basescan tx count lookup failed: %s", e)
        return None

    result = data.get("result")
    if result is None:
        return None

    try:
        return int(result, 16)
    except (ValueError, TypeError):
        return None


def detect_deployer_reputation(
    address: str, api_key: str
) -> list[Finding]:
    """Check deployer wallet age and tx count. Returns findings.

    Graceful: returns empty list if API key is missing or API fails.
    """
    if not api_key:
        return []

    creator_info = get_contract_creator(address, api_key)
    if creator_info is None:
        return [
            Finding(
                detector="deployer_reputation",
                severity=Severity.INFO,
                title="Contract creator not found on Basescan",
                description=(
                    "Could not determine the deployer of this contract. "
                    "It may be very new or deployed via an unusual method."
                ),
                points=3,
            )
        ]

    deployer, _tx_hash = creator_info
    findings: list[Finding] = []

    # Check wallet age
    first_ts = get_first_tx_timestamp(deployer, api_key)
    if first_ts is not None:
        age_days = (int(time.time()) - first_ts) / 86400
        if age_days < YOUNG_WALLET_DAYS:
            findings.append(
                Finding(
                    detector="deployer_reputation",
                    severity=Severity.INFO,
                    title="Deployer wallet is very new",
                    description=(
                        f"Deployer {deployer[:10]}... is only "
                        f"{int(age_days)} days old. Fresh wallets deploying "
                        "contracts can be a scam signal."
                    ),
                    points=5,
                )
            )

    # Check tx count
    tx_count = get_tx_count(deployer, api_key)
    if tx_count is not None and tx_count < LOW_TX_COUNT:
        findings.append(
            Finding(
                detector="deployer_reputation",
                severity=Severity.INFO,
                title="Deployer wallet has very few transactions",
                description=(
                    f"Deployer {deployer[:10]}... has only {tx_count} "
                    "transactions. Low-activity wallets deploying contracts "
                    "can indicate disposable scam wallets."
                ),
                points=5,
            )
        )

    return findings


def clear_reputation_cache() -> None:
    """Clear all reputation LRU caches (for testing)."""
    get_contract_creator.cache_clear()
    get_first_tx_timestamp.cache_clear()
    get_tx_count.cache_clear()
