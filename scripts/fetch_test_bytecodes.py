#!/usr/bin/env python3
"""One-time script to fetch real contract bytecodes from Base mainnet.

Usage: python scripts/fetch_test_bytecodes.py

Fetches bytecodes for well-known contracts and prints them.
Useful for updating test fixtures with real-world data.
"""

from __future__ import annotations

import json
import sys

import requests

RPC_URL = "https://mainnet.base.org"

# Well-known contracts on Base
CONTRACTS = {
    "USDC_PROXY": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "WETH": "0x4200000000000000000000000000000000000006",
}


def fetch_code(address: str) -> str:
    """Fetch bytecode via eth_getCode."""
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getCode",
        "params": [address, "latest"],
        "id": 1,
    }
    resp = requests.post(RPC_URL, json=payload, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        print(f"  RPC error: {data['error']}", file=sys.stderr)
        return ""
    return data.get("result", "")


def main() -> None:
    for name, address in CONTRACTS.items():
        print(f"\n# {name} ({address})")
        code = fetch_code(address)
        if code and code != "0x":
            bytecode_len = (len(code) - 2) // 2
            print(f"# Bytecode length: {bytecode_len} bytes")
            print(f'{name} = "{code}"')
        else:
            print(f"# No bytecode (EOA or empty)")
            print(f'{name} = "0x"')


if __name__ == "__main__":
    main()
