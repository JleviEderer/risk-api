# Registrations & Discovery Tracker

Single source of truth for everywhere Augur (risk-api) is registered and discoverable.

## Active Registrations

| Registry | Status | URL / ID | How to Update | Env Vars | Last Verified |
|----------|--------|----------|---------------|----------|---------------|
| ERC-8004 | Live | [Agent #19074](https://8004scan.io/agents/base/19074) | `scripts/register_erc8004.py` | wallet key | 2026-03-29 |
| x402.jobs | Live | [x402.jobs listing](https://www.x402.jobs/resources/augurrisk-com/augur-base) | `scripts/register_x402jobs.py` | `X402_JOBS_API_KEY` | 2026-03-29 |
| MoltMart | Live | [moltmart.app](https://moltmart.app) | `scripts/register_moltmart.py` | `MOLTMART_API_KEY`, `MOLTMART_SERVICE_ID` | 2026-03-29 |
| Work402 | Live (testnet) | [work402.com](https://work402.com) | `scripts/register_work402.py` | `WORK402_DID` | 2026-03-29 |
| IPFS | Live | `QmfCBvB5wdBCTeT1XUiXyXY3z2TmUm1rUnQsqrW58reL6S` | `scripts/pin_metadata_ipfs.py` | `PINATA_JWT` | 2026-03-29 |
| 8004scan | Live but stale/cached | [8004scan.io/agents/base/19074](https://8004scan.io/agents/base/19074) | Wallet verification via browser | - | 2026-03-29 |
| x402scan | Live | [x402scan.com](https://www.x402scan.com) | Register at x402scan.com/resources/register | - | 2026-03-01 |
| x402 Bazaar | Historical / unverified | ID `6352e8b7-9662-4029-bf60-6becc2ec9457` | POST to `x402-discovery-api.onrender.com/register` | - | 2026-03-08 |
| Coinbase Bazaar | Not confirmed in public feed | [CDP Bazaar](https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources) (`augurrisk.com/analyze`) | Auto-indexed via CDP facilitator settlement | `CDP_API_KEY_ID`, `CDP_API_KEY_SECRET` | 2026-03-10 |

## 2026-03-29 Alignment Checklist

Use this checklist when public positioning changes, especially when machine-readable output emphasis changes like `score`-first to `decision` / `recommended_policy` first.

The important distinction is:

- repo files updated = source metadata is ready
- external listing updated = the third-party directory actually received and shows the new metadata

| Surface | Control Type | Repo State | What Must Happen Next | How To Verify |
|---------|--------------|------------|------------------------|---------------|
| Internal app surfaces (`/`, `/openapi.json`, `/skill.md`, `/llms.txt`, `/llms-full.txt`, `/.well-known/agent-card.json`, `/agent-metadata.json`, `/.well-known/x402`) | direct deploy | updated in repo | deploy app changes | fetch each live route on `https://augurrisk.com` and confirm admission-control / `decision` / `recommended_policy` wording |
| IPFS metadata CID | script-driven | updated in repo | rerun `scripts/pin_metadata_ipfs.py` to pin a new CID | confirm new CID exists and metadata payload matches current wording |
| ERC-8004 on-chain `agentURI` / 8004scan | script-driven + browser verification | updated in repo | after pinning IPFS, run `scripts/register_erc8004.py --update-uri ipfs://<new-CID>` | verify [8004scan agent #19074](https://8004scan.io/agents/base/19074) shows the new metadata |
| x402.jobs | script-driven | updated in repo | rerun `scripts/register_x402jobs.py --update <UUID>` | verify public listing text and response schema mention admission control plus `decision` / `recommended_policy` |
| MoltMart | script-driven | updated in repo | rerun `scripts/register_moltmart.py --update <SERVICE_ID>` | verify public listing/service view shows the new positioning and response fields |
| Work402 (testnet) | script-driven | updated in repo | rerun `scripts/register_work402.py` if we still care about the testnet listing | verify public agent profile text reflects admission-control language |
| x402scan | manual / browser-driven | no repo automation here | update manually if the listing exposes editable metadata | verify listing text manually in browser |
| x402.org/ecosystem | curated / manual upstream | no direct script update | verify current listing; if stale, open or update a PR in `coinbase/x402` | confirm public ecosystem entry text and link are still acceptable |
| Coinbase public discovery feed | external / auto-indexed | repo/app ready after deploy | do at least one real paid call after deploy, then re-check feed | rerun `scripts/check_cdp_discovery.py` carefully and/or inspect the public feed |
| x402list.fun | external / stale third-party state | repo/app already point at canonical domain | verify only; do not expect repo changes alone to fix it | check whether legacy `risk-api.life.conway.tech` listing is still stale |
| Historical x402 Bazaar manual ID | historical | no current repo action needed | leave alone unless we decide to revive that path explicitly | treat as historical until a live public surface is found |

### Practical Sequence

If the goal is full public alignment rather than only local repo correctness, do this in order:

1. Deploy the app changes.
2. Verify the internal machine-readable routes on the live domain.
3. Pin new IPFS metadata and update the ERC-8004 on-chain URI.
4. Rerun script-driven external listings:
   - `scripts/register_x402jobs.py`
   - `scripts/register_moltmart.py`
   - `scripts/register_work402.py` if we still care about that testnet surface
5. Manually audit the public external surfaces against this file.
6. Treat Coinbase feed visibility and `x402list.fun` as external-state checks, not purely repo-side checks.

## 2026-03-29 Recheck

This is the current post-deploy, post-update snapshot after the script-driven alignment pass and browser recheck.

| Surface | Current State | Evidence | Notes |
|---------|---------------|----------|-------|
| [ERC-8004 agent #19074](https://www.8004scan.io/agents/base/19074) | Updated on-chain | `scripts/register_erc8004.py --update-uri ipfs://QmfCBvB5wdBCTeT1XUiXyXY3z2TmUm1rUnQsqrW58reL6S` succeeded on 2026-03-29 with tx `24cc2388aa6a2b714f783ffb4f24888c35ed9c761a50854156e01adcce79d733`. | Treat the chain update as done even though the 8004scan UI still looks stale. |
| [8004scan agent #19074](https://www.8004scan.io/agents/base/19074) | Stale or cached | Browser recheck on 2026-03-29 still showed the older score-first wording and the old-looking truncated agent URI. | Needs later recheck or manual refresh path; do not assume the UI reflects the current on-chain URI yet. |
| [x402.jobs listing route](https://www.x402.jobs/resources/augurrisk-com/augur-base) | Correct | Public page recheck on 2026-03-29 showed the new admission-control wording and `augurrisk.com` endpoint. | Treat x402.jobs as aligned. |
| [MoltMart service](https://moltmart.app/services/984bf985-8f69-4237-b0e4-cd5452f1c489) | Correct | Public page recheck on 2026-03-29 showed the new admission-control wording. | Treat MoltMart as aligned. |
| [Work402 agent](https://www.work402.com/agents/did%3Aerc8004%3A37906) | Correct | Public page recheck on 2026-03-29 showed the new admission-control wording for `did:erc8004:37906`. | Treat Work402 as aligned if we still care about the testnet-style listing. |
| [x402.org ecosystem](https://www.x402.org/ecosystem) | Stale wording, PR open | Public card recheck on 2026-03-29 still showed the older score-first wording. Follow-up upstream PR is [coinbase/x402 #1869](https://github.com/coinbase/x402/pull/1869). | This surface is curated from the `coinbase/x402` site repo, not from the script-driven listings. |
| [Coinbase public x402 discovery feed](https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources) | Not confirmed in public feed | `python scripts/check_cdp_discovery.py --max-pages 5` returned `NOT_FOUND` over the first 5 pages / 500 items on 2026-03-29. | Still looks like indexing/feed behavior or support-escalation territory. |
| [x402list.fun legacy provider page](https://x402list.fun/provider/risk-api.life.conway.tech) | Stale | Browser/API recheck on 2026-03-29 still pointed at the legacy Conway domain rather than `augurrisk.com`. | Keep treating this as external stale state rather than a repo-controlled bug. |

## Historical Audit Status (2026-03-08)

Use this table as the current `G-004` source of truth. The list above still includes historical or manual registrations; this table records what was verifiable from live public surfaces on 2026-03-08.

| Surface | Current State | Evidence | Notes |
|---------|---------------|----------|-------|
| [ERC-8004 / 8004scan agent #19074](https://www.8004scan.io/agents/base/19074) | Correct | Public 8004scan page shows `Augur`, `https://augurrisk.com/`, `https://augurrisk.com/avatar.png`, and Base agent `19074`. | Canonical domain and metadata are aligned on the public registry page. |
| [x402.jobs listing route](https://www.x402.jobs/resources/augurrisk-com/augur-base) | Correct | Public route returns `200` on 2026-03-08, uses the canonical `augurrisk-com/augur-base` slug, and browser verification on 2026-03-08 showed the correct `augurrisk.com` endpoint, Base network, and $0.10 price. Static CLI fetches still only expose a `MaintenanceGate` shell. | Treat x402.jobs as verified and done unless the listing content changes later. |
| [x402list.fun legacy provider page](https://x402list.fun/provider/risk-api.life.conway.tech) | Stale | Public provider page still returns `200` on 2026-03-08, while `https://x402list.fun/provider/augurrisk.com` returns `404`. Embedded endpoint data still points at `https://risk-api.life.conway.tech/analyze`. | This is confirmed stale directory state, not just a search-index blind spot. Repo-side metadata already points at `augurrisk.com`. |
| x402 Bazaar legacy manual ID `6352e8b7-9662-4029-bf60-6becc2ec9457` | Blocked / historical | Current repo notes still have the manual registration ID, but this audit did not find a matching public page or public API response tied back to that ID. | Treat this as historical until a public surface can be linked to it. |
| [x402.org ecosystem](https://www.x402.org/ecosystem) | Live | Public page HTML includes `Augur` and links to `https://augurrisk.com/` as of 2026-03-10. Submission path was [coinbase/x402 PR #1515](https://github.com/coinbase/x402/pull/1515). | Treat this as a separate, curated ecosystem directory from the facilitator-backed Bazaar discovery feed. |
| [Coinbase public x402 discovery feed](https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources) | Not confirmed in public feed | Live JSON feed responded successfully on 2026-03-10 with `pagination.total=13836`. A direct scan of the first 800 items found no match for `Augur`, `augurrisk`, `augurrisk.com`, or `https://augurrisk.com/analyze`. The repo checker (`python scripts/check_cdp_discovery.py`) hit `HTTP 429` on 2026-03-10 before completing a full scan. Real paid calls through the CDP facilitator had already succeeded on 2026-03-08, and Fly production confirmed `FACILITATOR_URL=https://api.cdp.coinbase.com/platform/v2/x402` with deployed CDP credentials. | Public-feed absence is still not explained by wrong facilitator config or missing Bazaar extension metadata. Treat this as CDP-side indexing lag, feed behavior, or support-escalation territory unless a full successful scan finds Augur later. |

### CDP Facilitator Verification (2026-03-08)

- Real paid call executed from Conway wallet `0x79301Cf19Aaea29fbe40F0F5B78F73e2c3b0a2b8` to `https://augurrisk.com/analyze?address=0x4200000000000000000000000000000000000006`.
- Request returned `402`, then `200` after payment, with score `3` / `safe`.
- On 2026-03-08, three additional real paid calls were executed from the same Conway wallet to the same live endpoint and all three returned the expected `402 -> signed payment -> 200` flow.
- All three additional paid calls settled successfully and returned the same `score=3`, `level=safe` result for `0x4200000000000000000000000000000000000006`.
- Live Fly production machine `e2861d10f1e928` confirmed:
  - `FACILITATOR_URL=https://api.cdp.coinbase.com/platform/v2/x402`
  - `PUBLIC_URL=https://augurrisk.com`
  - `CDP_API_KEY_ID` present
  - `WALLET_ADDRESS=0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891`
- Practical conclusion:
  - production is pointed at the CDP facilitator
  - paid settlement via CDP is working
  - missing Coinbase public-feed discovery is not caused by the app using the wrong facilitator

### Coinbase Bazaar Indexing Checklist

Use this before treating missing Coinbase discovery as a repo bug.

1. Confirm `FACILITATOR_URL` in production is `https://api.cdp.coinbase.com/platform/v2/x402`.
2. Confirm the paid endpoint returns a live `402` with x402 v2 metadata and a populated `extensions.bazaar` block.
3. Confirm the server exposes `/.well-known/x402` and `openapi.json` on the canonical host.
4. Run at least one real paid call against `https://augurrisk.com/analyze` through the CDP facilitator.
5. Re-check the public feed with:
   ```bash
   python scripts/check_cdp_discovery.py
   ```
   The default scan walks up to 200 pages of the public feed, which is intended to cover the full current catalog size rather than only the first page.
6. If the feed still does not show Augur after repeated successful paid calls, treat it as CDP-side indexing lag or support escalation rather than app-route failure.

Current status on 2026-03-08:
- Step 1: confirmed in Fly production.
- Step 2: confirmed from live `402` response.
- Step 3: confirmed on `augurrisk.com`.
- Step 4: confirmed from one initial Conway-wallet paid call plus three additional successful paid calls on 2026-03-08.
- Step 5: spot-check returned `NOT_FOUND` over the first 300 public-feed items; broader scans currently need rate-limit-aware retries because CDP returns `429` when polled too aggressively.
- Step 6: next action if still absent after more paid traffic is Coinbase/CDP follow-up, not another metadata rewrite.

Re-check on 2026-03-10:
- `x402.org/ecosystem` is now live and includes Augur, confirming the curated ecosystem listing landed.
- The CDP discovery feed remains unconfirmed for Augur: direct feed sampling still found no Augur match, and the full repo checker hit `HTTP 429`.
- Working assumption remains that successful settlement through CDP is necessary but may not be sufficient for immediate or reliably queryable appearance in the public feed.

### How to verify wallet on 8004scan

Free points on publisher score. Go to https://8004scan.io, connect agent wallet (`0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891`), sign a message.

## Pending Registrations

| Registry | Status | Notes |
|----------|--------|-------|
| HOL.org | Pending | Sign in at `hol.org/registry/register`. ERC-8004 adapter not indexing agent #19074 - investigate. |
| a2a-directory | PR pending | [GitHub PR #17](https://github.com/nicholascpark/a2a-directory/pull/17) |
| e2b | PR pending | [GitHub PR #327](https://github.com/e2b-dev/awesome-ai-agents/pull/327) |
| kyrolabs | PR pending | [GitHub PR #150](https://github.com/kyrolabs/awesome-ai-agents/pull/150) |
| slavakurilyak PR | Not started | Open manually via compare URL |
| a2aregistry.org | Blocked | Monitoring for SSL fix |
| Swarms | Not started | - |
| AI Agent Store | Not started | - |
| AI Agents Directory | Not started | - |
| Agent.ai | Not started | - |

## Discovery Endpoints

All endpoints are live and free (no x402 payment required):

| Endpoint | Description |
|----------|-------------|
| [`/`](https://augurrisk.com/) | Landing page (Schema.org JSON-LD, Open Graph) |
| [`/health`](https://augurrisk.com/health) | Health check |
| [`/dashboard`](https://augurrisk.com/dashboard) | Analytics dashboard (Chart.js, auto-refresh 30s) |
| [`/stats`](https://augurrisk.com/stats) | Stats JSON |
| [`/avatar.png`](https://augurrisk.com/avatar.png) | Agent avatar image |
| [`/robots.txt`](https://augurrisk.com/robots.txt) | Crawler directives + sitemap |
| [`/sitemap.xml`](https://augurrisk.com/sitemap.xml) | XML sitemap |
| [`/openapi.json`](https://augurrisk.com/openapi.json) | OpenAPI 3.0.3 spec |
| [`/agent-metadata.json`](https://augurrisk.com/agent-metadata.json) | ERC-8004 agent metadata |
| [`/.well-known/ai-plugin.json`](https://augurrisk.com/.well-known/ai-plugin.json) | AI plugin manifest |
| [`/.well-known/agent.json`](https://augurrisk.com/.well-known/agent.json) | A2A agent card |
| [`/.well-known/agent-card.json`](https://augurrisk.com/.well-known/agent-card.json) | A2A agent card (8004scan expects this path) |
| [`/.well-known/x402`](https://augurrisk.com/.well-known/x402) | x402 discovery document |
| [`/.well-known/x402-verification.json`](https://augurrisk.com/.well-known/x402-verification.json) | x402 verification |
| [`/.well-known/api-catalog`](https://augurrisk.com/.well-known/api-catalog) | RFC 9727 API Catalog (`application/linkset+json`) |
| [`/llms.txt`](https://augurrisk.com/llms.txt) | LLM-optimized service documentation |
| [`/llms-full.txt`](https://augurrisk.com/llms-full.txt) | Full LLM documentation (schema, detectors, examples) |

## IPFS Pinning Workflow

When agent metadata changes (new endpoints, updated fields, etc.):

1. Update the metadata in `app.py` (`/agent-metadata.json` route)
2. Deploy to Fly.io (`fly deploy`)
3. Pin updated metadata to IPFS:
   ```bash
   python scripts/pin_metadata_ipfs.py
   ```
4. Update on-chain `agentURI` with new CID:
   ```bash
   python scripts/register_erc8004.py --update-uri ipfs://<new-CID>
   ```
5. Verify on [8004scan](https://8004scan.io/agents/base/19074) that metadata refreshes

## Domain & Hosting

Domain `augurrisk.com` is hosted on Fly.io with Cloudflare DNS. Conway (`risk-api.life.conway.tech`) is historical fallback state.

Canonical host policy:
- `PUBLIC_URL=https://augurrisk.com` is the source of truth for public metadata and discovery links.
- The Flask app now issues a `308` redirect to the matching `augurrisk.com` URL when a request arrives on a different host.
- `TESTING` bypasses that redirect so local pytest fixtures can keep using the default Flask host.

## Monitoring & Health

- Better Stack is the external uptime monitor for `https://augurrisk.com/health`.
- `scripts/health_check.py` is the matching manual probe for that public health check.
- Treat `/dashboard` and `/stats` as app telemetry, not the authoritative monitoring surface.
- Legacy mode: if only `REQUEST_LOG_PATH` is configured, both surfaces read from the local JSONL request log and will reset on deploy or machine replacement.
- Durable mode: if `ANALYTICS_DB_PATH` is configured on a mounted persistent path such as a Fly volume, request events are also written to SQLite and survive app restarts on that volume.
- Current production state as of 2026-03-09: Fly now mounts volume `augur_analytics` at `/data`, and live `/stats` reports `storage_backend=sqlite`, `storage_path=/data/analytics.sqlite3`, and `storage_durable=true`.

## x402list.fun Note

- As of 2026-03-08, x402list.fun still serves the legacy provider page at `https://x402list.fun/provider/risk-api.life.conway.tech`.
- The canonical hostname page at `https://x402list.fun/provider/augurrisk.com` returns `404`.
- The embedded endpoint data on the live legacy page still points to `https://risk-api.life.conway.tech/analyze`.
- This appears to be an external directory or indexing state issue, not an app-route or `PUBLIC_URL` issue in this repo.
- Do not assume code changes alone will update the x402list.fun provider page; treat it as stale external state until the directory itself reflects `augurrisk.com`.
