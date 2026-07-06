# Augur Growth Execution Plan

> Last updated: 2026-07-06

This document is the active operating tracker for product, distribution, and conversion work.

Use it to stay on task, sequence work, and mark off execution as it lands.

This is not the place for long-form strategy argument. When the strategy changes, update the source docs first, then reflect the execution consequences here.

## Source Docs

Primary source docs for this plan:

- `docs/PRODUCT_DIRECTION_UPDATE.md`
  Current product-direction call. This is the main strategy source.
- `docs/REGISTRATIONS.md`
  Source of truth for public listings, registry status, and discovery hygiene.
- `docs/outreach.md`
  Source of truth for community-post and outreach execution status.
- `docs/SELLING_TO_AGENTS_MEMO.md`
  Current market-fit and agent-buying behavior guidance.
- `docs/llm_discoverability_synthesis.md`
  Current answer-engine and retrieval problem framing.

Secondary/background docs:

- `docs/PRODUCT_WEDGE_MEMO.md`
- `docs/agent-economy-primer.md`
- `docs/X402_ECOSYSTEM_SUBMISSION.md`

## Current Product Thesis

Augur should win as:

- deterministic Base contract admission control for agents
- a pre-transaction decision layer, not just a contract score
- a narrow, machine-readable service that agents are rational to call before touching money

Current product rule:

- keep the contract-screening engine
- keep policy outputs explicit
- move one step closer to the action point
- stay narrow and additive
- do not broaden into wallet security, transaction simulation, or a general control plane unless real demand proves it

## Current North Star

- Increase real paid `/analyze` calls from qualified users

Current leading indicators:

- real paid calls per week
- valid unpaid `402` attempts
- source/referral quality
- repeat usage from real evaluators
- whether action-aware policy improves clarity at the moment of decision

## Operating Rules

1. Do not batch several semantic product changes into one deploy if they affect the decision layer.
2. Keep action-aware work narrow, additive, and machine-readable.
3. Treat production verification as part of the task, not follow-up.
4. Use `docs/REGISTRATIONS.md` for listing state, not this file.
5. Use `docs/outreach.md` for post history, not this file.
6. Keep this file focused on active execution only.

## July 2026 Execution Checklist

Current rule:
- hygiene, discovery repair, tracking, and evidence capture come before product API changes
- do not change the paid response contract until logging and regression evidence are in place
- keep the main product direction as `Base contract admission control for agents`

### 1. Hygiene

- [x] `H-001` Verify live health and bounded `/stats`
  Output: live `/health`, `/stats`, and Fly machine state checked on 2026-07-06.
  Evidence: Fly app `augurrisk`, machine `48e64d2fd31728`, version `115`, `1` passing check; `/health` returned `ok`; `/stats` returned `storage_backend=sqlite`, `storage_durable=true`, `storage_path=/data/analytics.sqlite3`, `total_requests=339399`, `paid_requests=34`, and populated `traffic_classes`.

- [x] `H-002` Commit and push the deployed `/stats` SQLite analytics fix
  Output: persist the already-deployed version `115` behavior in git so a future clean deploy does not reintroduce the dashboard timeout.
  Done means: full tests pass, live behavior matches the local fix, commit is on `origin/master`, and no product API behavior changes are included.
  Status: completed in the 2026-07-06 hygiene pass after full test suite validation.

- [x] `H-003` Revoke the exposed Fly app token from the June deploy session
  Output: token `codex-deploy-2026-06-04` was found active and revoked on 2026-07-06 using `flyctl tokens revoke`.
  Remaining note: Fly CLI can list app limited-access tokens, but account-wide personal access-token review may still require the Fly dashboard.

- [ ] `H-004` Review remaining long-lived Fly deploy tokens
  Output: decide whether the two generic `flyctl deploy token` entries and `augurrisk` token are still needed.
  Why now: they are not proven exposed, so do not revoke during a narrow hygiene pass without confirming their current use.
  Done means: unused long-lived tokens are revoked or renamed with owner/purpose.

### 2. Discovery

- [ ] `D-001` Repair Coinbase Bazaar / CDP discovery indexing
  Output: make `https://augurrisk.com/analyze` discoverable in CDP Bazaar search.
  Evidence from 2026-07-06: `scripts/check_cdp_discovery.py` scanned `20,000` resources and did not find `augurrisk.com/analyze`; the only Augur-related match was the stale `https://risk-api.life.conway.tech/analyze` resource. The old Conway domain timed out from this machine.
  Done means: CDP discovery returns the canonical `augurrisk.com` resource for Augur-related searches or there is a support/escalation packet with the stale-resource evidence.

- [ ] `D-002` Re-list or repair x402.jobs
  Output: restore an Augur x402.jobs listing pointing at `https://augurrisk.com/analyze?address=0x4200000000000000000000000000000000000006`.
  Evidence from 2026-07-06: `https://www.x402.jobs/search?q=augur` returned `404`; `python scripts/register_x402jobs.py --list` succeeded with the available API key but returned no Augur resource.
  Done means: `scripts/register_x402jobs.py --list` shows Augur or the dashboard shows the current listing with the canonical URL.

- [ ] `D-003` Refresh `docs/REGISTRATIONS.md` after discovery repair
  Output: update registry status after CDP/Bazaar and x402.jobs are actually fixed or proven external.
  Depends on: `D-001` and `D-002`.

### 3. API-Output Clarity

- [ ] `A-003` Make the machine-branching field unambiguous
  Output: ensure agents can branch on one primary decision field without being misled by `level=safe` plus action-level `warn`.
  Why now: real paid callers exist, so response ambiguity is commercial risk.
  Constraint: no product API changes in the July hygiene pass; design this only after logging and regression cases are locked.
  Done means: response shape, OpenAPI, examples, and tests make the primary branch field explicit.

### 4. Logging

- [ ] `L-001` Log full paid analysis responses safely
  Output: persist the paid response body or a bounded redacted response snapshot for paid `/analyze` rows.
  Why now: current durable analytics records timing, UA, referer, analyzed address, action/spender, score, level, and paid status, but not the full findings or policy output.
  Done means: paid-call forensics can reconstruct what Augur told the caller without storing payer wallet, transaction hash, or source IP.

- [ ] `L-002` Add payer attribution plan without over-logging
  Output: decide whether to store facilitator record IDs, payment transaction hashes, or a correlation key.
  Done means: payer attribution can be audited without adding unnecessary personal data or brittle scraper dependence.

### 5. Paid-Contract Regressions

- [ ] `Q-001` Build a golden regression suite from real paid contracts
  Output: fixtures and expected outcomes for contracts that real paid callers screened.
  Initial set: Base WETH `0x4200000000000000000000000000000000000006`, Mintpad `0xfb51d2120c27bb56d91221042cb2dd2866a647fe`, RUG PULL `0x3Af31D295C09aCa8AE4524DAA6108F17F9e54F32`, Pudgy Penguin `0x722dF2b5552354950a7b55d8872a4e8f33eD1b07`, and the recurring Beefy/AERO-style paid cases from the July analytics pull.
  Depends on: `L-001` for future exact-response capture.
  Done means: future detector or policy edits fail tests if they regress real paid use cases without an intentional fixture update.

### 6. Pricing

- [ ] `P-001` Decide whether to test a lower x402 price
  Output: keep `$0.10`, or run a dated `$0.02-$0.03` price test with clear success criteria.
  Why now: the category has cheaper x402 scanners and the funnel shows many valid unpaid `402` attempts versus `34` paid calls.
  Timing: decide by 2026-07-20 even if CDP/Bazaar repair is still waiting on Coinbase or other external support.
  Done means: the price decision is documented with the test window, target paid calls/week, and rollback rule.

### 7. Distribution

- [ ] `O-001` Execute one focused distribution push after discovery hygiene
  Output: one concrete Base/x402 community post or reply using the live WETH proof and admission-control framing.
  Depends on: fix or document CDP/Bazaar and x402.jobs first, so the outreach sends agents to working discovery surfaces.

- [ ] `O-002` Add basic source attribution for outreach and registry traffic
  Output: a simple way to distinguish marketplace, docs, and outreach-driven traffic without relying on raw request counts.

## Immediate Queue

Do now:

1. Finish `H-002`: commit and push the bounded `/stats` fix plus this tracking update after tests pass.
2. Run `D-001`: repair CDP/Bazaar indexing or prepare the stale Conway escalation packet.
3. Run `D-002`: recreate or update the x402.jobs listing with the canonical Augur URL.

Do next:

1. Implement `L-001` full paid-response logging.
2. Build `Q-001` paid-contract regression cases.
3. Design `A-003` decision-primary output clarity without widening the product.

Do later:

1. Decide `P-001` pricing test after discovery is no longer obviously broken.
2. Execute `O-001` distribution after the main directories point at working URLs.
3. Consider A-003-plus/batch ergonomics only after logging and regressions are in place.

## Completed Baseline

These are no longer the active bottleneck, but they matter as completed prerequisites:

- [x] canonical domain and redirect policy
- [x] public machine-readable docs and discovery surfaces
- [x] x402 payment docs and examples
- [x] MCP packaging path
- [x] first proof-of-work report
- [x] initial registry alignment pass
- [x] action-aware `approve` V1 in production
- [x] first-party action-aware `approve` example live on `/`, `skill.md`, `llms.txt`, and `llms-full.txt`

## Not In Scope Right Now

Do not turn this plan into a queue for:

- a wallet product
- broad transaction simulation
- generic anti-phishing or session security
- a broad multi-action expansion without live evidence
- framework wrappers without actual pull
