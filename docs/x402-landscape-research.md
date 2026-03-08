# Competitive Landscape: x402 Risk & Security Services

> Last updated: 2026-03-08 (Stripe annual letter source refreshed; Conway wallet paid call reconfirmed)

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

### 3. Emerging Competitors (risk search, March 2026)

Discovered via `x402list.fun/?q=risk&network=base` on 2026-03-02. Several new entrants targeting the risk/security vertical:

| Provider | Domain | Endpoints | Tx | Price | Notes |
|----------|--------|-----------|-----|-------|-------|
| **CyberCentry** | 5 Railway apps (`*.up.railway.app`) | 5 | 63 each | $0.02–$0.10 | Split-domain strategy: separate app per verification type (web, solidity, wallet, solana token, ERC-8004 agent). Each domain has identical 63 tx — likely self-generated. |
| **cryptorugmunch** | `cryptorugmunch.app` | 4 | 35 | $0.04–$0.30 | Rug detection — closest to our use case. Multiple price tiers suggest depth levels. |
| **BlockSec** | `x402.blocksec.ai` | 7 | 7 | $0.10–$1.00 | Legit security firm with real audit business. Premium pricing ($1.00 top tier). Low tx count suggests new listing. |
| **Hexens** | `data-x402.hexens.io` | 1 | 9 | $0.90 | Real security auditor. Single premium endpoint. |
| **smartanalyst / agentanalyst** | Railway apps | 1 each | 44 | $0.05 | Generic names, Railway-hosted. Low-effort entries. |

**Takeaways:**
- **CyberCentry's split-domain strategy is aggressive.** 5 separate Railway apps means 5 separate provider listings on x402list.fun, each appearing in different search results. The identical 63 tx across all endpoints confirms self-dealing, but the discovery surface multiplication is real.
- **BlockSec and Hexens are legit threats.** Both are established security firms with real audit businesses. If they invest in their x402 listings, they bring brand credibility we can't match.
- **cryptorugmunch is the closest direct competitor.** "Rug detection" overlaps heavily with our honeypot/hidden mint/fee-on-transfer detectors. Their lower price floor ($0.04) could attract price-sensitive agents.
- **Railway hosting is the new default.** CyberCentry, smartanalyst, and agentanalyst all use Railway. Low barrier to entry = expect more entrants.

---

## Our Listing on x402list.fun

> Updated 2026-03-02

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

| | **Augur (us)** | **GoPlus x402** | **x402-secure** | **BlockSec** | **CyberCentry** | **cryptorugmunch** |
|---|---|---|---|---|---|---|
| **What's scored** | Smart contract bytecode | Token security + address reputation | x402 server trust | Smart contract security | Multi-type verification | Rug detection |
| **Input** | Contract address | Token address OR wallet address | Server URL | Contract address | Varies by type | Token/contract |
| **Price** | $0.10 | $0.10–$0.20 | $0.01–$0.10 | $0.10–$1.00 | $0.02–$0.10 | $0.04–$0.30 |
| **Endpoints** | 1 | 2 × 2 domains | 8 | 7 | 5 (separate domains) | 4 |
| **Transactions** | 6 | 2,600 (shared) | 1.48M (suspect) | 7 | 63 (identical, suspect) | 35 |
| **Output** | 0-100 score, 8 detectors, proxy resolution | Binary flags | 0-100 score, 4 sub-scores | Unknown | Unknown | Unknown |
| **Network** | Base | Base | Base + Solana | Base | Base | Base |
| **Discovery** | ERC-8004, x402.jobs, Bazaar, llms.txt, A2A, OpenAPI | x402list.fun only | x402list.fun, SDK | x402list.fun | x402list.fun (5 listings) | x402list.fun |
| **Status** | Active dev (March 2026) | Graduated to production | Active | New (7 tx) | Active | Active |

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

9. **The scoring engine is the asset, not the payment rail.** Stripe, Google, and OpenAI are building competing agent payment protocols (see Platform-Level Threats below). If ACP or UCP wins over x402, Augur's bytecode analysis pipeline still works — swap the middleware layer. Build the scoring engine as protocol-portable; don't couple business logic to x402 primitives.

---

## Platform-Level Threats

The direct competitors above are x402-native services competing for the same agent queries. The threats below are **protocol-level** — platforms building alternative agent payment rails that could make x402 itself irrelevant.

### Stripe Agentic Commerce (Feb 2026)

Stripe's 2025 annual letter (published Feb 24, 2026) reveals a comprehensive push into machine-to-machine payments that directly overlaps with x402's value proposition.

**Scale context:** $1.9T payment volume in 2025, 5M+ businesses, 350+ product updates shipped in 2025. This is the largest payment processor in tech making agent commerce a strategic priority.

**Key announcements:**

| Initiative | What it does | x402 overlap |
|---|---|---|
| **Machine payments** | Stablecoin micropayments for API calls, MCP tool usage, and HTTP requests | This is literally x402's model — pay-per-request for machine services — but on Stripe rails instead of on-chain |
| **ACP (Agentic Commerce Protocol)** | Open protocol co-developed with OpenAI for AI platforms to transact with businesses | Competing open standard to x402 for agent→service payments |
| **Shared Payment Tokens** | Agents initiate payments without exposing user credentials | Solves the same trust problem as x402's facilitator-verified payment proofs |
| **Google UCP support** | Stripe's Agentic Commerce Suite integrates Google's Universal Commerce Protocol | Another competing agent payment standard with Stripe distribution |
| **Tempo blockchain** | Payments-optimized L1: sub-second finality, 1M+ TPS target. Visa, Nubank, Shopify testing. Mainnet "soon" | If Stripe moves stablecoin payments to Tempo, they own the full stack — rails + settlement |
| **Privy acquisition** | 110M programmable wallets acquired | Instant wallet infrastructure for agent identity and payment, no web3 onboarding friction |

**Why this matters for x402:**

- **Distribution asymmetry.** x402 has ~94K payments/month across the entire ecosystem. Stripe processes $1.9T/year across 5M businesses. If Stripe offers "add one line to accept agent payments," most API providers will choose Stripe over x402 middleware.
- **OpenAI alignment.** ACP is co-developed with OpenAI. If ChatGPT/GPT agents default to ACP for payments, that's the largest agent platform routing around x402.
- **Stablecoin + Tempo.** Stripe already supports USDC. If Tempo launches with native stablecoin micropayments at sub-second finality, it undercuts x402's on-chain settlement advantage while adding Stripe's compliance and dispute resolution.
- **"Mid-90s protocol wars."** Stripe's own framing — they see agent commerce protocols as unsettled. x402, ACP, UCP, and others are competing for the standard. Stripe is betting they can win by embedding payments into the platforms agents already use.

**What this does NOT change:**

- x402 is live today with real settlements. ACP, Tempo, and machine payments are announced but not yet generally available.
- x402 is permissionless — no Stripe account, no KYC, no approval. That matters for autonomous agents.
- Our scoring engine is independent of the payment rail. Bytecode analysis works regardless of whether the caller pays via x402, ACP, or Stripe checkout.

**Augur-specific interpretation:**

- Stripe should be treated as an active agent-commerce platform contender, not just a generic enterprise billing provider.
- But the current Augur distribution model still aligns better with x402 because Augur already sells open, accountless HTTP access without merchant onboarding.
- If Stripe's ACP, Shared Payment Tokens, machine payments, and ChatGPT or Copilot integrations gain real buyer distribution, that strengthens the case for keeping Augur's scoring engine portable behind multiple payment surfaces.

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
- [Stripe 2025 Annual Letter — Agentic Commerce, Machine Payments, Tempo](https://x.com/stripe/status/2026294241450979364)
- [x402list.fun — risk search on Base](https://x402list.fun/?q=risk&network=base) (March 2026 competitor audit)
- [x402list.fun — BlockSec provider page](https://x402list.fun/provider/x402.blocksec.ai)
- [x402list.fun — Hexens provider page](https://x402list.fun/provider/data-x402.hexens.io)
- [x402list.fun — cryptorugmunch provider page](https://x402list.fun/provider/cryptorugmunch.app)
- [x402list.fun — CyberCentry (multiple Railway domains)](https://x402list.fun/?q=cybercentry)
