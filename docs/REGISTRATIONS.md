# Registrations & Discovery Tracker

Single source of truth for everywhere Augur (risk-api) is registered and discoverable.

## Active Registrations

| Registry | Status | URL / ID | How to Update | Env Vars | Last Verified |
|----------|--------|----------|---------------|----------|---------------|
| ERC-8004 | Live | [Agent #19074](https://8004scan.io/agents/base/19074) | `scripts/register_erc8004.py` | wallet key | 2026-03-01 |
| x402.jobs | Live | [x402.jobs listing](https://x402.jobs/resources/risk-api-life-conway-tech/smart-contract-risk-scorer-base) | `scripts/register_x402jobs.py` | `X402_JOBS_API_KEY` | 2026-02-23 |
| MoltMart | Live | [moltmart.app](https://moltmart.app) | `scripts/register_moltmart.py` | `MOLTMART_API_KEY`, `MOLTMART_SERVICE_ID` | 2026-02-25 |
| Work402 | Live (testnet) | [work402.com](https://work402.com) | `scripts/register_work402.py` | `WORK402_DID` | 2026-02-25 |
| IPFS | Live | `QmUUtXC4uSTMfTUBNhnWncGUShJ6qnw8YWdNSU9g49hFfV` | `scripts/pin_metadata_ipfs.py` | `PINATA_JWT` | 2026-03-02 |
| 8004scan | Live (unverified wallet) | [8004scan.io/agents/base/19074](https://8004scan.io/agents/base/19074) | Wallet verification via browser | — | 2026-03-01 |
| x402scan | Live | [x402scan.com](https://www.x402scan.com) | Register at x402scan.com/resources/register | — | 2026-03-01 |
| x402 Bazaar | Live | ID `6352e8b7-9662-4029-bf60-6becc2ec9457` | POST to `x402-discovery-api.onrender.com/register` | — | 2026-03-01 |
| Coinbase Bazaar | Live | [CDP Bazaar](https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources) (`augurrisk.com/analyze`) | Auto-indexed via CDP facilitator settlement | `CDP_API_KEY_ID`, `CDP_API_KEY_SECRET` | 2026-03-02 |

### How to verify wallet on 8004scan

Free points on publisher score. Go to https://8004scan.io, connect agent wallet (`0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891`), sign a message.

## Pending Registrations

| Registry | Status | Notes |
|----------|--------|-------|
| HOL.org | Pending | Sign in at `hol.org/registry/register`. ERC-8004 adapter not indexing agent #19074 — investigate. |
| a2a-directory | PR pending | [GitHub PR #17](https://github.com/nicholascpark/a2a-directory/pull/17) |
| e2b | PR pending | [GitHub PR #327](https://github.com/e2b-dev/awesome-ai-agents/pull/327) |
| kyrolabs | PR pending | [GitHub PR #150](https://github.com/kyrolabs/awesome-ai-agents/pull/150) |
| slavakurilyak PR | Not started | Open manually via compare URL |
| a2aregistry.org | Blocked | Monitoring for SSL fix |
| Swarms | Not started | — |
| AI Agent Store | Not started | — |
| AI Agents Directory | Not started | — |
| Agent.ai | Not started | — |

## Discovery Endpoints

All endpoints are live and free (no x402 payment required):

| Endpoint | Description |
|----------|-------------|
| [`/`](https://augurrisk.com/) | Landing page (Schema.org JSON-LD, Open Graph) |
| [`/health`](https://augurrisk.com/health) | Health check |
| [`/dashboard`](https://augurrisk.com/dashboard) | Analytics dashboard (Chart.js, auto-refresh 30s) |
| [`/stats`](https://augurrisk.com/stats) | Stats JSON |
| [`/avatar.png`](https://augurrisk.com/avatar.png) | Agent avatar image |
| [`/robots.txt`](https://augurrisk.com/robots.txt) | Crawler directives + sitemap |
| [`/sitemap.xml`](https://augurrisk.com/sitemap.xml) | XML sitemap |
| [`/openapi.json`](https://augurrisk.com/openapi.json) | OpenAPI 3.0.3 spec |
| [`/agent-metadata.json`](https://augurrisk.com/agent-metadata.json) | ERC-8004 agent metadata |
| [`/.well-known/ai-plugin.json`](https://augurrisk.com/.well-known/ai-plugin.json) | AI plugin manifest |
| [`/.well-known/agent.json`](https://augurrisk.com/.well-known/agent.json) | A2A agent card |
| [`/.well-known/agent-card.json`](https://augurrisk.com/.well-known/agent-card.json) | A2A agent card (8004scan expects this path) |
| [`/.well-known/x402`](https://augurrisk.com/.well-known/x402) | x402 discovery document |
| [`/.well-known/x402-verification.json`](https://augurrisk.com/.well-known/x402-verification.json) | x402 verification |
| [`/.well-known/api-catalog`](https://augurrisk.com/.well-known/api-catalog) | RFC 9727 API Catalog (`application/linkset+json`) |
| [`/llms.txt`](https://augurrisk.com/llms.txt) | LLM-optimized service documentation |
| [`/llms-full.txt`](https://augurrisk.com/llms-full.txt) | Full LLM documentation (schema, detectors, examples) |

## IPFS Pinning Workflow

When agent metadata changes (new endpoints, updated fields, etc.):

1. Update the metadata in `app.py` (`/agent-metadata.json` route)
2. Deploy to Fly.io (`fly deploy`)
3. Pin updated metadata to IPFS:
   ```bash
   python scripts/pin_metadata_ipfs.py
   ```
4. Update on-chain `agentURI` with new CID:
   ```bash
   python scripts/register_erc8004.py --update-uri ipfs://<new-CID>
   ```
5. Verify on [8004scan](https://8004scan.io/agents/base/19074) that metadata refreshes

## Domain & Hosting

Domain `augurrisk.com` is hosted on Fly.io with Cloudflare DNS. Conway (`risk-api.life.conway.tech`) kept as historical fallback during transition.

## Monitoring & Health

- Better Stack is the external uptime monitor for `https://augurrisk.com/health`.
- `scripts/health_check.py` is the matching manual probe for that public health check.
- Treat `/dashboard` and `/stats` as per-instance request-log views, not the authoritative monitoring surface.

## x402list.fun Note

- As of 2026-03-07, x402list.fun is still showing the legacy Conway hostname (`risk-api.life.conway.tech`) rather than `augurrisk.com`.
- This appears to be an external directory/indexing state issue, not an app-route or `PUBLIC_URL` issue in this repo.
- Do not assume code changes alone will update the x402list.fun provider page; verify directory state separately after any settlement or registration changes.
