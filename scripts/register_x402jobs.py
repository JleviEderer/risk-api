"""Register risk-api on x402.jobs marketplace.

Usage:
    python scripts/register_x402jobs.py [API_KEY]

    If API_KEY is not provided, reads from X402_JOBS_API_KEY in .env file.

Get an API key:
    1. Sign up at https://www.x402.jobs/signup
    2. Go to https://www.x402.jobs/dashboard/api-keys
    3. Create a key and either pass it as argument or add to .env
"""

from __future__ import annotations

import os
import sys

import httpx
from dotenv import load_dotenv

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
    # Include default address (WETH) so x402.jobs "Run" button works out of box.
    # Real agents construct their own URL with their target address.
    "resourceUrl": "https://risk-api.life.conway.tech/analyze?address=0x4200000000000000000000000000000000000006",
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
    load_dotenv()

    api_key = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("X402_JOBS_API_KEY")

    if not api_key:
        print("ERROR: No API key provided.")
        print("  Pass as argument: python scripts/register_x402jobs.py <API_KEY>")
        print("  Or set X402_JOBS_API_KEY in .env file")
        print("\nGet a key at: https://www.x402.jobs/dashboard/api-keys")
        sys.exit(1)

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
        resource = data.get("resource", data)
        print(f"  Listing: https://x402.jobs/resources/{resource.get('display_path', '?')}")
        print(f"  Price: ${resource.get('price_usdc', '?')}")
        print(f"  Active: {resource.get('is_active', '?')}")
    else:
        print(f"\nERROR: {resp.status_code}")
        print(f"Response: {resp.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()
