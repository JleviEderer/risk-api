# Local Candidate Cases

Drop newly discovered local cases here as `*.local.json`.

Example filename:

```text
auto/candidates/discovered-2026-03-16.local.json
```

The benchmark runner loads these files automatically and reports:

- `new_reproducible_failures_found`
- `distinct_blind_spots_found`

Keep tracked/public cases in `auto/corpus/public_cases.json`. Use this folder for local discovery and triage before promoting cases into the tracked corpus.
