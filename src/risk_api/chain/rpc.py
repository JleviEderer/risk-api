"""Base chain RPC client using raw JSON-RPC via requests."""

from __future__ import annotations

import functools

import requests


class RPCError(Exception):
    """Raised when an RPC call fails."""

    def __init__(self, message: str, code: int | None = None):
        super().__init__(message)
        self.code = code


@functools.lru_cache(maxsize=256)
def get_code(address: str, rpc_url: str) -> str:
    """Fetch contract bytecode via eth_getCode.

    Returns hex string (with 0x prefix). Returns "0x" for EOAs.
    Raises RPCError on network/RPC failures.
    """
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getCode",
        "params": [address, "latest"],
        "id": 1,
    }

    try:
        resp = requests.post(rpc_url, json=payload, timeout=10)
        resp.raise_for_status()
    except (requests.RequestException, ConnectionError) as e:
        raise RPCError(f"RPC request failed: {e}") from e

    try:
        data = resp.json()
    except ValueError as e:
        raise RPCError(f"RPC returned invalid JSON: {e}") from e

    if "error" in data:
        err = data["error"]
        raise RPCError(
            f"RPC error: {err.get('message', 'unknown')}",
            code=err.get("code"),
        )

    result = data.get("result")
    if result is None:
        raise RPCError("RPC returned null result")

    return result


@functools.lru_cache(maxsize=256)
def get_storage_at(address: str, slot: str, rpc_url: str) -> str:
    """Fetch storage value via eth_getStorageAt.

    Returns hex string (with 0x prefix). Returns 0x0...0 for empty slots.
    Raises RPCError on network/RPC failures.
    """
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getStorageAt",
        "params": [address, slot, "latest"],
        "id": 1,
    }

    try:
        resp = requests.post(rpc_url, json=payload, timeout=10)
        resp.raise_for_status()
    except (requests.RequestException, ConnectionError) as e:
        raise RPCError(f"RPC request failed: {e}") from e

    try:
        data = resp.json()
    except ValueError as e:
        raise RPCError(f"RPC returned invalid JSON: {e}") from e

    if "error" in data:
        err = data["error"]
        raise RPCError(
            f"RPC error: {err.get('message', 'unknown')}",
            code=err.get("code"),
        )

    result = data.get("result")
    if result is None:
        raise RPCError("RPC returned null result")

    return result


def clear_cache() -> None:
    """Clear LRU caches (useful for testing)."""
    get_code.cache_clear()
    get_storage_at.cache_clear()
