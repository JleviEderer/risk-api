"""Deployer wallet reputation scoring via Base Blockscout.

Checks deployer wallet age and transaction count. Fresh/inactive deployers
are a risk signal - scammers often use burner wallets.

Graceful degradation: if the explorer fails, returns empty findings.
"""

from __future__ import annotations

import functools
import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum

import requests

from risk_api.analysis.patterns import Finding, Severity

logger = logging.getLogger(__name__)

BLOCKSCOUT_API = "https://base.blockscout.com/api"
REQUEST_TIMEOUT_SECONDS = 10
REQUEST_INTERVAL_SECONDS = 0.25
RETRY_BACKOFF_SECONDS = 0.5
MAX_REQUEST_ATTEMPTS = 2

# Thresholds
YOUNG_WALLET_DAYS = 7
LOW_TX_COUNT = 5


class CreatorLookupStatus(str, Enum):
    FOUND = "found"
    NOT_FOUND = "not_found"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class CreatorLookupResult:
    status: CreatorLookupStatus
    deployer: str = ""
    tx_hash: str = ""


_creator_cache: dict[tuple[str, str], CreatorLookupResult] = {}
_CREATOR_CACHE_MAX_SIZE = 256
_request_lock = threading.Lock()
_last_request_started_at = 0.0


def _normalize_text(value: object) -> str:
    return str(value).strip().lower()


def _looks_like_blockscout_not_found(data: object) -> bool:
    """Return True when the body indicates missing data rather than an API failure."""
    if not isinstance(data, dict):
        return False

    status = _normalize_text(data.get("status", ""))
    if status == "1":
        return False

    message = _normalize_text(data.get("message", ""))
    result = data.get("result")
    result_text = _normalize_text(result) if isinstance(result, str) else ""

    if isinstance(result, list) and not result:
        return True

    not_found_markers = (
        "no data found",
        "no records found",
        "no transactions found",
        "not found",
    )
    return any(marker in message or marker in result_text for marker in not_found_markers)


def _looks_like_blockscout_retryable_soft_error(data: object) -> bool:
    """Return True when the body indicates a temporary Blockscout-side failure."""
    if not isinstance(data, dict):
        return False

    status = _normalize_text(data.get("status", ""))
    if status == "1":
        return False

    message = _normalize_text(data.get("message", ""))
    result = data.get("result")
    result_text = _normalize_text(result) if isinstance(result, str) else ""
    combined = f"{message} {result_text}"

    retryable_markers = (
        "rate limit",
        "too many requests",
        "temporarily unavailable",
        "timeout",
        "server too busy",
    )
    return any(marker in combined for marker in retryable_markers)


def _looks_like_blockscout_soft_error(data: object) -> bool:
    """Return True when a 200 response body still indicates an API-side failure."""
    if not isinstance(data, dict):
        return True

    if _looks_like_blockscout_not_found(data):
        return False

    status = _normalize_text(data.get("status", ""))
    if status == "1":
        return False

    message = _normalize_text(data.get("message", ""))
    result = data.get("result")
    result_text = _normalize_text(result) if isinstance(result, str) else ""
    error_markers = (
        "notok",
        "invalid api key",
        "missing api key",
        "unknown module",
        "unknown action",
        "error",
        "invalid value",
    )
    return any(marker in message or marker in result_text for marker in error_markers)


def _throttle_blockscout_requests() -> None:
    global _last_request_started_at
    with _request_lock:
        now = time.monotonic()
        sleep_for = REQUEST_INTERVAL_SECONDS - (now - _last_request_started_at)
        if sleep_for > 0:
            time.sleep(sleep_for)
            now = time.monotonic()
        _last_request_started_at = now


def _blockscout_get(params: dict[str, object], api_key: str) -> dict[str, object] | None:
    request_params = dict(params)
    if api_key:
        request_params["apikey"] = api_key

    backoff_seconds = RETRY_BACKOFF_SECONDS

    for attempt in range(MAX_REQUEST_ATTEMPTS):
        _throttle_blockscout_requests()
        try:
            resp = requests.get(
                BLOCKSCOUT_API,
                params=request_params,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            if resp.status_code in {429, 500, 502, 503, 504}:
                raise requests.HTTPError(
                    f"Blockscout returned retryable status {resp.status_code}",
                    response=resp,
                )
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError) as e:
            logger.debug("Blockscout request failed: %s", e)
            if attempt + 1 >= MAX_REQUEST_ATTEMPTS:
                return None
            time.sleep(backoff_seconds)
            backoff_seconds *= 2
            continue

        if _looks_like_blockscout_retryable_soft_error(data):
            logger.debug("Blockscout request returned retryable soft error: %s", data)
            if attempt + 1 >= MAX_REQUEST_ATTEMPTS:
                return data
            time.sleep(backoff_seconds)
            backoff_seconds *= 2
            continue

        return data

    return None


def get_contract_creator(
    address: str, api_key: str
) -> CreatorLookupResult:
    """Get contract deployer address and creation tx hash from Blockscout."""
    key = (address.lower(), api_key)
    cached = _creator_cache.get(key)
    if cached is not None:
        return cached

    params = {
        "module": "contract",
        "action": "getcontractcreation",
        "contractaddresses": address,
    }
    data = _blockscout_get(params, api_key)
    if data is None:
        logger.debug("Blockscout contract creator lookup failed for %s", address)
        return CreatorLookupResult(CreatorLookupStatus.ERROR)

    result_list = data.get("result")
    if isinstance(result_list, list) and result_list:
        entry = result_list[0]
        result = CreatorLookupResult(
            status=CreatorLookupStatus.FOUND,
            deployer=entry["contractCreator"],
            tx_hash=entry["txHash"],
        )
        _creator_cache_put(key, result)
        return result

    if _looks_like_blockscout_not_found(data):
        result = CreatorLookupResult(CreatorLookupStatus.NOT_FOUND)
        _creator_cache_put(key, result)
        return result

    if _looks_like_blockscout_soft_error(data):
        logger.debug("Blockscout contract creator lookup returned soft error: %s", data)
        return CreatorLookupResult(CreatorLookupStatus.ERROR)

    return CreatorLookupResult(CreatorLookupStatus.ERROR)


def _creator_cache_put(
    key: tuple[str, str], result: CreatorLookupResult
) -> None:
    """Cache only stable creator lookup outcomes."""
    if len(_creator_cache) >= _CREATOR_CACHE_MAX_SIZE:
        oldest_key = next(iter(_creator_cache))
        del _creator_cache[oldest_key]
    _creator_cache[key] = result


@functools.lru_cache(maxsize=256)
def get_first_tx_timestamp(
    deployer: str, api_key: str
) -> int | None:
    """Get timestamp of deployer's first transaction (account age proxy)."""
    params = {
        "module": "account",
        "action": "txlist",
        "address": deployer,
        "startblock": 0,
        "endblock": 99999999,
        "page": 1,
        "offset": 1,
        "sort": "asc",
    }
    data = _blockscout_get(params, api_key)
    if data is None:
        logger.debug("Blockscout txlist lookup failed for %s", deployer)
        return None

    if _looks_like_blockscout_soft_error(data):
        logger.debug("Blockscout txlist lookup returned soft error: %s", data)
        return None

    if not data.get("result"):
        return None

    try:
        return int(data["result"][0]["timeStamp"])
    except (KeyError, TypeError, ValueError):
        return None


@functools.lru_cache(maxsize=256)
def get_tx_count(deployer: str, api_key: str) -> int | None:
    """Return an exact low-tx count or LOW_TX_COUNT when the wallet is busier."""
    params = {
        "module": "account",
        "action": "txlist",
        "address": deployer,
        "startblock": 0,
        "endblock": 99999999,
        "page": 1,
        "offset": LOW_TX_COUNT,
        "sort": "desc",
    }
    data = _blockscout_get(params, api_key)
    if data is None:
        logger.debug("Blockscout tx-count probe failed for %s", deployer)
        return None

    if _looks_like_blockscout_soft_error(data):
        logger.debug("Blockscout tx-count probe returned soft error: %s", data)
        return None

    result = data.get("result")
    if not isinstance(result, list):
        return None

    return min(len(result), LOW_TX_COUNT)


def detect_deployer_reputation(
    address: str, api_key: str
) -> list[Finding]:
    """Check deployer wallet age and tx count. Returns findings."""
    creator_info = get_contract_creator(address, api_key)
    if creator_info.status == CreatorLookupStatus.ERROR:
        return []

    if creator_info.status == CreatorLookupStatus.NOT_FOUND:
        return [
            Finding(
                detector="deployer_reputation",
                severity=Severity.INFO,
                title="Contract creator not found in Base explorer data",
                description=(
                    "Could not determine the deployer of this contract. "
                    "It may be very new or deployed via an unusual method."
                ),
                points=3,
            )
        ]

    deployer = creator_info.deployer
    findings: list[Finding] = []

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
    """Clear all reputation caches (for testing)."""
    global _last_request_started_at
    _creator_cache.clear()
    get_first_tx_timestamp.cache_clear()
    get_tx_count.cache_clear()
    _last_request_started_at = 0.0
