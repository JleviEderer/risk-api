# Handover — 2026-03-07

**Repo:** `C:/Users/justi/dev/risk-api/`
**Live at:** https://augurrisk.com (Fly.io, `iad` region)
**Git status:** Clean on `master`, pushed to origin
**Latest commit:** `e3880e4 chore(scripts): add test_x402_payment.py for manual on-chain settlement`

---

## What We Did This Session

### 1. Triage of all planned/discussed work

Reviewed HANDOVER.md, DECISIONS.md, BizPlanning.md, napkin.md to find unimplemented work. Prioritized into:
- Immediately actionable: x402list.fun domain update, pyright CI, napkin graduation
- Monitoring/passive: 8004scan OASF, OOM watch, oracle score
- Directory submissions: needs research
- Product backlog: deliberately deferred (ADR-006)

### 2. x402.jobs listing updated to augurrisk.com

**Problem:** x402.jobs listing still pointed to `risk-api.life.conway.tech`.

**Actions:**
- Ran `python scripts/register_x402jobs.py --list` — old listing wasn't shown (API returns public directory, not own resources)
- Ran default create — new listing created: UUID `4964c164-c748-4cd6-a7a5-0ac33e118b6a`, URL `https://x402.jobs/resources/augurrisk-com/augur-base`, price auto-detected as $0.10
- Old "Smart Contract Risk Scorer" listing deleted via UI (UUID found there)
- Added `--delete UUID` command to `scripts/register_x402jobs.py`

### 3. GitHub Actions pyright CI added

**Why:** `pyright` hangs indefinitely on Windows/MINGW due to x402 EVM import chain (no `__pycache__` write permission). CI on Linux doesn't have this problem.

**Created:** `.github/workflows/typecheck.yml` — runs on every push, `python -m pyright src/ tests/`

**Result:** Both Fly Deploy and Typecheck workflows passing on every push.

### 4. Napkin lessons graduated to global CLAUDE.md

Two stable lessons promoted from `.claude/napkin.md` Graduation Queue to `~/.claude/CLAUDE.md`:
- Always use `eip155:CHAINID` CAIP-2 format (not string names like "base-mainnet")
- Always use single quotes for env var values containing `$` (e.g. `PRICE='$0.10'`)

Added as new sections `## Shell Rules` and `## x402 / Blockchain` in global CLAUDE.md.

### 5. x402.jobs server ownership claimed

**Problem:** x402.jobs showed a "Claim Server Ownership" button requiring a verification file at `/.well-known/x402-verification.json`.

**Discovery:** The route already existed in `app.py` (`@app.route("/.well-known/x402-verification.json")`) but with a stale token (`64cb3a6a29bb`). The new token was `dccd5db92bc9`.

**Fix:** Updated the token in `app.py`, committed, pushed — auto-deployed via GitHub Actions.

### 6. x402 SDK 2.3.0 broke payments — pinned to <2.3

**Problem:** After our deploy, paid `/analyze` requests started returning 500. Error: `AttributeError: 'PaymentPayloadV1' object has no attribute 'accepted'`

**Root cause:** x402 SDK 2.3.0 was released. Our constraint `>=2.2.0,<3` allowed it. Docker's fresh `pip install` grabbed 2.3.0. The 2.3.0 SDK's internal `_process_request_core` tries to access `payload.accepted` which doesn't exist on the v1 payload format.

**Fix:** Pinned `pyproject.toml` to `x402[flask,evm]>=2.2.0,<2.3`. Redeployed. Confirmed 2.2.0 on server via `fly ssh console`.

**Note:** Need to investigate x402 2.3.0 changes before upgrading.

### 7. x402list.fun — triggered indexing via real on-chain payment

**Context:** x402list.fun is a separate auto-indexing directory (not x402.jobs). It indexes by watching on-chain facilitator settlements. Old listing `risk-api.life.conway.tech` appeared automatically from previous settlements.

**Solution:** Wrote `scripts/test_x402_payment.py` — makes a real x402 payment from the Conway wallet (`~/.conway/wallet.json`, address `0x79301Cf19Aaea29fbe40F0F5B78F73e2c3b0a2b8`) to `augurrisk.com/analyze`. Costs $0.10 USDC.

**Key bug fixed during development:** Script initially used x402 v1 payload format (`x402Version: 1`). The server's 2.2.0 SDK uses `PaymentPayload` (v2) internally and calls `payload.accepted` — which doesn't exist on v1 objects. Fix: send v2 format with `accepted` field populated from the 402 response option.

**v2 proof format:**
```json
{
  "x402Version": 2,
  "payload": {"signature": "0x...", "authorization": {...}},
  "accepted": {<full option object from 402 response>}
}
```

**Result:** Payment succeeded (Response 200, score 3/safe). On-chain settlement triggered from Conway wallet. x402list.fun should create `/provider/augurrisk.com` within ~1 hour.

---

## Current State

### Production
- **URL:** https://augurrisk.com
- **Status:** Healthy, x402 payments working
- **x402 SDK:** Pinned to 2.2.0 (`<2.3`)
- **Agent wallet:** ~$1.70 USDC (7+ settlements, including today's Conway test payment)
- **ERC-8004:** Agent #19074, on-chain URI = `ipfs://QmNUK1ZnwN8fShKFFSmDa2EZvy6VBquftpU7m2oazsPZv1`

### Registrations
| Directory | Status |
|-----------|--------|
| x402.jobs | ✅ Updated — `augurrisk-com/augur-base`, UUID `4964c164` |
| x402list.fun | ⏳ Pending — on-chain settlement triggered today, indexing within ~1hr |
| 8004scan | ✅ Active, agent #19074, OASF fixed last session |
| Coinbase Bazaar | ✅ Indexed |

### Tests
- 238/238 passing

### Git
- Branch `master`, clean, pushed to origin
- Latest: `e3880e4`

---

## What Worked

- GitHub Actions pyright CI avoids the Windows MINGW import hang
- x402 v2 proof format requires `accepted` field (full option from 402 response) — v1 format silently fails on 2.2.0 server
- `fly ssh console --command "pip show x402"` to verify installed version without SSHing interactively
- `fly logs --no-tail` + grep for errors faster than tailing live logs

## What Didn't Work / Gotchas

1. **x402 SDK version drift** — `>=2.2.0,<3` is too loose. Docker builds silently upgrade. Always pin to `<NEXT_MINOR` until new version is validated.

2. **x402.jobs `--list` returns public directory, not your own resources** — `GET /api/v1/resources` returns all public resources. Your own listings appear in the UI under your account but may be paginated out of the API response. Find UUID via UI if needed.

3. **x402 v1 proof format causes 500 on 2.2.0 server** — The SDK still parses v1 but then internally calls `payload.accepted` (v2 field) causing AttributeError. Always use v2 format when building manual payment proofs.

4. **x402list.fun is read-only** — No submission API. It auto-indexes from on-chain facilitator settlements. To appear there: make a real paid call. x402.jobs "Run" button is internal accounting only, doesn't trigger on-chain settlement.

---

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Pin x402 to `<2.3` | 2.3.0 broke payment verification; don't upgrade until validated |
| Use Conway wallet for test payment | Agent wallet paying itself nets to zero and looks weird |
| One shared HANDOVER.md, separate napkins per agent | Handover = project state (shared). Napkin = per-agent working memory (separate) |

---

## Next Steps

### Verify x402list.fun indexed augurrisk.com
- Check `https://x402list.fun/provider/augurrisk.com` within ~1 hour
- If not indexed after a few hours, run `python scripts/test_x402_payment.py` again

### x402.jobs ownership verification
- Deploy is done. Go to x402.jobs, open the Augur listing, click **Claim** → **Verify Ownership**
- The route `/.well-known/x402-verification.json` returns `{"x402": "dccd5db92bc9"}`

### Investigate x402 2.3.0
- Check changelog/release notes for what changed in `PaymentPayloadV1`
- Determine if we can upgrade `pyproject.toml` pin to `<2.4`

### Directory submissions (still pending)
- hol.org — ERC-8004 adapter not indexing agent #19074
- Swarms, AI Agent Store, AI Agents Directory, Agent.ai — no submission URLs documented
- Monitor GitHub PRs: a2a-directory #17, e2b #327, kyrolabs #150
- slavakurilyak PR — manual PR via compare URL
- a2aregistry.org SSL fix

### Infrastructure
- Watch for OOM — if recurring: `fly scale memory 512 -a augurrisk` ($2.50/mo)

---

## Files Modified This Session

| File | Change |
|------|--------|
| `src/risk_api/app.py` | Updated x402 ownership verification token |
| `pyproject.toml` | Pinned `x402[flask,evm]>=2.2.0,<2.3` |
| `.github/workflows/typecheck.yml` | **NEW** — pyright CI on every push |
| `scripts/register_x402jobs.py` | Added `--delete UUID` command |
| `scripts/test_x402_payment.py` | **NEW** — manual x402 payment script (Conway wallet) |
| `.claude/napkin.md` | Removed graduated items, added x402 2.3.0 gotcha, added Useful Scripts section |
| `~/.claude/CLAUDE.md` | Added `## Shell Rules` and `## x402 / Blockchain` sections |

---

## Commands Reference

```bash
cd C:/Users/justi/dev/risk-api
python -m pytest tests/ -v                                    # 238 tests
python scripts/test_x402_payment.py                           # real on-chain payment (Conway wallet, $0.10)
python scripts/register_x402jobs.py --list                    # list x402.jobs resources
python scripts/register_x402jobs.py --delete <UUID>           # delete x402.jobs resource
fly logs -a augurrisk --no-tail                               # production logs
fly ssh console -a augurrisk --command "pip show x402"        # check SDK version on server
fly scale memory 512 -a augurrisk                             # if OOM recurs
gh run list --repo JleviEderer/risk-api --limit 5             # check CI status
```
