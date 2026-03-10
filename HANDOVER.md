# Handover

## Snapshot
- Date: 2026-03-10
- Repo root: `C:\Users\justi\dev\risk-api`
- Branch: `master`
- Status: green

## What Changed
- Shipped the live proof-of-work report:
  - `https://augurrisk.com/reports/base-bluechip-bytecode-snapshot`
- Added a report-specific Open Graph card for the proof page:
  - image route: `https://augurrisk.com/og/base-bluechip-bytecode-snapshot.png`
  - report pages now use that asset instead of the generic `/avatar.png`
- The proof report now:
  - uses the live `/analyze` response shape in its embedded snapshot JSON
  - includes nested `implementation` output for proxy examples
  - clearly labels the JSON as a dated snapshot, not a live rerun
- Added registry-backed report routing in `src/risk_api/app.py` via `/reports/<slug>`.
- Added a public MCP discovery/install surface:
  - live page: `https://augurrisk.com/mcp`
  - linked from the homepage, `llms.txt`, and `llms-full.txt`
- Added a root agent-facing skill document:
  - live doc: `https://augurrisk.com/skill.md`
  - linked from the homepage, sitemap, robots, `llms.txt`, and `llms-full.txt`
- Packaged and published the MCP wrapper as `augurrisk-mcp`:
  - npm: `https://www.npmjs.com/package/augurrisk-mcp`
  - current version: `1.0.1`
  - public install path: `npx -y augurrisk-mcp`
- Updated the homepage, MCP page, `README.md`, `llms.txt`, and `llms-full.txt` to surface the MCP package directly.
- Recorded the first Coinbase x402 Discord post in `docs/outreach.md`.
- Added OpenClaw (`r/OpenClaw` / OpenClaw Discord) as a secondary outreach target; avoid treating the AI-only OpenClaw forum as the primary posting surface.
- Re-verified Coinbase discovery surfaces: `x402.org/ecosystem` now lists Augur, while the CDP Bazaar feed still does not reliably show an Augur match in public queries.
- Verified the live deploys on `augurrisk.com`.

## Current Read
- Public-facing product/discovery surface is now in good shape for promotion:
  - root skill doc is live
  - proof page is live
  - report OG card is fixed
  - payment explainer is live
  - MCP setup page is live
  - npm MCP package is live
  - buyer-intent pages are live
- `coinbase/x402` PR `#1515` is merged into `main`.
- Current next step is still `G-015`: use the live proof report for targeted distribution and watch for qualified traffic.
- OpenClaw looks relevant for agent-builder reach, but it should stay behind Base/x402-first distribution.
- Treat `x402.org/ecosystem` and the CDP `discovery/resources` feed as separate surfaces; being live on the former does not imply the latter is queryable.
- Existing upstream follow-up:
  - determine whether Augur eventually appears in the CDP public discovery feed or whether Coinbase support clarification is needed

## Recommended Next Steps
1. Work through the 2026-03-11 outreach queue in `docs/outreach.md`, with OpenClaw after the tighter Base/x402 targets.
2. Watch:
   - `proof_report_view`
   - `top_referers`
   - `/how-payment-works` visits
   - unpaid `402` attempts
   - paid requests
3. Re-check CDP discovery feed visibility without tripping `429`, or escalate to Coinbase/CDP support with the successful-settlement evidence.
4. Only build more proof/demo surfaces if distribution shows confusion or weak conversion.
