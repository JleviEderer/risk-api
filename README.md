# Augur - Smart Contract Risk Scoring API

> Base mainnet smart contract bytecode risk analysis for agents and the developers building them, sold via [x402](https://x402.org) at $0.10/call in USDC on Base.

**Live:** https://augurrisk.com
**Agent registry:** [ERC-8004 #19074 on Base](https://8004scan.io/agents/base/19074)
**GitHub:** https://github.com/JleviEderer/risk-api
**Agent wallet:** `0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891`

---

## What It Does

Augur accepts a Base mainnet contract address and returns a composite 0-100 risk score derived from deterministic bytecode pattern analysis - no LLM inference, no external oracles. A paying agent sends one HTTP request, gets a structured risk assessment back.

Canonical message: Augur scores Base mainnet smart contract bytecode for agents and the developers building them. It is a fast deterministic screen, not a full security audit or guarantee.

**Why x402?** GoPlus has 717M calls/month but requires API key signup - autonomous agents can't use it. Augur is the only x402-native risk scoring option: pay with USDC, get a result, no account needed.

---

## Fastest Paid Call (Python)

Use the existing Python x402 client flow. The full guide is in [`docs/PYTHON_PAYMENT_QUICKSTART.md`](docs/PYTHON_PAYMENT_QUICKSTART.md).

```bash
pip install -e ".[dev]"
export CLIENT_PRIVATE_KEY="0xYOUR_PRIVATE_KEY"
python scripts/test_x402_client.py --dry-run
python scripts/test_x402_client.py
```

On PowerShell, set the key with:

```powershell
$env:CLIENT_PRIVATE_KEY = "0xYOUR_PRIVATE_KEY"
```

What happens:

1. The first request returns `402 Payment Required`
2. The client signs the payment payload from your wallet
3. The script retries with `PAYMENT-SIGNATURE`
4. Augur returns the scored JSON response

Defaults:

- URL: `https://augurrisk.com`
- Contract: `0x4200000000000000000000000000000000000006` (Base WETH)
- Script: `scripts/test_x402_client.py`

Use `--dry-run` first if you want to inspect the payment requirements without spending funds.

## JavaScript / Node Example

A matching Node example now lives in [`examples/javascript/augur-paid-call`](examples/javascript/augur-paid-call).

```bash
cd examples/javascript/augur-paid-call
npm install
npm run dry-run
```

For a real paid call:

```bash
cp .env.example .env
# set CLIENT_PRIVATE_KEY in .env
npm start
```

Need the protocol steps without code first? Read the live explainer at [`/how-payment-works`](https://augurrisk.com/how-payment-works).

## MCP / Claude Desktop Example

A local stdio MCP wrapper now lives in [`examples/javascript/augur-mcp`](examples/javascript/augur-mcp).

This is the recommended MCP packaging shape for Augur:

1. keep Augur itself as the canonical paid HTTP API
2. run the MCP bridge locally so wallet signing stays on the operator machine
3. expose Augur as MCP tools that pay `/analyze` over x402 on demand

Quick start:

```bash
cd examples/javascript/augur-mcp
npm install
npm run smoke
npm run smoke -- --paid
```

The example exports two tools:

- `analyze_base_contract_risk`
- `describe_augur_service`

---

## API

### `GET /analyze?address={base_contract_address}`

**Requires x402 payment: $0.10 USDC on Base (eip155:8453)**

The x402 flow:
1. Client sends request -> server returns `402 Payment Required` with payment details in `Payment-Required` header
2. Client pays via facilitator, gets settlement proof
3. Client resends request with `PAYMENT-SIGNATURE` header containing proof
4. Server verifies with facilitator -> returns analysis

Wallet, EOA, or undeployed addresses return `422` with an explicit `No contract bytecode found at Base address: ...` error and are not billed.

**Example response:**
```json
{
  "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
  "score": 60,
  "level": "high",
  "bytecode_size": 1485,
  "findings": [
    {
      "detector": "proxy",
      "severity": "medium",
      "title": "EIP-1967 Proxy Detected",
      "description": "Contract uses the EIP-1967 transparent proxy pattern. Logic resides in a separate implementation contract that can be upgraded.",
      "points": 20
    },
    {
      "detector": "delegatecall",
      "severity": "medium",
      "title": "Delegatecall Usage",
      "description": "Contract uses DELEGATECALL to execute code from another contract.",
      "points": 15,
    }
  ],
  "category_scores": {
    "proxy": 20,
    "delegatecall": 15,
    "impl_delegatecall": 15,
    "impl_hidden_mint": 10
  },
  "implementation": {
    "address": "0x2cE6409Bc2Ff3E36834E44e15bbE83e4aD02d779",
    "bytecode_size": 24576,
    "findings": [...],
    "category_scores": {...}
  }
}
```

**Risk levels:**
| Score | Level |
|-------|-------|
| 0-15 | safe |
| 16-35 | low |
| 36-55 | medium |
| 56-75 | high |
| 76-100 | critical |

`safe` means no major bytecode-level risk signals were detected in that scan. It does not guarantee the contract is safe.

### Free Endpoints (no payment required)

| Endpoint | Description |
|----------|-------------|
| `GET /health` | `{"status": "ok"}` |
| `GET /` | Landing page with Schema.org JSON-LD, FAQPage, OpenGraph |
| `GET /openapi.json` | OpenAPI 3.0.3 spec with dynamic `servers` array |
| `GET /agent-metadata.json` | ERC-8004 compatible agent metadata |
| `GET /.well-known/agent.json` | A2A agent card |
| `GET /.well-known/agent-card.json` | A2A agent card (8004scan canonical path) |
| `GET /.well-known/x402` | x402 discovery document |
| `GET /.well-known/ai-plugin.json` | AI plugin manifest |
| `GET /.well-known/api-catalog` | RFC 9727 API catalog (linkset+json) |
| `GET /avatar.png` | Agent avatar image |
| `GET /llms.txt` | LLM-optimized service description |
| `GET /llms-full.txt` | Full LLM documentation with schema + examples |
| `GET /robots.txt` | Crawler directives |
| `GET /sitemap.xml` | XML sitemap |
| `GET /dashboard` | Analytics dashboard (Chart.js, auto-refreshes 30s) |

---

## Architecture

```
Request
  `-- Flask app (app.py)
      |-- validate_analyze_params  <- before_request hook, 422 on bad/missing address
      |-- x402_payment_gate        <- before_request hook, 402 if unpaid
      `-- /analyze handler
            `-- analyze_contract() [engine.py]
                  |-- get_code(address) [rpc.py]                      -> raw bytecode hex
                  |-- disassemble(bytecode) [disassembler.py]         -> list[Instruction]
                  |-- run_all_detectors(instructions) [patterns.py]   -> list[Finding]
                  |-- detect_deployer_reputation() [reputation.py]    -> Finding|None
                  |-- proxy slot lookup -> get_storage_at() [rpc.py]
                  |   `-- if impl found: recurse on impl address (max 1 hop)
                  `-- compute_score(findings) [scoring.py]            -> ScoreResult
```

### Analysis Pipeline Modules

| Module | Role |
|--------|------|
| `chain/rpc.py` | Raw JSON-RPC over `requests` - `get_code()`, `get_storage_at()`. LRU-cached. **No web3.py.** |
| `analysis/opcodes.py` | EVM opcode table |
| `analysis/disassembler.py` | Bytecode hex -> `list[Instruction]` |
| `analysis/selectors.py` | PUSH4 extraction -> known malicious/suspicious selector matching |
| `analysis/patterns.py` | 7 bytecode pattern detectors -> `list[Finding]` |
| `analysis/reputation.py` | 8th detector: deployer reputation via Basescan API |
| `analysis/scoring.py` | Weighted scoring with per-category caps -> 0-100 score + RiskLevel |
| `analysis/engine.py` | Orchestrator: fetch -> disassemble -> detect -> proxy-resolve -> score. TTL cache (5min, 128 entries). |

### The 8 Detectors

| Detector | Max Points | How |
|----------|-----------|-----|
| `proxy` | 10 | EIP-1967, EIP-1822, OpenZeppelin proxy storage slots |
| `reentrancy` | 10 | CALL before SSTORE patterns |
| `selfdestruct` | 30 | SELFDESTRUCT opcode presence |
| `honeypot` | 25 | Selector patterns blocking transfers/sells |
| `hidden_mint` | 25 | Selector patterns for undisclosed minting |
| `fee_manipulation` | 15 | Dynamic fee/tax selector patterns |
| `delegatecall` | 15 | DELEGATECALL opcode presence |
| `deployer_reputation` | 10 | Basescan: deployer tx count, contract count, age |

Proxy contracts auto-resolve their implementation (EIP-1967 -> EIP-1822 -> OZ, max 1 hop). Implementation findings are prefixed `impl_` and merged into the final score.

---

## Stack - **Python 3.10+** package requirement (**Python 3.13** in Docker), **Flask**, **gunicorn** - **x402[flask,evm] >=2.3.0,<2.4** - x402 payment middleware - **httpx** - x402 SDK runtime dependency (undeclared transitive dep, must install explicitly) - **requests** - Base RPC calls - **python-dotenv**, **PyJWT**, **cryptography** - **pytest + responses** (testing), **pyright** (type checking)

---

## Payment Infrastructure

| Facilitator | URL | Notes |
|-------------|-----|-------|
| **CDP (production)** | `https://api.cdp.coinbase.com/platform/v2/x402` | Requires Ed25519 JWT auth. Required for Coinbase Bazaar indexing. 1K tx/month free. |
| **Mogami (fallback)** | `https://v2.facilitator.mogami.tech` | Free, no auth, gas limit 120k. Confirmed working. |
| OpenFacilitator | `https://pay.openfacilitator.io` | **BROKEN** - gas limit 100k < 109k needed. Silently reverts. |

### Critical x402 SDK Gotchas - Current **x402[flask,evm] 2.3.x** integration does **not** use a `PaymentMiddleware` class here - middleware is built manually using `x402HTTPResourceServerSync` + `process_http_request()` (see `app.py`) - Payment header is `PAYMENT-SIGNATURE` (not `X-PAYMENT`) - Network must be CAIP-2: `eip155:8453` (mainnet), `eip155:84532` (sepolia) - CDP auth: SDK does NOT auto-read `CDP_API_KEY_ID`/`CDP_API_KEY_SECRET` - `cdp_auth.py` implements `CreateHeadersAuthProvider` manually using Ed25519 JWT - `create_app(enable_x402=False)` disables payment middleware - used in tests - x402 EVM import chain pulls ~60 packages (web3, aiohttp, eth_account, pydantic). On Windows/MINGW without writable `__pycache__`, imports hang indefinitely. Tests use a **fake x402 gate** to avoid this - see `tests/conftest.py`

---

## Project Structure

```
risk-api/
|-- src/risk_api/
|   |-- app.py                  # Flask app, x402 middleware, ALL route handlers
|   |-- config.py               # Environment config (load_config() -> Config dataclass)
|   |-- cdp_auth.py             # CDP facilitator JWT auth (Ed25519, no full cdp-sdk)
|   |-- x402JobsAvatar.png      # Agent avatar (loaded at module level)
|   |-- analysis/
|   |   |-- engine.py           # Main orchestrator + TTL result cache
|   |   |-- patterns.py         # 7 detectors + Finding/Severity dataclasses + proxy slots
|   |   |-- scoring.py          # Weighted scoring + RiskLevel + CATEGORY_CAPS
|   |   |-- disassembler.py     # Bytecode hex -> list[Instruction]
|   |   |-- opcodes.py          # EVM opcode table
|   |   |-- selectors.py        # PUSH4 extraction + malicious/suspicious selector lists
|   |   `-- reputation.py       # Basescan deployer reputation detector
|   `-- chain/
|       `-- rpc.py              # Raw JSON-RPC: get_code(), get_storage_at(). LRU-cached.
|-- tests/
|   |-- conftest.py             # Fixtures + fake x402 gate (avoids SDK import hang)
|   |-- test_app.py             # Flask route integration tests
|   |-- test_engine.py          # Engine + proxy resolution
|   |-- test_patterns.py        # Detector unit tests
|   |-- test_scoring.py         # Scoring edge cases
|   |-- test_selectors.py       # Selector extraction
|   |-- test_rpc.py             # RPC client
|   `-- test_pin_metadata.py    # IPFS metadata structure
|-- scripts/
|   |-- pin_metadata_ipfs.py    # Pin agent metadata to IPFS via Pinata
|   |-- register_erc8004.py     # Register/update ERC-8004 on Base (reads ~/.automaton/wallet.json)
|   |-- register_x402jobs.py    # List on x402.jobs marketplace
|   |-- register_moltmart.py    # List on MoltMart marketplace
|   |-- register_work402.py     # Onboard on Work402 (testnet)
|   |-- health_check.py         # External health check script (Better Stack / uptime monitors)
|   `-- test_x402_client.py     # First paid-call Python quickstart / manual x402 payment flow
|-- examples/
|   `-- javascript/
|       |-- augur-paid-call/      # Node x402 client example for Augur
|       `-- augur-mcp/            # Local stdio MCP wrapper that pays Augur over x402
|-- docs/
|   |-- DECISIONS.md            # ADRs (ADR-001 through ADR-006)
|   |-- BizPlanning.md          # Strategy, moat thesis, pricing rationale
|   |-- MCP_PACKAGING_PLAN.md   # Chosen MCP wrapper shape and rationale
|   |-- PYTHON_PAYMENT_QUICKSTART.md # Fastest path to a successful paid Python call
|   `-- REGISTRATIONS.md        # Registry tracker + IPFS workflow
|-- .github/workflows/
|   `-- fly-deploy.yml          # Auto-deploy to Fly.io on push to master
|-- .claude/
|   |-- CLAUDE.md               # Project-level AI coding rules
|   `-- napkin.md               # Session lessons, gotchas, corrections log
|-- Dockerfile
|-- fly.toml                    # Fly.io config (app: augurrisk, region: iad)
|-- pyproject.toml              # Package + deps + pytest config
|-- HANDOVER.md                 # Latest session handover (AI agent shift-change report)
`-- README.md                   # This file
```

---

## Environment Variables

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `WALLET_ADDRESS` | Yes | - | USDC payment destination |
| `BASE_RPC_URL` | No | `https://mainnet.base.org` | Base JSON-RPC endpoint |
| `FACILITATOR_URL` | No | `https://v2.facilitator.mogami.tech` | Production uses CDP URL |
| `CDP_API_KEY_ID` | No | - | Required for CDP facilitator |
| `CDP_API_KEY_SECRET` | No | - | Ed25519 base64, required for CDP |
| `NETWORK` | No | `eip155:8453` | CAIP-2 format. Not a string name. |
| `PRICE` | No | `$0.10` | Use single quotes: `'$0.10'` - double quotes expand `$0` |
| `BASESCAN_API_KEY` | No | - | Enables deployer reputation detector. Degrades gracefully without it. |
| `PUBLIC_URL` | No | - | Required behind reverse proxies. e.g. `https://augurrisk.com` |
| `REQUEST_LOG_PATH` | No | - | Path for JSON-lines request log |
| `PINATA_JWT` | No | - | Pinata API JWT for IPFS pinning |
| `ERC8004_AGENT_ID` | No | - | Adds `registrations` array to agent metadata |

**Production secrets** are stored in Fly.io (`fly secrets set KEY=VALUE -a augurrisk`), not in `.env`.

---

## Commands

```bash
# Install
pip install -e ".[dev]"

# Run dev server
flask --app risk_api.app:create_app run

# Run prod (matches Dockerfile)
gunicorn "risk_api.app:create_app()" --bind 0.0.0.0:8000 --workers 1 --max-requests 500 --max-requests-jitter 50

# Test (238 tests, ~5s)
python -m pytest tests/ -v

# Coverage
python -m pytest tests/ -v --cov=src/risk_api

# Type check (slow on Windows - use CI instead)
python -m pyright src/ tests/

# Docker
docker compose up -d --build

# Deploy to Fly.io (auto-deploys on push to master, but manual works too)
fly deploy

# Fly.io ops
fly logs -a augurrisk               # tail production logs
fly status -a augurrisk             # machine status
fly scale memory 512 -a augurrisk   # increase memory if OOM

# External uptime probe
python scripts/health_check.py      # check the public /health endpoint

# Fastest live paid-call test (Python)
python scripts/test_x402_client.py --dry-run
python scripts/test_x402_client.py

# Fastest live paid-call test (JavaScript / Node)
cd examples/javascript/augur-paid-call
npm install
npm run dry-run

# MCP wrapper smoke test (Node / stdio)
cd examples/javascript/augur-mcp
npm install
npm run smoke
npm run smoke -- --paid

# Load .env in bash
set -a && source .env && set +a

# Re-pin agent metadata to IPFS (outputs new CID)
python scripts/pin_metadata_ipfs.py

# Update on-chain agent URI after re-pinning
python scripts/register_erc8004.py --update-uri ipfs://<NEW_CID>
```

---

## Monitoring

- Better Stack is the external uptime monitor for `https://augurrisk.com/health`.
- `scripts/health_check.py` mirrors that public health probe for manual checks and simple alert integrations.
- `/dashboard` and `/stats` are per-deployment request-log views, not the canonical uptime source of truth.

---

## Testing

**238 tests, ~5 seconds** on Windows.

The x402 SDK imports ~60 packages and hangs indefinitely on Windows/MINGW (no `.pyc` write permission). `tests/conftest.py` patches `risk_api.app._setup_x402_middleware` with a lightweight fake gate to avoid importing the SDK in tests.

Key test fixtures:
- `client` - x402 disabled (`enable_x402=False`), for testing route logic
- `client_with_x402` - fake x402 gate active, for testing 402 behavior
- `app` - Flask app instance for config/context tests

RPC calls are mocked via the `responses` library. Call `clear_analysis_cache()` in test setup/teardown to prevent TTL cache interference.

**Do not run `pyright` locally on Windows** - same import hang. Run it in CI.

---

## Deployment

**Platform:** Fly.io, `iad` region, app name `augurrisk`
**Domain:** augurrisk.com -> Cloudflare DNS -> Fly.io
**Auto-deploy:** GitHub Actions (`.github/workflows/fly-deploy.yml`) - triggers on push to `master`
**Health check:** `GET /health` -> `{"status": "ok"}`
**Memory:** 256MB VM. 1 gunicorn worker + `--max-requests 500` for leak prevention. If OOM: `fly scale memory 512 -a augurrisk`.

---

## Agent Discovery

| Registry | Details |
|----------|---------|
| **ERC-8004 #19074** | Base mainnet, owner `0x1358...9891`, IPFS metadata |
| **Coinbase Bazaar** | Production is using the CDP facilitator, but Augur is still missing from the public discovery feed as of 2026-03-08 |
| **x402.jobs** | Listed at the canonical `augurrisk-com/augur-base` URL and browser-verified correct on 2026-03-08 |
| **x402list.fun** | Listed (old domain - needs update) |

**Current on-chain agent URI:** `ipfs://QmNUK1ZnwN8fShKFFSmDa2EZvy6VBquftpU7m2oazsPZv1`

To update metadata: re-pin with `pin_metadata_ipfs.py`, then call `register_erc8004.py --update-uri ipfs://<CID>`. Agent wallet private key is at `~/.automaton/wallet.json`.

---

## Key Design Decisions

- **No LLM in scoring pipeline** - deterministic pattern matching only. Speed + reliability + margins.
- **No web3.py** - raw JSON-RPC via `requests`. Lighter dependency footprint.
- **Single price tier ($0.10)** - no free tier (removes x402 differentiator), no tiering (over-engineering).
- **Pre-paywall validation** - malformed address requests rejected 422 before x402 processing, preventing wasted payment attempts.
- **Proxy auto-resolution** - follows EIP-1967/1822/OZ impl slot (max 1 hop) so USDC/WETH score correctly against their actual bytecode.
- **Moat thesis** - autonomous agents can't use GoPlus (requires signup). x402-native = frictionless agent integration. Window: ~6-18 months before incumbents adapt.

Full ADR log: `docs/DECISIONS.md`
Full strategy: `docs/BizPlanning.md`

---

## License

MIT
