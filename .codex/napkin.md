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
4. **[2026-03-08] Prefer a local stdio MCP wrapper over a hosted MCP surface**
   Do instead: keep Augur as the canonical paid HTTP API and expose MCP through a local Node stdio bridge in `examples/javascript/augur-mcp` so wallet signing stays client-side and the wrapper can reuse the existing x402 client path.
5. **[2026-03-08] MCP tool responses should not leak the payer wallet**
   Do instead: keep wallet signing local, but do not include the local wallet address in model-visible tool output; expose only the payment path and whether a wallet is required.
6. **[2026-03-08] Enforce the canonical host from `PUBLIC_URL`**
   Do instead: keep `PUBLIC_URL` set to `https://augurrisk.com` in production and expect non-canonical hosts to `308` redirect there, but exempt `/health` so Fly and external uptime probes do not get trapped by canonical-host enforcement; only bypass all redirects in `TESTING`.
7. **[2026-03-08] The official `x402.org/ecosystem` listing is an upstream PR, not app config**
   Do instead: use `docs/X402_ECOSYSTEM_SUBMISSION.md` and `docs/submissions/x402-ecosystem/metadata.json`, then open a PR against `coinbase/x402` under `typescript/site/app/ecosystem/partners-data/<slug>` with a logo in `typescript/site/public/logos/`.
8. **[2026-03-08] Keep trust-language copy explicit about Base and non-guarantees**
   Do instead: whenever editing landing/docs/metadata/registry descriptions, say `Base mainnet`, say the product scores bytecode for agents, and clarify that `safe` is a heuristic bucket rather than an audit or guarantee across `src/risk_api/app.py`, `scripts/pin_metadata_ipfs.py`, and registration scripts together.
9. **[2026-03-07] Reject no-bytecode addresses before the x402 paywall**
   Do instead: run a pre-paywall Base `eth_getCode` check for `GET` and `POST` `/analyze` requests and return `422` for EOAs or undeployed addresses so they are not billed or shown as `safe`.
10. **[2026-03-07] Use `funnel_stage` rather than raw status codes for conversion reads**
   Do instead: read `/stats.funnel` and per-entry `funnel_stage` values from the request log when diagnosing drop-off; `paid` plus `422` or `402` totals alone are too coarse.

## User Directives
1. **[2026-03-06] Give opinionated codebase recommendations**
   Do instead: review the local repo first, use the GitHub mirror only if needed, and return concrete strengths, risks, and next-step suggestions.

## Repo Workflow
1. **[2026-03-07] Keep `AGENTS.md` stable and use it for startup rules only**
   Do instead: put durable repo-wide agent instructions in `AGENTS.md`, and keep session state in `HANDOVER.md` plus recurring runbook knowledge in `.codex/napkin.md`.
