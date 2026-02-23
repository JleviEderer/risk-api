# Handover — risk-api

**Session date:** 2026-02-23
**Repo:** https://github.com/JleviEderer/risk-api (private)
**Latest commit:** `a62f5af` on `master` — deployment + Dexter facilitator switch
**Live at:** https://risk-api.life.conway.tech

---

## What We Did This Session

Two tracks: **deployment/ops** (first half) and **strategic analysis** (second half).

### Track 1: Deployment & Paywall Activation

Picked up from previous session where the API was built locally but not deployed.

1. **Deployed to Conway sandbox** (`76cfc42df7955d2a7de0ec7e2473f686`, us-east, 1GB RAM)
   - Created venv at `/root/risk-api-venv/`, installed all deps
   - Wrote all source files via `sandbox_write_file`
   - Started gunicorn with explicit env vars (dotenv doesn't work with gunicorn)

2. **Switched facilitator from Coinbase to Dexter**
   - Coinbase facilitator (`api.cdp.coinbase.com`) returned 401 — requires CDP API key
   - Dexter (`https://x402.dexter.cash`) — free, no auth, 20K settlements/day
   - Updated startup script, restarted gunicorn, verified paywall works

3. **Verified live endpoints:**
   - `/health` → 200 `{"status":"ok"}` (no paywall)
   - `/analyze?address=0x...` → 402 with `Payment-Required` header containing base64 JSON payment details
   - Payment details confirmed: USDC on Base, $0.01 (will be updated to $0.10), pay to wallet `0x1358...`

4. **Updated local config defaults** — `config.py`, `.env.example`, `.env.production`, `CLAUDE.md` all now default to Dexter
5. **Added Docker setup** — Dockerfile, docker-compose.yml, .dockerignore, deploy.sh
6. **Added gunicorn** to pyproject.toml dependencies
7. **All 64 tests pass** locally after changes
8. **Committed and pushed** as `a62f5af`

### Track 2: Strategic Analysis

Deep discussion about competitive positioning, pricing, and build priorities. Key outcomes:

1. **GoPlus competitive analysis** — 717M calls/month, free API, 30+ chains. They check more things than us BUT can't serve autonomous agents (requires signup + API key). Our x402-native access is a categorical advantage, not just convenience.

2. **Moat thesis** — The moat is x402 frictionlessness, not analysis depth. GoPlus can't easily add x402 (would cannibalize free tier). Moat is time-bounded (6-18 months). Ship fast, be first.

3. **Pricing decision** — Single tier at $0.10/call. No free tier (removes differentiator). No tiered pricing (over-engineering for zero users). Can adjust down based on data.

4. **Build priorities** — Discovery first (ERC-8004 + x402.jobs), then deployer reputation + expanded selectors, then iterate from live feedback. Don't build honeypot simulation or cross-contract analysis until users ask.

5. **Updated docs:**
   - `docs/BizPlanning.md` — comprehensive rewrite with GoPlus analysis, moat thesis, pricing, build priorities (sections 6-13 are new)
   - `docs/DECISIONS.md` — added ADR-005 (pricing) and ADR-006 (ship fast, iterate)
   - `MEMORY.md` — added Strategic Insights section

---

## What Worked

- Conway sandbox deployment via `sandbox_exec` + `sandbox_write_file` — reliable once you use simple commands (compound commands over SSH are flaky)
- Dexter facilitator — zero-friction setup, just works
- x402 middleware gracefully handles facilitator failures (try/except on `initialize()`)
- The strategy discussion surfaced critical insights that changed the build plan

## What Didn't Work / Gotchas

- **Coinbase facilitator needs CDP API key** — returns 401 without it. Not documented clearly. Use Dexter instead.
- **Conway sandbox SSH flaky with compound commands** — `cmd1 && cmd2` often fails with exit 255. Write scripts via `sandbox_write_file` and execute them instead.
- **gunicorn doesn't auto-load .env** — must pass env vars explicitly on command line or in startup script
- **Taskmaster skill is annoying for discussion sessions** — designed for action tasks, kept blocking every response during strategy analysis. Disabled it mid-session. Re-enable for building sessions.

---

## Key Decisions Made

| Decision | Why | ADR |
|----------|-----|-----|
| Dexter facilitator (not Coinbase) | Free, no auth, 20K/day. Coinbase needs CDP key. | — |
| Single tier $0.10/call | Simple, good margins, adjustable. No free tier. | ADR-005 |
| Ship fast, iterate from data | Zero users = zero feedback. Discovery > features. | ADR-006 |
| Don't match GoPlus features | Different market (agents vs humans). x402 access is the moat. | — |
| No LLM in scoring pipeline | Speed + reliability + margins favor deterministic | — |

---

## Current State

### Live API
- **URL:** https://risk-api.life.conway.tech
- **Sandbox:** `76cfc42df7955d2a7de0ec7e2473f686` (us-east, 1GB)
- **Startup script:** `/root/start-risk-api.sh` (env vars + gunicorn)
- **Restart:** `kill $(pgrep -f gunicorn) && nohup /root/start-risk-api.sh > /root/gunicorn.log 2>&1 &`
- **Price:** Currently $0.01 (needs update to $0.10)
- **Facilitator:** Dexter (`https://x402.dexter.cash`)
- **Paywall:** Active on `/analyze`, open on `/health`

### Local Dev
- **64 tests pass**, 91% coverage, 0 pyright errors
- Default facilitator: Dexter (updated in config.py, .env.example, .env.production)
- Git: clean working tree, `a62f5af` pushed to origin/master

### Taskmaster
- **Currently disabled** — Stop hook removed from `~/.claude/settings.json`
- Re-enable by adding the Stop hook back (see napkin.md for config)

---

## Next Steps (Priority Order)

### Immediate
1. **Update price to $0.10** — Change `PRICE` in `/root/start-risk-api.sh` on sandbox, restart gunicorn
2. **Register on ERC-8004** — Permissionless contract at `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` on Base mainnet. Need to call it from wallet `0x1358...`. This makes us discoverable to agents.
3. **List on x402.jobs** — Additional discovery channel for agent-to-agent services.

### Phase 2 (while waiting for traffic)
4. **Deployer wallet reputation** — Add Basescan API call (free tier, 5/sec). Deployer age + contract count. High signal, fast win.
5. **Expand selector database** — Research common scam signatures, grow from 15 to 50-100. Our bytecode approach works on unverified contracts (most scams).
6. **Storage state reads** — `eth_getStorageAt` for paused state, owner address.

### Phase 3 (after seeing real traffic)
7. Build whatever users actually ask for — we don't know yet what matters most.

---

## Important Files Modified/Created This Session

### risk-api/ (committed as `a62f5af`)
| File | Change |
|------|--------|
| `src/risk_api/config.py` | Default facilitator → Dexter, network → mainnet |
| `pyproject.toml` | Added gunicorn dependency |
| `Dockerfile` | New — containerized deployment |
| `docker-compose.yml` | New — one-command Docker deploy |
| `.dockerignore` | New |
| `.env.production` | New — mainnet config template (Dexter) |
| `scripts/deploy.sh` | New — VPS deploy script |
| `.env.example` | Updated defaults (Dexter, mainnet) |
| `CLAUDE.md` | Updated stack, commands, env var defaults |
| `.claude/napkin.md` | Added Dexter notes, Conway sandbox gotchas |

### docs/ (in web4/, NOT in risk-api — not committed yet)
| File | Change |
|------|--------|
| `docs/BizPlanning.md` | Major rewrite — sections 6-13 new (GoPlus analysis, moat, pricing, priorities) |
| `docs/DECISIONS.md` | Added ADR-005 (pricing) and ADR-006 (ship fast) |

### Memory/Config
| File | Change |
|------|--------|
| `~/.claude/projects/.../MEMORY.md` | Added Strategic Insights section, updated price/status |
| `~/.claude/settings.json` | Taskmaster Stop hook removed (disabled) |

---

## Commands

```bash
cd C:/Users/justi/dev/web4/risk-api

# Install
pip install -e ".[dev]"

# Test
pytest tests/ -v --cov=src/risk_api

# Type check
pyright src/risk_api/

# Run locally (dev)
WALLET_ADDRESS=0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891 flask --app risk_api.app:create_app run

# Run locally (prod)
gunicorn "risk_api.app:create_app()" --bind 0.0.0.0:8000 --workers 2

# Docker
docker compose up -d --build

# Verify live
curl https://risk-api.life.conway.tech/health
curl -sD - https://risk-api.life.conway.tech/analyze?address=0x4200000000000000000000000000000000000006
```
