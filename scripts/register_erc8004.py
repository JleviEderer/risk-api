"""Register risk-api on ERC-8004 Identity Registry (Base mainnet).

Usage:
    python scripts/register_erc8004.py

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
    "name": "Smart Contract Risk Scorer",
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
}

# ABI for register(string) function
REGISTER_ABI = [
    {
        "inputs": [{"name": "agentURI", "type": "string"}],
        "name": "register",
        "outputs": [{"name": "agentId", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]


def main() -> None:
    # Load private key
    if not WALLET_FILE.exists():
        print(f"ERROR: Wallet file not found at {WALLET_FILE}")
        sys.exit(1)

    with open(WALLET_FILE) as f:
        wallet_data = json.load(f)
    private_key: str = wallet_data["privateKey"]

    account = Account.from_key(private_key)
    print(f"Wallet: {account.address}")

    # Connect to Base
    w3 = Web3(Web3.HTTPProvider(BASE_RPC))
    if not w3.is_connected():
        print("ERROR: Cannot connect to Base RPC")
        sys.exit(1)

    # Check balance
    balance = w3.eth.get_balance(account.address)
    balance_eth = w3.from_wei(balance, "ether")
    print(f"Balance: {balance_eth} ETH")

    if balance == 0:
        print("ERROR: Wallet has no ETH for gas. Send ~$0.01 worth of ETH to:")
        print(f"  {account.address}  (on Base mainnet)")
        sys.exit(1)

    # Build agent URI as data: URI
    metadata_json = json.dumps(METADATA)
    encoded = base64.b64encode(metadata_json.encode()).decode()
    agent_uri = f"data:application/json;base64,{encoded}"
    print(f"Agent URI length: {len(agent_uri)} chars")

    # Build contract call
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(REGISTRY_ADDRESS),
        abi=REGISTER_ABI,
    )

    nonce = w3.eth.get_transaction_count(account.address)
    gas_price = int(w3.eth.gas_price)
    max_fee = gas_price * 2
    priority_fee = int(w3.to_wei(0.001, "gwei"))

    # Estimate gas
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

    gas_estimate = w3.eth.estimate_gas(tx)
    gas_with_buffer = int(gas_estimate * 1.2)
    tx["gas"] = gas_with_buffer
    gas_cost = w3.from_wei(gas_with_buffer * max_fee, "ether")
    print(f"Estimated gas: {gas_estimate} (using {gas_with_buffer} with buffer)")
    print(f"Max gas cost: {gas_cost} ETH")

    if balance < gas_with_buffer * max_fee:
        print(f"ERROR: Insufficient ETH. Need {gas_cost} ETH, have {balance_eth} ETH")
        sys.exit(1)

    # Sign and send
    print("\nSending registration transaction...")
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"TX hash: {tx_hash.hex()}")
    print(f"Basescan: https://basescan.org/tx/{tx_hash.hex()}")

    # Wait for receipt
    print("Waiting for confirmation...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

    if receipt["status"] == 1:
        # Parse logs to find the agentId
        # Registered event: Registered(uint256 agentId, string agentURI, address owner)
        # Topic0 for Registered event
        for log in receipt["logs"]:
            # Transfer event (ERC-721 mint) has the tokenId as topic[3]
            # Transfer(address from, address to, uint256 tokenId)
            transfer_topic = w3.keccak(text="Transfer(address,address,uint256)")
            if log["topics"][0] == transfer_topic:
                agent_id = int(log["topics"][3].hex(), 16)
                print(f"\nSUCCESS! Registered as agent #{agent_id}")
                print(f"View: https://8004scan.io/agents/base/{agent_id}")
                print(f"\nUpdate your app config with: ERC8004_AGENT_ID={agent_id}")
                break
        else:
            print("\nSUCCESS! Transaction confirmed but could not parse agentId from logs.")
            print("Check Basescan for the agentId.")

        print(f"\nGas used: {receipt['gasUsed']}")
        print(f"Effective gas price: {w3.from_wei(receipt['effectiveGasPrice'], 'gwei')} gwei")
        actual_cost = w3.from_wei(
            receipt["gasUsed"] * receipt["effectiveGasPrice"], "ether"
        )
        print(f"Actual cost: {actual_cost} ETH")
    else:
        print(f"\nERROR: Transaction reverted! Receipt: {receipt}")
        sys.exit(1)


if __name__ == "__main__":
    main()
