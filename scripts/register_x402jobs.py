"""Register/manage risk-api on x402.jobs marketplace.

Usage:
    python scripts/register_x402jobs.py              # Create new resource
    python scripts/register_x402jobs.py --list       # List your resources (shows UUIDs)
    python scripts/register_x402jobs.py --update UUID # Update existing resource by UUID

    API key is read from X402_JOBS_API_KEY in .env file,
    or pass as --key <KEY>.

Get an API key:
    1. Sign up at https://www.x402.jobs/signup
    2. Go to https://www.x402.jobs/dashboard/api-keys
    3. Create a key and add to .env
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import httpx
from dotenv import load_dotenv

API_BASE = "https://api.x402.jobs/api/v1"

RESOURCE = {
    "name": "Augur",
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
    "documentation_url": "https://risk-api.life.conway.tech/openapi.json",
    "price_usdc": "0.10",
    "logo_url": "https://risk-api.life.conway.tech/avatar.png",
    "example_request": (
        "GET /analyze?address=0x4200000000000000000000000000000000000006"
    ),
    "response_schema": {
        "address": "string",
        "score": "integer (0-100)",
        "level": "safe | low | medium | high | critical",
        "bytecode_size": "integer",
        "findings": "[{detector, severity, title, description, points}]",
        "category_scores": "{category: number}",
        "implementation": "object | null (for proxy contracts)",
    },
    "authentication": "x402 (USDC on Base)",
    "output_format": "application/json",
}


def get_api_key(args: argparse.Namespace) -> str:
    key = args.key or os.environ.get("X402_JOBS_API_KEY", "")
    if not key:
        print("ERROR: No API key provided.")
        print("  --key <KEY>  or  set X402_JOBS_API_KEY in .env")
        print("\nGet a key at: https://www.x402.jobs/dashboard/api-keys")
        sys.exit(1)
    return key


def cmd_create(args: argparse.Namespace) -> None:
    api_key = get_api_key(args)
    print("Creating resource on x402.jobs...")
    print(f"  Name: {RESOURCE['name']}")
    print(f"  URL: {RESOURCE['resourceUrl']}")

    resp = httpx.post(
        f"{API_BASE}/resources",
        json=RESOURCE,
        headers={"x-api-key": api_key, "Content-Type": "application/json"},
        timeout=30,
    )

    if resp.status_code in (200, 201):
        data = resp.json()
        print("\nSUCCESS! Resource created on x402.jobs")
        resource = data.get("resource", data)
        print(f"  UUID: {resource.get('id', '?')}")
        print(f"  Listing: https://x402.jobs/resources/{resource.get('display_path', '?')}")
        print(f"  Price: ${resource.get('price_usdc', '?')}")
        print(f"  Active: {resource.get('is_active', '?')}")
    else:
        print(f"\nERROR: {resp.status_code}")
        print(f"Response: {resp.text}")
        sys.exit(1)


def cmd_list(args: argparse.Namespace) -> None:
    api_key = get_api_key(args)
    print("Listing your resources on x402.jobs...\n")

    resp = httpx.get(
        f"{API_BASE}/resources",
        headers={"x-api-key": api_key},
        timeout=30,
    )

    if resp.status_code != 200:
        print(f"ERROR: {resp.status_code}")
        print(f"Response: {resp.text}")
        sys.exit(1)

    data = resp.json()
    resources = data if isinstance(data, list) else data.get("resources", data.get("data", []))
    if not resources:
        print("No resources found.")
        return

    for r in resources:
        rid = r.get("id", "?")
        name = r.get("name", "?")
        url = r.get("resourceUrl", r.get("resource_url", "?"))
        active = r.get("is_active", "?")
        slug = r.get("display_path", r.get("slug", "?"))
        print(f"  UUID: {rid}")
        print(f"  Name: {name}")
        print(f"  URL:  {url}")
        print(f"  Slug: {slug}")
        print(f"  Active: {active}")
        print()


def cmd_update(args: argparse.Namespace) -> None:
    api_key = get_api_key(args)
    uuid = args.uuid
    if not uuid:
        print("ERROR: --update requires a UUID. Run --list to find it.")
        sys.exit(1)

    print(f"Updating resource {uuid} on x402.jobs...")
    print(f"  Name: {RESOURCE['name']}")
    print(f"  URL: {RESOURCE['resourceUrl']}")

    resp = httpx.put(
        f"{API_BASE}/resources/{uuid}",
        json=RESOURCE,
        headers={"x-api-key": api_key, "Content-Type": "application/json"},
        timeout=30,
    )

    if resp.status_code in (200, 201):
        data = resp.json()
        print("\nSUCCESS! Resource updated on x402.jobs")
        resource = data.get("resource", data)
        print(f"  UUID: {resource.get('id', uuid)}")
        print(f"  Listing: https://x402.jobs/resources/{resource.get('display_path', '?')}")
    else:
        print(f"\nERROR: {resp.status_code}")
        print(f"Response: {resp.text}")
        sys.exit(1)


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Manage risk-api on x402.jobs")
    parser.add_argument("--key", help="x402.jobs API key (or set X402_JOBS_API_KEY in .env)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--list", action="store_true", help="List your resources (shows UUIDs)")
    group.add_argument("--update", metavar="UUID", help="Update existing resource by UUID")
    # Legacy: positional API key for backwards compat
    parser.add_argument("api_key_pos", nargs="?", help=argparse.SUPPRESS)

    args = parser.parse_args()

    # Support legacy positional API key
    if args.api_key_pos and not args.key:
        args.key = args.api_key_pos

    if args.list:
        cmd_list(args)
    elif args.update:
        args.uuid = args.update
        cmd_update(args)
    else:
        cmd_create(args)


if __name__ == "__main__":
    main()
