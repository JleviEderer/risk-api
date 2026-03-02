"""Register risk-api on MoltMart marketplace (Base mainnet).

MoltMart is an x402-native agent marketplace on Base that uses ERC-8004
for identity verification. Registration is free and fully API-driven.

Usage:
    python scripts/register_moltmart.py                    # Full flow: register agent + list service
    python scripts/register_moltmart.py --register-only    # Just register agent (get API key)
    python scripts/register_moltmart.py --list-service     # List service (requires MOLTMART_API_KEY)
    python scripts/register_moltmart.py --update SERVICE_ID # Update existing service
    python scripts/register_moltmart.py --show              # Show current agent profile
    python scripts/register_moltmart.py --recover           # Recover API key with wallet signature

Requires:
    - Agent wallet private key at ~/.automaton/wallet.json
    - MOLTMART_API_KEY in .env (after first registration, or use --recover)

Docs: https://moltmart.app/skill.md
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
from eth_account import Account
from eth_account.messages import encode_defunct

import os

API_BASE = "https://api.moltmart.app"
WALLET_FILE = Path.home() / ".automaton" / "wallet.json"

AGENT_NAME = "Augur"
AGENT_DESCRIPTION = (
    "EVM smart contract risk scoring API on Base. "
    "Analyzes bytecode patterns (proxy detection, reentrancy, selfdestruct, "
    "honeypot, hidden mint, fee manipulation, delegatecall) and deployer "
    "reputation. Returns a composite 0-100 risk score with severity levels. "
    "Pay $0.10/call via x402 in USDC on Base."
)

SERVICE_LISTING = {
    "name": "Augur",
    "description": (
        "Analyzes EVM smart contract bytecode for security risks. "
        "Detects proxy patterns (EIP-1967/1822/OZ), reentrancy guards, "
        "selfdestruct, honeypot patterns, hidden mint functions, fee manipulation, "
        "and delegatecall usage. For proxy contracts, automatically resolves and "
        "analyzes the implementation. Returns a composite risk score (0-100) with "
        "per-detector findings and severity level (safe/low/medium/high/critical). "
        "Deployer reputation check via Basescan when API key is configured."
    ),
    "endpoint_url": "https://risk-api.life.conway.tech/analyze",
    "price_usdc": 0.10,
    "category": "analysis",
    "usage_instructions": (
        "## Usage\n\n"
        "Send a GET or POST request with a Base mainnet contract address.\n\n"
        "### GET\n"
        "```\n"
        "GET https://risk-api.life.conway.tech/analyze?address=0x4200000000000000000000000000000000000006\n"
        "```\n\n"
        "### POST\n"
        "```json\n"
        'POST https://risk-api.life.conway.tech/analyze\n'
        '{"address": "0x4200000000000000000000000000000000000006"}\n'
        "```\n\n"
        "### Payment\n"
        "x402 protocol — send $0.10 USDC on Base via the `PAYMENT-SIGNATURE` header. "
        "The server returns HTTP 402 with payment details if no valid payment is included.\n\n"
        "### Response\n"
        "Returns JSON with `score` (0-100), `risk_level`, and `findings` array."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "address": {
                "type": "string",
                "description": "Base mainnet contract address (0x format, 42 chars)",
                "pattern": "^0x[a-fA-F0-9]{40}$",
            }
        },
        "required": ["address"],
    },
    "output_schema": {
        "type": "object",
        "properties": {
            "address": {"type": "string", "description": "Analyzed contract address"},
            "score": {
                "type": "integer",
                "description": "Composite risk score 0-100 (higher = riskier)",
                "minimum": 0,
                "maximum": 100,
            },
            "risk_level": {
                "type": "string",
                "description": "Human-readable risk level",
                "enum": ["safe", "low", "medium", "high", "critical"],
            },
            "findings": {
                "type": "array",
                "description": "List of detected risk indicators",
                "items": {
                    "type": "object",
                    "properties": {
                        "detector": {"type": "string"},
                        "severity": {"type": "string"},
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                    },
                },
            },
        },
        "required": ["address", "score", "risk_level", "findings"],
    },
    "example_request": {
        "address": "0x4200000000000000000000000000000000000006",
    },
    "example_response": {
        "address": "0x4200000000000000000000000000000000000006",
        "score": 0,
        "risk_level": "safe",
        "findings": [],
        "metadata": {
            "chain": "base",
            "has_code": True,
            "code_size": 2958,
        },
    },
}


def _load_wallet() -> tuple[Account, str]:
    """Load wallet private key. Returns (account, private_key)."""
    if not WALLET_FILE.exists():
        print(f"ERROR: Wallet file not found at {WALLET_FILE}")
        sys.exit(1)

    with open(WALLET_FILE) as f:
        wallet_data = json.load(f)
    private_key: str = wallet_data["privateKey"]

    account = Account.from_key(private_key)
    print(f"Wallet: {account.address}")
    return account, private_key


def _get_api_key() -> str:
    """Get MoltMart API key from env."""
    key = os.environ.get("MOLTMART_API_KEY", "")
    if not key:
        print("ERROR: No MOLTMART_API_KEY found in .env")
        print("  Run this script without flags first to register and get a key,")
        print("  or use --recover to recover an existing key.")
        sys.exit(1)
    return key


def cmd_register() -> str:
    """Register agent on MoltMart. Returns API key."""
    account, private_key = _load_wallet()

    # Step 1: Get challenge
    print("\n1. Getting challenge from MoltMart...")
    resp = requests.get(f"{API_BASE}/agents/challenge", timeout=30)
    if resp.status_code != 200:
        print(f"ERROR getting challenge: {resp.status_code}")
        print(f"Response: {resp.text}")
        sys.exit(1)

    data = resp.json()
    challenge_message = data.get("challenge", "")
    if not challenge_message:
        print(f"ERROR: No challenge in response: {data}")
        sys.exit(1)
    print(f"  Challenge: {challenge_message[:80]}...")

    # Step 2: Sign challenge
    print("\n2. Signing challenge with wallet...")
    message = encode_defunct(text=challenge_message)
    signed = Account.sign_message(message, private_key=private_key)
    signature = signed.signature.hex()
    if not signature.startswith("0x"):
        signature = "0x" + signature
    print(f"  Signature: {signature[:20]}...")

    # Step 3: Register
    print("\n3. Registering agent...")
    register_body = {
        "name": AGENT_NAME,
        "wallet_address": account.address,  # type: ignore[attr-defined]  # eth_account stubs
        "signature": signature,
        "description": AGENT_DESCRIPTION,
        "erc8004_id": 19074,
    }

    resp = requests.post(
        f"{API_BASE}/agents/register",
        json=register_body,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )

    if resp.status_code in (200, 201):
        result = resp.json()
        api_key = result.get("api_key", "")
        agent_id = result.get("id", "?")
        print(f"\n  SUCCESS! Agent registered on MoltMart")
        print(f"  Agent ID: {agent_id}")
        print(f"  API Key: {api_key}")
        print(f"\n  Add to .env:")
        print(f"  MOLTMART_API_KEY={api_key}")
        return api_key
    else:
        print(f"\nERROR: {resp.status_code}")
        print(f"Response: {resp.text}")
        sys.exit(1)


def cmd_recover() -> str:
    """Recover API key using wallet signature."""
    account, private_key = _load_wallet()

    print("\n1. Getting challenge...")
    resp = requests.get(f"{API_BASE}/agents/challenge", timeout=30)
    if resp.status_code != 200:
        print(f"ERROR: {resp.status_code} — {resp.text}")
        sys.exit(1)

    challenge_message = resp.json().get("challenge", "")
    message = encode_defunct(text=challenge_message)
    signed = Account.sign_message(message, private_key=private_key)
    signature = signed.signature.hex()
    if not signature.startswith("0x"):
        signature = "0x" + signature

    print("2. Recovering key...")
    resp = requests.post(
        f"{API_BASE}/agents/recover-key",
        json={"wallet_address": account.address, "signature": signature},  # type: ignore[attr-defined]
        headers={"Content-Type": "application/json"},
        timeout=30,
    )

    if resp.status_code == 200:
        result = resp.json()
        api_key = result.get("api_key", "")
        print(f"\n  SUCCESS! API Key: {api_key}")
        print(f"\n  Add to .env:")
        print(f"  MOLTMART_API_KEY={api_key}")
        return api_key
    else:
        print(f"\nERROR: {resp.status_code}")
        print(f"Response: {resp.text}")
        sys.exit(1)


def cmd_list_service(api_key: str) -> None:
    """List our service on MoltMart."""
    print("\nListing service on MoltMart...")
    print(f"  Name: {SERVICE_LISTING['name']}")
    print(f"  Endpoint: {SERVICE_LISTING['endpoint_url']}")
    print(f"  Price: ${SERVICE_LISTING['price_usdc']}")
    print(f"  Category: {SERVICE_LISTING['category']}")

    resp = requests.post(
        f"{API_BASE}/services",
        json=SERVICE_LISTING,
        headers={
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        },
        timeout=30,
    )

    if resp.status_code in (200, 201):
        result = resp.json()
        service_id = result.get("id", "?")
        secret_token = result.get("secret_token", "")
        print(f"\n  SUCCESS! Service listed on MoltMart")
        print(f"  Service ID: {service_id}")
        if secret_token:
            print(f"  Secret Token: {secret_token}")
            print(f"  (Used for HMAC verification of incoming calls)")
            print(f"\n  Add to .env:")
            print(f"  MOLTMART_SERVICE_ID={service_id}")
            print(f"  MOLTMART_SECRET_TOKEN={secret_token}")
    else:
        print(f"\nERROR: {resp.status_code}")
        print(f"Response: {resp.text}")
        sys.exit(1)


def cmd_update_service(api_key: str, service_id: str) -> None:
    """Update existing service listing."""
    print(f"\nUpdating service {service_id} on MoltMart...")

    resp = requests.patch(
        f"{API_BASE}/services/{service_id}",
        json=SERVICE_LISTING,
        headers={
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        },
        timeout=30,
    )

    if resp.status_code == 200:
        print(f"\n  SUCCESS! Service updated.")
    else:
        print(f"\nERROR: {resp.status_code}")
        print(f"Response: {resp.text}")
        sys.exit(1)


def cmd_show(api_key: str) -> None:
    """Show current agent profile."""
    print("\nFetching agent profile...")

    resp = requests.get(
        f"{API_BASE}/agents/me",
        headers={"X-API-Key": api_key},
        timeout=30,
    )

    if resp.status_code == 200:
        data = resp.json()
        print(json.dumps(data, indent=2))
    else:
        print(f"ERROR: {resp.status_code}")
        print(f"Response: {resp.text}")
        sys.exit(1)


def main() -> None:
    load_dotenv()

    if "--recover" in sys.argv:
        cmd_recover()
        return

    if "--register-only" in sys.argv:
        cmd_register()
        return

    if "--list-service" in sys.argv:
        api_key = _get_api_key()
        cmd_list_service(api_key)
        return

    if "--update" in sys.argv:
        idx = sys.argv.index("--update")
        if idx + 1 >= len(sys.argv):
            print("ERROR: --update requires a SERVICE_ID")
            sys.exit(1)
        service_id = sys.argv[idx + 1]
        api_key = _get_api_key()
        cmd_update_service(api_key, service_id)
        return

    if "--show" in sys.argv:
        api_key = _get_api_key()
        cmd_show(api_key)
        return

    # Default: full flow — register + list service
    print("=== MoltMart Registration ===")
    print(f"Agent: {AGENT_NAME}")
    print(f"ERC-8004 ID: 19074")

    # Check if we already have a key
    existing_key = os.environ.get("MOLTMART_API_KEY", "")
    if existing_key:
        print(f"\nMOLTMART_API_KEY found in .env — skipping registration.")
        print(f"  Use --register-only to force re-registration.")
        api_key = existing_key
    else:
        api_key = cmd_register()

    print("\n--- Listing Service ---")
    cmd_list_service(api_key)

    print("\n=== Done! ===")
    print("View your listing at: https://moltmart.app")


if __name__ == "__main__":
    main()
