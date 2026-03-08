# Handover

## Snapshot
- Date: 2026-03-08
- Repo root: `C:\Users\justi\dev\risk-api`
- Branch: `master`
- Status: yellow
- Working tree:
  - Modified: `.codex/napkin.md`, `HANDOVER.md`, `docs/GrowthExecutionPlan.md`, `docs/REGISTRATIONS.md`
  - Untracked: `.claude/settings.local.json`, `.playwright-mcp/`, `avatar.html`

## What We Worked On
- Executed the first pass of the growth backlog in priority order:
  - `G-001` hard-error no-bytecode inputs
  - `G-002` standardize public example addresses
  - `G-004` audit registry and directory state
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

### 4) `G-004` is now closed as an audit
- Rechecked the public surfaces on 2026-03-08 and updated `docs/REGISTRATIONS.md`:
  - `8004scan`: still correct
  - `x402.jobs`: canonical route is live, but public HTML still only exposes a `MaintenanceGate` shell
  - `x402list.fun`: stale legacy provider page is still live at `risk-api.life.conway.tech`, while `augurrisk.com` returns `404`
  - legacy `x402 Bazaar` ID is now treated as historical or unverified until it can be tied to a public surface
  - Coinbase public x402 discovery feed still does not expose Augur
  - `x402.org/ecosystem` still does not list Augur
- Practical result:
  - `G-004` is complete as a current-state audit
  - the next follow-up is `G-005`, not more audit work

### 5) Growth plan docs were updated to reflect progress
- `docs/GrowthExecutionPlan.md`
  - marked `G-001`, `G-002`, `G-004`, and `G-016` complete
- `docs/REGISTRATIONS.md`
  - now records the confirmed stale x402list legacy page and canonical `404`

## Validation
- Previously ran:
  - `cmd /c python -m pytest tests\test_app.py tests\test_logging.py -q`
- Result:
  - `97 passed in 0.92s`
- No code changed in this audit-only follow-up, so no additional test run was needed.

## What Worked
- Doing the no-bytecode check before the paywall was the right product behavior.
  - Because `risk_api.chain.rpc.get_code()` is cached, the later analysis path can reuse the same lookup instead of paying for a second live RPC roundtrip.
- Extending the existing request-log flow was enough for `G-016`.
  - No new analytics service or schema migration was needed.
- Static CLI fetches were enough to confirm the most important discovery facts this time.
  - `x402list.fun/provider/risk-api.life.conway.tech` is live
  - `x402list.fun/provider/augurrisk.com` is `404`

## What Didn't / Gotchas
- Dynamic public directory pages are still awkward to audit from static HTML alone.
  - `x402.jobs` exposes a `MaintenanceGate` shell instead of a clean rendered listing payload.
- The Coinbase public discovery feed responds with JSON, but Augur is not present there.
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
- Treat `x402list.fun` as confirmed stale external directory state for now.
  - Reason: the live old-host provider page still exists and the canonical host page is `404`, even though repo-side metadata already points at `augurrisk.com`.

## Recommended Next Steps
1. Start `G-005`.
   - Treat `x402list.fun` as the main stale Conway-domain follow-up.
   - If there is no self-service update path, document it as directory-side blockage rather than a repo bug.
2. Start `G-003`.
   - Now that examples are standardized, audit wording across landing page, docs, and machine-readable metadata for any remaining trust leaks or chain ambiguity.
3. Consider a small `/dashboard` follow-up only if needed.
   - The data is now in `/stats`; only do more UI work if the current dashboard makes the funnel hard to read.
4. If Augur is still absent from the public CDP feed, treat that as follow-up work for discovery or distribution, not an app bug.

## Important Files Modified
- `docs/GrowthExecutionPlan.md`
  - checked off `G-004`
- `docs/REGISTRATIONS.md`
  - updated the 2026-03-08 current-state audit table
  - marked x402list.fun as confirmed stale on the legacy Conway host
  - downgraded the old manual `x402 Bazaar` ID to historical or unverified
- `.codex/napkin.md`
  - tightened the x402list.fun runbook note with the confirmed live stale provider page and canonical `404`

## Suggested Restart Context For Next Agent
- `G-001`, `G-002`, and `G-016` are implemented and tested.
- `G-004` is complete as an audit and documented in `docs/REGISTRATIONS.md`.
- The highest-signal external discovery finding is:
  - `x402list.fun/provider/risk-api.life.conway.tech` still serves the old provider page
  - `x402list.fun/provider/augurrisk.com` returns `404`
- The most important runtime behavior change is:
  - `/analyze` now rejects empty-bytecode Base addresses with `422` before payment
- The most important analytics change is:
  - `/stats` now exposes funnel counts and recent events via `funnel_stage`
