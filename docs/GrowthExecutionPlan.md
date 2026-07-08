# Augur Growth Execution Plan

> Last updated: 2026-07-08

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
  Evidence: Fly app `augurrisk`, machine `48e64d2fd31728`, `1` passing check; `/health` returned `ok`; `/stats` returned `storage_backend=sqlite`, `storage_durable=true`, `storage_path=/data/analytics.sqlite3`, `paid_requests=35`, and populated `traffic_classes` after the discovery-pass paid smoke. The exact Fly machine version and total request count are volatile after each deploy/request.

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
  Evidence from 2026-07-06: `scripts/check_cdp_discovery.py --max-pages 200` scanned `20,000` resources after validation and paid settlement and did not find `augurrisk.com/analyze`; the only Augur-related match was the stale `https://risk-api.life.conway.tech/analyze` resource. The old Conway domain timed out from this machine.
  Current status: rechecked on 2026-07-07 and still stale. Full CDP scan still returned `NOT_FOUND`; merchant discovery for payTo still returns only `https://risk-api.life.conway.tech/analyze`; search `urlSubstring=augurrisk.com` returns no resources; search `urlSubstring=risk-api.life.conway.tech` returns the stale resource. User submitted the CDP support case on 2026-07-07 using `docs/CDP_BAZAAR_ESCALATION_2026-07-06.md`; next recheck is 2026-07-09 or after support replies.
  Done means: CDP discovery returns the canonical `augurrisk.com` resource for Augur-related searches or a CDP support/Discord escalation has been submitted and tracked.

- [x] `D-002` Re-list or repair x402.jobs
  Output: restore an Augur x402.jobs listing pointing at `https://augurrisk.com/analyze?address=0x4200000000000000000000000000000000000006`.
  Evidence from 2026-07-06: `https://www.x402.jobs/search?q=augur` returned `404`; `python scripts/register_x402jobs.py --list` succeeded with the available API key but returned no Augur resource.
  Status: repaired on 2026-07-06. Resource ID `4964c164-c748-4cd6-a7a5-0ac33e118b6a`, listing `https://x402.jobs/resources/augurrisk-com/augur-2`, canonical URL, `max_amount_required=100000` (`$0.10` USDC).
  Done means: `scripts/register_x402jobs.py --list` shows Augur or the dashboard shows the current listing with the canonical URL.

- [x] `D-003` Refresh `docs/REGISTRATIONS.md` after discovery repair
  Output: update registry status after CDP/Bazaar and x402.jobs are actually fixed or proven external.
  Depends on: `D-001` and `D-002`.
  Status: refreshed on 2026-07-06 with x402.jobs repair and CDP/Bazaar escalation evidence.

### 3. API-Output Clarity

- [x] `A-003` Make the machine-branching field unambiguous
  Output: ensure agents can branch on one primary decision field without being misled by `level=safe` plus action-level `warn`.
  Why now: real paid callers exist, so response ambiguity is commercial risk.
  Preconditions completed: `L-001` paid-response logging, `Q-001` real paid-contract regressions, and the 2026-07-07 pre-A-003 coverage gap pass are done. The added coverage lives outside the paid-only corpus and locks both a synthetic `block` primary-decision case and the exact WETH approve ambiguity (`level=safe`, top-level `decision=allow`, `action_evaluation.decision=warn`).
  Status: implemented and deployed on 2026-07-08 from `docs/A003_DESIGN_SPEC.md` v2. Top-level `decision` is now the effective max-strictness branch field, `contract_decision` is always emitted as the contract-only policy action, and top-level `recommended_policy.action` is rebuilt to equal `decision`. `action_context` and `action_evaluation` remain unchanged. Public docs/OpenAPI/examples/MCP wrapper surfaces were updated, including the MCP output schema so structured content no longer strips `decision`, `contract_decision`, or `recommended_policy`.
  Validation: `python -m pytest -q` -> `429 passed`; `python -m pyright src\ tests\` -> `0 errors`; `python auto\loop.py` -> `PASS (59/59 checks passed)`; `python -m py_compile ...` passed; `npm run smoke` in `examples/javascript/augur-mcp` passed without paid credentials; GitHub Typecheck and Fly Deploy passed for implementation commit `51bedaa`. Live checks passed for `/health`, unpaid WETH `/analyze` returning `402`, `payment-required` header presence, OpenAPI `contract_decision` schema/required field, and `/llms-full.txt` `contract_decision`/primary-decision prose. Fable review approved the implementation with no blocking findings. Paid approve smoke on 2026-07-08 used the configured local payer wallet against WETH approve and returned `200`; Fly SQLite pull `.codex/live_db/2026-07-08-1610/analytics.sqlite3` showed `37` paid `/analyze` 200 rows and `2` paid response snapshots, with the latest snapshot `decision=warn`, `contract_decision=allow`, top-level policy action `warn`, `action_evaluation.decision=warn`, `action=approve`, untruncated `response_bytes=797`, and no payment/private markers. Paid MCP smoke passed and returned structured content containing `decision`, `contract_decision`, and `recommended_policy`. `tests/fixtures/paid_contract_cases.json` and `tests/test_paid_contract_regressions.py` were not edited.
  Remaining: monitor post-A-003 paid traffic and decide whether future payer attribution (`L-002`) needs facilitator IDs or whether off-chain correlation is enough.

### 4. Logging

- [x] `L-001` Log full paid analysis responses safely
  Output: persist the paid response body or a bounded redacted response snapshot for paid `/analyze` rows.
  Why now: current durable analytics records timing, UA, referer, analyzed address, action/spender, score, level, and paid status, but not the full findings or policy output.
  Status: completed on 2026-07-07. Durable SQLite now creates `paid_response_snapshots` beside `request_events` and stores a redacted, byte-bounded copy of the serialized public `/analyze` response only for paid `/analyze` HTTP 200 rows. Snapshot rows are linked to `request_events.id` and `request_fingerprint`; `/stats` still aggregates only from `request_events`.
  Post-logging smoke: a canonical paid WETH smoke on 2026-07-07 succeeded with response `200`, `score=0`, `level=safe`, `findings=0`. A fresh Fly SQLite pull at `.codex/live_db/2026-07-07-1335/analytics.sqlite3` showed `36` paid `/analyze` rows and `1` `paid_response_snapshots` row. The snapshot row was untruncated (`response_bytes=339`), `decision=allow`, `score=0`, `level=safe`, and did not contain payment signature, payer wallet, or tx-hash markers.
  Privacy limits: the snapshot path does not add source IP, payer wallet, transaction hash, payment signature, or facilitator payload logging. Keys containing payment/signature/payer/wallet/transaction/IP-style terms are redacted, and oversized snapshots are stored as a bounded valid JSON preview with `truncated=1`.
  Query:
  ```powershell
  @'
  import json, sqlite3, sys
  db = sys.argv[1]
  con = sqlite3.connect(db)
  con.row_factory = sqlite3.Row
  for r in con.execute("""
    SELECT e.ts, e.address, e.action, e.spender, e.score, e.level,
           s.truncated, s.response_bytes, s.snapshot_json
    FROM paid_response_snapshots s
    JOIN request_events e ON e.id = s.request_event_id
    ORDER BY e.ts DESC
    LIMIT 25
  """):
      snap = json.loads(r["snapshot_json"])
      print({
          "ts": r["ts"],
          "address": r["address"],
          "action": r["action"],
          "spender": r["spender"],
          "score": r["score"],
          "level": r["level"],
          "truncated": bool(r["truncated"]),
          "response_bytes": r["response_bytes"],
          "decision": snap.get("decision"),
          "action_decision": (snap.get("action_evaluation") or {}).get("decision"),
          "findings": len(snap.get("findings", [])) if isinstance(snap.get("findings"), list) else None,
      })
  '@ | python - ".codex\live_db\<stamp>\analytics.sqlite3"
  ```
  Done means: paid-call forensics can reconstruct what Augur told the caller without storing payer wallet, transaction hash, or source IP.

- [ ] `L-002` Add payer attribution plan without over-logging
  Output: decide whether to store facilitator record IDs, payment transaction hashes, or a correlation key.
  Done means: payer attribution can be audited without adding unnecessary personal data or brittle scraper dependence.

### 5. Paid-Contract Regressions

- [x] `Q-001` Build a golden regression suite from real paid contracts
  Output: fixtures and expected outcomes for contracts that real paid callers screened.
  Status: completed on 2026-07-07 in `tests/fixtures/paid_contract_cases.json` and `tests/test_paid_contract_regressions.py`.
  Fixture source: durable Fly SQLite pull `.codex/live_db/2026-07-07-1249/analytics.sqlite3`, using real paid `/analyze` rows only. `paid_response_snapshots` existed but had `0` rows at generation time because no paid call had landed after the 2026-07-07 logging deploy, so the fixtures use historical `request_events` address/output metadata plus current public Base bytecode snapshots.
  Contracts covered:
  - Base WETH `0x4200000000000000000000000000000000000006` (`22` paid rows): protects the canonical WETH/WWETH-context integration path as `score=0`, `level=safe`, `decision=allow`.
  - Moo Beefy Aerodrome FUN-USDC `0x73fd88f0c1364f9f81d52dd6bb9fff6429597ccd` (`3` paid rows): protects EIP-1167 proxy resolution into Beefy implementation bytecode and the `warn` outcome for proxy/delegatecall/suspicious selector context.
  - Aerodrome AERO `0x940181a94a35a4569e4529a3cdfb74e38fd98631` (`3` paid rows): protects hidden-mint signal surfacing as `manual_review`, not `allow`.
  - Moo Beefy Aero WETH-ZRO `0x8b1f5874e0b5aa3eeb117b82af8d59fcb52d122a` (`2` paid rows): protects the WETH-pair Beefy vault path with the same proxy-resolution outcome.
  - Mintpad `0xfb51d2120c27bb56d91221042cb2dd2866a647fe` (`2` paid rows): protects non-WETH suspicious-selector warning behavior.
  - Recover `0x1f9840a85d5af5bf1d1762f925bdaddc4201f984` (`1` paid row): protects a non-WETH clean `allow` baseline.
  - RUG PULL `0x3af31d295c09aca8ae4524daa6108f17f9e54f32` (`1` paid row): protects the corrected valid address and suspicious-selector warning behavior.
  - Pudgy Penguin on Base `0x722df2b5552354950a7b55d8872a4e8f33ed1b07` (`1` paid row): protects another non-WETH clean `allow` baseline.
  Privacy limits: fixtures store paid contract addresses, paid counts/timestamps, public bytecode, and expected analyzer outputs only. They do not store source IP, payer wallet, transaction hash, user agent, referer, payment signature, or facilitator payloads.
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

1. Recheck CDP/Bazaar on 2026-07-09 or when CDP support replies.
2. Monitor the next post-A-003 paid rows and use `paid_response_snapshots` for any caller-quality review.
3. Keep x402.jobs monitored at `https://x402.jobs/resources/augurrisk-com/augur-2`.

Do next:

1. Decide whether `L-002` needs facilitator IDs or transaction hashes, or whether off-chain correlation is enough.
2. After A-003 live verification, compare new paid action-aware snapshots against the design invariants.
3. Decide whether `L-002` can wait until after A-003 or whether payer-attribution planning should happen first.

Do later:

1. Decide `P-001` pricing test by 2026-07-20 even if CDP/Bazaar is still waiting on external support.
2. Execute `O-001` distribution after x402.jobs is stable and CDP/Bazaar is either fixed or actively escalated.
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
