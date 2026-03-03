# Handover — risk-api

**Session date:** 2026-03-02
**Repo:** `C:/Users/justi/dev/risk-api/`
**Live at:** https://augurrisk.com (pending deploy — see Next Steps)
**Fallback:** https://risk-api.life.conway.tech (Conway sandbox, still running)
**Git status:** Unstaged changes on `master`. 17 modified files + 1 new (`fly.toml`). NOT yet committed.

---

## What We Did This Session

### 1. Fly.io Migration Prep (Conway → Fly.io + augurrisk.com)

Prepared the full migration from Conway sandbox hosting to Fly.io with the new `augurrisk.com` domain (registered on Cloudflare). This is code-complete but NOT yet deployed.

**Created:**
- `fly.toml` — Fly.io app config: `iad` region (US East), 256MB shared VM, always-on (`min_machines_running = 1`), health check at `/health`, force HTTPS

**Fixed:**
- `Dockerfile` — Added `COPY x402JobsAvatar.png src/risk_api/` to fix avatar bug in Docker builds. The avatar file lives at repo root but after `pip install` in Docker the package dir is at `/usr/local/lib/`, not `/app/`, so the fallback path never found it.

**Updated `.env.example`:**
- Added `PUBLIC_URL=https://augurrisk.com`
- Changed `FACILITATOR_URL` default from Dexter (which is down) to CDP facilitator

**Global URL migration** (`risk-api.life.conway.tech` → `augurrisk.com`) across 17 files:

| Category | Files |
|----------|-------|
| Registration scripts | `register_erc8004.py` (4 URLs), `register_x402jobs.py` (3), `register_moltmart.py` (3), `register_work402.py` (1), `pin_metadata_ipfs.py` (1) |
| Operational scripts | `health_check.py` (1), `test_x402_client.py` (1) |
| Documentation | `README.md`, `HANDOVER.md`, `CLAUDE.md`, `docs/REGISTRATIONS.md` |
| Tests | `test_app.py` (29 refs), `test_config.py` (2), `test_pin_metadata.py` (5), `test_register_moltmart.py` (1) |

**Intentionally unchanged:** `docs/x402-landscape-research.md` — historical research snapshot, old URLs are accurate for that context.

---

## What Worked

- **Global find-replace was clean** — `risk-api.life.conway.tech` appeared only in places that needed updating
- **All 238 tests pass** after migration, 0 pyright errors
- **Dockerfile fix is minimal** — one COPY line, addresses a real bug (avatar 404 in Docker)

## What Didn't Work

- Nothing failed this session. Clean execution.

---

## Key Decisions

1. **Fly.io over other hosts** — Docker-native (existing Dockerfile works), free tier, built-in SSL, custom domains, `fly deploy` workflow vs Conway's painful double-upload
2. **`iad` region** — US East, close to Base mainnet RPC for low latency
3. **Always-on (`min_machines_running = 1`)** — x402 payments need instant responses, can't tolerate cold start
4. **256MB memory** — Flask app is lightweight, no need for more
5. **Keep Conway running during transition** — fallback until Fly.io is verified stable (24-48 hours)
6. **Updated tests to use new domain** — test assertions reference the URLs from source constants, so they must match

---

## Lessons Learned / Gotchas

- **Dockerfile avatar path bug** — `x402JobsAvatar.png` at repo root isn't in the package dir after `pip install` in Docker. The app searches package dir first, then repo root — but in Docker, repo root is `/app/` while package is `/usr/local/lib/`. The fix copies avatar into `src/risk_api/` before install.
- **Dexter facilitator is still down** — updated `.env.example` default to CDP instead
- **Test files reference source constants** — when changing URLs in source, tests that assert on those values must change too

---

## Next Steps (Prioritized)

### Immediate: Deploy to Fly.io

All code changes are ready. User needs to execute these manual steps:

```bash
# 1. Install Fly CLI
curl -L https://fly.io/install.sh | sh
fly auth signup   # or fly auth login

# 2. Launch app (reads fly.toml)
fly launch --copy-config --no-deploy

# 3. Set secrets
fly secrets set \
  WALLET_ADDRESS=0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891 \
  FACILITATOR_URL=https://api.cdp.coinbase.com/platform/v2/x402 \
  CDP_API_KEY_ID=<from ~/.config/risk-api/cdp_api_key.json> \
  CDP_API_KEY_SECRET=<from ~/.config/risk-api/cdp_api_key.json> \
  ERC8004_AGENT_ID=19074 \
  PUBLIC_URL=https://augurrisk.com \
  BASESCAN_API_KEY=<if available>

# 4. Deploy
fly deploy

# 5. Custom domain
fly certs add augurrisk.com
# Then in Cloudflare DNS: CNAME @ → augurrisk.fly.dev

# 6. Verify
curl https://augurrisk.com/health
curl https://augurrisk.com/.well-known/x402
curl https://augurrisk.com/openapi.json
curl https://augurrisk.com/agent-metadata.json
curl https://augurrisk.com/avatar.png -o /dev/null -w "%{http_code}"
curl -I "https://augurrisk.com/analyze?address=0x4200000000000000000000000000000000000006"
```

### After Deploy: Update Registrations

Once Fly.io is live and verified, re-run registration scripts to update all marketplaces:

```bash
# Update x402.jobs listing
python scripts/register_x402jobs.py --update <UUID>

# Update MoltMart service
python scripts/register_moltmart.py --update <SERVICE_ID>

# Update Work402 profile
python scripts/register_work402.py

# Pin updated metadata to IPFS (new CID needed — URLs changed)
PINATA_JWT=<jwt> python scripts/pin_metadata_ipfs.py
# Then update on-chain URI:
python scripts/register_erc8004.py --update-uri ipfs://<new-CID>
```

### From Previous Sessions (still pending)
- Open slavakurilyak PR manually via compare URL
- Register on hol.org — investigate why ERC-8004 adapter isn't indexing agent #19074
- Submit to Swarms, AI Agent Store, AI Agents Directory, Agent.ai
- Monitor 3 GitHub PRs (a2a-directory #17, e2b #327, kyrolabs #150)
- Monitor a2aregistry.org for SSL fix
- Verify wallet on 8004scan (free points on publisher score)
- Check x402list.fun to confirm Bazaar listing appears

### After Conway Decommission (24-48h post-deploy)
- Shut down Conway sandbox (or let it idle)
- Remove Conway-specific notes from docs

---

## Important Files

### Created This Session
| File | Purpose |
|------|---------|
| `fly.toml` | Fly.io app config (region, VM size, health check, auto-scaling) |

### Modified This Session
| File | What Changed |
|------|-------------|
| `Dockerfile` | Added `COPY x402JobsAvatar.png src/risk_api/` (avatar bug fix) |
| `.env.example` | Added `PUBLIC_URL`, updated `FACILITATOR_URL` default to CDP |
| `CLAUDE.md` | URL migration (`PUBLIC_URL` example) |
| `README.md` | All URLs updated to `augurrisk.com` |
| `docs/REGISTRATIONS.md` | All URLs updated, domain strategy section rewritten for Fly.io |
| `scripts/register_erc8004.py` | 4 URL replacements |
| `scripts/register_x402jobs.py` | 3 URL replacements |
| `scripts/register_moltmart.py` | 3 URL replacements |
| `scripts/register_work402.py` | 1 URL replacement |
| `scripts/pin_metadata_ipfs.py` | 1 URL replacement (`BASE_URL` constant) |
| `scripts/health_check.py` | 1 URL replacement (`DEFAULT_URL`) |
| `scripts/test_x402_client.py` | 1 URL replacement (default `--url`) |
| `tests/test_app.py` | 29 URL replacements in test assertions |
| `tests/test_config.py` | 2 URL replacements |
| `tests/test_pin_metadata.py` | 5 URL replacements |
| `tests/test_register_moltmart.py` | 1 URL replacement |

### Key Files (for reference)
| File | Purpose |
|------|---------|
| `src/risk_api/app.py` | Flask app — all routes, x402 middleware, request logging, dashboard |
| `src/risk_api/cdp_auth.py` | CDP facilitator JWT auth (Ed25519, no full cdp-sdk) |
| `src/risk_api/config.py` | Environment config (`Config` dataclass) |
| `scripts/test_x402_client.py` | x402 test client — makes real payments |
| `tests/test_app.py` | Tests for all app routes (238 tests) |
| `docs/REGISTRATIONS.md` | Single source of truth for all registrations and discovery |

---

## Current State

### Git
- **Branch:** `master`, up to date with `origin/master`
- **Uncommitted:** 17 modified files + 1 new (`fly.toml`). Ready to commit.

### Live API (Conway — still running)
- **URL:** https://risk-api.life.conway.tech
- **Status:** Healthy, all routes working
- **Facilitator:** CDP (`https://api.cdp.coinbase.com/platform/v2/x402`)
- **Paywall:** Active on `/analyze` at $0.10/call USDC on Base
- **Agent wallet balance:** $0.60 USDC (6 settlements: 2 Mogami + 4 CDP)
- **On-chain URI:** `ipfs://QmUUtXC4uSTMfTUBNhnWncGUShJ6qnw8YWdNSU9g49hFfV` (will need new CID after deploy)
- **Coinbase Bazaar:** INDEXED — `risk-api.life.conway.tech/analyze`

### Registrations (all live, pointing to old domain until re-registered)
ERC-8004 (#19074), x402.jobs, MoltMart, Work402, IPFS, 8004scan, x402scan, x402 Bazaar, Coinbase Bazaar

### Test Suite
- **238 tests**, all passing
- **0 pyright errors**

### Commands
```bash
cd C:/Users/justi/dev/risk-api
pip install -e ".[dev]"
pytest tests/ -v
npx pyright src/ tests/
flask --app risk_api.app:create_app run
fly deploy                        # deploy to Fly.io
fly logs                          # tail production logs
fly ssh console                   # SSH into Fly.io machine
```
