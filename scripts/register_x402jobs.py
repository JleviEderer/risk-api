"""Register risk-api on x402.jobs marketplace.

Usage:
    python scripts/register_x402jobs.py <API_KEY>

Get an API key:
    1. Sign up at https://www.x402.jobs/signup
    2. Go to https://www.x402.jobs/dashboard/api-keys
    3. Create a key and pass it as the argument
"""

from __future__ import annotations

import sys

import httpx

API_BASE = "https://api.x402.jobs/api/v1"

RESOURCE = {
    "name": "Smart Contract Risk Scorer",
    "description": (
        "EVM smart contract risk scoring API on Base. "
        "Analyzes bytecode patterns (proxy detection, reentrancy, "
        "selfdestruct, honeypot, hidden mint, fee manipulation, "
        "delegatecall) and returns a composite 0-100 risk score with "
        "severity levels (safe/low/medium/high/critical). "
        "Pay $0.10/call via x402 in USDC on Base."
    ),
    "resourceUrl": "https://risk-api.life.conway.tech/analyze",
    "network": "base",
    "payTo": "0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891",
    "category": "api",
    "tags": [
        "security",
        "smart-contract",
        "risk-scoring",
        "evm",
        "base",
        "defi",
        "audit",
        "bytecode-analysis",
    ],
    "capabilities": [
        "contract risk scoring",
        "proxy detection",
        "bytecode analysis",
        "honeypot pattern detection",
        "reentrancy detection",
        "security assessment",
    ],
    "server_name": "risk-api",
}


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/register_x402jobs.py <API_KEY>")
        print("\nGet a key at: https://www.x402.jobs/dashboard/api-keys")
        sys.exit(1)

    api_key = sys.argv[1]

    print("Registering resource on x402.jobs...")
    print(f"  Name: {RESOURCE['name']}")
    print(f"  URL: {RESOURCE['resourceUrl']}")

    resp = httpx.post(
        f"{API_BASE}/resources",
        json=RESOURCE,
        headers={
            "x-api-key": api_key,
            "Content-Type": "application/json",
        },
        timeout=30,
    )

    if resp.status_code in (200, 201):
        data = resp.json()
        print(f"\nSUCCESS! Resource registered on x402.jobs")
        print(f"Response: {data}")
    else:
        print(f"\nERROR: {resp.status_code}")
        print(f"Response: {resp.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()
