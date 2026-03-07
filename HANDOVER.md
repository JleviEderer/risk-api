# Handover

## Snapshot
- Date: 2026-03-07
- Repo root: `C:\Users\justi\dev\risk-api`
- Branch: `master`
- Status: yellow
- Working tree:
  - Modified: `HANDOVER.md`, `docs/BizPlanning.md`
  - Untracked: `docs/GrowthExecutionPlan.md`
  - Untracked: `.claude/settings.local.json`, `.codex/`, `.playwright-mcp/`, `avatar.html`

## What We Worked On
- Reviewed the codebase and turned that review into a strategy-aware, bugfix-first refactor roadmap.
- Cross-checked refactor advice against `docs/DECISIONS.md`, especially ADR-006 (`ship fast, iterate from live data`).
- Fixed two real correctness issues:
  - proxy implementation scoring missed shared heuristics
  - deployer reputation conflated true "not found" with external API failure
- Synced version/runtime docs with the actual package and container config.
- Refreshed repo handoff and napkin guidance for future sessions.
- Reorganized strategy and execution docs so business planning and active backlog are no longer mixed together.

## What Got Done

### 1) Code review and priority reset
- Reviewed the main flow in:
  - `src/risk_api/app.py`
  - `src/risk_api/analysis/engine.py`
  - `src/risk_api/analysis/scoring.py`
  - `src/risk_api/analysis/reputation.py`
  - `src/risk_api/chain/rpc.py`
- Initial refactor plan over-emphasized modularization.
- After reading `docs/DECISIONS.md`, the practical order became:
  1. Fix implementation scoring correctness
  2. Fix version/doc drift
  3. Fix reputation edge-case semantics
  4. Assess `/stats` scalability risk
  5. Defer `app.py` modularization until traffic or change pain justifies it

### 2) Fixed implementation scoring bug
- Problem:
  - `_analyze_implementation()` in `src/risk_api/analysis/engine.py` manually summed finding points instead of using `compute_score()`.
  - Proxy implementation contracts were missing shared heuristics such as:
    - `suspicious_selector`
    - `tiny_bytecode`
- Fix:
  - Replaced the manual category accumulation path with `compute_score(findings, instructions, bytecode_hex)`.
- Result:
  - Implementation scoring now matches top-level contract scoring behavior.

### 3) Added regression tests for implementation scoring
- Updated `tests/test_engine.py` with new cases covering:
  - implementation-level suspicious selector scoring
  - implementation-level tiny bytecode scoring
- Validation run:
  - `python -m pytest tests/test_engine.py -q`
  - Result: `19 passed in 0.27s`

### 4) Fixed reputation edge-case semantics
- Problem:
  - `get_contract_creator()` in `src/risk_api/analysis/reputation.py` returned `None` for both:
    - genuine "creator not found"
    - Basescan/network/API failure
  - `detect_deployer_reputation()` treated both as a 3-point `"Contract creator not found on Basescan"` finding.
  - This meant external API failure could incorrectly raise contract risk.
- Fix:
  - Added explicit creator lookup states with:
    - `CreatorLookupStatus`
    - `CreatorLookupResult`
  - `get_contract_creator()` now distinguishes:
    - `FOUND`
    - `NOT_FOUND`
    - `ERROR`
  - `detect_deployer_reputation()` now:
    - returns `[]` on external/API error
    - only adds the 3-point finding on true `NOT_FOUND`
- Result:
  - Basescan failure now degrades gracefully without false penalties.

### 5) Updated reputation tests
- Updated `tests/test_reputation.py` to cover the new semantics:
  - creator found
  - creator not found
  - creator API error
  - full graceful failure path returns no findings
- Validation run:
  - `cmd /c python -m pytest tests\test_reputation.py -q`
  - Result: `14 passed in 0.18s`
- Note:
  - A direct PowerShell test invocation hit an environment/runtime issue (`OutOfMemoryException`) unrelated to repo code, so the suite was rerun successfully via `cmd`.

### 6) Fixed docs/runtime drift
- Synced docs to actual runtime config from:
  - `pyproject.toml`
  - `Dockerfile`
- Updated:
  - `README.md`
  - `CLAUDE.md`
- Specific corrections:
  - Python requirement described as `3.10+` package requirement with `3.13` in Docker
  - x402 reference updated from stale `v2.2.0` wording to current `>=2.3.0,<2.4` / `2.3.x` wording
  - production `gunicorn` command in `CLAUDE.md` now matches `Dockerfile`

### 7) Napkin updates
- Updated `.codex/napkin.md` with reusable repo guidance:
  - prefer `pyproject.toml` as dependency/version source of truth
  - metadata/discovery content is duplicated across runtime and scripts
  - reuse `compute_score()` across analysis paths
  - keep Basescan external failure distinct from true "not found"

### 8) Reorganized growth planning docs
- `docs/BizPlanning.md` was rewritten as the durable strategy document:
  - funnel diagnosis
  - durable priorities
  - pricing and moat
  - explicit "what not to do first"
- Added `docs/GrowthExecutionPlan.md` as the operating backlog:
  - workstreams
  - current sprint checklist
  - issue-style items `G-001` through `G-017`
  - sequencing across `Now`, `Next`, and `Later`
- Key planning outcome:
  - prioritize trust and correctness before expanding surface area
  - instrument the funnel early enough to guide the next sprint
  - treat old-domain redirect work as conditional on the registry audit

## What Worked
- Reading `docs/DECISIONS.md` was the right strategic constraint; it prevented an over-engineered refactor path.
- Both correctness fixes were small, local, and easy to regression test.
- Focused test runs (`test_engine.py`, `test_reputation.py`) were fast and sufficient for these changes.
- Using `login:false` for shell commands avoided several PowerShell startup issues in this environment.
- Falling back to `cmd /c` was effective when PowerShell itself became unstable.

## What Didn’t / Gotchas
- Do **not** trust `README.md` / `CLAUDE.md` as the source of truth for versions; they had drifted from `pyproject.toml` and `Dockerfile`.
- `handover` and `napkin` are **skills**, not necessarily slash commands visible in the `/` picker.
- PowerShell in this environment is flaky:
  - some commands failed with CLR/init issues under normal startup
  - one pytest invocation failed with a PowerShell `OutOfMemoryException` before tests even ran
  - `cmd /c ...` is a good fallback for test commands

## Key Decisions
- Do **not** do a large `app.py` modularization now.
  - Reason: `docs/DECISIONS.md` ADR-006 favors shipping and learning over speculative architecture work.
- Treat both discovered issues as **correctness bugs**, not broad refactors:
  - implementation scoring gap
  - reputation error/not-found conflation
- Prefer low-cost correctness and documentation fixes before structural cleanup.

## Recommended Next Steps
1. `G-001` Hard-error no-bytecode inputs in `/analyze`
   - Wrong-address or wallet-address inputs should not return `safe`.
2. `G-002` Standardize all public example addresses
   - Replace any lingering Base/mainnet-confusing examples in landing page, OpenAPI, Bazaar metadata, and `llms.txt`.
3. `G-004` Audit registry and directory listings
   - Verify which surfaces still point at old domains before changing redirect/canonical behavior.
4. `G-016` Instrument the funnel baseline
   - At minimum: landing page views, valid unpaid `402` attempts, invalid addresses, no-bytecode requests, paid requests.
5. Optionally assess `/stats` behavior in `src/risk_api/app.py`
   - It appears to scan the full request log on every request; verify whether that matters yet.

## Important Files Modified This Session
- `src/risk_api/analysis/engine.py`
  - Fixed implementation scoring to route through `compute_score()`.
- `tests/test_engine.py`
  - Added regression coverage for implementation suspicious-selector and tiny-bytecode scoring.
- `src/risk_api/analysis/reputation.py`
  - Added explicit creator lookup result states so API failure and true not-found are handled differently.
- `tests/test_reputation.py`
  - Updated tests for the new reputation semantics.
- `README.md`
  - Synced version/runtime docs with actual package/runtime config.
- `CLAUDE.md`
  - Synced stack and production command docs with `pyproject.toml` and `Dockerfile`.
- `.codex/napkin.md`
  - Added reusable repo guidance for future sessions.
- `docs/BizPlanning.md`
  - Rewritten to hold durable strategy instead of mixed strategy/backlog content.
- `docs/GrowthExecutionPlan.md`
  - New execution backlog for growth, conversion, and revenue work.
- `HANDOVER.md`
  - Updated to reflect the planning split and current execution priorities.

## Important Files Read For Context
- `docs/DECISIONS.md`
- `pyproject.toml`
- `Dockerfile`
- `src/risk_api/app.py`
- `src/risk_api/analysis/scoring.py`
- `src/risk_api/analysis/reputation.py`
- `tests/test_engine.py`
- `tests/test_reputation.py`

## Suggested Restart Context For Next Agent
- The two main correctness issues found during review are already fixed:
  - implementation scoring gap
  - reputation error/not-found conflation
- Current planning now lives in two places:
  - `docs/BizPlanning.md` for durable strategy
  - `docs/GrowthExecutionPlan.md` for active execution
- Best immediate follow-up is the top of the growth checklist:
  - `G-001`
  - `G-002`
  - `G-004`
  - `G-016` in parallel once `G-001` is defined
- Keep the strategy constraint in mind: prefer bug fixes and low-cost cleanup over structural churn unless real usage pain justifies it.
