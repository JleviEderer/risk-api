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
- `src/risk_api/app.py` — Flask app + x402 middleware + request logging + dashboard
- `src/risk_api/config.py` — Environment config
- `scripts/health_check.py` — External health check for monitoring/alerting
- `scripts/register_moltmart.py` — Register agent + list service on MoltMart marketplace
- `scripts/register_work402.py` — Onboard agent on Work402 hiring marketplace (testnet)

## Key Env Vars
- `WALLET_ADDRESS` — payment destination (required)
- `BASE_RPC_URL` — defaults to https://mainnet.base.org
- `FACILITATOR_URL` — defaults to https://v2.facilitator.mogami.tech (Mogami — free, no auth, confirmed working for Base USDC). OpenFacilitator has gas limit bug (100k < 109k needed). Dexter was down 2026-02-23/24 (server upgrade).
- `NETWORK` — defaults to eip155:8453 (Base mainnet, CAIP-2 format)
- `PRICE` — defaults to $0.10
- `ERC8004_AGENT_ID` — ERC-8004 agent registration ID (optional, adds `registrations` to metadata)
- `BASESCAN_API_KEY` — Basescan API key for deployer reputation checks (optional, degrades gracefully)
- `PUBLIC_URL` — public base URL for agent metadata endpoint (optional, e.g. `https://risk-api.life.conway.tech`). Falls back to `request.url_root` if unset. Required behind reverse proxies that rewrite the origin.
- `REQUEST_LOG_PATH` — path for structured JSON-lines request log (optional, e.g. `/root/risk-api-logs/requests.jsonl`)
- `PINATA_JWT` — Pinata API JWT for IPFS pinning (optional, used by `scripts/pin_metadata_ipfs.py`)
- `MOLTMART_API_KEY` — MoltMart marketplace API key (optional, used by `scripts/register_moltmart.py`)
- `MOLTMART_SERVICE_ID` — MoltMart service listing ID (optional, for updates)
- `WORK402_DID` — Work402 agent DID (optional, returned after onboarding)

## Gotchas
- No web3.py — we use raw JSON-RPC via requests
- Bytecode analysis is pure pattern matching, no LLM inference
- x402 SDK v2.2.0 has no `PaymentMiddleware` class — we build Flask middleware manually using `x402HTTPResourceServerSync` + `process_http_request`
- x402 SDK v2 reads payment from `PAYMENT-SIGNATURE` header (not `X-PAYMENT`) via the adapter's `get_header()` — clients must send this header name
- x402 SDK needs `httpx` at runtime (undeclared transitive dep)
- Network must be CAIP-2 format: `eip155:84532` (sepolia), `eip155:8453` (mainnet)
- `create_app(enable_x402=False)` to skip payment middleware in tests
- All scores 0-100, higher = riskier
- 8 detectors: 7 bytecode pattern detectors + 1 deployer reputation detector (Basescan)
- Proxy detection covers EIP-1967, EIP-1822, and OpenZeppelin (pre-1967) slots
- Proxy contracts auto-resolve implementation via `eth_getStorageAt` (max 1 hop). Impl findings get `impl_` prefixed detector names. Response includes nested `implementation` object. Graceful degradation if storage read or impl fetch fails.
- Deployer reputation detector requires `BASESCAN_API_KEY`; silently skipped without it
- `analyze_contract()` results are cached (TTL 5 min, max 512 entries, case-insensitive address keys). Use `clear_analysis_cache()` in test setup/teardown. RPC-level caching also exists via `@lru_cache` on `get_code()`/`get_storage_at()`.
- `/dashboard` serves an inline HTML analytics page (Chart.js from CDN, auto-refreshes every 30s, not behind x402 paywall)
- `/avatar.png` serves agent avatar image (loaded from `x402JobsAvatar.png` at module level, searches package dir then repo root)
- `/openapi.json` serves OpenAPI 3.0.3 spec with dynamic `servers` array from `PUBLIC_URL`
- `/.well-known/ai-plugin.json` serves AI plugin manifest for agent tool discovery
- `/agent-metadata.json` includes `image`, `updatedAt`, `pricing`, `openapi_url`, `capabilities` fields for registry quality scoring
- `/.well-known/agent.json` and `/.well-known/agent-card.json` both serve A2A (Agent-to-Agent) protocol agent card for discovery (8004scan expects `agent-card.json`)
- All discovery endpoints (`/avatar.png`, `/openapi.json`, `/.well-known/ai-plugin.json`, `/.well-known/agent.json`, `/.well-known/agent-card.json`, `/agent-metadata.json`) are NOT behind x402 paywall
- Agent metadata `services` array includes: web, A2A, OASF (skills=OASF taxonomy codes, domains=OASF taxonomy codes), agentWallet (CAIP-10 format)
- OASF taxonomy codes: skills `1304` (Risk Classification), domains `109` (Blockchain), `10903` (Smart Contracts), `405` (Risk Management)
- On-chain `agentURI` points to IPFS (`ipfs://{CID}`) for content-addressed metadata (fixes 8004scan WA040). HTTP endpoint stays live for other discovery. To update: `python scripts/pin_metadata_ipfs.py` → `python scripts/register_erc8004.py --update-uri ipfs://{CID}`
