# Competitive Landscape: x402 Risk & Security Services

> Last updated: 2026-03-02

---

## Direct Competitors

### 1. GoPlus x402 — Two Deployments

**The incumbent with a prototype AND a production domain.**

GoPlus runs two x402 domains sharing the same wallet (`0xf823...4b2`) and 2,600 tx count — confirming migration from prototype to production while keeping both live for double discovery surface.

| | **Vercel prototype** | **Production domain** |
|---|---|---|
| **Domain** | `goplus-x402-site-3.vercel.app` | `x402.gopluslabs.io` |
| **Endpoints** | 1 (`/api/detect-token`) | 2 (`/api/detect-token`, `/api/detect-address`) |
| **Method** | GET | POST (JSON body: `contractAddress`/`address`, `chainId`) |
| **Token Detection price** | $0.20 | $0.20 |
| **Address Detection price** | — | **$0.10** |
| **Categories** | Data & Analytics | Identity & Authentication, Developer Tools |
| **Transactions** | 2,600 | 2,600 (same wallet, shared count) |
| **Payment address** | `0xf823a3ed999132b27a5c95305e0559cdf208f4b2` | same |
| **Last updated** | October 2025 (stale) | Unknown |
| **Discovery endpoints** | None (no `/.well-known/agent.json` — 404) | None (404) |

**What they detect:**
- **Token Detection** ($0.20) — Scams, honeypots, rug pulls, suspicious token behaviors. Binary flags.
- **Address Detection** ($0.10) — Malicious address identification: phishing, scams, address threats. Accepts optional `chainId` suggesting multi-chain readiness.

Six advertised capabilities: honeypot ID, token risk assessment, address threat analysis, phishing/scam recognition, real-time verification, multi-chain blockchain support.

**Context:** GoPlus does 717M calls/month on their free API with 30+ chain coverage. Their x402 offering is barely adopted — 2,600 tx total across both domains proves the thesis that their free model makes paid x402 contradictory. The Vercel subdomain (`-site-3` = iteration) was the prototype; `x402.gopluslabs.io` is the production graduation with a second endpoint added.

**`detect-address` is our most direct competitor.** Same price ($0.10), same network (Base), same input (0x address). Key difference: they check if an **address** is known-bad (reputation/blacklist lookup), we check if a **contract's code** is dangerous (bytecode analysis). Complementary but will compete for the same "is this address safe?" agent query.

**Our advantages over GoPlus x402:**
- **Richer output** (8 detectors, 0-100 scored, proxy resolution vs their binary flags)
- **Active development** (deployed March 2026 vs their Oct 2025 Vercel update)
- **Full discovery stack** (ERC-8004, A2A agent card, llms.txt, OpenAPI, Bazaar, x402.jobs) vs no discovery endpoints on either GoPlus domain
- **Price parity** on address detection ($0.10 = $0.10), **half price** on token-level analysis ($0.10 vs $0.20)

**Their advantages:**
- Brand recognition, 30+ chain coverage on their free API
- Two domains = double listing surface on x402list.fun (a tactic we noted)
- `chainId` param suggests multi-chain readiness on the x402 side too

---

### 2. x402-secure — `x402-secure-api.t54.ai`

**Different angle: scores x402 servers, not smart contracts.**

| Field | Detail |
|-------|--------|
| **Endpoints** | 8 separate tools |
| **Price** | $0.01–$0.10 USDC per call |
| **Transactions** | 1.48M (likely inflated — every endpoint shows identical count) |
| **Network** | Base + Solana |
| **Landing** | Redirect to `x402secure.com` (SDK/proxy product) |

**Their 8 endpoints:**

| Endpoint | Price | Description |
|----------|-------|-------------|
| `get_overall_score` | $0.01 | Overall x402 server security score (0-100) |
| `get_social_trust` | $0.01 | Twitter/X reputation analysis |
| `get_webpage_trust` | $0.01 | AI-powered webpage quality analysis |
| `get_api_health` | $0.01 | Response latency, availability, protocol compliance |
| `get_available_resources` | $0.01 | Searchable directory of x402 servers |
| `evaluate_agent_payment` (Base) | $0.10 | Pre-transaction risk assessment |
| `get_onchain_trust` | $0.01 | Payment address evaluation, suspicious pattern detection |
| `evaluate_agent_payment` (Solana) | $0.001 | Same as Base version, Solana (0 tx) |

**Positioning:** "The missing piece of x402" — an SDK + proxy that adds risk signals before transactions execute. Analyzes 6 failure modes: prompt injection, counterfeit sourcing, hidden auto-renewal, tool-chain tampering, specification substitution, opinion poisoning.

**What we can learn from them:**
- **Endpoint splitting** — 8 endpoints at $0.01 each = 8x discovery surface on x402list.fun. Each appears as a separate listing.
- **Cheap entry point** — $0.01 gets agents in the door. Upsell on `evaluate_agent_payment` at $0.10.
- **Category diversity** — They spread across "Storage & Infrastructure", "Data & Analytics", "AI & Machine Learning", "Developer Tools" — appearing in more search filters.
- **The 1.48M number** — Shared across all endpoints, likely synthetic/inflated. But it dominates sort-by-transactions rankings.

**Key difference:** They score *servers* (is this x402 provider trustworthy?). We score *contracts* (is this smart contract safe?). Complementary, not directly competing — except the `get_onchain_trust` endpoint which evaluates payment addresses for suspicious patterns.

---

## Our Listing on x402list.fun

Source: `x402list.fun/provider/risk-api.life.conway.tech`

| Field | Current |
|-------|---------|
| **Services** | 1 |
| **Transactions** | 0 |
| **Price** | $0.10 |
| **Description** | "Smart contract risk scoring" |
| **Category** | Other |
| **Method** | GET |
| **Latency** | Unavailable |

**Problems:**
- "Other" category = invisible in filtered searches
- Bare-minimum description — no mention of detectors, scoring range, proxy resolution
- Single endpoint vs x402-secure's 8 = less discovery surface
- Zero transactions = bottom of any sort

**Similar providers shown alongside us:**
- `ainalyst-api.xyz` — 2 services, 4.2M tx
- `pay.lnpay.ai` — 3 services, 3.4M tx
- `api.barvis.io` — 5 services, 2.7M tx
- `x402.aiape.tech` — 1 service, 2.5M tx

---

## Competitive Matrix

| | **Augur (us)** | **GoPlus x402** | **x402-secure** |
|---|---|---|---|
| **What's scored** | Smart contract bytecode | Token security + address reputation | x402 server trust |
| **Input** | Contract address | Token address OR wallet address | Server URL |
| **Price** | $0.10 | $0.10–$0.20 | $0.01–$0.10 |
| **Endpoints** | 1 | 2 (token + address) × 2 domains | 8 |
| **Transactions** | 0 | 2,600 (shared across both domains) | 1.48M (suspect) |
| **Output** | 0-100 score, 8 detectors, proxy resolution | Binary flags (scam/honeypot/rug) | 0-100 score, 4 sub-scores |
| **Network** | Base | Base (chainId param = multi-chain ready) | Base + Solana |
| **Domains** | Custom (conway.tech) | 2: Vercel prototype + gopluslabs.io | Custom (t54.ai) |
| **Discovery** | ERC-8004, x402.jobs, Bazaar, llms.txt, A2A, OpenAPI | x402list.fun only (no agent cards) | x402list.fun, SDK |
| **Status** | Active dev (March 2026) | Graduated to production domain | Active |

---

## Strategic Takeaways

1. **Price is competitive but not a differentiator.** GoPlus's `detect-address` matches us at $0.10. Their `detect-token` at $0.20 is more expensive, but the address endpoint is the closer comp. x402-secure is cheaper ($0.01) but scores different things.

2. **Discovery surface is our problem.** x402-secure has 8 listings per directory, GoPlus has 2 domains × 2 endpoints = 4 listing surfaces, we have 1. GoPlus has brand gravity on top of that. We have zero transactions and a bare description.

3. **GoPlus x402 adoption validates our moat thesis.** 717M free calls/month → 2,600 paid x402 calls across both domains. Their free users won't switch to paying. The x402 market is agents-only, and we're built for that.

4. **GoPlus's dual-domain tactic is worth noting.** Running `goplus-x402-site-3.vercel.app` and `x402.gopluslabs.io` with the same wallet gives them double the discovery surface on x402list.fun for free. Same wallet, same tx count, zero extra cost. We could do similar with a second domain if needed.

5. **Endpoint splitting is worth considering.** Breaking analysis into sub-endpoints (bytecode score, deployer score, proxy resolution, individual detectors) would multiply our x402list.fun presence and lower the entry price.

6. **Listing metadata matters.** Rich descriptions, correct categories, and response schema details drive discoverability. Our "Smart contract risk scoring" in "Other" is losing to x402-secure's spread across 4 categories. GoPlus has no discovery endpoints (no agent cards, no OpenAPI) on either domain — our discovery stack is a genuine advantage.

7. **Transaction count is a vanity metric.** x402-secure's 1.48M is almost certainly inflated (identical across all 8 endpoints). GoPlus's 2,600 is shared/identical across both domains. Don't chase it — focus on real usage and revenue.

8. **Our analysis is deeper, not broader.** GoPlus `detect-address` is blacklist/reputation lookup — "is this address known-bad?" We do bytecode analysis — "is this contract's code dangerous?" Both answer "is this safe?" but from different angles. An agent could use both.

---

## x402 Ecosystem Context

- 14+ facilitators (commoditized layer)
- Coinbase ~70% share, Dexter competitive on tx count
- $600M+ total volume, 94K payments in last 30 days
- Protocol: HTTP 402 → client pays → resends with proof → server verifies via facilitator
- ERC-8004: Permissionless agent registry on Base (`0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`)
- Key directories: x402list.fun, x402.jobs, Coinbase Bazaar, 8004scan.io

---

## Sources

- [x402list.fun — x402-secure provider page](https://x402list.fun/provider/x402-secure-api.t54.ai)
- [x402list.fun — GoPlus Vercel prototype](https://x402list.fun/provider/goplus-x402-site-3.vercel.app)
- [x402list.fun — GoPlus production domain](https://x402list.fun/provider/x402.gopluslabs.io)
- [x402.gopluslabs.io — GoPlus production landing page](https://x402.gopluslabs.io)
- [x402list.fun — Our provider page](https://x402list.fun/provider/risk-api.life.conway.tech)
- [x402secure.com — Product page](https://x402secure.com)
- [x402 ecosystem directory](https://www.x402.org/ecosystem)
