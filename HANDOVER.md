# Handover — risk-api

**Session date:** 2026-02-24 (early morning)
**Repo:** https://github.com/JleviEderer/risk-api (private)
**Latest commit on master:** `1205b57` (pushed)
**Uncommitted changes:** Yes — see Files Modified below
**Live at:** https://risk-api.life.conway.tech

---

## What We Did This Session

### 1. x402.jobs Resource Listing (fixed + rebuilt)

The x402.jobs resource listing from the previous session was deleted/missing ("Resource not found"). We:

1. Re-registered via `scripts/register_x402jobs.py` with a new API key
2. Discovered the "Run" button failed because it hit `/analyze` without an `address` param → 422 error
3. This caused "0% success (1 calls)" degraded health — **publicly visible** on the listing
4. Created a new resource with default WETH address in the URL: `https://risk-api.life.conway.tech/analyze?address=0x4200000000000000000000000000000000000006`
5. Deleted the old degraded resource via API (DELETE by UUID: `43ef12aa-...`)
6. New listing is healthy: `https://x402.jobs/resources/risk-api-life-conway-tech/smart-contract-risk-scorer-base`
7. User tested "Run ($0.10)" — successful, returned WETH score 3/safe

**x402.jobs API quirks discovered:**
- POST (create) works with `x-api-key` header
- PUT/PATCH/DELETE by slug fail with "Missing authorization header"
- DELETE works by UUID: `DELETE /api/v1/resources/{uuid}` with `x-api-key` header
- Re-POSTing same resource URL creates a duplicate with different slug (appends `-base`)

### 2. API Key Storage

Stored the x402.jobs API key in `.env` (gitignored) and updated `.env.example` with placeholder. Updated `scripts/register_x402jobs.py` to auto-read from `X402_JOBS_API_KEY` env var via `load_dotenv()`.

### 3. Test Fix — `.env` Leaking Into Tests

Creating `.env` broke 2 config tests (`test_load_config_defaults`, `test_load_config_missing_wallet`) because `load_dotenv()` in `config.py` loads `.env` values even after `monkeypatch.delenv()`. Fixed by mocking `load_dotenv` in the test fixture:
```python
monkeypatch.setattr("risk_api.config.load_dotenv", lambda **kwargs: None)
```
**107 tests pass**, 0 failures.

### 4. Conway Server Restart Bug (found + fixed)

While adding debug logging, restarted gunicorn with inline `export PRICE="$0.10"` which bash expanded `$0` to `bash` → `PRICE=bash.10` → x402 SDK crash: `ValueError: could not convert string to float: 'bash.10'`. Fixed by using the existing startup script (`/root/start-risk-api.sh`) which has correct single-quote escaping: `export PRICE='$0.10'`.

### 5. Settlement Investigation

Discovered **zero USDC has ever transferred on-chain** to our agent wallet (`0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891`). Checked via:
- `eth_call` balanceOf → 0 USDC
- `eth_getLogs` Transfer events to our address → 0 results

**Conclusion:** x402.jobs handles payments internally via custodial wallets. When user clicks "Run":
- x402.jobs deducts from caller's spending balance
- x402.jobs credits to resource owner's earnings
- When calling your own resource, it nets to zero (balance unchanged)
- $0.70 "Total Earnings" includes $0.50 phantom earnings from deleted resource's failed 422 calls
- Actual successful calls: 2 on the new resource ($0.20)
- On-chain settlement does NOT happen through x402.jobs' Run button — it's all internal accounting

### 6. Competitive Analysis

Reviewed top x402.jobs resources:
- **`open-facilitator/stats-solana`**: Top earner, $5/call, 507 calls, Verified badge, zero description. First-party Memeputer/OpenFacilitator team product.
- **`memeputer/honeypot-guardian`**: Chat agent (not security tool despite name), $0.03/call, has Input Schema defined with body fields, custom avatar, playful description.
- **Key takeaway:** Verified badge + avatar + call count matter for visibility. Input Schema config unlocks proper Run button UX. Our info-heavy description is correct for agent-to-agent (agents parse keywords, not personality).

---

## Files Modified This Session (uncommitted)

| File | Changes |
|------|---------|
| `.env` | **NEW** — Local secrets (gitignored), includes `X402_JOBS_API_KEY` |
| `.env.example` | Added `X402_JOBS_API_KEY=` placeholder |
| `.env.production` | Fixed facilitator URL: Dexter → OpenFacilitator |
| `scripts/register_x402jobs.py` | Reads key from `.env`, better output formatting, default WETH address in URL |
| `tests/test_config.py` | Mock `load_dotenv` to prevent `.env` leaking into tests |
| `src/risk_api/app.py` | POST support on `/analyze` (from previous session, was uncommitted) |
| `tests/test_app.py` | POST endpoint tests (from previous session, was uncommitted) |
| `CLAUDE.md` | Added `X402_JOBS_API_KEY` to env vars |
| `.claude/napkin.md` | Updated with x402.jobs API quirks |

---

## Key Decisions

| Decision | Why |
|----------|-----|
| Default WETH address in x402.jobs resource URL | x402.jobs "Run" button hits URL as-is — without a default address, it gets 422 → degraded health. WETH is clean (0/safe), fast, and demonstrates the API works. Real agents construct their own URLs. |
| Store API key in `.env` not `.env.production` | `.env.production` is tracked in git — can't put secrets there. `.env` is gitignored. |
| Mock `load_dotenv` in config tests | Prevents `.env` from contaminating test isolation. More robust than `monkeypatch.chdir(tmp_path)` since `find_dotenv()` walks parent dirs. |
| Keep info-heavy API description | Agent-to-agent product — agents parse for keywords ("proxy detection", "risk score", "0-100"). Playful/short descriptions are for human browsers. |

---

## Gotchas & Lessons Learned

- **x402.jobs API inconsistency** — POST works with `x-api-key`, but PUT/PATCH/DELETE by slug need different auth. DELETE by UUID with `x-api-key` works.
- **x402.jobs "Payment Successful" toast is misleading** — means payment was *authorized/signed*, not *settled on-chain*. Actual USDC transfer depends on facilitator settlement.
- **x402.jobs custodial model** — Run button payments are internal accounting, not on-chain. Earnings tracked separately from spending balance. Calling your own resource nets to zero.
- **Bash `$0` expansion** — `export PRICE="$0.10"` in bash expands `$0` to script name. Use single quotes: `export PRICE='$0.10'`
- **`load_dotenv()` re-reads .env on every call** — Even after `monkeypatch.delenv()`, the next `load_config()` call re-loads from `.env`. Must mock `load_dotenv` in tests.
- **x402.jobs re-POST creates duplicate** — POSTing same `resourceUrl` doesn't upsert, it creates a new resource with a different slug. Delete old one by UUID first.

---

## Current State

### Live API
- **URL:** https://risk-api.life.conway.tech
- **Status:** Healthy (restarted with correct PRICE quoting)
- **Sandbox:** `76cfc42df7955d2a7de0ec7e2473f686` (us-east, 1GB)
- **Price:** $0.10/call
- **Facilitator:** OpenFacilitator (`https://pay.openfacilitator.io`)
- **Paywall:** Active on `/analyze`, open on `/health` and `/agent-metadata.json`

### Discovery
- **ERC-8004:** Agent #19074 (https://8004scan.io/agents/base/19074)
- **x402.jobs:** https://x402.jobs/resources/risk-api-life-conway-tech/smart-contract-risk-scorer-base
  - Health: healthy, 2 successful calls, $0.20 earned on this resource
  - Status: "New" badge, not yet Verified (user about to Claim)
  - Slug includes "conway-tech" (derived from URL, need custom domain to change)

### Local Dev
- **107 tests pass**, 0 failures
- Uncommitted changes (see Files Modified above)
- `.env` file now exists with API key + config

### Agent Wallet
- `0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891`
- On-chain USDC balance: **$0.00** (settlement not happening via x402.jobs — internal accounting only)

---

## Open Issues

1. **On-chain settlement not working** — When agents call our API directly (not through x402.jobs), settlement should go through OpenFacilitator. We haven't tested this path yet. The `x402_settle` after_request hook exists but has never successfully settled on-chain. Needs debug logging to confirm it's being called and what errors (if any) the facilitator returns.

2. **Orphaned Job #784** — Old Job still exists on x402.jobs dashboard (Jobs tab). User should delete via UI (three-dot menu).

3. **Claim server on x402.jobs** — User was about to click "Claim" to get Verified badge and potentially unlock Input Schema config.

---

## Next Steps

1. **Claim the x402.jobs server** — Gets Verified badge, may unlock Input Schema editing (so Run button shows address field)
2. **Debug on-chain settlement** — Add logging to `x402_settle` hook, test direct API call (not through x402.jobs) to confirm facilitator settlement works
3. **Delete orphaned Job #784** from x402.jobs UI
4. **Commit uncommitted changes** — POST support, test fix, registration script, env files
5. **Update ERC-8004 agentURI** — Call `setAgentURI(19074, "https://risk-api.life.conway.tech/agent-metadata.json")`
6. **Monitor for real (non-self) traffic** — First external user hasn't happened yet

---

## Commands

```bash
cd C:/Users/justi/dev/risk-api

# Install
pip install -e ".[dev]"

# Test
pytest tests/ -v --cov=src/risk_api

# Type check
pyright src/ tests/

# Register/update x402.jobs listing (reads key from .env)
python scripts/register_x402jobs.py

# Verify live
curl https://risk-api.life.conway.tech/health
curl https://risk-api.life.conway.tech/agent-metadata.json
curl -sD - "https://risk-api.life.conway.tech/analyze?address=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

# Conway sandbox
# Sandbox ID: 76cfc42df7955d2a7de0ec7e2473f686
# Startup script: /root/start-risk-api.sh
# Logs: /root/gunicorn.log
# Restart: pkill -f gunicorn; nohup /root/start-risk-api.sh > /root/gunicorn.log 2>&1 &
```
