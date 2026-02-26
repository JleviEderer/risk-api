"""Register risk-api on Work402 agent hiring marketplace (Base Sepolia testnet).

Work402 is an agent-to-agent hiring marketplace where agents post services
and hire other agents. Currently on Base Sepolia (testnet).

Usage:
    python scripts/register_work402.py              # Onboard as seller agent
    python scripts/register_work402.py --show       # Show agents list

Note: Work402 is currently testnet-only (Base Sepolia 84532).
      Registration is free and requires no API key.

Docs: https://www.work402.com/hire/skill.md
"""

from __future__ import annotations

import json
import sys

import requests
from dotenv import load_dotenv

API_BASE = "https://work402.com/api"

WALLET_ADDRESS = "0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891"

AGENT_PROFILE = {
    "name": "Smart Contract Risk Scorer",
    "bio": (
        "EVM smart contract risk scoring API. Analyzes bytecode patterns "
        "(proxy detection, reentrancy, selfdestruct, honeypot, hidden mint, "
        "fee manipulation, delegatecall) and deployer reputation. Returns "
        "a composite 0-100 risk score. Live at risk-api.life.conway.tech. "
        "Pay $0.10/call via x402 in USDC on Base."
    ),
    "role": "seller",
    "wallet_address": WALLET_ADDRESS,
}


def cmd_onboard() -> None:
    """Register agent on Work402."""
    print("=== Work402 Registration ===")
    print(f"Agent: {AGENT_PROFILE['name']}")
    print(f"Role: {AGENT_PROFILE['role']}")
    print(f"Wallet: {AGENT_PROFILE['wallet_address']}")

    print("\nOnboarding agent...")
    resp = requests.post(
        f"{API_BASE}/agents/onboard",
        json=AGENT_PROFILE,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )

    if resp.status_code in (200, 201):
        result = resp.json()
        data = result.get("data", result)
        did = data.get("did", "?")
        wallet = data.get("wallet_address", "?")
        msg = result.get("message", "")

        print(f"\n  SUCCESS! Agent onboarded on Work402")
        print(f"  DID: {did}")
        print(f"  Wallet: {wallet}")
        print(f"  Message: {msg}")
        print(f"\n  Add to .env:")
        print(f"  WORK402_DID={did}")
        print(f"\n  Note: Work402 is currently on Base Sepolia (testnet).")
        print(f"  View: https://www.work402.com")
    else:
        print(f"\nERROR: {resp.status_code}")
        print(f"Response: {resp.text}")
        # Don't exit on 409 (already registered)
        if resp.status_code == 409:
            print("\nAgent may already be registered. Try --show to check.")
        else:
            sys.exit(1)


def cmd_show() -> None:
    """Browse agents on Work402."""
    print("Fetching Work402 agents...\n")

    resp = requests.get(f"{API_BASE}/agents", timeout=30)

    if resp.status_code == 200:
        data = resp.json()
        agents = data.get("agents", data) if isinstance(data, dict) else data
        if not agents:
            print("No agents found.")
            return

        for agent in agents if isinstance(agents, list) else [agents]:
            name = agent.get("name", "?")
            did = agent.get("did", "?")
            skills = agent.get("skills", [])
            rep = agent.get("reputation_score", "?")
            catalog = agent.get("task_catalog", [])
            print(f"  Name: {name}")
            print(f"  DID: {did}")
            print(f"  Reputation: {rep}")
            if skills:
                print(f"  Skills: {', '.join(skills)}")
            if catalog:
                for task in catalog:
                    print(f"  Service: {task.get('name', '?')} — ${task.get('price_amount', '?')}")
            print()
    else:
        print(f"ERROR: {resp.status_code}")
        print(f"Response: {resp.text}")
        sys.exit(1)


def main() -> None:
    load_dotenv()

    if "--show" in sys.argv:
        cmd_show()
    else:
        cmd_onboard()


if __name__ == "__main__":
    main()
