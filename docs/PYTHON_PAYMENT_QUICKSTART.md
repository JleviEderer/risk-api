# Python Payment Quickstart

Fastest path from zero to a successful paid call against Augur.

## What You Need

- Python 3.10+
- A wallet private key you control
- At least `$0.10` USDC on Base mainnet in that wallet

## 1) Install The Repo

```bash
pip install -e ".[dev]"
```

That installs the x402 client pieces used by `scripts/test_x402_client.py`.

## 2) Set Your Wallet Key

Bash:

```bash
export CLIENT_PRIVATE_KEY="0xYOUR_PRIVATE_KEY"
```

PowerShell:

```powershell
$env:CLIENT_PRIVATE_KEY = "0xYOUR_PRIVATE_KEY"
```

Use a wallet you control and fund specifically for testing. The script will sign a real x402 payment.

## 3) See The 402 Response First

```bash
python scripts/test_x402_client.py --dry-run
```

By default this hits:

- `https://augurrisk.com`
- `GET /analyze?address=0x4200000000000000000000000000000000000006`

Expected behavior:

1. Request returns `402 Payment Required`
2. Script decodes and prints the `Payment-Required` header
3. Script stops before signing anything

This is the fastest way to confirm the endpoint, payment requirements, and Base network settings are all correct.

## 4) Make The Paid Call

```bash
python scripts/test_x402_client.py
```

Expected behavior:

1. First request returns `402`
2. Script signs the payment payload from your wallet
3. Script retries with `PAYMENT-SIGNATURE`
4. Augur returns JSON with `score`, `level`, `findings`, and optional proxy implementation details

## 5) Use A Different Contract

```bash
python scripts/test_x402_client.py --address 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
```

You can also point the client at a local server:

```bash
python scripts/test_x402_client.py --url http://localhost:5000 --address 0x4200000000000000000000000000000000000006
```

## Common Errors

- `422 No contract bytecode found at Base address: ...`
  You passed a wallet, EOA, or undeployed address. Augur only analyzes deployed Base mainnet contracts.
- `200 without payment`
  x402 is disabled on the target server.
- `402` but no usable follow-up
  The server is misconfigured or you are not hitting the expected Augur endpoint.

## Where The Flow Lives

- Script: `scripts/test_x402_client.py`
- Public endpoint: `https://augurrisk.com/analyze`
- Discovery doc: `https://augurrisk.com/.well-known/x402`
