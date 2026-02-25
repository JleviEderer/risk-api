# Handover — risk-api

**Session date:** 2026-02-24 (evening)
**Repo:** `C:/Users/justi/dev/risk-api/`
**Live at:** https://risk-api.life.conway.tech
**Git status:** Clean — all changes committed and pushed to `origin/master`

---

## What We Did This Session

### 1. Built `/dashboard` HTML Analytics Page

Added a self-hosted dark-themed analytics dashboard at `/dashboard`:

- **3 summary cards:** Total Requests, Paid Requests, Avg Response Time
- **Hourly bar chart:** Paid vs unpaid requests (Chart.js 4.x from CDN, stacked bars)
- **Recent requests table:** Last 20 entries with truncated addresses, risk level badges, relative timestamps
- **Auto-refresh:** `setInterval` every 30s, no full page reload
- **Graceful degradation:** If Chart.js CDN is unreachable, shows "Chart unavailable" text
- **Not behind x402 paywall** — operational tool, not monetized

The entire dashboard is a single inline HTML string constant (`DASHBOARD_HTML`) in `app.py` — no templates directory, no new files, no new Python dependencies.

### 2. Enhanced `/stats` JSON Endpoint

Added two new fields to the existing `/stats` response (backward-compatible):

- `avg_duration_ms` — global average response time across all logged requests
- `hourly` — list of `{"hour": "2026-02-24T14:00:00Z", "count": N, "paid": N, "avg_duration_ms": N}` bucketed by hour

Computed in the existing single-pass file read with accumulators. Hourly buckets use `ts[:13]` for grouping.

### 3. Deployed to Conway

Uploaded `app.py` to both Conway paths and restarted gunicorn:
- `/root/risk-api/src/risk_api/app.py` (source)
- `/root/risk-api-venv/lib/python3.10/site-packages/risk_api/app.py` (site-packages — where gunicorn loads from)

Verified all live endpoints:
- `https://risk-api.life.conway.tech/health` — OK
- `https://risk-api.life.conway.tech/dashboard` — serving HTML
- `https://risk-api.life.conway.tech/stats` — includes new `hourly` and `avg_duration_ms` fields

### 4. Set Up BetterStack Uptime Monitoring

User created a BetterStack account and configured uptime monitoring:
- **Monitor:** `https://risk-api.life.conway.tech/health`
- **Alerts:** Email + Slack (free tier — no phone)
- **Interval:** 3 minutes
- This closes the last ops gap (alerting when gunicorn dies)

### 5. Committed & Pushed

Single commit `1cbe4c7`: `feat(app): add /dashboard HTML analytics page with hourly charts`
- Pushed to `origin/master`

---

## What Worked

- **Inline HTML approach** — single constant in `app.py`, no template engine, no new files. Clean and self-contained.
- **Single-pass stats computation** — hourly bucketing and avg duration computed in the same file read loop as total/paid counts. No second pass needed.
- **Conway deploy via API** — upload JSON + exec works reliably. Upload to both paths (source + site-packages) then `pkill -f gunicorn` + `nohup start script`.

## What Didn't Work / Gotchas

- **`/tmp` paths on Windows/MINGW** — Python's `open('/tmp/...')` resolves differently on Windows vs MINGW bash. Use `tempfile.mkdtemp()` for cross-platform temp files.
- **`git diff --stat` argument order** — `--stat` must come before file paths. Use `git diff --stat -- file1 file2`.
- **x402 tests take 20+ minutes** — Tests using `client_with_x402` fixture connect to the real Mogami facilitator during `http_server.initialize()`. This is a pre-existing issue, not caused by our changes. Use `-k "not x402"` to skip them for fast iteration (non-x402 tests run in ~3 seconds).
- **Conway upload API format** — It's `{"path": "...", "content": "..."}` (flat), NOT `{"files": [{"path": "...", "content": "..."}]}` (array).

---

## Key Decisions

| Decision | Why |
|----------|-----|
| Inline HTML constant, not templates | No Jinja2 dependency, no templates directory. Dashboard is ~130 lines of HTML/CSS/JS — small enough for a string constant. |
| Chart.js from CDN, not bundled | Zero build step. Graceful fallback if CDN is down. |
| `/dashboard` NOT behind x402 paywall | It's an operational tool for the owner, not a product endpoint. |
| BetterStack for uptime monitoring | Free tier: 10 monitors, 3-min intervals, email+Slack alerts. Recommended over UptimeRobot (5-min intervals on free tier). |
| All 3 ops gaps now closed | Logging/analytics (dashboard), rate limiting (x402 paywall), alerting (BetterStack). |

---

## Ops Gaps Status (All Closed)

| Gap | Status | Solution |
|-----|--------|----------|
| No logging/analytics | **CLOSED** | Request logging (`REQUEST_LOG_PATH`), `/stats` JSON, `/dashboard` HTML |
| No rate limiting | **CLOSED** (N/A) | x402 paywall at $0.10/call is natural rate limiting |
| No alerting | **CLOSED** | BetterStack uptime monitoring (email + Slack, 3-min intervals) |

---

## Current State

### Live API
- **URL:** https://risk-api.life.conway.tech
- **Status:** Healthy, all routes working
- **Facilitator:** Mogami (`https://v2.facilitator.mogami.tech`)
- **Paywall:** Active on `/analyze` (GET+POST)
- **Open routes:** `/health`, `/stats`, `/dashboard`, `/agent-metadata.json`, `/.well-known/x402-verification.json`
- **Logging:** Active at `/root/risk-api-logs/requests.jsonl`
- **Monitoring:** BetterStack uptime (email + Slack alerts)

### Agent Wallet
- **Address:** `0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891`
- **USDC Balance:** $0.20 (2 settlements via Mogami)

### Local Dev
- **118 tests pass**, 0 pyright errors
- Git: clean, pushed to origin/master

### Discovery
- **ERC-8004:** Agent #19074 on Base mainnet
- **x402.jobs:** Listed at https://x402.jobs/resources/risk-api-life-conway-tech/smart-contract-risk-scorer-base

---

## Files Modified This Session

| File | Changes |
|------|---------|
| `src/risk_api/app.py` | Added `DASHBOARD_HTML` constant (~130 lines), `/dashboard` route, enhanced `/stats` with `avg_duration_ms` + `hourly` bucketing |
| `tests/test_app.py` | +2 tests: `test_dashboard_returns_html`, `test_dashboard_not_behind_paywall` |
| `tests/test_logging.py` | +1 test: `test_stats_includes_hourly_and_avg_duration` |
| `CLAUDE.md` | Updated structure line, added `/dashboard` to gotchas |

---

## Open Issues

1. **Facilitator fallback not implemented** — Need to test Heurist/PayAI/Dexter gas limits before adding fallback logic
2. **Dexter coming back** — Watch @dexteraisol on X. When back, test gas limit with real settlement
3. **Settlement errors are silent** — Server returns 200 even if facilitator settlement fails. Consider: log more aggressively, or return a warning header to client
4. **Result caching** — Same contract re-analyzed every call. Add TTL cache when traffic justifies it
5. **x402 tests are slow** — `client_with_x402` fixture hits real facilitator (~20 min). Could mock the facilitator connection for faster CI.

---

## Next Steps

1. **Monitor dashboard** — Check `https://risk-api.life.conway.tech/dashboard` for organic traffic
2. **Test facilitator gas limits** — When Dexter is back, run `scripts/test_x402_client.py` against each facilitator
3. **Add facilitator fallback** — Once 2-3 facilitators confirmed working, add retry logic in settlement
4. **Result caching** — Add TTL cache for contract analysis when traffic justifies it
5. **Consider mocking x402 in tests** — Speed up test suite from 21 min to <5 sec

---

## Commands

```bash
cd C:/Users/justi/dev/risk-api

# Install
pip install -e ".[dev]"

# Test (fast — skip x402 facilitator tests)
pytest tests/ -v -k "not x402"

# Test (full — includes x402 tests, takes ~20 min)
pytest tests/ -v

# Type check
npx pyright src/ tests/

# Run dev server
flask --app risk_api.app:create_app run
# Then open http://localhost:5000/dashboard

# Health check
python scripts/health_check.py

# Check live
curl https://risk-api.life.conway.tech/health
curl https://risk-api.life.conway.tech/stats
# Open https://risk-api.life.conway.tech/dashboard in browser

# Conway sandbox
# Sandbox ID: 76cfc42df7955d2a7de0ec7e2473f686
# API: https://api.conway.tech, Auth: cnwy_k_LKnBkOgIX3FH817Zr7sB_y3KuraHR1fM
# Startup script: /root/start-risk-api.sh
# Request log: /root/risk-api-logs/requests.jsonl
# Gunicorn log: /root/gunicorn.log
# Restart: pkill -f gunicorn (separate exec), then nohup /root/start-risk-api.sh > /root/gunicorn.log 2>&1 &
# Deploy: Upload to BOTH /root/risk-api/src/risk_api/ AND /root/risk-api-venv/lib/python3.10/site-packages/risk_api/
```
