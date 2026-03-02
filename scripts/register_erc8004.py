"""Register risk-api on ERC-8004 Identity Registry (Base mainnet).

Usage:
    python scripts/register_erc8004.py                          # register new agent
    python scripts/register_erc8004.py --update-uri              # update agentURI to default HTTP URL
    python scripts/register_erc8004.py --update-uri ipfs://Qm... # update agentURI to custom URI (e.g. IPFS)

Requires:
    - ETH in the agent wallet for gas (~$0.002)
    - Agent wallet private key at ~/.automaton/wallet.json
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

from eth_account import Account
from web3 import Web3

# --- Config ---
REGISTRY_ADDRESS = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
BASE_RPC = "https://mainnet.base.org"
CHAIN_ID = 8453
WALLET_FILE = Path.home() / ".automaton" / "wallet.json"

# ERC-8004 registration metadata
METADATA = {
    "type": "https://eips.ethereum.org/EIPS/eip-8004#registration-v1",
    "name": "Augur",
    "description": (
        "EVM smart contract risk scoring API on Base. "
        "Analyzes bytecode patterns (proxy detection, reentrancy, "
        "selfdestruct, honeypot, hidden mint, fee manipulation, "
        "delegatecall) and returns a composite 0-100 risk score. "
        "Pay $0.10/call via x402 in USDC on Base. "
        "Endpoint: GET https://risk-api.life.conway.tech/analyze?address={contract_address}"
    ),
    "services": [
        {
            "name": "web",
            "endpoint": "https://risk-api.life.conway.tech/",
        }
    ],
    "x402Support": True,
    "active": True,
    "supportedTrust": ["reputation"],
    "image": "https://risk-api.life.conway.tech/avatar.png",
    "updatedAt": 1740528000,  # 2025-02-26T00:00:00Z — update when re-registering
}

AGENT_ID = 19074
AGENT_METADATA_URL = "https://risk-api.life.conway.tech/agent-metadata.json"

# ABI for register(string) and setAgentURI(uint256, string)
REGISTRY_ABI = [
    {
        "inputs": [{"name": "agentURI", "type": "string"}],
        "name": "register",
        "outputs": [{"name": "agentId", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "agentId", "type": "uint256"},
            {"name": "agentURI", "type": "string"},
        ],
        "name": "setAgentURI",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]


def _load_wallet() -> tuple[Web3, "Account", int]:  # type: ignore[name-defined]
    """Load wallet and connect to Base. Returns (w3, account, balance)."""
    if not WALLET_FILE.exists():
        print(f"ERROR: Wallet file not found at {WALLET_FILE}")
        sys.exit(1)

    with open(WALLET_FILE) as f:
        wallet_data = json.load(f)
    private_key: str = wallet_data["privateKey"]

    account = Account.from_key(private_key)
    print(f"Wallet: {account.address}")

    w3 = Web3(Web3.HTTPProvider(BASE_RPC))
    if not w3.is_connected():
        print("ERROR: Cannot connect to Base RPC")
        sys.exit(1)

    balance = w3.eth.get_balance(account.address)
    balance_eth = w3.from_wei(balance, "ether")
    print(f"Balance: {balance_eth} ETH")

    if balance == 0:
        print("ERROR: Wallet has no ETH for gas. Send ~$0.01 worth of ETH to:")
        print(f"  {account.address}  (on Base mainnet)")
        sys.exit(1)

    return w3, account, balance


def _send_tx(
    w3: Web3, account: "Account", tx: dict[str, object], balance: int  # type: ignore[name-defined]
) -> None:
    """Estimate gas, sign, send, and wait for a transaction."""
    gas_price = int(w3.eth.gas_price)
    max_fee = gas_price * 2

    gas_estimate = w3.eth.estimate_gas(tx)
    gas_with_buffer = int(gas_estimate * 1.2)
    tx["gas"] = gas_with_buffer
    gas_cost = w3.from_wei(gas_with_buffer * max_fee, "ether")
    print(f"Estimated gas: {gas_estimate} (using {gas_with_buffer} with buffer)")
    print(f"Max gas cost: {gas_cost} ETH")

    if balance < gas_with_buffer * max_fee:
        balance_eth = w3.from_wei(balance, "ether")
        print(f"ERROR: Insufficient ETH. Need {gas_cost} ETH, have {balance_eth} ETH")
        sys.exit(1)

    print("\nSending transaction...")
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"TX hash: {tx_hash.hex()}")
    print(f"Basescan: https://basescan.org/tx/{tx_hash.hex()}")

    print("Waiting for confirmation...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

    if receipt["status"] == 1:
        print(f"\nSUCCESS! Gas used: {receipt['gasUsed']}")
        print(f"Effective gas price: {w3.from_wei(receipt['effectiveGasPrice'], 'gwei')} gwei")
        actual_cost = w3.from_wei(
            receipt["gasUsed"] * receipt["effectiveGasPrice"], "ether"
        )
        print(f"Actual cost: {actual_cost} ETH")
        return
    else:
        print(f"\nERROR: Transaction reverted! Receipt: {receipt}")
        sys.exit(1)


def register() -> None:
    """Register a new agent on the ERC-8004 registry."""
    w3, account, balance = _load_wallet()

    # Build agent URI as data: URI
    metadata_json = json.dumps(METADATA)
    encoded = base64.b64encode(metadata_json.encode()).decode()
    agent_uri = f"data:application/json;base64,{encoded}"
    print(f"Agent URI length: {len(agent_uri)} chars")

    contract = w3.eth.contract(
        address=Web3.to_checksum_address(REGISTRY_ADDRESS),
        abi=REGISTRY_ABI,
    )

    nonce = w3.eth.get_transaction_count(account.address)
    gas_price = int(w3.eth.gas_price)
    max_fee = gas_price * 2
    priority_fee = int(w3.to_wei(0.001, "gwei"))

    tx_params: dict[str, object] = {
        "from": account.address,
        "nonce": nonce,
        "chainId": CHAIN_ID,
        "maxFeePerGas": max_fee,
        "maxPriorityFeePerGas": priority_fee,
    }
    tx = contract.functions.register(agent_uri).build_transaction(
        tx_params  # type: ignore[arg-type]  # web3 TxParams TypedDict is overly strict
    )

    _send_tx(w3, account, tx, balance)

    print(f"\nCheck 8004scan.io for your new agentId.")
    print("Then set ERC8004_AGENT_ID in your config.")


def update_uri(agent_id: int, new_uri: str) -> None:
    """Update the agentURI for an existing agent registration."""
    w3, account, balance = _load_wallet()

    print(f"Updating agentURI for agent #{agent_id}")
    print(f"New URI: {new_uri}")

    contract = w3.eth.contract(
        address=Web3.to_checksum_address(REGISTRY_ADDRESS),
        abi=REGISTRY_ABI,
    )

    nonce = w3.eth.get_transaction_count(account.address)
    gas_price = int(w3.eth.gas_price)
    max_fee = gas_price * 2
    priority_fee = int(w3.to_wei(0.001, "gwei"))

    tx_params: dict[str, object] = {
        "from": account.address,
        "nonce": nonce,
        "chainId": CHAIN_ID,
        "maxFeePerGas": max_fee,
        "maxPriorityFeePerGas": priority_fee,
    }
    tx = contract.functions.setAgentURI(agent_id, new_uri).build_transaction(
        tx_params  # type: ignore[arg-type]  # web3 TxParams TypedDict is overly strict
    )

    _send_tx(w3, account, tx, balance)

    print(f"\nAgent #{agent_id} URI updated successfully.")
    print(f"View: https://8004scan.io/agents/base/{agent_id}")


def main() -> None:
    if "--update-uri" in sys.argv:
        idx = sys.argv.index("--update-uri")
        # Use next positional arg as URI if provided, else default HTTP URL
        if idx + 1 < len(sys.argv) and not sys.argv[idx + 1].startswith("--"):
            uri = sys.argv[idx + 1]
        else:
            uri = AGENT_METADATA_URL
        update_uri(AGENT_ID, uri)
    else:
        register()


if __name__ == "__main__":
    main()
