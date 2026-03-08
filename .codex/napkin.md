# Codex Napkin Runbook

## Curation Rules
- Re-prioritize on every read.
- Keep recurring, high-value notes only.
- Max 10 items per category.
- Each item includes date + "Do instead".

## Execution & Validation (Highest Priority)
1. **[2026-03-06] Prefer targeted review over broad local type checks**
   Do instead: inspect the touched modules and lean on the existing pytest suite; avoid local `pyright` runs on Windows because the repo documents import hangs around x402 dependencies.

## Shell & Command Reliability
1. **[2026-03-06] Limit repo-wide recursive scans from `C:\Users\justi`**
   Do instead: locate the actual project root first, then search from that directory to avoid slow timeouts and noisy results.

## Repo-Specific Gotchas
1. **[2026-03-06] Treat `pyproject.toml` as the runtime source of truth**
   Do instead: verify Python and dependency versions in `pyproject.toml` before trusting `README.md` or `CLAUDE.md`, which currently drift on x402 and Python details.
2. **[2026-03-08] Keep trust-language copy explicit about Base and non-guarantees**
   Do instead: whenever editing landing/docs/metadata/registry descriptions, say `Base mainnet`, say the product scores bytecode for agents, and clarify that `safe` is a heuristic bucket rather than an audit or guarantee across `src/risk_api/app.py`, `scripts/pin_metadata_ipfs.py`, and registration scripts together.
3. **[2026-03-07] Reject no-bytecode addresses before the x402 paywall**
   Do instead: run a pre-paywall Base `eth_getCode` check for `GET` and `POST` `/analyze` requests and return `422` for EOAs or undeployed addresses so they are not billed or shown as `safe`.
4. **[2026-03-07] Use `funnel_stage` rather than raw status codes for conversion reads**
   Do instead: read `/stats.funnel` and per-entry `funnel_stage` values from the request log when diagnosing drop-off; `paid` plus `422` or `402` totals alone are too coarse.
5. **[2026-03-06] Discovery metadata is duplicated in multiple places**
   Do instead: when changing agent metadata or discovery behavior, update `src/risk_api/app.py`, `scripts/pin_metadata_ipfs.py`, and registry scripts together to prevent drift.
6. **[2026-03-06] Reuse `compute_score()` for all analysis paths**
   Do instead: route proxy implementation scoring through `src/risk_api/analysis/scoring.py` so heuristic categories like `suspicious_selector` and `tiny_bytecode` stay consistent with top-level analysis.
7. **[2026-03-06] Keep Basescan failure distinct from "not found"**
   Do instead: model creator lookups with explicit success, not-found, and error states so external API failures degrade gracefully and do not add false risk points.
8. **[2026-03-07] Treat `/dashboard` and `/stats` as per-instance logs, not canonical analytics**
   Do instead: use them only to inspect the local `REQUEST_LOG_PATH` stream for that deployment and rely on registry, edge analytics, or durable storage when comparing traffic across domains or hosts.
9. **[2026-03-07] Use Better Stack as the uptime source of truth**
   Do instead: verify service health against Better Stack and the public `/health` probe before inferring availability from the dashboard or request-log volume.
10. **[2026-03-08] Treat x402list.fun stale-host drift as external directory state**
   Do instead: once app config, scripts, and `PUBLIC_URL` all point to `augurrisk.com`, assume the live `risk-api.life.conway.tech` provider page and `augurrisk.com` `404` on x402list.fun need directory-side intervention, not more repo-side edits.

## User Directives
1. **[2026-03-06] Give opinionated codebase recommendations**
   Do instead: review the local repo first, use the GitHub mirror only if needed, and return concrete strengths, risks, and next-step suggestions.

## Repo Workflow
1. **[2026-03-07] Keep `AGENTS.md` stable and use it for startup rules only**
   Do instead: put durable repo-wide agent instructions in `AGENTS.md`, and keep session state in `HANDOVER.md` plus recurring runbook knowledge in `.codex/napkin.md`.
