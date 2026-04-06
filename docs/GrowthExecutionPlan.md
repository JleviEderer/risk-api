# Augur Growth Execution Plan

> Last updated: 2026-04-06

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

## Active Workstreams

### 1. Action-Aware Product Execution

Goal:
- make Augur more useful at the moment of action without broadening scope

Current rule:
- `approve` is the only supported action for now
- action-aware output must stay additive on top of the contract-level policy
- top-level `decision` remains the contract-level result

Active tasks:

- [x] `A-001` Ship narrow action-aware `approve` support
  Output: optional `action`, `spender`, and `chain` inputs plus additive `action_context` and `action_evaluation` in the response.
  Done means: code, tests, and live OpenAPI are in production.

- [x] `A-002` Add opt-in spender allowlist refinement for `approve`
  Output: optional `APPROVE_SPENDER_ALLOWLIST` config path that lets clean contracts preserve `allow` for trusted spenders and escalates non-allowlisted spenders to `manual_review`.
  Done means: local code and tests are complete.
  Status: complete locally on 2026-04-06; not yet deployed.

- [ ] `A-003` Add explicit machine-readable spender trust output
  Output: a small response field for action-aware `approve` that exposes spender trust state directly, rather than forcing clients to infer it only from reason codes.
  Why now: this sharpens the API contract without broadening scope.
  Depends on: `A-002`.
  Done means: the response shape, OpenAPI, and tests all expose the trust state clearly.

- [x] `A-004` Add action-aware observability for `approve`
  Output: request/event logging that shows whether `approve` used no allowlist, an allowlisted spender, or a non-allowlisted spender.
  Why now: this gives production evidence about whether the new policy is useful before adding more actions.
  Depends on: `A-002`.
  Done means: logs or analytics can answer how action-aware `approve` is actually being used.
  Status: complete locally on 2026-04-06; not yet deployed.

- [ ] `A-005` Deploy the next narrow `approve` refinement
  Output: commit, push, deploy, and verify the next `approve` slice.
  Why now: keep the product loop moving without piling up undeployed semantic changes.
  Depends on: choose one of `A-003` or `A-004`, not both plus more.
  Done means:
  - app deploy is live
  - `https://augurrisk.com/health` is healthy
  - live `openapi.json` matches the new contract
  - one real paid production smoke covers the action-aware request shape

Rule for this workstream:
- do one more narrow refinement, then deploy

### 2. Conversion And First-Use Clarity

Goal:
- make it easier for a new evaluator to reach a justified first paid call

Active tasks:

- [ ] `C-001` Review whether the homepage and machine docs now describe action-aware `approve` clearly enough
  Output: small wording pass only if the current public copy undersells or confuses the action-aware layer.
  Why now: the product has moved closer to the action point, so the public explanation may lag.
  Depends on: `A-005`.
  Done means: public docs explain the narrow `approve` layer without over-claiming destination validation.

- [ ] `C-002` Keep the paid-call quickstarts aligned with the live contract
  Output: Python, JavaScript, MCP, and machine-doc examples stay accurate as the action-aware layer evolves.
  Why now: drift here creates trust loss before the first payment.
  Depends on: any action-aware contract change that ships.
  Done means: examples and docs match the live API shape.

### 3. Registry And Discovery Hygiene

Goal:
- keep public discovery aligned while treating external indexing issues correctly

Active tasks:

- [ ] `R-001` Re-check Coinbase public discovery feed after the next production deploy
  Output: one fresh feed check after a real paid smoke on the current live app.
  Why now: the app is healthy and the remaining gap still looks external.
  Depends on: `A-005`.
  Done means: we either see Augur in the feed or have a cleaner escalation packet.

- [ ] `R-002` Keep `x402list.fun` classified as external stale state unless the directory itself changes
  Output: no repo-side churn disguised as progress.
  Why now: this has repeatedly looked external rather than app-side.
  Depends on: none.
  Done means: we stop revisiting this unless there is actual external movement.

Note:
- execution details and verification steps live in `docs/REGISTRATIONS.md`

### 4. Distribution And Outreach

Goal:
- get qualified builder traffic from the right channels

Active tasks:

- [ ] `D-001` Execute one targeted distribution push
  Output: one relevant post or reply plus one supporting follow-up, taken from the queue in `docs/outreach.md`.
  Why now: distribution still needs a real measured follow-through, not more planning.
  Depends on: existing proof and machine-readable surfaces are already good enough.
  Done means: the post is live and we can watch traffic/referral impact.

- [ ] `D-002` Add basic source attribution where feasible
  Output: better visibility into docs, registries, and outreach as traffic sources.
  Why now: we should not keep doing discoverability work that cannot be judged.
  Depends on: none.
  Done means: major acquisition surfaces can be compared with simple evidence.

- [ ] `D-003` Track AI-answer visibility separately from registry work
  Output: a lightweight recurring check for whether Augur is retrieved or cited in answer engines.
  Why now: retrieval remains a real problem, and it is not the same problem as listing hygiene.
  Depends on: `D-002` ideally, but can start manually before then.
  Done means: answer-engine visibility is reviewed as its own workstream.

## Immediate Queue

Do now:

1. `A-005` Deploy the next narrow `approve` refinement
2. real paid production smoke on the action-aware request shape
3. `R-001` Re-check Coinbase public discovery feed

Do next:

1. `D-001` Execute one targeted distribution push
2. `D-002` Improve source attribution
3. `D-003` Run a lightweight AI-answer visibility check
4. consider `A-003` only if the current logs show a real need for explicit spender-trust output

Do later:

1. only consider a second action after live evidence shows the `approve` layer is useful and stable
2. only broaden beyond `approve` if the next action is equally narrow and defensible

## Completed Baseline

These are no longer the active bottleneck, but they matter as completed prerequisites:

- [x] canonical domain and redirect policy
- [x] public machine-readable docs and discovery surfaces
- [x] x402 payment docs and examples
- [x] MCP packaging path
- [x] first proof-of-work report
- [x] initial registry alignment pass
- [x] action-aware `approve` V1 in production

## Not In Scope Right Now

Do not turn this plan into a queue for:

- a wallet product
- broad transaction simulation
- generic anti-phishing or session security
- a broad multi-action expansion without live evidence
- framework wrappers without actual pull
