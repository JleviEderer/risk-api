# risk-api — Smart Contract Risk Scoring API

## Stack
- Python 3.10+, Flask, gunicorn, x402[flask,evm] v2.2.0, httpx
- requests (Base RPC), python-dotenv
- pytest + responses (testing), pyright (type checking)
- Docker + docker-compose (production deployment)

## Commands
- Install: `pip install -e ".[dev]"`
- Run (dev): `flask --app risk_api.app:create_app run`
- Run (prod): `gunicorn "risk_api.app:create_app()" --bind 0.0.0.0:8000 --workers 2`
- Docker: `docker compose up -d --build`
- Test: `pytest tests/ -v`
- Coverage: `pytest tests/ -v --cov=src/risk_api`

## Structure
- `src/risk_api/analysis/` — EVM bytecode analysis pipeline
- `src/risk_api/chain/` — Base RPC client
- `src/risk_api/app.py` — Flask app + x402 middleware
- `src/risk_api/config.py` — Environment config

## Key Env Vars
- `WALLET_ADDRESS` — payment destination (required)
- `BASE_RPC_URL` — defaults to https://mainnet.base.org
- `FACILITATOR_URL` — defaults to https://x402.dexter.cash (Dexter — free, no auth). Production currently uses https://pay.openfacilitator.io (Dexter was down 2026-02-23)
- `NETWORK` — defaults to eip155:8453 (Base mainnet, CAIP-2 format)
- `PRICE` — defaults to $0.10

## Gotchas
- No web3.py — we use raw JSON-RPC via requests
- Bytecode analysis is pure pattern matching, no LLM inference
- x402 SDK v2.2.0 has no `PaymentMiddleware` class — we build Flask middleware manually using `x402HTTPResourceServerSync` + `process_http_request`
- x402 SDK needs `httpx` at runtime (undeclared transitive dep)
- Network must be CAIP-2 format: `eip155:84532` (sepolia), `eip155:8453` (mainnet)
- `create_app(enable_x402=False)` to skip payment middleware in tests
- All scores 0-100, higher = riskier
- Proxy detection covers EIP-1967, EIP-1822, and OpenZeppelin (pre-1967) slots
