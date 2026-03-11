# Handover

## Snapshot
- Date: 2026-03-10
- Repo root: `C:\Users\justi\dev\risk-api`
- Branch: `master`
- HEAD: `572b206`
- Status: green

## What Changed
- Patched the in-repo MCP wrapper so startup and tool discovery no longer hard-fail when `CLIENT_PRIVATE_KEY` is unset:
  - `examples/javascript/augur-mcp/index.mjs` now requires the key only when `analyze_base_contract_risk` is actually called
  - `npm run smoke` now passes locally on the read-only path without a wallet key
  - `examples/javascript/augur-mcp/README.md` now documents the split between read-only startup and paid analyze calls
- Ran a 12-chat ChatGPT discoverability check for Augur and distilled the results into:
  - `docs/llm_discoverability_synthesis.md`
  - `docs/llm_discoverability_runs_filled.csv`
  - `docs/llm_discoverability_summary_filled.csv`
- Moved the raw LLM transcript dumps out of `docs/` and into the local archive:
  - `.codex/research.local/llm-discoverability/`
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
- Tightened the homepage visual hierarchy:
  - added a stronger brand lockup, hero stats, and denser section intros
  - kept the same public routes and machine-readable entrypoints
- Clarified homepage wording around capability vs entry pages:
  - renamed the misleading "Use Augur For" block to "Public Entry Pages"
  - explicitly states that those pages are task-specific fronts for the same full 8-detector `/analyze` pass
- Brought `/mcp` into the same visual system as the homepage without adding human-first promo sections:
  - keeps the page focused on local stdio setup, client-side x402, and canonical machine docs
- Deployed the latest public-surface pass to Fly from `master`:
  - live commit: `572b206`
  - verified live `https://augurrisk.com/`, `https://augurrisk.com/skill.md`, and `https://augurrisk.com/mcp`
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
- ChatGPT discoverability is currently weak:
  - Augur did not appear unprompted in the 12 blind runs
  - after direct comparison, the model consistently classifies Augur as a serious but narrow Base-only deterministic prefilter
  - repeated perceived gap is transaction simulation plus broader runtime/interactions coverage
- Treat the LLM result as a distribution/messaging signal first, not as proof that Augur should pivot into a full execution-security platform.
- Follow-up review of the LLM research sharpened the interpretation:
  - the problem is partly entity resolution (`Augur` often resolves to unrelated products) as well as generic discoverability
  - at least a couple of blind runs were methodologically contaminated or ambiguous, so the `0/12` headline is directionally useful but not a clean benchmark
  - stronger strategic takeaway is still category ownership and retrievability for a narrow wedge, not feature expansion toward simulation
- MCP wrapper behavior is now cleaner for demos and onboarding:
  - startup/read-only introspection works without `CLIENT_PRIVATE_KEY`
  - paid analyze calls still require the key at tool invocation time
- Public-facing product/discovery surface is now in good shape for promotion:
  - root skill doc is live
  - homepage wording no longer confuses public entry pages with full detector coverage
  - proof page is live
  - report OG card is fixed
  - payment explainer is live
  - MCP setup page is live
  - npm MCP package is live
  - buyer-intent pages are live
- Current positioning rule: Augur stays agent-first. Prefer machine-readable docs, direct integration paths, and MCP/x402 clarity over social-proof or human-marketing sections.
- `coinbase/x402` PR `#1515` is merged into `main`.
- Current next step is still `G-015`: use the live proof report for targeted distribution and watch for qualified traffic.
- OpenClaw looks relevant for agent-builder reach, but it should stay behind Base/x402-first distribution.
- Treat `x402.org/ecosystem` and the CDP `discovery/resources` feed as separate surfaces; being live on the former does not imply the latter is queryable.
- Existing upstream follow-up:
  - determine whether Augur eventually appears in the CDP public discovery feed or whether Coinbase support clarification is needed

## Recommended Next Steps
1. Work through the 2026-03-11 outreach queue in `docs/outreach.md`, with OpenClaw after the tighter Base/x402 targets.
2. Revise the LLM discoverability artifacts on the next pass:
   - separate clean runs from contaminated runs
   - capture entity-resolution failures explicitly
   - fill missing rank/provenance fields in the filled CSV
3. Use the LLM memo to tighten both category wording and entity disambiguation around `Augur Risk`, `augurrisk.com`, and Base-first deterministic contract gating before broader promotion.
4. Do one real paid end-to-end MCP test with a wallet configured before any broader MCP push or npm patch release.
5. Watch:
   - `proof_report_view`
   - `top_referers`
   - `/how-payment-works` visits
   - unpaid `402` attempts
   - paid requests
6. Re-check CDP discovery feed visibility without tripping `429`, or escalate to Coinbase/CDP support with the successful-settlement evidence.
7. Only build more proof/demo surfaces if distribution shows confusion or weak conversion.
8. If more public-page polish happens, keep checking that `/skill.md`, OpenAPI, and the paid `/analyze` path remain the dominant integration cues above the fold.
