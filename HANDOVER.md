# Handover

## Snapshot
- Date: 2026-03-12
- Repo root: `C:\Users\justi\dev\risk-api`
- Branch: `master`
- HEAD: `6246a92`
- Status: green; local worktree still has the uncommitted public-copy pass

## What Changed
- Added a strategy memo that locks the current wedge:
  - `docs/PRODUCT_WEDGE_MEMO.md`
  - frames Augur as `Base contract admission control for agents`
  - keeps the product narrow rather than broadening into a full execution-security platform
- Updated the public copy in `README.md`, homepage/`skill.md`/`llms.txt`/`llms-full.txt` generation in `src/risk_api/app.py`, and the growth-plan pointer so the same wedge appears across repo docs and public machine-readable surfaces.
- Tightened the public wording pass across the main docs and discovery surfaces:
  - standardizes the public headline around `Deterministic Base contract risk screening for agents`
  - standardizes the short explainer around `Screen Base contracts before your agent buys, routes funds, approves, or interacts`
  - adds compact use-case education on the homepage and README so the product need is clearer at a glance
- Did a second public-copy pass after review findings:
  - homepage setup language is plainer
  - use-case pages no longer use `Buyer Intent` framing
  - `llms-full.txt` now describes Augur as a paid HTTP API instead of an agent-to-agent API
  - `examples/javascript/augur-mcp/README.md` is more customer-facing
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
- Deployed the latest copy pass to Fly from the local worktree and verified live:
  - homepage hero and `Explore by Use Case`
  - `https://augurrisk.com/skill.md`
  - `https://augurrisk.com/llms-full.txt`
  - `https://augurrisk.com/honeypot-detection-api`

## Current Read
- Current product-scope rule:
  - keep all 8 existing detectors inside the same narrow admission-gate product
  - do not narrow scope by removing detectors like honeypot, proxy, or deployer reputation
  - do not broaden scope into simulation, generalized runtime monitoring, or wallet/session protection
- Current wording rule:
  - keep `Base contract admission control for agents` as internal strategy language
  - prefer clearer public phrasing such as `Deterministic Base contract risk screening for agents`
  - use straightforward user-facing copy like `Screen Base contracts before your agent buys, routes funds, approves, or interacts`
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
- Current messaging rule: keep one plain public headline plus one plain trigger-moment sentence across homepage, README, machine docs, and registration metadata; add brief use-case examples where they clarify why an agent would call Augur.
- Current discovery/docs rule:
  - `/skill.md` is the shortest agent quickstart/discovery doc, not a separate product
  - keep core machine surfaces (`/skill.md`, OpenAPI, `llms*.txt`, `.well-known/*`, MCP page) unless there is a clear reason to retire one
  - use-case pages are optional support surfaces; keep them only if they improve clarity or qualified traffic
- Current product-output rule:
  - do not claim explicit policy outputs in public copy until the API actually returns a stable field such as `recommended_policy` or `recommended_action`
  - current truthful claim is that Augur returns policy-ready inputs (`score`, `level`, `findings`, `category_scores`, optional `implementation`)
- `coinbase/x402` PR `#1515` is merged into `main`.
- Current next step is still `G-015`: use the live proof report for targeted distribution and watch for qualified traffic.
- OpenClaw looks relevant for agent-builder reach, but it should stay behind Base/x402-first distribution.
- Treat `x402.org/ecosystem` and the CDP `discovery/resources` feed as separate surfaces; being live on the former does not imply the latter is queryable.
- Existing upstream follow-up:
  - determine whether Augur eventually appears in the CDP public discovery feed or whether Coinbase support clarification is needed
- Separate local side-task status:
  - QMD vault retrieval on this laptop is usable now
  - default strong mode on the 8 GB Intel iGPU machine is structured hybrid `lex+vec`, not blind reliance on plain auto-expanded `qmd query "..."`
  - the failure mode observed was intermittent Vulkan GPU out-of-memory on the heaviest local query path, not a broken QMD index
  - `C:\Users\justi\Obsidian Vault\Outputs\2026-03-08-qmd-reference.md` was updated with current QMD `2.0.1` status, retrieval workflow, and CPU fallback guidance
  - local `vault-synth` now exists at `C:\Users\justi\dev\vault-synth`
  - it retrieves notes with QMD, synthesizes with OpenAI, prints answer plus sources, and only saves when `--save` is passed
  - current Windows implementation uses fused `qmd search` + `qmd vsearch` for the default `lex+vec` path because multiline structured `qmd query` arguments were brittle through `qmd.cmd`
  - it can fall back to `C:\Users\justi\dev\risk-api\.env` for `OPENAI_API_KEY` if no local `vault-synth\.env` exists
  - `vault-synth` now auto-runs `qmd --index vault-core update` before retrieval by default; use `--no-refresh` only when you explicitly want speed over freshness
  - this fixed a real stale-index mismatch where QMD served an older `QMD` reference note than the file on disk
  - `vault-synth` now excludes its own saved notes from default retrieval so synthesis output does not become a self-referential source on later runs

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
9. If policy outputs are added next, implement the response contract first, verify behavior on real contracts, then update homepage, `skill.md`, README, and machine docs.
10. In the next session, tune `C:\Users\justi\dev\vault-synth` retrieval quality:
   - compare fused `search + vsearch` against plain `qmd query` on questions that should hit `outputs/`
   - decide whether the lexical branch should stay acronym-first, use a broader distilled keyword query, or use collection-aware hints
   - if `vault-synth` becomes a regular tool, add its own local `.env` or move `OPENAI_API_KEY` to a user-level secret store instead of relying on the `risk-api` fallback
