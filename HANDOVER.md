# Handover — risk-api

**Session date:** 2026-03-01
**Repo:** `C:/Users/justi/dev/risk-api/`
**Live at:** https://risk-api.life.conway.tech
**Git status:** Clean on `master`, pushed to origin. 3 commits this session.

---

## What We Did This Session

### Triggered Coinbase Bazaar Indexing via Real CDP Payment

**Goal:** Make a real $0.10 USDC payment through the CDP facilitator to trigger Coinbase Bazaar auto-indexing of our `/analyze` endpoint.

#### 1. Made a real x402 payment

Ran `scripts/test_x402_client.py` with the Conway wallet (`0x79301Cf19Aaea29fbe40F0F5B78F73e2c3b0a2b8`) as payer:

```bash
CLIENT_PRIVATE_KEY="0x9d29..." python scripts/test_x402_client.py
```

Flow: GET → 402 → sign EIP-712 → retry with `PAYMENT-SIGNATURE` → CDP facilitator verifies + settles → 200 with risk analysis.

**Result:** WETH scored 3/100 (safe). $0.10 USDC transferred on-chain.

#### 2. Verified on-chain settlement

- Agent wallet (`0x1358...`): $0.20 → **$0.30 USDC** (+$0.10)
- Conway wallet (`0x7930...`): $3.29 → **$3.19 USDC** (-$0.10)

#### 3. Confirmed Coinbase Bazaar indexing

Queried `GET https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources` — our endpoint is **indexed among 13,023 resources**:

```json
{
  "resource": "https://risk-api.life.conway.tech/analyze",
  "lastUpdated": "2026-03-02T05:26:46.081Z",
  "x402Version": 2
}
```

Indexing was **instant** after the first CDP settlement — no delay.

#### 4. Verified CDP facilitator auth

Hit `/supported` with our JWT auth — 200 OK. Confirms `eip155:8453` (Base mainnet) with x402 v2 and `bazaar` extension.

#### 5. Verified all discovery endpoints

All healthy: `/health`, `/.well-known/x402`, `/.well-known/agent-card.json`, `/agent-metadata.json`.

#### 6. Updated docs and pushed

Updated `docs/REGISTRATIONS.md`: Coinbase Bazaar status changed from "Pending indexing" → "Live". Committed and pushed 3 commits to origin.

#### 7. Researched where to browse the Bazaar listing

Found that Coinbase Bazaar has **no official web UI** — it's API-only ("early development, more like Yahoo search"). Third-party explorers that index it:

| Explorer | URL | Notes |
|----------|-----|-------|
| x402list.fun | `https://x402list.fun/explore?q=risk-api` | 13K+ services, search + categories |
| x402 Playground | `https://www.x402playground.com/bazaar` | Bazaar search UI |
| x402scan.com | `https://www.x402scan.com` | Already listed here |
| x402station.com | `https://x402station.com` | Analytics platform |
| BlockRun.AI | `https://blockrun.ai` | Service catalog |
| Rencom | `https://x402.rencom.ai` | Search + ranks by agent outcomes |

---

## What Worked

- **CDP facilitator settlement was instant** — no warm-up, no delay, just worked
- **Bazaar indexing was immediate** — appeared in the discovery API right after first settlement
- **Existing `test_x402_client.py` script** worked perfectly end-to-end with the Conway wallet
- **CDP auth (`cdp_auth.py`)** generating correct JWTs — `/supported` returns 200

## What Didn't Work

- Nothing failed this session. Clean execution.

---

## Key Decisions

1. **Used Conway wallet as payer** (not agent wallet) — Conway wallet had $3.29 USDC, separate from the agent's revenue wallet
2. **Analyzed WETH** (not USDC) for the test payment — WETH is a simple non-proxy contract, predictable score (3/safe)
3. **No code changes needed** — all infrastructure (client script, CDP auth, Bazaar extension) was already in place from prior sessions

---

## Lessons Learned / Gotchas

- **Bazaar indexes on first CDP settlement** — just returning 402 responses is NOT enough. A real payment must complete (verify + settle) through the CDP facilitator
- **Coinbase Bazaar has no web UI** — purely machine-readable API. Use third-party explorers (x402list.fun, x402scan.com) to browse visually
- **WETH scores 3/100 now** (not 0) — deployer reputation detector adds 3 points when Basescan can't find the deployer. This is expected behavior, not a bug
- **CDP facilitator supports Solana too** — `/supported` shows solana mainnet + devnet alongside EVM chains

---

## Next Steps (Prioritized)

### From Previous Sessions (still pending)
- Open slavakurilyak PR manually via compare URL
- Register on hol.org (sign in at `hol.org/registry/register`) — investigate why ERC-8004 adapter isn't indexing agent #19074
- Submit to Swarms, AI Agent Store, AI Agents Directory, Agent.ai
- Monitor 3 GitHub PRs (a2a-directory #17, e2b #327, kyrolabs #150)
- Monitor a2aregistry.org for SSL fix
- Verify wallet on 8004scan (free points on publisher score)

### Consider Later
- Check x402list.fun to confirm our listing appears there
- Investigate adding richer `metadata` to Bazaar listing (currently `{}`)
- Pin updated metadata to IPFS if any discovery endpoints changed
- Buy a domain (e.g. `augur-api.xyz`) to decouple from Conway branding

---

## Important Files

### Modified This Session
| File | What Changed |
|------|-------------|
| `docs/REGISTRATIONS.md` | Coinbase Bazaar status: "Pending indexing" → "Live" with indexed resource URL |

### Key Files (for reference)
| File | Purpose |
|------|---------|
| `src/risk_api/app.py` | Flask app — all routes, x402 middleware, Bazaar extension, request logging, dashboard |
| `src/risk_api/cdp_auth.py` | CDP facilitator JWT auth (Ed25519, no full cdp-sdk) |
| `src/risk_api/config.py` | Environment config (`Config` dataclass) |
| `scripts/test_x402_client.py` | x402 test client — makes real payments (used this session) |
| `tests/test_cdp_auth.py` | Tests for CDP auth module |
| `tests/test_app.py` | Tests for all app routes |
| `docs/REGISTRATIONS.md` | Single source of truth for all registrations and discovery |
| `cdp_api_key.json` | CDP API key (gitignored) — key ID + Ed25519 private key |

---

## Current State

### Live API
- **URL:** https://risk-api.life.conway.tech
- **Status:** Healthy, all routes working
- **Facilitator:** CDP (`https://api.cdp.coinbase.com/platform/v2/x402`) — production
- **Paywall:** Active on `/analyze` at $0.10/call USDC on Base
- **Agent wallet balance:** $0.30 USDC (3 settlements: 2 Mogami + 1 CDP)
- **On-chain URI:** `ipfs://QmNWWhyo7KHnYPTiEeMWdHik9i6yMAM3prDKEVQTSXNEFQ`
- **Coinbase Bazaar:** INDEXED — `risk-api.life.conway.tech/analyze`

### Registrations (all live)
ERC-8004 (#19074), x402.jobs, MoltMart, Work402, IPFS, 8004scan, x402scan, x402 Bazaar, **Coinbase Bazaar**

### Test Suite
- **218 tests**, all passing
- **0 pyright errors**

### Commands
```bash
cd C:/Users/justi/dev/risk-api
pip install -e ".[dev]"
pytest tests/ -v
npx pyright src/ tests/
flask --app risk_api.app:create_app run
# Make a test payment:
CLIENT_PRIVATE_KEY="0x..." python scripts/test_x402_client.py
# Check Bazaar listing:
curl -s "https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources?type=http&limit=100" | python -m json.tool
```
