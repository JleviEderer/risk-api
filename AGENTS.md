# AGENTS.md

Repo-level operating instructions for any agent working in `risk-api`.

## Startup

Before making decisions, read:

1. `HANDOVER.md`
2. `.codex/napkin.md`

These are the current operator notes for the repo.

## Source Of Truth

If docs and implementation disagree, treat live code and runtime config as source of truth.

Primary sources:
- `src/`
- `pyproject.toml`
- `Dockerfile`
- `fly.toml`
- production env and secrets such as `PUBLIC_URL`

Secondary sources:
- `HANDOVER.md`
- `.codex/napkin.md`
- `README.md`
- `CLAUDE.md`
- `docs/`

## Operational Rules

- Prefer small correctness and operational fixes before structural refactors.
- Keep `PUBLIC_URL` aligned with the canonical production domain: `https://augurrisk.com`.
- Treat discovery metadata as duplicated state. When changing public agent/discovery behavior, update:
  - `src/risk_api/app.py`
  - `scripts/pin_metadata_ipfs.py`
  - registration scripts such as `scripts/register_erc8004.py` and `scripts/register_x402jobs.py`
- Reuse `compute_score()` for all analysis paths so top-level and proxy implementation scoring stay consistent.
- Keep Basescan/API failure distinct from true "not found" behavior in reputation logic.

## Monitoring And Traffic

- Better Stack plus the public `/health` endpoint are the uptime source of truth.
- `/dashboard` and `/stats` are per-instance views over the local `REQUEST_LOG_PATH` log stream, not canonical analytics.
- Do not infer total traffic or migration success from `/dashboard` alone.
- If `x402list.fun` still shows `risk-api.life.conway.tech` after app config, scripts, and `PUBLIC_URL` all point at `augurrisk.com`, treat it as an external directory/indexing issue rather than a repo-side bug.

## Verification Priorities

For production or discovery issues, check in this order:

1. live app/runtime config (`PUBLIC_URL`, Fly deployment state, env/secrets)
2. route behavior in `src/risk_api/app.py`
3. external health via Better Stack and `/health`
4. registration/discovery state in `docs/REGISTRATIONS.md` and the registration scripts
5. external directories such as x402.jobs, x402list.fun, Bazaar, and 8004scan

## Documentation Hygiene

When the current session changes operational behavior, update:

- `HANDOVER.md`
- `.codex/napkin.md`

Keep both short, current, and execution-focused. Keep `AGENTS.md` stable; do not use it as a session log.
