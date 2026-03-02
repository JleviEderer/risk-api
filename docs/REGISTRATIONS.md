# Registrations & Discovery Tracker

Single source of truth for everywhere Augur (risk-api) is registered and discoverable.

## Active Registrations

| Registry | Status | URL / ID | How to Update | Env Vars | Last Verified |
|----------|--------|----------|---------------|----------|---------------|
| ERC-8004 | Live | [Agent #19074](https://8004scan.io/agents/base/19074) | `scripts/register_erc8004.py` | wallet key | 2026-03-01 |
| x402.jobs | Live | [x402.jobs listing](https://x402.jobs/resources/risk-api-life-conway-tech/smart-contract-risk-scorer-base) | `scripts/register_x402jobs.py` | `X402_JOBS_API_KEY` | 2026-02-23 |
| MoltMart | Live | [moltmart.app](https://moltmart.app) | `scripts/register_moltmart.py` | `MOLTMART_API_KEY`, `MOLTMART_SERVICE_ID` | 2026-02-25 |
| Work402 | Live (testnet) | [work402.com](https://work402.com) | `scripts/register_work402.py` | `WORK402_DID` | 2026-02-25 |
| IPFS | Live | `QmNWWhyo7KHnYPTiEeMWdHik9i6yMAM3prDKEVQTSXNEFQ` | `scripts/pin_metadata_ipfs.py` | `PINATA_JWT` | 2026-03-01 |
| 8004scan | Live (unverified wallet) | [8004scan.io/agents/base/19074](https://8004scan.io/agents/base/19074) | Wallet verification via browser | — | 2026-03-01 |
| x402scan | Live | [x402scan.com](https://www.x402scan.com) | Register at x402scan.com/resources/register | — | 2026-03-01 |

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
| [`/`](https://risk-api.life.conway.tech/) | Landing page (Schema.org JSON-LD, Open Graph) |
| [`/health`](https://risk-api.life.conway.tech/health) | Health check |
| [`/dashboard`](https://risk-api.life.conway.tech/dashboard) | Analytics dashboard (Chart.js, auto-refresh 30s) |
| [`/stats`](https://risk-api.life.conway.tech/stats) | Stats JSON |
| [`/avatar.png`](https://risk-api.life.conway.tech/avatar.png) | Agent avatar image |
| [`/robots.txt`](https://risk-api.life.conway.tech/robots.txt) | Crawler directives + sitemap |
| [`/sitemap.xml`](https://risk-api.life.conway.tech/sitemap.xml) | XML sitemap |
| [`/openapi.json`](https://risk-api.life.conway.tech/openapi.json) | OpenAPI 3.0.3 spec |
| [`/agent-metadata.json`](https://risk-api.life.conway.tech/agent-metadata.json) | ERC-8004 agent metadata |
| [`/.well-known/ai-plugin.json`](https://risk-api.life.conway.tech/.well-known/ai-plugin.json) | AI plugin manifest |
| [`/.well-known/agent.json`](https://risk-api.life.conway.tech/.well-known/agent.json) | A2A agent card |
| [`/.well-known/agent-card.json`](https://risk-api.life.conway.tech/.well-known/agent-card.json) | A2A agent card (8004scan expects this path) |
| [`/.well-known/x402`](https://risk-api.life.conway.tech/.well-known/x402) | x402 discovery document |
| [`/.well-known/x402-verification.json`](https://risk-api.life.conway.tech/.well-known/x402-verification.json) | x402 verification |
| [`/.well-known/api-catalog`](https://risk-api.life.conway.tech/.well-known/api-catalog) | RFC 9727 API Catalog (`application/linkset+json`) |

## IPFS Pinning Workflow

When agent metadata changes (new endpoints, updated fields, etc.):

1. Update the metadata in `app.py` (`/agent-metadata.json` route)
2. Deploy to Conway (upload to both source and site-packages)
3. Pin updated metadata to IPFS:
   ```bash
   python scripts/pin_metadata_ipfs.py
   ```
4. Update on-chain `agentURI` with new CID:
   ```bash
   python scripts/register_erc8004.py --update-uri ipfs://<new-CID>
   ```
5. Verify on [8004scan](https://8004scan.io/agents/base/19074) that metadata refreshes

## Domain Strategy

Current domain `risk-api.life.conway.tech` ties branding to Conway. Not urgent to change (zero users care today), but worth planning:

- Agent wallet and private key are self-custodied (not Conway-controlled)
- ERC-8004 registration and IPFS CID are wallet-controlled (on-chain)
- Changing domain later means updating: on-chain URI, all discovery endpoints, all registry listings (x402.jobs, MoltMart, Work402, x402scan, etc.)
- **Recommendation:** Buy a domain (e.g. `augur-api.xyz`) and CNAME to Conway when ready to decouple. Not a blocker today.
