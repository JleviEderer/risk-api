"""
One-off script: make a real x402 paid call to augurrisk.com using the Conway wallet.
This triggers an on-chain USDC settlement, which gets indexed by x402list.fun.

Usage:
    python scripts/test_x402_payment.py
"""

from __future__ import annotations

import base64
import json
import os
import secrets
import time
from pathlib import Path

import requests
from eth_account import Account
from eth_account.messages import encode_typed_data

WALLET_PATH = Path.home() / ".conway" / "wallet.json"
ANALYZE_URL = "https://augurrisk.com/analyze?address=0x4200000000000000000000000000000000000006"

# USDC on Base mainnet
USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
USDC_DECIMALS = 6
BASE_CHAIN_ID = 8453

# EIP-3009 domain for USDC on Base
USDC_DOMAIN = {
    "name": "USD Coin",
    "version": "2",
    "chainId": BASE_CHAIN_ID,
    "verifyingContract": USDC_ADDRESS,
}

TRANSFER_WITH_AUTH_TYPES = {
    "EIP712Domain": [
        {"name": "name", "type": "string"},
        {"name": "version", "type": "string"},
        {"name": "chainId", "type": "uint256"},
        {"name": "verifyingContract", "type": "address"},
    ],
    "TransferWithAuthorization": [
        {"name": "from", "type": "address"},
        {"name": "to", "type": "address"},
        {"name": "value", "type": "uint256"},
        {"name": "validAfter", "type": "uint256"},
        {"name": "validBefore", "type": "uint256"},
        {"name": "nonce", "type": "bytes32"},
    ],
}


def load_wallet() -> tuple[str, str]:
    """Returns (private_key, address)."""
    data = json.loads(WALLET_PATH.read_text())
    pk = data["privateKey"]
    acct = Account.from_key(pk)
    return pk, acct.address


def check_usdc_balance(address: str) -> float:
    """Returns USDC balance in dollars."""
    rpc = os.environ.get("BASE_RPC_URL", "https://mainnet.base.org")
    # balanceOf(address)
    data = "0x70a08231" + address[2:].lower().zfill(64)
    resp = requests.post(rpc, json={
        "jsonrpc": "2.0", "id": 1, "method": "eth_call",
        "params": [{"to": USDC_ADDRESS, "data": data}, "latest"],
    }, timeout=10)
    result = resp.json().get("result", "0x0")
    balance_raw = int(result, 16)
    return balance_raw / (10 ** USDC_DECIMALS)


def get_payment_requirements() -> dict:
    """Fetch 402 from server and parse Payment-Required header."""
    resp = requests.get(ANALYZE_URL, timeout=15)
    if resp.status_code != 402:
        raise RuntimeError(f"Expected 402, got {resp.status_code}: {resp.text[:200]}")

    header = resp.headers.get("Payment-Required") or resp.headers.get("X-Payment-Required")
    if not header:
        raise RuntimeError(f"No Payment-Required header. Headers: {dict(resp.headers)}")

    # Header is base64-encoded JSON
    decoded = base64.b64decode(header + "==").decode()
    return json.loads(decoded)


def build_payment_proof(
    private_key: str,
    from_address: str,
    to_address: str,
    amount_usdc: int,
    accepted_option: dict,
) -> str:
    """Build x402 v2 payment proof string for PAYMENT-SIGNATURE header."""
    nonce = "0x" + secrets.token_bytes(32).hex()
    valid_before = int(time.time()) + 300  # 5 minutes

    authorization = {
        "from": from_address,
        "to": to_address,
        "value": str(amount_usdc),
        "validAfter": "0",
        "validBefore": str(valid_before),
        "nonce": nonce,
    }

    # Sign EIP-712 TransferWithAuthorization
    structured_data = {
        "primaryType": "TransferWithAuthorization",
        "domain": USDC_DOMAIN,
        "types": TRANSFER_WITH_AUTH_TYPES,
        "message": {
            "from": from_address,
            "to": to_address,
            "value": amount_usdc,
            "validAfter": 0,
            "validBefore": valid_before,
            "nonce": bytes.fromhex(nonce[2:]),
        },
    }

    signed = Account.sign_typed_data(
        private_key,
        full_message=structured_data,
    )
    signature = signed.signature.hex()
    if not signature.startswith("0x"):
        signature = "0x" + signature

    # x402 v2 format: accepted mirrors the payment option from the 402 response
    proof = {
        "x402Version": 2,
        "payload": {
            "signature": signature,
            "authorization": authorization,
        },
        "accepted": accepted_option,
    }

    return base64.b64encode(json.dumps(proof).encode()).decode()


def main() -> None:
    print("Loading Conway wallet...")
    private_key, address = load_wallet()
    print(f"  Address: {address}")

    print("\nChecking USDC balance on Base...")
    balance = check_usdc_balance(address)
    print(f"  Balance: ${balance:.6f} USDC")

    if balance < 0.10:
        print(f"\nERROR: Need at least $0.10 USDC, have ${balance:.6f}")
        print("Transfer USDC to this address on Base first.")
        return

    print(f"\nFetching payment requirements from {ANALYZE_URL}...")
    try:
        reqs = get_payment_requirements()
    except RuntimeError as e:
        print(f"ERROR: {e}")
        return

    print(f"  Raw requirements: {json.dumps(reqs, indent=2)[:500]}")

    # Parse payment details from requirements (x402 v2 format)
    options = reqs.get("accepts", [])
    if not options:
        print(f"ERROR: No payment options found in: {json.dumps(reqs, indent=2)}")
        return

    option = options[0]
    print(f"\nFull payment option:\n{json.dumps(option, indent=2)}")

    # v2 field names: pay_to / payTo (try both)
    to_address = (
        option.get("pay_to")
        or option.get("payTo")
        or option.get("extra", {}).get("pay_to")
        or option.get("extra", {}).get("payTo", "")
    )
    amount_raw = option.get("amount") or option.get("maxAmountRequired") or "100000"
    amount_int = int(amount_raw)
    network = option.get("network", "eip155:8453")

    if not to_address:
        print(f"ERROR: Could not find pay_to/payTo in option")
        return

    print(f"\nPayment details:")
    print(f"  To:      {to_address}")
    print(f"  Amount:  {amount_int / 10**USDC_DECIMALS:.6f} USDC")
    print(f"  Network: {network}")

    print("\nSigning payment authorization...")
    proof = build_payment_proof(private_key, address, to_address, amount_int, option)

    print("Sending paid request...")
    resp = requests.get(
        ANALYZE_URL,
        headers={"PAYMENT-SIGNATURE": proof},
        timeout=30,
    )

    print(f"\nResponse: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"  Score: {data.get('score')} / {data.get('level')}")
        print(f"  Findings: {len(data.get('findings', []))}")
        print("\nSUCCESS — on-chain settlement triggered.")
        print("x402list.fun should index augurrisk.com within ~1 hour.")
    else:
        print(f"  Body: {resp.text[:500]}")


if __name__ == "__main__":
    main()
