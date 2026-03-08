# Handover

## Snapshot
- Date: 2026-03-08
- Repo root: `C:\Users\justi\dev\risk-api`
- Branch: `master`
- Status: green
- Working tree:
  - Modified: `.codex/napkin.md`, `HANDOVER.md`, `README.md`, `docs/GrowthExecutionPlan.md`, `docs/REGISTRATIONS.md`, `docs/x402-landscape-research.md`
  - Untracked: `.claude/settings.local.json`, `.playwright-mcp/`, `avatar.html`, `docs/MCP_PACKAGING_PLAN.md`, `docs/agent-economy-primer.md`, `examples/javascript/augur-mcp/`, `scripts/check_cdp_discovery.py`

## What We Worked On
- Continued the growth backlog and completed `G-005`, `G-006`, `G-007`, `G-010`, `G-011`, and `G-012` from `docs/GrowthExecutionPlan.md`.
- Aligned the public GitHub repository homepage setting with the canonical production domain.
- Flagged the current `coinbase/x402` ecosystem PR as blocked on Coinbase-side review/deploy controls based on the 2026-03-08 email thread.
- Added a Coinbase Bazaar indexing checklist and a one-command public-feed monitor script.
- Logged three additional successful Conway-wallet paid calls against the live CDP facilitator path.
- Completed `G-008` and `G-009` with a working local Node stdio MCP wrapper example for Augur.
- Tightened the MCP wrapper so Augur API errors become MCP errors, wallet addresses are not exposed in tool output, and the x402 client is pinned to Base mainnet.

## What Got Done

### 1) Closed repo-side canonical-domain cleanup (`G-005`)
- Re-audited the repo for `risk-api.life.conway.tech` references.
- Confirmed all editable runtime surfaces, registration scripts, and metadata already point to `https://augurrisk.com`.
- Left only historical/audit references in docs where they are evidence, not live config.

### 2) Implemented canonical-host enforcement in the app (`G-006`)
- Added a `before_request` hook in `src/risk_api/app.py` that:
  - reads `PUBLIC_URL`
  - compares the incoming request host to the canonical host
  - issues a `308` redirect to the matching canonical URL when the host is different
- This runs before `/analyze` validation and the x402 paywall, so old hosts stop competing in public discovery.
- `TESTING` bypasses the redirect so existing local pytest fixtures can keep using Flask's default test host.
- Redirect-only requests are excluded from the per-instance request log to avoid polluting `/dashboard` and `/stats`.

### 3) Tightened tests around host behavior
- Added focused tests in `tests/test_app.py` to verify:
  - non-canonical hosts redirect to `https://augurrisk.com`
  - query strings are preserved on redirect
  - `TESTING` bypasses canonical-host enforcement

### 4) Updated operator docs
- `docs/GrowthExecutionPlan.md`
  - marked `G-005`, `G-006`, and `G-007` complete
  - updated the canonical-domain workstream wording to reflect the new steady state
- `docs/REGISTRATIONS.md`
  - documented the canonical-host policy tied to `PUBLIC_URL`
  - documented the prepared `x402.org/ecosystem` submission state
- `.codex/napkin.md`
  - added the recurring rule that `PUBLIC_URL` is enforced via `308` canonical redirects
  - added the upstream `coinbase/x402` PR path for ecosystem listing updates

### 5) Prepared the official x402 ecosystem submission packet (`G-007`)
- Verified that `https://www.x402.org/ecosystem` still does not list Augur on 2026-03-08.
- Verified that the upstream submission path is a PR to `coinbase/x402` using:
  - `typescript/site/app/ecosystem/partners-data/[slug]/metadata.json`
  - `typescript/site/public/logos/`
- Added:
  - `docs/X402_ECOSYSTEM_SUBMISSION.md`
  - `docs/submissions/x402-ecosystem/metadata.json`
- Chose:
  - slug `augur`
  - category `Services/Endpoints`
  - logo target `/logos/augur.png` sourced from `x402JobsAvatar.png`
- Opened upstream submission PR:
  - [coinbase/x402 PR #1515](https://github.com/coinbase/x402/pull/1515)
- Remaining blocker:
  - wait for PR review, merge, and live ecosystem refresh

### 6) Promoted the Python payment flow into first-class docs (`G-010`)
- Added `docs/PYTHON_PAYMENT_QUICKSTART.md` as the shortest path to a successful paid call.
- Updated `README.md` near the top with a visible Python quickstart:
  - install
  - set `CLIENT_PRIVATE_KEY`
  - `--dry-run` to inspect the `402`
  - full paid retry with `PAYMENT-SIGNATURE`
- Updated the repo tree and commands section so `scripts/test_x402_client.py` is presented as the main onboarding path rather than a buried maintenance script.

### 7) Added a matching JavaScript / Node paid-call example (`G-011`)
- Added `examples/javascript/augur-paid-call/` with:
  - `package.json`
  - `.env.example`
  - `index.mjs`
  - `README.md`
- The example uses the published `@x402/fetch` and `@x402/evm` packages rather than monorepo-only workspace references.
- Added `--dry-run` so the JavaScript flow can be validated without spending funds.
- Updated the top of `README.md` to link the Node path alongside the Python quickstart.

### 8) Published a short payment explainer page (`G-012`)
- Added live route `/how-payment-works` in `src/risk_api/app.py`.
- The page explains:
  - request `/analyze`
  - receive `402 Payment Required`
  - sign payment
  - retry with `PAYMENT-SIGNATURE`
  - receive JSON
- Linked it from the landing page and from `README.md`.
- Added sitemap coverage and route tests so the explainer stays discoverable and public.
- Deployed the route live to `https://augurrisk.com/how-payment-works`.
- Follow-up bug fix:
  - canonical-host enforcement originally redirected Fly's internal `/health` probe
  - fixed by exempting `/health` from canonical redirects
  - verified live `https://augurrisk.com/health` returns `{"status":"ok"}`

### 9) Fixed the public GitHub homepage setting
- Verified the repository `JleviEderer/risk-api` is public and already linked from public docs and metadata.
- Updated the GitHub repository homepage from `https://risk-api.life.conway.tech` to `https://augurrisk.com`.
- This removes the last editable GitHub-side canonical-domain mismatch for users landing on the repo from public surfaces.

### 10) Marked the x402 ecosystem submission as externally blocked
- Updated `docs/GrowthExecutionPlan.md` so `G-007` explicitly records the current blocker.
- Updated `docs/REGISTRATIONS.md` so the `x402.org ecosystem` row now reads `PR pending / externally blocked`.
- Evidence captured from the 2026-03-08 email thread:
  - `vercel[bot]` requested Coinbase team authorization before deploy
  - Heimdall reported a review error on the `litlife1127-bot` approval citing MFA/public-email requirements
- Practical conclusion:
  - the PR is not currently blocked by repo metadata or app config
  - next action is Coinbase-side maintainer clearance, then live listing verification after merge

### 11) Added a Coinbase Bazaar discovery monitor
- Added `scripts/check_cdp_discovery.py`.
- The script scans the public CDP x402 discovery feed for `https://augurrisk.com/analyze` plus Augur-related needles and exits `0` when found, `2` when not found.
- Added a short `Coinbase Bazaar Indexing Checklist` section to `docs/REGISTRATIONS.md` so future sessions can quickly distinguish:
  - repo-side discovery setup
  - successful facilitator settlement
  - remaining CDP-side indexing lag

### 12) Logged additional live CDP settlement evidence
- Executed three additional real paid calls from Conway wallet `0x79301Cf19Aaea29fbe40F0F5B78F73e2c3b0a2b8` to `https://augurrisk.com/analyze`.
- All three showed:
  - `402` from the live endpoint
  - x402 v2 payment requirements
  - populated Bazaar extension metadata
  - successful signed retry returning `200`
- All three returned the same result for the test contract:
  - `score=3`
  - `level=safe`
- Immediate public-feed spot-check still returned `NOT_FOUND` on the first page, so additional successful settlements did not produce instant visible indexing.

### 13) Shipped the first MCP-compatible packaging surface (`G-008`, `G-009`)
- Added `docs/MCP_PACKAGING_PLAN.md`.
- Chosen approach:
  - local Node.js stdio MCP server
  - no hosted MCP transport
  - x402 payment handled client-side against the canonical `https://augurrisk.com/analyze` endpoint
- Added `examples/javascript/augur-mcp/` with:
  - `package.json`
  - `.env.example`
  - `index.mjs`
  - `smoke-test.mjs`
  - `README.md`
- Exposed two MCP tools:
  - `analyze_base_contract_risk`
  - `describe_augur_service`
- Verification:
  - `npm install`
  - `npm run smoke`
  - `npm run smoke -- --paid`
- Paid smoke test succeeded from Conway wallet and returned the same live Augur result (`score=3`, `level=safe`) for the Base WETH example address.

### 14) Hardened the MCP wrapper behavior
- Updated `examples/javascript/augur-mcp/index.mjs` so non-`200` Augur responses are handled explicitly and returned as MCP `isError` tool results with status + body details.
- Removed payer wallet address leakage from model-visible MCP output and from `describe_augur_service`.
- Locked the x402 client registration to `eip155:8453` instead of `eip155:*`.
- Verified:
  - happy path still works via `npm run smoke -- --paid`
  - no-bytecode path now returns a clean MCP error for `0x000000000000000000000000000000000000dEaD` with HTTP `422`

## Validation
- Ran:
  - `python -m pytest tests\test_app.py -q`
- Result:
  - `91 passed in 2.29s`
- Verified current upstream listing/submission path against:
  - `https://www.x402.org/ecosystem`
  - `https://github.com/coinbase/x402`
  - `https://github.com/coinbase/x402/tree/main/typescript/site`
- Verified GitHub repo metadata:
  - `gh repo view --json homepageUrl,visibility,isPrivate`
  - result now shows `homepageUrl=https://augurrisk.com`, `visibility=PUBLIC`, `isPrivate=false`

## Key Decisions
- Treat `x402list.fun` stale Conway-host output as external directory state, not a repo-side metadata bug.
- Enforce canonical origin at runtime rather than relying only on metadata cleanup.
- Use `308` so method and query string are preserved when clients hit the wrong host.

## Recommended Next Steps
1. Keep `G-005` and `G-006` marked done unless new evidence shows an editable external listing still points at Conway.
2. Monitor [coinbase/x402 PR #1515](https://github.com/coinbase/x402/pull/1515) and verify `https://www.x402.org/ecosystem` after merge.
   Current blocker: Coinbase-side review/deploy gate clearance shown in the 2026-03-08 email thread.
3. Move to `G-008` to decide the MCP packaging path, or skip ahead to `G-013` if you want more buyer-intent surface area before packaging work.
4. If external directories are refreshed manually, use the repo scripts and `docs/REGISTRATIONS.md` rather than old notes.

## Suggested Restart Context For Next Agent
- `G-001`, `G-002`, `G-003`, `G-004`, `G-005`, `G-006`, `G-007`, and `G-016` are done in repo state.
- The canonical production origin is `https://augurrisk.com`.
- Non-canonical hosts now redirect to the canonical host when `PUBLIC_URL` is set and `TESTING` is off.
- x402list.fun still shows the Conway provider page, but current repo guidance treats that as external stale state.
- `G-007` is now represented by upstream [coinbase/x402 PR #1515](https://github.com/coinbase/x402/pull/1515); next step is merge plus live verification.
- Current known blocker on `G-007`: Coinbase-side review/deploy controls, not repo-side metadata.
- Use `python scripts/check_cdp_discovery.py` before assuming Coinbase Bazaar absence is caused by local metadata drift.
- There are now four confirmed Conway-wallet paid settlements against the live CDP path on 2026-03-08 (one earlier verification plus three additional calls).
- `G-010` is done via the new Python quickstart in `README.md` and `docs/PYTHON_PAYMENT_QUICKSTART.md`.
- `G-011` is done via `examples/javascript/augur-paid-call` and the README link near the top.
- `G-012` is done via the live `/how-payment-works` route linked from the landing page and README.
- The public GitHub repository homepage now matches the canonical site: `https://augurrisk.com`.
- `G-008` and `G-009` are done via `docs/MCP_PACKAGING_PLAN.md` and `examples/javascript/augur-mcp`.
- MCP wrapper guardrails: keep payer wallet addresses out of model-visible output and return explicit MCP errors for Augur `422` / API failures.
