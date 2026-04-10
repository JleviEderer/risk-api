# Augur Autoresearch Harness

This folder is a bounded local harness for finding detector weaknesses and API-contract drift in Augur.

It is not an autonomous deploy system. It is a repeatable benchmark loop around a labeled corpus plus a few built-in public-surface checks.

## What It Measures

- new reproducible failing cases found
- distinct blind spots found
- disagreement against a labeled holdout corpus
- policy regressions such as dangerous patterns still returning `allow`
- serializer and doc drift against the live route contract

## Files

- `auto/program.md`: prompt/spec for an agent running the loop
- `auto/bench.py`: CLI entrypoint
- `auto/loop.py`: thin runner that writes `auto/runs/latest.json` and prints a compact summary
- `auto/corpus/public_cases.json`: tracked starter corpus
- `auto/corpus/*.local.json`: local holdout corpus, ignored by git
- `auto/candidates/*.local.json`: local discovered cases, ignored by git

## Run It

```bash
python auto/loop.py
python auto/loop.py --allow-failures
python auto/bench.py
python auto/bench.py --json-out auto/runs/latest.json
python auto/bench.py auto/corpus/public_cases.json --skip-app-contract-checks
```

Use `python auto/loop.py` for day-to-day work. It runs the bench, writes the latest
JSON summary to `auto/runs/latest.json`, and prints a compact summary grouped by
blind spot. Use `python auto/bench.py` when you want the raw JSON on stdout.

The command exits non-zero if any check fails, unless you pass `--allow-failures`.

## Case Kinds

### `bytecode`

Runs the local detector, scoring, and policy pipeline on synthetic bytecode.

Use this for:

- false negatives
- false positives
- score bucket mistakes
- policy mistakes on concrete bytecode

### `policy`

Runs policy derivation on structured inputs.

Use this for:

- unresolved proxy behavior
- nested proxy behavior
- reason code regressions
- action-layer regressions that cannot be expressed with a single bytecode blob

### `analysis`

Runs a fully mocked `analyze_contract()` pass, including RPC and explorer calls.

Use this for:

- deployer-reputation behavior that depends on explorer responses
- proxy `resolved` vs `no_code` vs `fetch_failed` runtime behavior
- mixed engine outcomes that need real fetch plus policy integration

### `serialization`

Normalizes a snapshot through the live serializer and checks the wire shape.

Use this for:

- `implementation` omission vs `null`
- nested implementation payload shape
- category score prefixing rules

## Suggested Workflow

1. Add or update local candidate cases under `auto/candidates/*.local.json`.
2. Run `python auto/loop.py`.
3. If a candidate fails reproducibly, decide whether to:
   - fix the engine/policy/serialization
   - promote the case into `auto/corpus/public_cases.json`
   - add a corresponding pytest regression
4. Keep holdout cases local so the harness cannot simply overfit the tracked corpus.

## Local Holdout

Start from `auto/corpus/holdout.local.example.json` and save your private holdout as something like:

```text
auto/corpus/holdout.local.json
```

Those files are ignored by git but loaded automatically by `auto/bench.py`.
