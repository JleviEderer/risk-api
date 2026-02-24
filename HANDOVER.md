# Handover — risk-api

**Session date:** 2026-02-24 (afternoon)
**Repo:** `C:/Users/justi/dev/risk-api/`
**Live at:** https://risk-api.life.conway.tech
**Uncommitted changes:** Yes — facilitator switch, request logging, health check, tests

---

## What We Did This Session

### 1. Diagnosed x402 Settlement Failure (from prior session)

The previous session discovered that our x402 payments were verifying (200 response) but USDC never arrived in the API wallet. Root cause: **OpenFacilitator gas limit bug**.

- OpenFacilitator submits `transferWithAuthorization` on Base USDC with gas limit = 100,000
- Base USDC (through its proxy) actually needs ~109,000 gas
- Transaction reverts silently, server swallows the error in `x402_settle` after_request handler
- **Proof:** Same payment signed once, settled through two different facilitators:
  - OpenFacilitator: gas limit 100k, used 98,964 → **REVERT**
  - Mogami: gas limit 120k, used 108,808 → **SUCCESS**

### 2. Switched Facilitator to Mogami

- Updated `config.py` default from `https://x402.dexter.cash` to `https://v2.facilitator.mogami.tech`
- Updated Conway startup script (`/root/start-risk-api.sh`) — `FACILITATOR_URL` env var
- Fixed `PRICE='$0.10'` quoting bug (bash `$0` was expanding to script name)
- Uploaded `config.py` to both Conway paths, restarted gunicorn
- **Verified end-to-end:** Payment settled, USDC arrived on-chain
- API wallet balance: **$0.20 USDC** (2 successful Mogami settlements)

### 3. Comprehensive Facilitator Research

Researched all x402 facilitators for compatibility with our setup (x402 SDK v2, Base mainnet, USDC):

| Facilitator | Status | Compatible? | Notes |
|---|---|---|---|
| **Mogami v2** | UP, confirmed | YES (120k gas) | Current production facilitator |
| **Heurist** | UP | Untested gas | 8 signers, good redundancy |
| **PayAI** | UP | Untested gas | 15 signers, 14+ chains |
| **Daydreams** | UP | Untested gas | Also supports "upto" scheme |
| **Ultravioleta DAO** | UP | Untested gas | 20+ chains |
| **Coinbase CDP** | UP | Likely yes | Requires CDP API key |
| **Dexter** | DOWN | Unknown | Server upgrade (4x capacity, AWS migration) — should be back soon |
| **OpenFacilitator** | UP | **NO** (100k gas) | Broken for Base USDC |
| **Meridian** | UP | **NO** (v1 only) | Incompatible with x402 SDK v2 |

**Decision:** Use Mogami now, test others when Dexter is back. Don't add facilitator fallback logic until we've confirmed gas limits on at least 2-3 alternatives.

### 4. Added Request Logging & Analytics

Added structured JSON-lines logging for every `/analyze` request:

- **Before request:** Timer starts
- **After request:** Logs JSON entry with: `ts`, `address`, `status`, `paid`, `duration_ms`, `user_agent`, `method`, `score`, `level`
- **File handler:** Writes to `REQUEST_LOG_PATH` env var (production: `/root/risk-api-logs/requests.jsonl`)
- **`/stats` endpoint:** Returns `total_requests`, `paid_requests`, last 20 entries
- **Deployed to Conway:** Already capturing requests

### 5. Created Health Check Script

`scripts/health_check.py` — standalone script for external monitoring:
- Pings `/health`, exits 0 (ok) or 1 (fail)
- Optional `--webhook` flag for Slack/Discord alerts
- Recommended BetterStack (free tier: 10 monitors, 3-min intervals, free status page) over UptimeRobot for external monitoring — user hasn't set this up yet

### 6. Updated Documentation

- `CLAUDE.md` — new env var (`REQUEST_LOG_PATH`), facilitator change, structure update
- Memory file updated with facilitator findings, Mogami switch, balance

---

## Files Modified (Uncommitted)

| File | Changes |
|------|---------|
| `src/risk_api/config.py` | Default facilitator: Dexter → Mogami |
| `src/risk_api/app.py` | Added `_setup_request_logging()`, `_configure_request_log_file()`, `/stats` endpoint, timer in before_request |
| `tests/test_logging.py` | **NEW** — 6 tests for logging + stats |
| `scripts/health_check.py` | **NEW** — External health check with webhook support |
| `CLAUDE.md` | New env var, facilitator docs, structure update |
| `HANDOVER.md` | This file |

**Also deployed to Conway (not in git):**
- Updated `app.py` in both source + site-packages paths
- Updated `config.py` in both paths
- Updated `/root/start-risk-api.sh` (Mogami URL, REQUEST_LOG_PATH, fixed PRICE quoting)
- Created `/root/risk-api-logs/` directory

---

## Key Decisions

| Decision | Why |
|----------|-----|
| Switch to Mogami facilitator | Only confirmed-working free facilitator for Base USDC. OpenFacilitator gas limit is broken. Dexter is down for upgrade. |
| Don't add facilitator fallback yet | Can't fall back to untested facilitators — they might silently fail the same way. Test gas limits first, then add fallback. |
| Log to JSON lines file | Simple, greppable, no dependencies. `/stats` endpoint reads it on demand. |
| Don't log /health requests | Noise — only log /analyze which is the business-critical path. |
| Recommend BetterStack over UptimeRobot | 3-min intervals (vs 5), free status page, we only need 1 monitor so lower limit is irrelevant. |

---

## Gotchas & Lessons Learned

### Conway Deployment
- **Upload to BOTH paths:** `/root/risk-api/src/risk_api/` AND `/root/risk-api-venv/lib/python3.10/site-packages/risk_api/` — gunicorn loads from site-packages
- **Shell escaping through Conway API:** Use base64-encoded Python scripts for anything with dollar signs or quotes. `sed` and heredocs are unreliable through the double-indirection (local Python → Conway API → remote bash).
- **`$0` in bash scripts:** `export PRICE="$0.10"` expands `$0` to the script name. Must use single quotes: `export PRICE='$0.10'`
- **Compound commands on Conway SSH:** Can fail. Use separate exec calls.

### x402 / Facilitators
- **Gas limits are internal to facilitators** — not exposed via API. Only way to know is to test with real settlement.
- **OpenFacilitator 100k gas limit** — Base USDC `transferWithAuthorization` through proxy needs ~109k. Reverts silently.
- **Settlement errors are swallowed** — Server returns 200 to client even if settlement fails. The `x402_settle` after_request handler catches exceptions and only logs them.
- **Dexter is upgrading** — @dexteraisol on X announced 4x server upgrade on AWS. Should be back soon.
- **Meridian is v1 only** — Uses legacy network names, not CAIP-2. Incompatible with x402 SDK v2.

### Testing
- **Windows file handle cleanup** — `logging.FileHandler` keeps files open on Windows. Must close handlers explicitly in test teardown before temp directory cleanup.

---

## Current State

### Live API
- **URL:** https://risk-api.life.conway.tech
- **Status:** Healthy, all routes working
- **Facilitator:** Mogami (`https://v2.facilitator.mogami.tech`) — confirmed working
- **Paywall:** Active on `/analyze` (GET+POST), open on `/health`, `/stats`, `/agent-metadata.json`, `/.well-known/x402-verification.json`
- **Logging:** Active, writing to `/root/risk-api-logs/requests.jsonl`

### Agent Wallet
- **Address:** `0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891`
- **USDC Balance:** $0.20 (2 test settlements via Mogami)

### Payer Wallet (test)
- **Address:** `0x79301Cf19Aaea29fbe40F0F5B78F73e2c3b0a2b8` (Conway wallet)
- **Private key exposed in chat history** — consider compromised, move funds if significant

### Local Dev
- **115 tests pass**, 0 pyright errors
- Git: uncommitted changes (facilitator switch + logging + health check)

### Discovery
- **ERC-8004:** Agent #19074 on Base mainnet
- **x402.jobs:** Listed, ownership verified (badge may still show as unverified — platform bug)

---

## Open Issues

1. **Uncommitted changes** — Facilitator switch, logging, health check, and tests need to be committed
2. **External monitoring not set up** — BetterStack recommended but user hasn't created account yet
3. **Facilitator fallback not implemented** — Need to test Heurist/PayAI/Dexter gas limits before adding fallback logic
4. **Dexter coming back** — Watch @dexteraisol on X. When back, test gas limit with real settlement
5. **Settlement errors are silent** — Server returns 200 even if facilitator settlement fails. Consider: log more aggressively, or return a warning header to client

---

## Next Steps

1. **Commit the changes** — facilitator switch + logging + health check + tests
2. **Set up BetterStack** — free external monitoring for `/health` endpoint
3. **Test facilitator gas limits** — When Dexter is back, run `scripts/test_x402_client.py` against each facilitator
4. **Add facilitator fallback** — Once 2-3 facilitators are confirmed working, add retry logic in settlement
5. **Monitor /stats** — Check `https://risk-api.life.conway.tech/stats` periodically for organic traffic
6. **Result caching** — Same contract re-analyzed every call. Add TTL cache when traffic justifies it.

---

## Commands

```bash
cd C:/Users/justi/dev/risk-api

# Install
pip install -e ".[dev]"

# Test
pytest tests/ -v --cov=src/risk_api

# Type check
python -m pyright src/ tests/

# Health check (local)
python scripts/health_check.py

# x402 client test (dry run — no payment)
python scripts/test_x402_client.py --dry-run

# x402 client test (real payment — costs $0.10 USDC)
export CLIENT_PRIVATE_KEY="0x..."
python scripts/test_x402_client.py

# Check live stats
curl https://risk-api.life.conway.tech/stats

# Verify live
curl https://risk-api.life.conway.tech/health

# Conway sandbox
# Sandbox ID: 76cfc42df7955d2a7de0ec7e2473f686
# Startup script: /root/start-risk-api.sh
# Request log: /root/risk-api-logs/requests.jsonl
# Gunicorn log: /root/gunicorn.log
# Restart: pkill -f gunicorn; nohup /root/start-risk-api.sh > /root/gunicorn.log 2>&1 &
# Deploy: Upload to BOTH /root/risk-api/src/risk_api/ AND /root/risk-api-venv/lib/python3.10/site-packages/risk_api/
```
