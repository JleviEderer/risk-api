# Handover

## Snapshot
- Date: 2026-03-07
- Repo root: `C:\Users\justi\dev\risk-api`
- Branch: `master`
- Status: yellow
- Working tree:
  - Modified: `README.md`, `docs/GrowthExecutionPlan.md`, `docs/REGISTRATIONS.md`, `src/risk_api/app.py`, `tests/conftest.py`, `tests/test_app.py`, `tests/test_logging.py`
  - Untracked: `.claude/settings.local.json`, `.playwright-mcp/`, `avatar.html`

## What We Worked On
- Executed the first pass of the growth backlog in priority order:
  - `G-001` hard-error no-bytecode inputs
  - `G-002` standardize public example addresses
  - `G-004` continue directory audit
  - `G-016` lightweight funnel instrumentation on the existing request-log `/stats` path

## What Got Done

### 1) `G-001` no-bytecode inputs now fail before payment
- Problem:
  - `/analyze` only validated address shape before the x402 gate.
  - EOA, wallet, or undeployed Base addresses could still reach analysis and look `safe`, which is misleading.
- Fix:
  - `src/risk_api/app.py`
    - added a pre-paywall `get_code()` check for `GET` and `POST`
    - returns `422` with `No contract bytecode found at Base address: ...` when bytecode is empty
    - keeps `HEAD` lightweight and syntax-only so payment preflight behavior is unchanged
    - returns `502` before payment if the Base RPC lookup itself fails
- Result:
  - wrong-address and wallet-address inputs no longer look analyzable or billable

### 2) `G-002` public examples now use one Base example set
- Canonical examples now used across public app surfaces:
  - safe example: Base WETH `0x4200000000000000000000000000000000000006`
  - proxy example: Base USDC `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
  - implementation example: `0x2cE6409Bc2Ff3E36834E44e15bbE83e4aD02d779`
- Updated in:
  - OpenAPI examples
  - landing-page curl example
  - Bazaar/x402 discovery examples
  - `llms.txt` / `llms-full.txt`
  - `README.md`
  - x402 test fixtures

### 3) `G-016` funnel instrumentation is now in the request log and `/stats`
- `src/risk_api/app.py`
  - request logging now tracks both `/` and `/analyze`
  - each logged event can carry `funnel_stage`
  - current stages in use:
    - `landing_view`
    - `unpaid_402`
    - `invalid_address`
    - `no_bytecode`
    - `paid_request`
    - `analyze_success`
    - `rpc_error`
- `/stats` now returns:
  - `funnel.landing_views`
  - `funnel.valid_unpaid_402_attempts`
  - `funnel.invalid_address_requests`
  - `funnel.no_bytecode_requests`
  - `funnel.paid_requests`
  - hourly buckets with the same breakdown
- `/dashboard` was only lightly adjusted:
  - labels now say "Tracked Events"
  - recent table shows event stage
  - it still uses the same `/stats` endpoint and is still a per-instance log view, not durable analytics

### 4) `G-004` directory audit continued and was documented
- Added a fresh audit table to `docs/REGISTRATIONS.md` for 2026-03-07.
- Current audit state captured there:
  - `8004scan` / ERC-8004 page: correct, canonical domain visible
  - `x402.jobs`: public listing route returns `200` but the page is wrapped in a `MaintenanceGate`; old Conway slug still appears in the path, so manual/authenticated verification is still needed
  - `x402list.fun`: still not trustworthy as a repo-side signal; static HTML did not expose the Augur listing in this pass
  - `x402.org/ecosystem`: missing
  - Coinbase public x402 discovery feed: responds, but no `Augur` / `augurrisk.com` item is present
- Practical result:
  - `G-004` advanced, but I would not mark it fully closed until the remaining manual/dynamic-directory checks are done

### 5) Growth plan docs were updated to reflect progress
- `docs/GrowthExecutionPlan.md`
  - marked `G-001`, `G-002`, and `G-016` complete
- `README.md`
  - now documents the explicit no-bytecode `422`
  - example response matches the canonical Base proxy example

## Validation
- Ran:
  - `cmd /c python -m pytest tests\test_app.py tests\test_logging.py -q`
- Result:
  - `97 passed in 3.24s`

## What Worked
- Doing the no-bytecode check before the paywall was the right product behavior.
  - Because `risk_api.chain.rpc.get_code()` is cached, the later analysis path can reuse the same lookup instead of paying for a second live RPC roundtrip.
- Extending the existing request-log flow was enough for `G-016`.
  - No new analytics service or schema migration was needed.
- Targeted route/logging tests were sufficient and fast.

## What Didn’t / Gotchas
- Dynamic/public directory pages are still awkward to audit from static HTML alone.
  - `x402.jobs` exposed a `MaintenanceGate` shell instead of a clean public listing payload.
  - `x402list.fun` did not expose the relevant listing details in prerendered HTML.
- The Coinbase public discovery feed endpoint currently responds with JSON, but Augur is not present there.
  - Do not assume facilitator settlements alone have indexed the service.
- `/stats` still scans the full request log on each request.
  - Acceptable for now, but worth revisiting if traffic grows.

## Key Decisions
- Keep the no-bytecode rejection before x402 payment.
  - Reason: users should not pay for EOAs or undeployed addresses, and those inputs should never look `safe`.
- Keep `HEAD /analyze` cheap.
  - Reason: it preserves the current payment-preflight behavior without forcing an RPC lookup on every HEAD request.
- Treat the new funnel instrumentation as log enrichment, not a dashboard project.
  - Reason: this satisfies `G-016` without introducing a heavier analytics dependency.
- Treat the remaining directory issues as external/manual verification work unless a live surface clearly exposes stale repo-controlled metadata.

## Recommended Next Steps
1. Finish `G-004`.
   - Manually verify `x402.jobs` from an authenticated browser session.
   - Recheck `x402list.fun` in a live browser and capture whether it still shows the Conway host.
   - Decide whether the legacy `x402 Bazaar` ID in `docs/REGISTRATIONS.md` still maps to a real public surface or should be downgraded to historical.
2. Start `G-003`.
   - Now that examples are standardized, audit wording across landing page, docs, and machine-readable metadata for any remaining trust leaks or chain ambiguity.
3. Consider a small `/dashboard` follow-up only if needed.
   - The data is now in `/stats`; only do more UI work if the current dashboard makes the funnel hard to read.
4. If Augur is still absent from the public CDP feed, treat that as follow-up work for discovery/distribution, not an app bug.

## Important Files Modified
- `src/risk_api/app.py`
  - pre-paywall no-bytecode validation
  - canonical example constants
  - funnel-stage request logging
  - richer `/stats`
  - minor `/dashboard` stage display tweak
- `tests/test_app.py`
  - route coverage for the new no-bytecode `422`
  - OpenAPI coverage for the new `422` examples
- `tests/test_logging.py`
  - landing-view logging coverage
  - no-bytecode logging coverage
  - `/stats` funnel coverage
- `tests/conftest.py`
  - canonical Bazaar fixture examples
  - default mocked bytecode for x402-gated tests
- `README.md`
  - documented no-bytecode `422`
  - canonicalized example response
- `docs/GrowthExecutionPlan.md`
  - checked off `G-001`, `G-002`, `G-016`
- `docs/REGISTRATIONS.md`
  - added the 2026-03-07 current-state audit table

## Suggested Restart Context For Next Agent
- `G-001`, `G-002`, and `G-016` are implemented and tested.
- `G-004` is partially completed in docs, but still needs manual/dynamic verification for `x402.jobs` and `x402list.fun`.
- The most important runtime behavior change is:
  - `/analyze` now rejects empty-bytecode Base addresses with `422` before payment
- The most important analytics change is:
  - `/stats` now exposes funnel counts and recent events via `funnel_stage`
