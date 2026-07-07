# A-003 Design Spec: Decision-Primary Response Output

> Date: 2026-07-07
> Author: Fable (design), pending Codex critique before implementation
> Status: DRAFT — design only. No product API behavior changes in this pass.
> Scope guard: this spec changes response serialization and documentation only. It does not change pricing, discovery metadata, detector behavior, scoring, or the policy engine.

## 1. Problem

Augur's response has two fields an agent can mistake for "the answer," and they can disagree. Real paid traffic hit both ambiguities:

**Ambiguity 1 — `level` vs `decision` (contract-level).**
`level` is a score band (measurement). `decision` is the policy recommendation. They diverge by design: Mintpad (`0xfb51d2120c27bb56d91221042cb2dd2866a647fe`, 2 paid rows) and RUG PULL (`0x3af31d295c09aca8ae4524daa6108f17f9e54f32`, 1 paid row) both return `level=safe` + `decision=warn` (locked in `tests/fixtures/paid_contract_cases.json`). An agent branching on `level` treats a warn-level contract as clean.

**Ambiguity 2 — top-level `decision` vs `action_evaluation.decision` (action-aware).**
When a caller asks the action-aware question (`?action=approve&spender=...`), the top-level `decision` stays contract-level while the stricter answer sits nested in `action_evaluation.decision`. The canonical case (locked in `tests/test_pre_a003_coverage.py::test_weth_approve_keeps_contract_allow_but_action_warn`, and observed in the real paid approve smoke of 2026-04-06):

- `level=safe`, top-level `decision=allow`, `action_evaluation.decision=warn`

An agent that pays for the approve-specific evaluation but branches on the top-level field gets the *less strict* answer than the one it paid to compute. Per `docs/PRODUCT_DIRECTION_UPDATE.md` ("sell a gate, not a score"), the gate must be the single unambiguous output. Real paid callers exist (36 paid rows), so response ambiguity is commercial risk, not cosmetic.

## 2. Current Field Semantics (as implemented today)

| Field | Layer | Meaning today | Source |
|---|---|---|---|
| `score` | measurement | 0-100 weighted risk score | `engine.analyze_contract` |
| `level` | measurement | score band: `safe(0-15)/low(16-35)/medium(36-55)/high(56-75)/critical(76-100)` | `scoring.py` |
| `decision` | contract policy | contract-level policy action; always equals `recommended_policy.action` | `AnalysisResult.decision` (`policy.derive_policy`) |
| `recommended_policy` | contract policy | `{action, summary, reason_codes}` — contract-level | `policy.derive_policy` |
| `action_context` | echo | present only when `action` requested: `{action, spender, chain}` | `app.py` route |
| `action_evaluation` | action policy | present only when `action` requested: `{decision, recommended_policy}` — action-aware | `action_policy.derive_action_evaluation` |

**Key structural fact (verified in `src/risk_api/analysis/action_policy.py:81-99`):** `_approve_decision` is monotonic non-decreasing. The action-level decision is always **at least as strict** as the contract-level decision:

- base `manual_review`/`block` → passthrough
- spender allowlisted → base preserved
- spender not allowlisted → `manual_review`
- spender unchecked → `allow`→`warn`, `warn`→`manual_review`

`action_evaluation.recommended_policy.reason_codes` already merges contract-level codes with `action_*` codes (`_merge_reason_codes`), and all action-originated codes carry the `action_` prefix.

Strictness ordering (from `PolicyAction` enum declaration order, `policy.py:12-16`):
`allow (0) < warn (1) < manual_review (2) < block (3)`

## 3. Proposal: `decision` Becomes the Effective Decision

**The primary machine-branching field is the existing top-level `decision`.** No new "primary" field is introduced; instead `decision` is made trustworthy for all request shapes:

1. **No `action` requested** (100% of organic traffic to date): `decision` unchanged — contract-level policy action, exactly as today.
2. **`action` requested:** top-level `decision` becomes the **effective decision** = the stricter of the contract-level policy action and `action_evaluation.decision`. Given monotonicity this is today equal to `action_evaluation.decision`, but the implementation MUST compute `max()` by strictness ordering so a future action type that could downgrade can never silently weaken the top-level answer.
3. **Top-level `recommended_policy` follows `decision`.** When an action is requested, top-level `recommended_policy` becomes the action-aware policy object (`action_evaluation.recommended_policy`: action-aware summary + merged reason codes). Never allow `decision` and `recommended_policy.action` to disagree — that would recreate the ambiguity one level down.
4. **New top-level field `contract_decision` (string, always present):** the contract-only policy action (the value `decision` has today). For no-action requests, `contract_decision == decision`. This preserves the contract-level answer for audit/analytics consumers and makes the escalation visible (`decision != contract_decision` ⇔ the action evaluation raised strictness).
5. **`action_evaluation` and `action_context` unchanged** — kept verbatim for detail and backward compatibility.
6. **`level` and `score` unchanged in value; re-documented** in OpenAPI + machine docs as measurement fields with explicit "do not branch on `level`; branch on `decision`" language. This resolves Ambiguity 1 by documentation and example, not by changing values (changing `level` semantics would break the score-band contract that fixtures and reports depend on).

### Where the change lives

`src/risk_api/api_contract.py::serialize_analysis_result` **only**. The engine (`AnalysisResult`), `derive_policy`, `derive_action_evaluation`, and all detectors are untouched. This is a serialization-layer change, which is what keeps `tests/fixtures/paid_contract_cases.json` valid with **zero fixture edits** (those tests assert engine-level results, pre-serialization).

### Rejected alternatives

- **Add a new `effective_decision` field, keep `decision` as-is:** rejected. It creates a third decision field, leaves every existing example/integration branching on the ambiguous one, and permanently splits "the documented primary field" from "the field everyone actually reads."
- **Mutate `level` to reflect policy:** rejected. `level` is the score band; the score/level contract is load-bearing for fixtures, proof reports, and the dashboard.
- **Add `decision_source` enum:** rejected for narrowness. It is derivable: `decision != contract_decision` ⇔ action-raised. Revisit only if a real caller asks.

## 4. Precedence Rules

```
effective(contract_action, action_eval) =
    contract_action                       if action_eval is None
    max_strictness(contract_action,
                   action_eval.decision)  otherwise

strictness: allow < warn < manual_review < block
```

- Top-level `decision` = `effective(...)`.
- Top-level `recommended_policy` = `action_evaluation.recommended_policy` when an action is requested **and** `action_evaluation.decision >= contract action` (always true today); otherwise (defensive branch, unreachable today) keep the contract-level policy object.
- `contract_decision` = contract-level policy action, always.
- Invariant to enforce in tests: `decision == recommended_policy.action` in **every** response shape.
- Invariant to enforce in tests: `strictness(decision) >= strictness(contract_decision)`.

## 5. Backward Compatibility

| Caller class | Impact |
|---|---|
| No-action callers (all 36 paid rows except our own approve smokes; all organic traffic) | Response byte-identical except one **additive** field `contract_decision`. Zero behavior change. |
| Action-aware callers reading top-level `decision` | `decision` may now be stricter (e.g. WETH approve: `allow` → `warn`). This is the intended fix, and it fails **safe**: no caller is told to proceed on something Augur would gate. Analytics show the only action-aware calls to date are our own smokes. |
| Action-aware callers reading `action_evaluation.decision` | Unchanged — field kept verbatim. |
| Clients with strict/closed response schemas | One new key `contract_decision`. Same additive pattern as `action_context`/`action_evaluation` in March (which broke no one). Note in llms docs changelog section. |

Not changed, verified by scope: `$0.10` price, x402 payment requirements, discovery metadata (`/.well-known/*`, `agent-metadata.json`, ERC-8004/IPFS metadata), detector behavior, scoring, `paid_response_snapshots` envelope (snapshot body is the serialized response and will naturally include the new field; envelope `schema_version` stays `1` — the body is self-describing).

## 6. Exact Response-Shape Proposal

**Case A — no action (WETH plain):** unchanged except additive field.

```json
{
  "address": "0x4200000000000000000000000000000000000006",
  "score": 0,
  "level": "safe",
  "decision": "allow",
  "contract_decision": "allow",
  "recommended_policy": {
    "action": "allow",
    "summary": "Allow by default for first-pass automation. ...",
    "reason_codes": []
  },
  "bytecode_size": 2041,
  "findings": [],
  "category_scores": {}
}
```

**Case B — WETH + `action=approve&spender=0x1111...` (the ambiguity case, AFTER this change):**

```json
{
  "address": "0x4200000000000000000000000000000000000006",
  "score": 0,
  "level": "safe",
  "decision": "warn",
  "contract_decision": "allow",
  "recommended_policy": {
    "action": "warn",
    "summary": "Allow with caution only if this workflow explicitly expects the approval. Keep the spender on an allowlist and the approval scope narrow.",
    "reason_codes": ["action_approve_requested"]
  },
  "bytecode_size": 2041,
  "findings": [],
  "category_scores": {},
  "action_context": {
    "action": "approve",
    "spender": "0x1111111111111111111111111111111111111111",
    "chain": "base"
  },
  "action_evaluation": {
    "decision": "warn",
    "recommended_policy": {
      "action": "warn",
      "summary": "Allow with caution only if this workflow explicitly expects the approval. Keep the spender on an allowlist and the approval scope narrow.",
      "reason_codes": ["action_approve_requested"]
    }
  }
}
```

Note: top-level `recommended_policy` and `action_evaluation.recommended_policy` are intentionally identical in Case B. Contract-level reason codes remain recoverable: they are `reason_codes` minus the `action_`-prefixed codes; `contract_decision` carries the contract-level action.

## 7. OpenAPI, Examples, and Doc-Surface Changes

Per `AGENTS.md`, discovery/response wording is duplicated state. Required updates:

1. **`src/risk_api/app.py` OpenAPI schema (`/analyze` response, ~line 900-930):** add `contract_decision` property; rewrite `decision` description to: primary machine-branching field, effective decision, always equals `recommended_policy.action`, always at least as strict as `contract_decision`; add "measurement, not recommendation — do not branch on this" language to `level`/`score` descriptions.
2. **`APPROVE_ACTION_ANALYSIS_EXAMPLE` (`app.py:198-215`):** currently a hand-built deepcopy showing top-level `decision=allow` + action warn. Must show the new shape (Case B above). Prefer deriving it through `serialize_analysis_result` with a real `ActionEvaluation` instead of hand-editing dicts, per napkin lesson #10 (round-trip through the live serializer).
3. **`SAFE_ANALYSIS_EXAMPLE` / `PROXY_ANALYSIS_EXAMPLE`:** regenerate via `normalize_analysis_snapshot` (they will pick up `contract_decision` automatically once the serializer emits it).
4. **Generated machine docs (`/llms.txt`, `/llms-full.txt`, `/skill.md`, homepage, `/how-payment-works`):** example JSON flows in via the `__*_EXAMPLE_JSON__` replacements automatically, but **prose must be edited** — `app.py` ~line 2508 ("This keeps the top-level contract `decision` intact...") and ~line 2594 become false and must be rewritten to describe effective-decision semantics. Grep `app.py` for `decision` prose near the machine-doc template strings.
5. **`README.md`:** example response (~line 104) gains `contract_decision`; the one-line product description already says "decision" — verify wording.
6. **`examples/javascript/augur-mcp/index.mjs` + its README:** verify the MCP wrapper passes the response through untouched (expected); update its README example JSON if it embeds one.
7. **Proof report pages (`proof_reports.py` / `REPORT_PAGES`):** snapshots round-trip through `normalize_analysis_snapshot`, so serialized output gains `contract_decision` automatically; `auto/loop.py` serializer-drift checks must stay green.
8. **NOT updated:** registration scripts / IPFS metadata / ERC-8004 URI — no discovery metadata text changes in this pass. External registry copy unchanged (positioning did not change).

## 8. Test Matrix

| # | Test | File | Expectation |
|---|---|---|---|
| 1 | Paid-contract corpus (8 real paid contracts) | `test_paid_contract_regressions.py` | **Zero edits, stays green.** Engine-level; serializer change is invisible to it. Any needed edit = design violation. |
| 2 | Synthetic critical `block` policy branch | `test_pre_a003_coverage.py::test_synthetic_critical_block_case...` | **Zero edits, stays green** (policy layer untouched). |
| 3 | WETH approve ambiguity | `test_pre_a003_coverage.py::test_weth_approve_keeps_contract_allow_but_action_warn` | **Intentionally updated** to Case B: top-level `decision=warn`, `contract_decision=allow`, `recommended_policy.action=warn` with `action_approve_requested`, `action_evaluation` unchanged. Rename to reflect new semantics. |
| 4 | **NEW** HTTP-level serialized block response | `test_pre_a003_coverage.py` (or `test_app.py`) | Mock `analyze_contract` → block-decision result; assert JSON `decision="block"`, `contract_decision="block"`, `recommended_policy.action="block"`. Closes the gap found in the pre-A-003 review (only set-membership HTTP assertions existed). |
| 5 | **NEW** serializer precedence unit tests | new/`test_api_contract.py` | (a) no action → `decision == contract_decision`; (b) action raises allow→warn; (c) contract `manual_review` + action passthrough; (d) defensive: artificial `ActionEvaluation` with decision *weaker* than contract → top-level `decision` stays at contract strictness (max rule). |
| 6 | **NEW** invariants across all examples | `test_app.py` | For SAFE, PROXY, APPROVE examples and live-route responses: `decision == recommended_policy.action`; `strictness(decision) >= strictness(contract_decision)`; `contract_decision` present. |
| 7 | OpenAPI examples match mocked route output | existing `test_openapi_*` tests | Updated expectations include `contract_decision`; approve example asserts Case B shape. |
| 8 | Proof-report serializer round-trip | existing `test_app.py` + `auto/loop.py` | Stays green; report snapshots gain `contract_decision` via the shared serializer only. |
| 9 | Analytics observability fields | `test_logging.py` | `action_decision` / `action_spender_trust` request-log extraction (reads `action_evaluation`, `app.py:~3158`) unchanged and green. |
| 10 | Paid snapshot body | `test_logging.py` | Snapshot body for a paid action-aware 200 includes `contract_decision`; privacy marker test stays green. |

Validation gate for the implementation pass: full `pytest` green, `pyright` 0 errors (CI), `auto/loop.py` all checks green, then live smoke (below).

## 9. Migration Risks and Rollout Plan

**Risks**

1. *External action-aware caller breaks on stricter `decision`.* Likelihood ~0 (analytics: action-aware calls to date are our own smokes). Direction of failure is safe (stricter). Mitigation: changelog note in `llms-full.txt`; `action_evaluation` kept verbatim.
2. *Prose drift across duplicated surfaces* (the known Augur failure mode). Mitigation: §7 checklist + napkin lesson #10 round-trip rule + `auto/loop.py` drift checks; implementer greps `decision` across `app.py` templates, `README.md`, `examples/` before closing.
3. *Dashboard/stats regressions.* `/stats` aggregates `request_events` only; no response-shape dependency. Verify `/dashboard` renders post-deploy.
4. *Snapshot-consumer confusion* (old snapshot rows lack `contract_decision`). Acceptable: snapshot bodies are self-describing; consumers must treat the field as optional for rows before the deploy date.

**Rollout**

1. Implement + full local validation (test matrix above).
2. Single deploy via existing CI gate (Typecheck → Fly Deploy).
3. Post-deploy verification, in order: `/health` 200 → unpaid `402` challenge unchanged (payment requirements byte-identical — pricing untouched) → `openapi.json` shows `contract_decision` → `/llms-full.txt` prose updated → one **paid WETH approve smoke** (`scripts/test_x402_payment.py` variant with `action=approve`): assert Case B shape live, then confirm a new `paid_response_snapshots` row contains `contract_decision`.
4. Rollback: single `git revert` + redeploy. No data migration, no schema change, no external metadata to unwind.

**Explicitly out of scope for the implementation pass:** new action types, `decision_source`, batch endpoints, spender-trust response fields beyond what exists (A-003 is not A-003-plus), pricing (P-001 decides separately by 2026-07-20), registry/IPFS metadata updates.

## 10. Implementation Checklist for Codex

Ordered; each step keeps the suite green except step 4's intentional update.

1. `src/risk_api/api_contract.py`: add `_STRICTNESS` ordering + `effective_decision()` helper; emit `contract_decision` always; when `action_evaluation` present, set top-level `decision`/`recommended_policy` per §4 max rule.
2. `tests/`: add matrix items 4-6 (new tests) — write them first against the new serializer behavior.
3. Run matrix items 1-2 untouched — confirm zero edits needed (design invariant).
4. Update matrix item 3 (WETH approve test) to Case B expectations; rename test.
5. `src/risk_api/app.py`: OpenAPI schema properties + descriptions (§7.1); rebuild `APPROVE_ACTION_ANALYSIS_EXAMPLE` through the serializer (§7.2); machine-doc prose (§7.4).
6. `README.md` + `examples/javascript/augur-mcp/` verification (§7.5-7.6).
7. Full validation: `pytest -q`, `auto/loop.py`, `py_compile`; CI typecheck.
8. Deploy; run §9 post-deploy verification including the paid approve smoke; confirm snapshot row.
9. Update `HANDOVER.md`, `.codex/napkin.md`, `docs/GrowthExecutionPlan.md` (A-003 → done with evidence), and this spec's Status line → IMPLEMENTED.

## 11. Evidence Base

- `tests/fixtures/paid_contract_cases.json` — 8 real paid contracts, 35 paid rows at generation; Mintpad + RUG PULL lock Ambiguity 1 (`level=safe`+`decision=warn`).
- `tests/test_pre_a003_coverage.py` — synthetic critical `block` policy case; WETH approve HTTP case locking Ambiguity 2 (`allow` top-level vs `warn` action-level).
- First real `paid_response_snapshots` row (2026-07-07 WETH smoke: 339 bytes, untruncated, `decision=allow`) — proves snapshot capture works and will evidence the new field post-deploy.
- 2026-04-06 production paid approve smoke — the live occurrence of Ambiguity 2.
- `src/risk_api/analysis/action_policy.py:81-99` — monotonicity that makes the §4 precedence rule sound.
