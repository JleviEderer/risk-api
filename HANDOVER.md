# Handover

## Snapshot
- Date: 2026-03-09
- Repo root: `C:\Users\justi\dev\risk-api`
- Branch: `master`
- Status: green
- Working tree:
  - Modified: `.codex/napkin.md`, `HANDOVER.md`, `README.md`, `docs/GrowthExecutionPlan.md`, `docs/REGISTRATIONS.md`, `fly.toml`, `src/risk_api/app.py`, `tests/test_app.py`, `tests/test_logging.py`
  - Untracked: `.claude/settings.local.json`, `.playwright-mcp/`, `avatar.html`, `docs/DURABLE_ANALYTICS_CUTOVER.md`, `docs/MCP_PACKAGING_PLAN.md`, `docs/agent-economy-primer.md`, `examples/javascript/augur-mcp/`, `scripts/backfill_analytics_db.py`, `scripts/check_cdp_discovery.py`, `src/risk_api/analytics.py`

## What We Worked On
- Audited scoring and honeypot detection before `G-014` and shipped the smallest high-confidence fixes in the analysis engine.
- Continued the growth backlog and completed `G-005`, `G-006`, `G-007`, `G-010`, `G-011`, and `G-012` from `docs/GrowthExecutionPlan.md`.
- Aligned the public GitHub repository homepage setting with the canonical production domain.
- Flagged the current `coinbase/x402` ecosystem PR as blocked on Coinbase-side review/deploy controls based on the 2026-03-08 email thread.
- Added a Coinbase Bazaar indexing checklist and a one-command public-feed monitor script.
- Logged three additional successful Conway-wallet paid calls against the live CDP facilitator path.
- Completed `G-008` and `G-009` with a working local Node stdio MCP wrapper example for Augur.
- Tightened the MCP wrapper so Augur API errors become MCP errors, wallet addresses are not exposed in tool output, and the x402 client is pinned to Base mainnet.
- Added repo-local git guardrails for parallel-session safety.
- Completed `G-013` with the first three buyer-intent pages and linked them from the landing page plus sitemap.
- Expanded app-level request logging so public page visits and discovery-doc fetches are measurable per instance with host/referrer context.
- Upgraded `/dashboard` into a human-readable traffic-quality view and deployed it live.
- Confirmed that current `/stats` and `/dashboard` still reset across Fly deploys because analytics remain local per-instance state.
- Chose the next direction: keep Fly for the app and move analytics to durable storage instead of migrating platforms just to fix telemetry.
- Started the durable analytics cut by adding a SQLite-backed request-event store behind `/stats` while keeping the JSONL request log as a fallback.
- Documented the new `ANALYTICS_DB_PATH` toggle and the requirement that Fly mount it on a persistent path for restart-safe dashboards.
- Added a one-command JSONL-to-SQLite backfill script plus dashboard/status metadata so cutover can be verified after deploy.
- Updated `fly.toml` so Fly deployments now expect the durable analytics volume and default to `/data/analytics.sqlite3` plus `/data/requests.jsonl`.
- Created the Fly volume, deployed the app, and verified that production `/stats` is now running from persistent SQLite storage on `/data`.

## What Got Done

### 0) Hardened analysis correctness before `G-014`
- Fixed Basescan creator lookup handling so soft API failures such as `NOTOK`, rate-limit, and invalid-key responses are treated as external errors rather than true "not found" deployer states.
- Expanded honeypot detection to catch blacklist-style transfer controls and a common compiled control-flow shape where `PUSH*` appears between the comparison and `JUMPI`.
- Raised unresolved proxy results above the old proxy-only baseline:
  - if a proxy implementation cannot be resolved or fetched, the result now adds an explicit high-risk proxy finding instead of quietly staying at the clean-proxy score
  - if the resolved implementation is itself another proxy, the response now includes `impl_proxy` and scores that unresolved extra hop instead of suppressing it
- Hardened the raw engine contract:
  - `analyze_contract()` now raises `NoBytecodeError` for EOAs or undeployed addresses instead of returning `score=0` / `level=safe`
  - `/analyze` still returns the same `422` no-bytecode response, and now also catches `NoBytecodeError` defensively in the route handler
- Follow-up fixes from second-pass review:
  - widened the honeypot control-flow matcher again so compiler-style transfer guards such as `EQ -> ISZERO -> PUSH* -> JUMPI -> JUMPDEST -> REVERT` are treated as honeypot signals
  - stopped transient Basescan soft errors from sticking in the creator cache; only stable `FOUND` / `NOT_FOUND` creator lookups are cached now
- Kept detector taxonomy stable where possible:
  - blacklist selectors now contribute through the existing `honeypot` signal
  - unresolved proxy states stay under the existing `proxy` category rather than introducing a new public detector family
- Wrote the post-`G-014` design doc for a minimal execution-based honeypot expansion:
  - new doc: `docs/HONEYPOT_EXECUTION_PHASE2.md`
  - preferred shape: separate execution endpoint rather than folding simulation into the current bytecode score path
  - explicit non-goal: do not build broad swap simulation before proving value with one narrow buy/sell path on supported Base routers
- Added focused regression coverage in:
  - `tests/test_patterns.py`
  - `tests/test_engine.py`
  - `tests/test_reputation.py`
- Validation:
  - `python -m pytest tests/test_engine.py tests/test_patterns.py tests/test_reputation.py tests/test_scoring.py -q`
  - `python -m pytest tests/test_app.py -q`

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

### 15) Added repo-local git guardrails
- Added `.githooks/pre-push`:
  - fetches the remote before push
  - blocks push if the upstream branch is ahead or diverged
  - tells the operator to fetch/rebase or merge first
- Added `.githooks/pre-commit`:
  - warns when committing directly on `master` or `main`
- Added the setup command to `README.md`:
  - `git config core.hooksPath .githooks`
- Intended scope:
  - lightweight guardrails only
  - no automatic pull, stash, or push mutation

### 16) Shipped the first buyer-intent pages (`G-013`)
- Added three live public pages in `src/risk_api/app.py`:
  - `/honeypot-detection-api`
  - `/proxy-risk-api`
  - `/deployer-reputation-api`
- Kept them mapped to the same canonical paid endpoint:
  - `https://augurrisk.com/analyze`
- Linked the new pages from the landing page and included them in `/sitemap.xml` so they are crawlable public entry points.
- Kept trust language explicit on every page:
  - `Base mainnet`
  - bytecode-level heuristics for agents
  - `safe` is not an audit or guarantee
- Added route and sitemap coverage in `tests/test_app.py`.

### 17) Tightened app-level traffic instrumentation
- Expanded request logging in `src/risk_api/app.py` beyond just `/` and `/analyze`.
- Logged public GET traffic for:
  - `/`
  - `/how-payment-works`
  - the three buyer-intent pages
  - key discovery/doc endpoints such as `/openapi.json`, `/llms.txt`, `/.well-known/x402`, `/agent-metadata.json`, `/robots.txt`, and `/sitemap.xml`
- Added these fields to each logged request:
  - `host`
  - `referer`
  - `request_id`
- Returned `X-Request-ID` on responses for easier correlation.
- Extended `/stats` with:
  - `stage_counts`
  - `top_paths`
  - `top_hosts`
  - `top_referers`
  - counters for intent-page views, machine-doc fetches, and payment-page views
- Important limitation:
  - this is still app-level telemetry only
  - if the old Conway host returns `403` before reaching Flask, those hits will not appear in app logs or `/stats`
  - edge-layer visibility still needs Fly / proxy / DNS-side inspection

### 18) Upgraded the dashboard and deployed it live
- Reworked `/dashboard` from a minimal chart/table page into a real operator view:
  - summary cards for tracked events, valuable signals, docs traffic, paid requests, landing views, intent views, `402` attempts, and response time
  - traffic-mix chart
  - top paths, hosts, referrers, and stage-count panels
  - a richer recent-events table with path, host, referer, user agent, payment state, and request ID
  - interpretation panels that explain whether traffic looks like crawler noise or movement toward paid demand
- Committed and deployed as:
  - `cd748d0` `Upgrade traffic dashboard`
- Live route:
  - `https://augurrisk.com/dashboard`

### 19) Confirmed the current telemetry limit on Fly
- Live `/dashboard` and `/stats` reset to zero after the dashboard deploy.
- Practical conclusion:
  - current analytics are backed by local per-instance request logs
  - Fly deploys / machine replacement make that state ephemeral
  - the upgraded dashboard is now a better UI, but it is still not canonical analytics
- Decision:
  - do not migrate away from Fly just to fix this
  - next build a durable analytics store, then repoint `/stats` and `/dashboard` to it

### 20) Started the durable analytics backend
- Added `src/risk_api/analytics.py` to centralize analytics aggregation and storage.
- Added a SQLite event-store path controlled by `ANALYTICS_DB_PATH`.
- Request logging now:
  - still writes JSONL when `REQUEST_LOG_PATH` is configured
  - also writes the same structured event into SQLite when `ANALYTICS_DB_PATH` is configured
- `/stats` now:
  - prefers the SQLite backend when `ANALYTICS_DB_PATH` is set
  - falls back to the legacy JSONL request log when only `REQUEST_LOG_PATH` is set
  - preserves the existing response shape used by `/dashboard`
- This is repo-side support only so far:
  - production persistence still requires mounting durable storage on Fly and pointing `ANALYTICS_DB_PATH` at that mounted path
  - without that runtime config, `/dashboard` and `/stats` will still reset on deploy

### 21) Documented the cutover requirements
- Updated `README.md` with:
  - the new `ANALYTICS_DB_PATH` environment variable
  - monitoring notes explaining JSONL fallback versus durable SQLite mode
- Added `docs/DURABLE_ANALYTICS_CUTOVER.md` with:
  - Fly volume creation command
  - `fly.toml` mount snippet
  - secret/env cutover steps
  - restart verification steps
  - single-machine constraint for the SQLite-on-volume approach
- Updated `docs/GrowthExecutionPlan.md`:
  - `G-017` now records that durable backend support exists in repo state, but production cutover is still pending
- Updated `docs/REGISTRATIONS.md`:
  - monitoring notes now distinguish legacy local-log mode from durable SQLite mode
- Updated `.codex/napkin.md`:
  - recurring note now says persistence only exists when `ANALYTICS_DB_PATH` points at mounted durable storage

### 22) Added cutover verification and backfill support
- `/stats` now includes:
  - `storage_backend`
  - `storage_path`
  - `storage_durable`
- The dashboard now surfaces the active analytics backend so operators can tell whether production is still on ephemeral JSONL or has moved to persistent SQLite.
- Added `scripts/backfill_analytics_db.py`:
  - imports legacy JSONL request logs into the SQLite analytics store
  - skips duplicate entries using a content fingerprint
- Hardened the SQLite store itself:
  - duplicate events are ignored on re-import
  - this makes backfill reruns safe enough for cutover/retry workflows

### 23) Wired Fly config for the persistent analytics path
- Updated `fly.toml` with:
  - `[env] ANALYTICS_DB_PATH='/data/analytics.sqlite3'`
  - `[env] REQUEST_LOG_PATH='/data/requests.jsonl'`
  - `[[mounts]] source='augur_analytics' destination='/data'`
- Practical consequence:
  - repo-side Fly config now points production at a persistent analytics path by default
  - production now has the required `augur_analytics` volume attached
  - any recreated or new environment must create the volume before deploy

### 24) Completed the Fly durable-analytics cutover in production
- Checked Fly volume state and confirmed no existing analytics volume was attached.
- Created production Fly volume:
  - `flyctl volumes create augur_analytics --region iad --size 1 -a augurrisk --yes`
  - created volume `vol_vpg0qzjp1y23o8kv`
- Deployed the current app state with:
  - `flyctl deploy --remote-only`
- Verified live production stats:
  - `https://augurrisk.com/stats` now returns
    - `storage_backend=sqlite`
    - `storage_path=/data/analytics.sqlite3`
    - `storage_durable=true`
- Verified restart persistence:
  - sent a logged landing-page hit
  - confirmed `total_requests` increased
  - restarted the live machine with `flyctl machine restart 68349d0fd43d08 -a augurrisk --force`
  - confirmed `total_requests` remained present after restart and `/stats` still reported SQLite durable mode
- Practical result:
  - `/dashboard` and `/stats` no longer reset on normal Fly app restarts/deploys as long as the single app machine keeps the attached volume
  - this solves the original restart-reset problem for the current one-machine deployment model

## Validation
- Ran:
  - `python -m pytest tests\test_logging.py tests\test_app.py -q`
- Result:
  - `120 passed in 7.89s`
- Manually verified:
  - `python scripts/backfill_analytics_db.py --from-log <sample.jsonl> --to-db <sample.sqlite3>`
  - duplicate JSONL entries imported once (`inserted=1 skipped=1`)
- Verified live infrastructure:
  - `flyctl volumes list -a augurrisk`
  - `flyctl machine list -a augurrisk`
  - `flyctl deploy --remote-only`
  - `flyctl machine restart 68349d0fd43d08 -a augurrisk --force`
  - live `https://augurrisk.com/stats` before and after restart
- Deployed and verified live:
  - [Fly Deploy run 22831735298](https://github.com/JleviEderer/risk-api/actions/runs/22831735298) for app-level instrumentation
  - [Fly Deploy run 22835049546](https://github.com/JleviEderer/risk-api/actions/runs/22835049546) for the dashboard upgrade
  - `https://augurrisk.com/dashboard`
  - `https://augurrisk.com/stats`
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
- Keep Fly for app hosting; the current problem is analytics durability, not app hosting.
- Treat `/dashboard` and `/stats` as a useful operator UI over app telemetry; they are now durably backed on the current single-machine Fly deployment, but they still are not canonical edge telemetry or a multi-machine analytics system.

## Recommended Next Steps
1. Keep `G-005` and `G-006` marked done unless new evidence shows an editable external listing still points at Conway.
2. Monitor [coinbase/x402 PR #1515](https://github.com/coinbase/x402/pull/1515) and verify `https://www.x402.org/ecosystem` after merge.
   Current blocker: Coinbase-side review/deploy gate clearance shown in the 2026-03-08 email thread.
3. Decide whether to backfill any historical JSONL request logs into production SQLite or accept the new durable count baseline from the cutover date.
4. If you keep this SQLite-on-volume plan, keep Fly on a single active app machine; do not scale analytics across multiple active machines without moving to shared storage.
5. For old-domain visibility, inspect edge-layer telemetry or config rather than assuming app logs can see Conway-host `403` traffic.
6. After durable analytics are live, return to `G-014` and publish one proof-of-work report that can reuse the buyer-intent pages as internal-link targets.

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
- `G-013` is done via the live `/honeypot-detection-api`, `/proxy-risk-api`, and `/deployer-reputation-api` pages, each internally linked from the landing page and sitemap.
- `/dashboard` is now a much more usable operator UI and is live on production, and it now reads from the persistent SQLite analytics store on `/data`.
- Current observed behavior after cutover: `/stats` and `/dashboard` survive normal Fly machine restarts and deploys on the active attached volume.
- Repo state includes a durable SQLite analytics backend behind `ANALYTICS_DB_PATH`, and production is now cut over to mounted persistent storage.
- There is now a cutover doc at `docs/DURABLE_ANALYTICS_CUTOVER.md` and a backfill helper at `scripts/backfill_analytics_db.py`.
- `/stats` and `/dashboard` now expose which backend is active so cutover can be checked live after deploy.
- `fly.toml` is already prepared to mount Fly volume `augur_analytics` at `/data` and use `/data/analytics.sqlite3` by default.
- Production durable analytics is now live on Fly volume `vol_vpg0qzjp1y23o8kv`, and live `/stats` survived a machine restart with `storage_backend=sqlite`.
- The next technical priority is historical backfill choice plus any future multi-machine analytics design, not migrating away from Fly.
- The public GitHub repository homepage now matches the canonical site: `https://augurrisk.com`.
- `G-008` and `G-009` are done via `docs/MCP_PACKAGING_PLAN.md` and `examples/javascript/augur-mcp`.
- MCP wrapper guardrails: keep payer wallet addresses out of model-visible output and return explicit MCP errors for Augur `422` / API failures.
- Git guardrails: use `.githooks/pre-push` to block pushes when remote history has moved, rather than trying to auto-rebase in hooks.
