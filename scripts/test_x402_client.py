#!/usr/bin/env python3
"""x402 test client — call the paywalled /analyze endpoint with a real payment.

Usage:
    # Set your MetaMask private key (export from Settings > Security)
    export CLIENT_PRIVATE_KEY="0x..."

    # Run against live endpoint
    python scripts/test_x402_client.py

    # Or specify a custom URL / contract address
    python scripts/test_x402_client.py --url http://localhost:5000 --address 0xC02...Cc2

Prerequisites:
    - The wallet behind CLIENT_PRIVATE_KEY must hold >= $0.10 USDC on Base mainnet
    - pip install eth-account requests  (already installed if you have risk-api[dev])
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from typing import Any

import requests
from eth_account import Account
from eth_account.signers.local import LocalAccount

from x402 import parse_payment_required, x402ClientSync
from x402.mechanisms.evm.exact import ExactEvmScheme
from x402.mechanisms.evm.types import TypedDataDomain, TypedDataField


class EthAccountSigner:
    """Adapts eth_account.LocalAccount to x402's ClientEvmSigner protocol."""

    def __init__(self, account: LocalAccount) -> None:
        self._account = account

    @property
    def address(self) -> str:
        return self._account.address

    def sign_typed_data(
        self,
        domain: TypedDataDomain,
        types: dict[str, list[TypedDataField]],
        primary_type: str,
        message: dict[str, Any],
    ) -> bytes:
        # Convert x402 TypedDataDomain to dict for eth_account
        domain_data = {
            "name": domain.name,
            "version": domain.version,
            "chainId": domain.chain_id,
            "verifyingContract": domain.verifying_contract,
        }

        # Convert x402 TypedDataField list to eth_account format
        # eth_account expects: {"TypeName": [{"name": ..., "type": ...}, ...]}
        message_types = {}
        for type_name, fields in types.items():
            if type_name == "EIP712Domain":
                continue
            message_types[type_name] = [
                {"name": f.name, "type": f.type} for f in fields
            ]

        signed = self._account.sign_typed_data(
            domain_data=domain_data,
            message_types=message_types,
            message_data=message,
        )
        return bytes(signed.signature)


def main() -> None:
    parser = argparse.ArgumentParser(description="Test x402 payment flow")
    parser.add_argument(
        "--url",
        default="https://risk-api.life.conway.tech",
        help="Base URL of the risk-api (default: live endpoint)",
    )
    parser.add_argument(
        "--address",
        default="0x4200000000000000000000000000000000000006",
        help="Contract address to analyze (default: Base WETH)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only fetch 402 response, don't sign/pay",
    )
    args = parser.parse_args()

    # Load private key
    private_key = os.environ.get("CLIENT_PRIVATE_KEY")
    if not private_key and not args.dry_run:
        print("ERROR: Set CLIENT_PRIVATE_KEY env var to your MetaMask private key")
        print("       Export from MetaMask: Settings > Security > Reveal Private Key")
        print("       Or use --dry-run to just see the 402 response")
        sys.exit(1)

    endpoint = f"{args.url.rstrip('/')}/analyze?address={args.address}"

    # Step 1: Hit the endpoint without payment — expect 402
    print(f"[1] GET {endpoint}")
    resp = requests.get(endpoint, timeout=30)
    print(f"    Status: {resp.status_code}")

    if resp.status_code == 200:
        print("    Endpoint returned 200 without payment (x402 might be disabled)")
        print(json.dumps(resp.json(), indent=2))
        return

    if resp.status_code != 402:
        print(f"    Unexpected status {resp.status_code}: {resp.text[:500]}")
        sys.exit(1)

    # Step 2: Parse the 402 payment requirements (base64-encoded JSON header)
    payment_required_header = resp.headers.get("Payment-Required")
    if not payment_required_header:
        print("    ERROR: No Payment-Required header in 402 response")
        print(f"    Response headers: {dict(resp.headers)}")
        sys.exit(1)

    decoded_json = base64.b64decode(payment_required_header).decode("utf-8")
    payment_data = json.loads(decoded_json)
    print(f"    Payment requirements: {json.dumps(payment_data, indent=2)}")
    payment_required = parse_payment_required(payment_data)

    print(f"    Payment version: {payment_required.x402_version}")
    if hasattr(payment_required, "accepts"):
        for i, req in enumerate(payment_required.accepts):
            print(f"    Requirement [{i}]: scheme={req.scheme}, network={req.network}, "
                  f"pay_to={req.pay_to}, amount={req.get_amount()}")
    else:
        print(f"    V1 requirements: {payment_required}")

    if args.dry_run:
        print("\n[dry-run] Stopping before payment. Use without --dry-run to pay.")
        return

    # Step 3: Set up x402 client with signer
    account: LocalAccount = Account.from_key(private_key)
    signer = EthAccountSigner(account)
    print(f"\n[2] Signing payment from wallet: {signer.address}")

    client = x402ClientSync()
    client.register("eip155:8453", ExactEvmScheme(signer=signer))

    # Step 4: Create signed payment payload
    payment_payload = client.create_payment_payload(payment_required)
    payload_json = payment_payload.model_dump_json(by_alias=True, exclude_none=True)
    payload_b64 = base64.b64encode(payload_json.encode("utf-8")).decode("utf-8")
    print(f"    Payment payload created ({len(payload_json)} bytes JSON, {len(payload_b64)} bytes base64)")

    # Step 5: Retry with PAYMENT-SIGNATURE header (base64-encoded)
    print(f"\n[3] Retrying with PAYMENT-SIGNATURE header...")
    resp2 = requests.get(
        endpoint,
        headers={"PAYMENT-SIGNATURE": payload_b64},
        timeout=60,
    )
    print(f"    Status: {resp2.status_code}")

    if resp2.status_code == 200:
        data = resp2.json()
        print(f"\n    SUCCESS! Payment settled.")
        print(f"    Contract: {data.get('address')}")
        print(f"    Risk score: {data.get('score')}/100 ({data.get('level')})")
        print(f"    Findings: {len(data.get('findings', []))}")
        print(f"\n    Full response:")
        print(json.dumps(data, indent=2))
    else:
        print(f"    Payment failed: {resp2.text[:1000]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
