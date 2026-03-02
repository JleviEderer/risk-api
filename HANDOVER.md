# Handover — risk-api

**Session date:** 2026-02-26
**Repo:** `C:/Users/justi/dev/risk-api/`
**Live at:** https://risk-api.life.conway.tech
**Git status:** Uncommitted changes on `master` — 3 files modified (`src/risk_api/app.py`, `tests/test_app.py`, `CLAUDE.md`), already deployed to Conway

---

## What We Did This Session

### Added `/.well-known/x402` Discovery Endpoint + Fixed 402 `resource.url`

Goal: make the service auto-discoverable by x402scan.com crawlers and fix the internal origin URL leaking through the 402 Payment-Required header.

#### 1. New endpoint: `/.well-known/x402`

Added x402 discovery document at `src/risk_api/app.py:753-770`. Returns:

```json
{
  "version": 1,
  "resources": ["https://risk-api.life.conway.tech/analyze"],
  "instructions": "# Smart Contract Risk Scorer\n\n..."
}
```

- Uses `PUBLIC_URL` when set, falls back to `request.url_root`
- NOT behind x402 paywall (follows existing pattern for discovery endpoints)

#### 2. Fixed `resource.url` in 402 response

`FlaskHTTPAdapter.get_url()` (`app.py:375-378`) was returning `request.url` which resolved to the internal Conway origin (`http://origin-us-east-3.conway.tech:8888/analyze`). Now uses `PUBLIC_URL` + `request.full_path` when configured.

**Before:** `resource.url` = `http://origin-us-east-3.conway.tech:8888/analyze`
**After:** `resource.url` = `https://risk-api.life.conway.tech/analyze`

#### 3. Added 3 tests

- `test_wellknown_x402_returns_discovery_doc` — JSON structure, version=1, resources array
- `test_wellknown_x402_not_behind_paywall` — exempt from x402 payment gate
- `test_wellknown_x402_uses_public_url` — resources/instructions use PUBLIC_URL

#### 4. Updated CLAUDE.md

Added `/.well-known/x402` to the discovery endpoints documentation list.

#### 5. Deployed to Conway

Uploaded `app.py` to both paths:
- `/root/risk-api/src/risk_api/app.py`
- `/root/risk-api-venv/lib/python3.10/site-packages/risk_api/app.py`

Restarted gunicorn. Both endpoints verified live.

#### 6. Verified

- `pytest tests/ -v` — 191 passed, 0 failed
- `npx pyright src/ tests/` — 0 errors
- `curl https://risk-api.life.conway.tech/.well-known/x402` — returns valid discovery JSON
- Decoded 402 `Payment-Required` header — confirms `resource.url` is now the public URL

---

## What Worked

- Conway upload API uses flat `{path, content}` payload (not `{files: [{path, content}]}`)
- `pkill -f gunicorn` then `nohup /root/start-risk-api.sh` restart pattern works reliably
- `current_app.config.get("PUBLIC_URL")` inside `FlaskHTTPAdapter` works because it's called during request context

## What Didn't Work

- First Conway upload attempt used `{files: [{path, content}]}` format and got 400 — the API expects flat `{path, content}` per file

---

## Key Decisions

1. **Used `current_app` import** for `get_url()` fix — the adapter is instantiated during request handling, so `current_app` is always available in the app context
2. **`request.full_path.rstrip('?')`** — Flask's `full_path` includes a trailing `?` even with no query string; stripping it keeps URLs clean
3. **Placed `/.well-known/x402` route after agent-card.json, before agent-metadata.json** — follows the existing endpoint ordering pattern

---

## Lessons Learned / Gotchas

- **Conway file upload format:** `POST /v1/sandboxes/{id}/files/upload/json` expects `{"path": "...", "content": "..."}` (flat), NOT `{"files": [{"path": "...", "content": "..."}]}`
- **`request.url` behind Conway proxy** leaks internal origin — always use `PUBLIC_URL` when constructing URLs that external clients/crawlers will see
- **Flask `request.full_path`** always has trailing `?` (even without query params) — must `.rstrip('?')` to avoid ugly URLs

---

## Next Steps (Prioritized)

### Immediate (user action)
1. **Register on x402scan.com** — go to https://www.x402scan.com/resources/register, submit `https://risk-api.life.conway.tech/analyze`
2. **Commit these changes** — 3 files modified, not yet committed

### From Previous Session (still pending)
- Open slavakurilyak PR manually via compare URL
- Register on hol.org (sign in at `hol.org/registry/register`)
- Submit to Swarms, AI Agent Store, AI Agents Directory, Agent.ai
- Monitor 3 GitHub PRs (a2a-directory #17, e2b #327, kyrolabs #150)
- Monitor a2aregistry.org for SSL fix

### Consider Later
- Switch from Mogami to a facilitator tracked by x402list.fun
- Investigate why HOL's ERC-8004 adapter isn't indexing agent #19074
- Pin updated metadata to IPFS (if `/.well-known/x402` should be referenced in on-chain metadata)

---

## Important Files

### Modified This Session
| File | What Changed |
|------|-------------|
| `src/risk_api/app.py` | Added `/.well-known/x402` route (lines 753-770), fixed `FlaskHTTPAdapter.get_url()` to use `PUBLIC_URL` (lines 375-378), added `current_app` import |
| `tests/test_app.py` | Added 3 tests for the new endpoint (lines 435-462) |
| `CLAUDE.md` | Added `/.well-known/x402` to discovery endpoints list |

### Key Files (for reference)
| File | Purpose |
|------|---------|
| `src/risk_api/app.py` | Flask app — all routes, x402 middleware, request logging, dashboard |
| `src/risk_api/config.py` | Environment config (`Config` dataclass) |
| `tests/test_app.py` | 45 tests for all app routes |
| `tests/conftest.py` | Test fixtures (`app`, `client`, `client_with_x402`) |
| `scripts/register_moltmart.py` | MoltMart marketplace registration |
| `scripts/register_work402.py` | Work402 hiring marketplace onboarding |
| `scripts/pin_metadata_ipfs.py` | Pin agent metadata to IPFS via Pinata |
| `scripts/register_erc8004.py` | ERC-8004 on-chain registration / URI update |

---

## Current State

### Live API
- **URL:** https://risk-api.life.conway.tech
- **Status:** Healthy, all routes working (including new `/.well-known/x402`)
- **Facilitator:** Mogami (`https://v2.facilitator.mogami.tech`)
- **Paywall:** Active on `/analyze` (GET+POST), 402 header now shows correct public URL
- **On-chain URI:** `ipfs://QmNWWhyo7KHnYPTiEeMWdHik9i6yMAM3prDKEVQTSXNEFQ`

### Discovery Endpoints (all live, none behind paywall)
- `/health` — health check
- `/dashboard` — analytics dashboard
- `/avatar.png` — agent avatar
- `/openapi.json` — OpenAPI 3.0.3 spec
- `/.well-known/ai-plugin.json` — AI plugin manifest
- `/.well-known/agent.json` / `/.well-known/agent-card.json` — A2A agent card
- `/.well-known/x402` — x402 discovery document (NEW)
- `/.well-known/x402-verification.json` — x402 verification
- `/agent-metadata.json` — ERC-8004 metadata

### Test Suite
- **191 tests**, all passing
- **0 pyright errors**

### Commands
```bash
cd C:/Users/justi/dev/risk-api
pip install -e ".[dev]"
pytest tests/ -v
npx pyright src/ tests/
flask --app risk_api.app:create_app run
curl https://risk-api.life.conway.tech/.well-known/x402
curl https://risk-api.life.conway.tech/health
```
