"""Pin agent metadata JSON to IPFS via Pinata for content-addressed agentURI.

Fixes 8004scan WA040 warning ("HTTP/HTTPS URI is not content-addressed").

Usage:
    export PINATA_JWT="your_jwt_here"
    python scripts/pin_metadata_ipfs.py
    # → prints: ipfs://Qm...

Then update on-chain URI:
    python scripts/register_erc8004.py --update-uri ipfs://Qm...

Requires:
    - PINATA_JWT env var (free signup at https://pinata.cloud)
    - No new dependencies (uses requests, already in stack)
"""

from __future__ import annotations

import json
import os
import sys
import time

import requests

PINATA_PIN_URL = "https://api.pinata.cloud/pinning/pinJSONToIPFS"

# Public base URL for the risk-api (used in metadata fields that need absolute URLs)
BASE_URL = "https://risk-api.life.conway.tech"

# ERC-8004 agent registration
AGENT_ID = 19074
REGISTRY_ADDRESS = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
WALLET_ADDRESS = "0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891"


def build_metadata() -> dict[str, object]:
    """Build agent metadata dict matching /agent-metadata.json endpoint.

    Uses a fixed updatedAt timestamp since IPFS content is immutable.
    Re-run this script to get a new CID when metadata changes.
    """
    return {
        "type": "https://eips.ethereum.org/EIPS/eip-8004#registration-v1",
        "name": "Smart Contract Risk Scorer",
        "description": (
            "EVM smart contract risk scoring API on Base. "
            "Analyzes bytecode patterns (proxy detection, reentrancy, "
            "selfdestruct, honeypot, hidden mint, fee manipulation, "
            "delegatecall) and returns a composite 0-100 risk score. "
            "Pay $0.10/call via x402 in USDC on Base. "
            "Endpoint: GET /analyze?address={contract_address}"
        ),
        "services": [
            {
                "name": "web",
                "endpoint": f"{BASE_URL}/",
            },
            {
                "name": "A2A",
                "endpoint": f"{BASE_URL}/.well-known/agent-card.json",
                "version": "0.3.0",
            },
            {
                "name": "OASF",
                "skills": ["1304"],
                "domains": ["109", "10903", "405"],
            },
            {
                "name": "agentWallet",
                "endpoint": f"eip155:8453:{WALLET_ADDRESS}",
            },
        ],
        "x402Support": True,
        "active": True,
        "supportedTrust": ["reputation"],
        "image": f"{BASE_URL}/avatar.png",
        # Fixed timestamp — re-pin to update
        "updatedAt": int(time.time()),
        "pricing": {
            "amount": "0.10",
            "currency": "USDC",
            "network": "eip155:8453",
        },
        "openapi_url": f"{BASE_URL}/openapi.json",
        "capabilities": [
            "contract risk scoring",
            "proxy detection",
            "bytecode analysis",
            "honeypot detection",
            "reentrancy detection",
            "security assessment",
        ],
        "registrations": [
            {
                "agentId": AGENT_ID,
                "agentRegistry": f"eip155:8453:{REGISTRY_ADDRESS}",
            }
        ],
    }


def pin_to_ipfs(metadata: dict[str, object], jwt: str) -> str:
    """Pin JSON to IPFS via Pinata. Returns the IPFS CID."""
    payload = {
        "pinataContent": metadata,
        "pinataMetadata": {
            "name": "risk-api-agent-metadata",
        },
    }

    resp = requests.post(
        PINATA_PIN_URL,
        json=payload,
        headers={
            "Authorization": f"Bearer {jwt}",
            "Content-Type": "application/json",
        },
        timeout=30,
    )

    if resp.status_code != 200:
        print(f"ERROR: Pinata API returned {resp.status_code}", file=sys.stderr)
        print(resp.text, file=sys.stderr)
        sys.exit(1)

    data = resp.json()
    cid: str = data["IpfsHash"]
    return cid


def main() -> None:
    jwt = os.environ.get("PINATA_JWT", "").strip()
    if not jwt:
        print("ERROR: PINATA_JWT env var is required", file=sys.stderr)
        print("  Get a free JWT at https://app.pinata.cloud/developers/api-keys", file=sys.stderr)
        sys.exit(1)

    metadata = build_metadata()

    print("Metadata to pin:")
    print(json.dumps(metadata, indent=2))
    print()

    cid = pin_to_ipfs(metadata, jwt)

    print(f"Pinned successfully!")
    print(f"  CID:     {cid}")
    print(f"  URI:     ipfs://{cid}")
    print(f"  Gateway: https://gateway.pinata.cloud/ipfs/{cid}")
    print()
    print("Next step — update on-chain agentURI:")
    print(f"  python scripts/register_erc8004.py --update-uri ipfs://{cid}")


if __name__ == "__main__":
    main()
