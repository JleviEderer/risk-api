# Augur Autoresearch Program

You are operating a bounded research loop for Augur.

Your job is not to make arbitrary code changes. Your job is to improve Augur against explicit measurable failure modes.

## Objective

Maximize signal on:

- new reproducible failing cases found
- distinct detector blind spots found
- disagreement against holdout cases
- policy regressions where dangerous patterns still return permissive actions
- serializer or doc drift from the live `/analyze` response contract

## Allowed Surfaces

- `auto/corpus/public_cases.json`
- `auto/candidates/*.local.json`
- `tests/`
- `src/risk_api/analysis/`
- `src/risk_api/api_contract.py`
- `src/risk_api/app.py`
- `src/risk_api/proof_reports.py`

## Required Loop

1. Read `auto/README.md`.
2. Run `python auto/loop.py`.
3. Inspect failures.
4. Prefer adding or refining a case before changing implementation.
5. If you change implementation, add or update:
   - an autoresearch case
   - a pytest regression when appropriate
6. Re-run `python auto/loop.py`.
7. Stop when failures are explained or fixed.

## Constraints

- Do not optimize only against visible tracked cases if local holdout files disagree.
- Do not delete difficult cases to improve the score.
- Do not loosen expected outputs without a concrete technical reason.
- Do not deploy or mutate production config from this loop.
- Treat machine-readable response shape as a contract.

## Research Heuristics

- Look for minimal bytecode that triggers a dangerous pattern with an unexpectedly low score.
- Look for combinations of findings that collapse into the wrong action.
- Look for proxy cases where top-level and implementation-level semantics drift.
- Look for examples/docs that no longer match the serializer.

## Success Condition

A good iteration either:

- finds a new failing case and makes it reproducible, or
- fixes a real failing case without introducing drift, or
- proves the current behavior is correct and updates the corpus/tests to lock it in.
