# Handover — risk-api

**Session date:** 2026-02-23 (afternoon)
**Repo:** https://github.com/JleviEderer/risk-api (private)
**Latest commit:** `2ea189a` on `master`
**Live at:** https://risk-api.life.conway.tech

---

## What We Did This Session

Three main tasks plus a deployment, all completed:

### 1. Price Update ($0.01 → $0.10)

Updated the default price across all files:
- `src/risk_api/config.py` — default `$0.10`
- `.env.example`, `.env.production` — `PRICE=$0.10`
- `tests/conftest.py` — test fixture price
- `CLAUDE.md` — docs

### 2. ERC-8004 Registration (Agent #19074)

Registered the risk-api as an on-chain agent identity on Base mainnet.

- **Added `/agent-metadata.json` endpoint** to Flask app — serves ERC-8004 metadata, NOT behind x402 paywall
- **Created `scripts/register_erc8004.py`** — signs and sends `register(string agentURI)` to the ERC-8004 registry contract using the agent wallet private key from `~/.automaton/wallet.json`
- **Executed registration** — agent #19074 on Base mainnet
  - TX: `9716a87ca45b10482efb42e0ebe53793c8cd14fa2987bc083aedd5606cb5e47d`
  - View: https://8004scan.io/agents/base/19074
  - Gas cost: 0.0000045710942064 ETH
- **Added 3 tests** for the metadata endpoint (basic, with agent_id, not behind paywall)
- **Metadata uses data: URI** (base64 encoded JSON) — could be upgraded to hosted URL via `setAgentURI(agentId, newURI)` later

### 3. x402.jobs Marketplace Listing

Listed the API on the x402.jobs discovery marketplace.

- **Created `scripts/register_x402jobs.py`** — POSTs resource to x402.jobs API
- **API key:** `kbaB-cpuBZaxvcEtrnC5tK2RVaFMsrXuarZDT0o0Duc` (user's account)
- **Resource ID:** `43ef12aa-6f26-4f48-9bba-b07d8fea87c9`
- **Live at:** https://x402.jobs/resources/risk-api-life-conway-tech/smart-contract-risk-scorer-base

### 4. Conway Sandbox Deployment

Deployed all code changes to the live server.

- **Uploaded updated files** via Conway API (`POST /v1/sandboxes/{id}/files/upload/json`)
- **Critical gotcha discovered:** gunicorn loads from `site-packages`, NOT from `/root/risk-api/src/`. Must upload to BOTH `/root/risk-api/src/risk_api/` AND `/root/risk-api-venv/lib/python3.10/site-packages/risk_api/`
- **Switched facilitator:** Dexter (`x402.dexter.cash`) was down with 522 timeout. Switched to **OpenFacilitator** (`pay.openfacilitator.io`) — free, no auth, supports Base mainnet v2 exact
- **Verified all endpoints live:**
  - `/health` → 200
  - `/agent-metadata.json` → 200 with ERC-8004 metadata
  - `/analyze` → 402 with $0.10 price (confirmed `amount: 100000` in payment header)

---

## What Worked

- **Conway API for deployment** — `POST /files/upload/json` and `POST /exec` work reliably. API key at `~/.conway/config.json`: `cnwy_k_LKnBkOgIX3FH817Zr7sB_y3KuraHR1fM`
- **OpenFacilitator as drop-in replacement** — one env var change, same x402 protocol, instant switch
- **ERC-8004 registration via Python** — `web3` and `eth_account` are transitive deps from x402, no new deps needed
- **x402.jobs API** — straightforward REST, worked after fixing field name casing

## What Didn't Work / Gotchas

- **Conway SSH compound commands fail** — `cmd1 && cmd2` returns exit 255. Use separate `exec` calls for each command.
- **Gunicorn loads from site-packages** — uploading to source dir does nothing. Previous deploy installed via pip, so gunicorn uses the installed copy. Upload to BOTH paths or re-run `pip install -e .`
- **Dexter facilitator down** — 522 Connection Timed Out on 2026-02-23. x402 middleware gracefully disables itself (by design), but the API serves without a paywall. Always check logs after restart.
- **x402.jobs field names are camelCase** — `resourceUrl` not `resource_url`. Also requires `network` and `payTo` fields not prominently documented.
- **`python3` doesn't exist on Windows MINGW** — use `python`
- **User's ETH transfer appeared as exchange internal ID** — not an on-chain tx hash. Had to wait ~3 min for exchange to broadcast.

---

## Key Decisions Made

| Decision | Why |
|----------|-----|
| OpenFacilitator over Dexter (for now) | Dexter is down. Facilitators are commoditized — swap with one env var. |
| data: URI for ERC-8004 (not hosted URL) | Simpler, no dependency on live server for registry metadata. Can upgrade via `setAgentURI` later. |
| `/agent-metadata.json` not behind paywall | Discovery endpoint — agents need to read it for free to decide whether to pay for `/analyze` |
| `type: ignore[arg-type]` for web3 TxParams | web3's TypedDict is overly strict, rejects plain dicts. Known SDK issue. |

---

## Current State

### Live API
- **URL:** https://risk-api.life.conway.tech
- **Sandbox:** `76cfc42df7955d2a7de0ec7e2473f686` (us-east, 1GB)
- **Conway API:** `https://api.conway.tech`, auth key in `~/.conway/config.json`
- **Startup script:** `/root/start-risk-api.sh`
- **Restart:** `pkill -f gunicorn` (via Conway exec), then `nohup /root/start-risk-api.sh > /root/gunicorn.log 2>&1 &` (separate exec calls — don't chain!)
- **Price:** $0.10/call
- **Facilitator:** OpenFacilitator (`https://pay.openfacilitator.io`)
- **Paywall:** Active on `/analyze`, open on `/health` and `/agent-metadata.json`
- **Endpoints:**
  - `GET /health` → `{"status":"ok"}` (free)
  - `GET /agent-metadata.json` → ERC-8004 metadata (free)
  - `GET /analyze?address=0x...` → risk score (402 paywall, $0.10 USDC on Base)

### Registrations
- **ERC-8004:** Agent #19074 on Base mainnet (https://8004scan.io/agents/base/19074)
- **x402.jobs:** https://x402.jobs/resources/risk-api-life-conway-tech/smart-contract-risk-scorer-base

### Local Dev
- **67 tests pass**, 0 pyright errors
- Git: clean working tree, `2ea189a` pushed to origin/master
- Taskmaster: enabled (Stop hook in `~/.claude/settings.json`)

---

## Next Steps (Priority Order)

### All "Immediate" items from last session are DONE

### Phase 2 (while waiting for traffic)
1. **Deployer wallet reputation** — Add Basescan API call (free tier, 5/sec). Deployer age + contract count. High signal, fast win.
2. **Expand selector database** — Research common scam signatures, grow from 15 to 50-100. Our bytecode approach works on unverified contracts (most scams).
3. **Storage state reads** — `eth_getStorageAt` for paused state, owner address.

### Phase 2.5 (ops improvements)
4. **Update ERC-8004 agentURI** — Currently a data: URI. After confirming `/agent-metadata.json` is stable, call `setAgentURI(19074, "https://risk-api.life.conway.tech/agent-metadata.json")` to point to the hosted endpoint.
5. **Set `ERC8004_AGENT_ID=19074`** in production env — enables the `registrations` field in the metadata response.
6. **Monitor Dexter** — If it comes back stable, consider switching back (higher volume facilitator). Or stay on OpenFacilitator — both are fine.

### Phase 3 (after seeing real traffic)
7. Build whatever users actually ask for — we don't know yet what matters most.

---

## Important Files Modified/Created This Session

### risk-api/ (commits `7c6eed8` and `2ea189a`)
| File | Change |
|------|--------|
| `src/risk_api/app.py` | Added `/agent-metadata.json` endpoint (ERC-8004 metadata) |
| `src/risk_api/config.py` | Default price $0.01 → $0.10 |
| `tests/test_app.py` | +3 tests for metadata endpoint (67 total) |
| `tests/conftest.py` | Test fixture price $0.01 → $0.10 |
| `.env.example` | Price → $0.10 |
| `.env.production` | Price → $0.10 |
| `CLAUDE.md` | Price docs, OpenFacilitator note |
| `.claude/napkin.md` | ERC-8004 notes, x402.jobs notes, deploy corrections |
| `scripts/register_erc8004.py` | **New** — on-chain ERC-8004 registration script |
| `scripts/register_x402jobs.py` | **New** — x402.jobs marketplace listing script |

### Memory/Config
| File | Change |
|------|--------|
| `~/.claude/projects/.../MEMORY.md` | Updated facilitator, test count, added registrations, Conway API details |
| `~/.claude/settings.json` | Taskmaster Stop hook re-enabled |

### Conway Sandbox (live)
| File | Change |
|------|--------|
| `/root/start-risk-api.sh` | Price → $0.10, facilitator → OpenFacilitator |
| `/root/risk-api-venv/lib/python3.10/site-packages/risk_api/app.py` | Added `/agent-metadata.json` endpoint |
| `/root/risk-api-venv/lib/python3.10/site-packages/risk_api/config.py` | Default price $0.10 |

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

# Run locally (dev)
WALLET_ADDRESS=0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891 flask --app risk_api.app:create_app run

# Verify live
curl https://risk-api.life.conway.tech/health
curl https://risk-api.life.conway.tech/agent-metadata.json
curl -sD - https://risk-api.life.conway.tech/analyze?address=0x4200000000000000000000000000000000000006

# Conway sandbox deploy (via Python)
python -c "
import httpx
API = 'https://api.conway.tech/v1/sandboxes/76cfc42df7955d2a7de0ec7e2473f686'
HEADERS = {'Authorization': 'cnwy_k_LKnBkOgIX3FH817Zr7sB_y3KuraHR1fM', 'Content-Type': 'application/json'}
# Upload file:
httpx.post(f'{API}/files/upload/json', headers=HEADERS, json={'path': '/root/...', 'content': '...'})
# Execute command:
httpx.post(f'{API}/exec', headers=HEADERS, json={'command': '...'})
"
```
