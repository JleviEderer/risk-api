# Handover

## Snapshot
- Date: 2026-03-08
- Repo root: `C:\Users\justi\dev\risk-api`
- Branch: `master`
- Status: green
- Working tree:
  - Modified: `.codex/napkin.md`, `HANDOVER.md`, `docs/GrowthExecutionPlan.md`, `docs/REGISTRATIONS.md`, `src/risk_api/app.py`, `tests/test_app.py`
  - Untracked: `.claude/settings.local.json`, `.playwright-mcp/`, `avatar.html`

## What We Worked On
- Continued the growth backlog and completed `G-005`, `G-006`, `G-007`, `G-010`, `G-011`, and `G-012` from `docs/GrowthExecutionPlan.md`.

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

## Validation
- Ran:
  - `python -m pytest tests\test_app.py -q`
- Result:
  - `91 passed in 2.29s`
- Verified current upstream listing/submission path against:
  - `https://www.x402.org/ecosystem`
  - `https://github.com/coinbase/x402`
  - `https://github.com/coinbase/x402/tree/main/typescript/site`

## Key Decisions
- Treat `x402list.fun` stale Conway-host output as external directory state, not a repo-side metadata bug.
- Enforce canonical origin at runtime rather than relying only on metadata cleanup.
- Use `308` so method and query string are preserved when clients hit the wrong host.

## Recommended Next Steps
1. Keep `G-005` and `G-006` marked done unless new evidence shows an editable external listing still points at Conway.
2. Monitor [coinbase/x402 PR #1515](https://github.com/coinbase/x402/pull/1515) and verify `https://www.x402.org/ecosystem` after merge.
3. Move to `G-008` to decide the MCP packaging path, or skip ahead to `G-013` if you want more buyer-intent surface area before packaging work.
4. If external directories are refreshed manually, use the repo scripts and `docs/REGISTRATIONS.md` rather than old notes.

## Suggested Restart Context For Next Agent
- `G-001`, `G-002`, `G-003`, `G-004`, `G-005`, `G-006`, `G-007`, and `G-016` are done in repo state.
- The canonical production origin is `https://augurrisk.com`.
- Non-canonical hosts now redirect to the canonical host when `PUBLIC_URL` is set and `TESTING` is off.
- x402list.fun still shows the Conway provider page, but current repo guidance treats that as external stale state.
- `G-007` is now represented by upstream [coinbase/x402 PR #1515](https://github.com/coinbase/x402/pull/1515); next step is merge plus live verification.
- `G-010` is done via the new Python quickstart in `README.md` and `docs/PYTHON_PAYMENT_QUICKSTART.md`.
- `G-011` is done via `examples/javascript/augur-paid-call` and the README link near the top.
- `G-012` is done via the live `/how-payment-works` route linked from the landing page and README.
