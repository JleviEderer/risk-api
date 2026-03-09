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
1. **[2026-03-08] Keep the GitHub repo homepage aligned with the canonical domain**
   Do instead: when auditing public discovery surfaces, treat the GitHub repository `homepageUrl` as editable metadata and keep it set to `https://augurrisk.com` so public repo cards and profile links do not advertise the retired Conway host.
2. **[2026-03-08] Coinbase Bazaar indexing is separate from the `x402.org` ecosystem PR**
   Do instead: verify CDP discovery through real facilitator-paid calls plus `python scripts/check_cdp_discovery.py`; do not assume a merged `coinbase/x402` PR will make Augur appear in Coinbase's public discovery feed.
3. **[2026-03-08] Anthropic's official directory is not the default discovery path for Augur MCP**
   Do instead: treat the MCP wrapper as a repo-distributed local install example first; Anthropic's current Connectors Directory policy excludes servers that transfer money or execute financial transactions, which likely includes Augur's x402-paying MCP wrapper.
4. **[2026-03-08] Use repo-local git hooks as guardrails, not automation**
   Do instead: enable `.githooks` with `git config core.hooksPath .githooks`; let `pre-push` block when upstream has moved, but do not auto-pull or auto-rebase inside hooks.
5. **[2026-03-08] Prefer a local stdio MCP wrapper over a hosted MCP surface**
   Do instead: keep Augur as the canonical paid HTTP API and expose MCP through a local Node stdio bridge in `examples/javascript/augur-mcp` so wallet signing stays client-side and the wrapper can reuse the existing x402 client path.
6. **[2026-03-08] MCP tool responses should not leak the payer wallet**
   Do instead: keep wallet signing local, but do not include the local wallet address in model-visible tool output; expose only the payment path and whether a wallet is required.
7. **[2026-03-08] Enforce the canonical host from `PUBLIC_URL`**
   Do instead: keep `PUBLIC_URL` set to `https://augurrisk.com` in production and expect non-canonical hosts to `308` redirect there, but exempt `/health` so Fly and external uptime probes do not get trapped by canonical-host enforcement; only bypass all redirects in `TESTING`.
8. **[2026-03-08] The official `x402.org/ecosystem` listing is an upstream PR, not app config**
   Do instead: use `docs/X402_ECOSYSTEM_SUBMISSION.md` and `docs/submissions/x402-ecosystem/metadata.json`, then open a PR against `coinbase/x402` under `typescript/site/app/ecosystem/partners-data/<slug>` with a logo in `typescript/site/public/logos/`.
9. **[2026-03-08] Keep trust-language copy explicit about Base and non-guarantees**
   Do instead: whenever editing landing/docs/metadata/registry descriptions or buyer-intent pages, say `Base mainnet`, say the product scores bytecode for agents, and clarify that `safe` is a heuristic bucket rather than an audit or guarantee across `src/risk_api/app.py`, `scripts/pin_metadata_ipfs.py`, and registration scripts together.
10. **[2026-03-07] Reject no-bytecode addresses before the x402 paywall**
   Do instead: run a pre-paywall Base `eth_getCode` check for `GET` and `POST` `/analyze` requests and return `422` for EOAs or undeployed addresses so they are not billed or shown as `safe`.

## Scoring & Analysis
1. **[2026-03-09] Keep Basescan soft failures distinct from real creator miss cases**
   Do instead: treat `NOTOK`, rate-limit, invalid-key, and similar Basescan creator responses as external errors that contribute no deployer-reputation points; reserve the 3-point "creator not found" finding for true empty-result cases only.
2. **[2026-03-09] Do not let unresolved proxies look like clean low-risk contracts**
   Do instead: when a proxy implementation cannot be resolved, fetched, or bottoms out in another proxy hop, add an explicit proxy-risk finding so the result reflects that the executable logic was not fully analyzed.
3. **[2026-03-09] Honeypot detection should cover blacklist controls and compiled jump shapes**
   Do instead: treat blacklist-style transfer controls as a honeypot signal and allow common compiler scaffolding such as `ISZERO`, `PUSH*`, and `JUMPDEST` around `JUMPI`/`REVERT` so the detector catches real transfer-blocking bytecode instead of only synthetic patterns.
4. **[2026-03-09] Raw engine callers must not treat no-bytecode addresses as safe**
   Do instead: keep the route-level `422` precheck, and also have `analyze_contract()` raise `NoBytecodeError` for EOAs or undeployed addresses so any scripts that bypass Flask cannot publish false-safe results.
5. **[2026-03-09] Do not cache transient Basescan creator errors**
   Do instead: cache only stable creator lookup outcomes; if Basescan returns a soft error like rate-limit or `NOTOK`, let the next call retry rather than suppressing deployer-reputation scoring for the rest of the process.
6. **[2026-03-09] Keep execution-based honeypot work separate from the bytecode API**
   Do instead: treat `docs/HONEYPOT_EXECUTION_PHASE2.md` as the scoped post-`G-014` plan; prefer a separate execution endpoint with one narrow buy/sell simulation path on supported Base routers instead of folding broad swap simulation into `/analyze`.

## User Directives
1. **[2026-03-06] Give opinionated codebase recommendations**
   Do instead: review the local repo first, use the GitHub mirror only if needed, and return concrete strengths, risks, and next-step suggestions.

## Repo Workflow
1. **[2026-03-07] Keep `AGENTS.md` stable and use it for startup rules only**
   Do instead: put durable repo-wide agent instructions in `AGENTS.md`, and keep session state in `HANDOVER.md` plus recurring runbook knowledge in `.codex/napkin.md`.
2. **[2026-03-09] Treat `/stats` and `/dashboard` as app telemetry, not canonical analytics**
   Do instead: use them for request-event summaries over logged public GET routes and `/analyze` including `host`, `referer`, `request_id`, `top_paths`, `top_hosts`, and `top_referers`; if `ANALYTICS_DB_PATH` is unset they still read from local JSONL state and reset across Fly deploys, so enable the SQLite backend on a mounted durable path before treating the dashboard as persistent. This Fly-volume SQLite path assumes a single active app machine; use edge telemetry for old-domain `403` traffic that never reaches Flask and redesign storage before scaling analytics across multiple active machines.
3. **[2026-03-09] Fly config now assumes the analytics volume exists**
   Do instead: production already has Fly volume `augur_analytics` in `iad`; if you recreate production or add another environment, create that volume first because `fly.toml` mounts it at `/data` and points `ANALYTICS_DB_PATH` plus `REQUEST_LOG_PATH` there by default.
4. **[2026-03-09] Production durable analytics is live on a Fly volume**
   Do instead: expect live `/stats` to report `storage_backend=sqlite`, `storage_path=/data/analytics.sqlite3`, and `storage_durable=true`; if those fields regress after future deploys, check Fly volume attachment before debugging app code.
