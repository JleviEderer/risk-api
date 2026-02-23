# Competitive Research: x402 Agentic Payments Landscape

> Research date: 2026-02-18

---

## The Artemis Landscape Map

Source: @OnchainLu on X (30K views, 222 likes, reposted by Dexter Agent)
URL: agenticpayments.artemisanalytics.com

The map categorizes the x402 ecosystem into 15 verticals. Our automaton (built on Conway Research) sits in "Agent Frameworks & Tooling."

---

## Facilitators Deep Dive (14 players)

The Facilitator layer is the **revenue engine** of x402 — they verify payments, settle on-chain, and take a cut. Think of them as "Stripe for agents."

### Tier 1: Dominant

| Company | Focus | Notes |
|---------|-------|-------|
| **Coinbase** | ~70% market share, multi-chain | The OG. Created x402. Their CDP facilitator is the default. |
| **Dexter** | Flipped Coinbase on transaction count | Payment infra + SDK. LLM-integrated trading. Voice control. SNS integration. Run by "Dexter Intelligence DAO LLC." Positioned as the developer-friendly alternative. |

### Tier 2: Significant

| Company | Focus | Notes |
|---------|-------|-------|
| **PayAI** | Solana-first, multi-network (Base, Avalanche, Polygon, Sei, IoTeX) | ~10% market share. Gasless payments. Has $PAYAI token. Free merchant simulator for testing. Three pricing tiers. |
| **Daydreams** | Agent commerce SDK ("Lucid Agents") | Pivoted from pure agent framework to commerce. TypeScript-first. Supports x402 + A2A + ERC-8004. Has OpenAI-compatible inference router with x402 billing. $DREAMS token. Solana Foundation backed. |
| **Stripe** | Traditional payments entering x402 | Appears in both Facilitators and Payments. Massive distribution advantage. |
| **Corbits** | "Faremeter" framework — open-source, modular, plugin-based | Building on Polygon + Solana. Launched "Nexus" for no-account API access. Partnered with Nansen for on-chain analytics. "Mallory" mobile agent toolkit. Active builder. |
| **thirdweb** | Web3 dev tools with x402 facilitator | Uses your own server wallet. EIP-7702 gasless transactions. Drop-in middleware. |

### Tier 3: Niche / Emerging

| Company | Focus | Notes |
|---------|-------|-------|
| **x402-rs** | Rust x402 facilitator | Open-source, self-hostable, ~10% market share. For teams that want full control. |
| **OpenFacilitator** | White-label facilitator-as-a-service | Deploy branded facilitator at `pay.yourdomain.com` for $5/month. Partners with x402.jobs for discovery. Open source. |
| **Openx402** | First permissionless facilitator | No login required. Supports Base, Solana, Monad. Aimed at smallest possible friction. |
| **Heurist** | Decentralized AI compute + facilitator | Also in Agent Networks and Hosting/Compute categories. Dual role. |
| **x402jobs** | Job marketplace + facilitator | Agents post/discover/execute structured jobs. Pay-per-use. $JOBS token. Originated from Memeputer ecosystem. |
| **AurraCloud** | Decentralized cloud + **0% fee facilitator** | Hold 1,000 $AURA to get API key. Privacy-focused via Virtuals Protocol shielded payments. Compute marketplace where both supply (nodes) and demand (agents) are AI-controlled. ~$7.8M market cap. |
| **CodeNut** | Full-stack agent infra + multi-chain facilitator | Supports Base, X Layer, Solana. "CodeNut AI" (agent building) + "CodeNut Pay" (facilitator). Partnered with **Nubila** (decentralized weather oracle) — agents pay per weather query via x402. |

---

## Key Verticals & What They Mean for Our Automaton

### 1. Agent-to-Agent Commerce (Dexter's thesis)
- Agents paying other agents for risk data, reputation checks, deployer scores
- Settled via x402 in milliseconds
- **Opportunity for our agent:** Sell intelligence (on-chain analytics, risk scoring) or buy it (security checks before transactions)

### 2. Discovery Layer
- x402scan, x402jobs, ClawIndex, Coinbase, UCP, Questflow
- How agents FIND services to pay for
- **Opportunity:** Register our agent's capabilities as discoverable x402 endpoints so other agents can hire it

### 3. Anti-Scam / Security Stack
- Dexter highlights: scam detection, contract audits, identity verification — all micropaid per-request
- **Opportunity:** Our agent could consume these services before making transactions, or PROVIDE them as a revenue stream

### 4. Inference-as-a-Service via x402
- Daydreams runs an OpenAI-compatible router with x402 billing
- **Direct relevance:** Our agent's inference is broken because Conway's OpenAI key is out of quota. We could route inference through Daydreams' x402 router instead — pay per call from the agent's own wallet.

### 5. Job Marketplaces
- x402jobs: structured, repeatable automation jobs — discoverable, composable, payable
- Work402: agents hiring agents
- AgentWork.wtf: agents posting/bidding on tasks
- **Opportunity:** Our agent could list itself as a worker on these platforms

---

## Competitive Positioning: Where Conway/Our Automaton Fits

Conway Research appears in "Agent Frameworks & Tooling" alongside MCP, Daydreams, Dexter, Corbits, Phantom, etc.

**Conway's differentiator:** Self-modifying autonomous agent with its own wallet, heartbeat, and survival instincts. Most other frameworks are SDKs/toolkits — Conway is an actual running agent.

**Our edge:** We have a LIVE agent with a funded wallet. Most projects are frameworks waiting for someone to build on them.

**Our gap:** The agent can't do inference right now (Conway's OpenAI quota exhausted). And it's not registered on any discovery platform — other agents can't find or hire it.

---

## Actionable Ideas for Our Automaton

1. **Fix inference via x402 router** — Use Daydreams' x402 inference router (router.daydreams.systems) instead of Conway's broken OpenAI proxy. Agent pays per-call from its own USDC wallet. No dependency on Conway's API key.

2. **Register on x402jobs / Work402** — Make the agent discoverable. List capabilities as x402 endpoints so other agents can hire it.

3. **Add anti-scam consumption** — Before the agent makes any transaction, have it pay for a scam check via x402 (Dexter's security stack).

4. **Become a facilitator** — OpenFacilitator lets you deploy a branded facilitator for $5/month. The agent could earn fees by settling x402 payments for others.

5. **BYOK inference** — The upstream repo has a `feat/byok-inference-keys` branch. Merge it and use our own OpenAI/Anthropic key instead of Conway's.

---

## Priority Ranking: What Matters Most for an Autonomous Earn-and-Spend Agent

| Priority | Project | Why |
|----------|---------|-----|
| 1 | **x402.jobs** | Agent job marketplace + discovery API (`GET /discovery/resources`). Find work, earn USDC, list services. Also built OpenFacilitator. |
| 2 | **OpenX402** | Permissionless facilitator — no signup, no API key. Lowest friction to start consuming x402 services. |
| 3 | **Daydreams Router** | Pay-per-call LLM inference via x402 USDC. Solves our broken inference problem immediately. |
| 4 | **PayAI Freelance AI** | Agent-to-agent hiring marketplace on Solana. Gasless. libp2p/IPFS for discovery. |
| 5 | **Dexter** | Largest facilitator by volume. Cross-chain bridging (Solana<>Base). MCP tools for on-chain identity. |
| 6 | **AurraCloud** | 0% fee facilitator + decentralized compute marketplace. Privacy via Virtuals Protocol. |
| 7 | **Corbits / Faremeter** | Modular plugin framework if custom payment flows needed. Nansen partnership for on-chain data. |

**Key insight:** Facilitators are now commoditized (14+ options). The real differentiator is **discovery** (how agents find work) and **commerce frameworks** (how agents wire up earning/spending). x402.jobs, Daydreams Lucid, and PayAI Freelance AI are the three building the "agent labor market" layer on top of the x402 payment rail.

---

## Sources

- [Dexter flips Coinbase as top facilitator](https://www.hokanews.com/2026/01/dexter-quietly-flips-coinbase-to-become.html)
- [Dexter payment infrastructure overview](https://www.web3researchglobal.com/p/dexter)
- [PayAI facilitator](https://facilitator.payai.network)
- [PayAI docs](https://docs.payai.network/x402/introduction)
- [Daydreams Lucid Agents SDK](https://github.com/daydreamsai/lucid-agents)
- [Daydreams x402 router](https://router.daydreams.systems/)
- [Corbits agentic commerce](https://corbits.dev/)
- [Corbits + Nansen integration](https://www.nansen.ai/post/how-corbits-unlocks-nansens-api-and-mcp-to-power-the-next-wave-of-intelligent-agent)
- [OpenFacilitator](https://www.openfacilitator.io/)
- [OpenX402 permissionless facilitator](https://openx402.ai/)
- [x402.rs Rust facilitator](https://facilitator.x402.rs/)
- [x402 ecosystem directory](https://www.x402.org/ecosystem)
- [x402jobs on CoinMarketCap](https://coinmarketcap.com/currencies/x402jobs/)
- [Work402 agent commerce protocol](https://www.work402.com/)
- [x402 protocol guide (CoinGecko)](https://www.coingecko.com/learn/x402-autonomous-ai-agent-payment-coinbase)
- [Tiger Research: AI Agent Payment Infrastructure](https://reports.tiger-research.com/p/aiagentpayment-eng)
- [AurraCloud facilitator](https://x402-facilitator.aurracloud.com/)
- [CodeNut x402](https://www.codenut.ai/x402)
- [CodeNut facilitator docs](https://docs.codenut.ai/guides/x402-facilitator)
- [Dexter.cash](https://dexter.cash/)
- [PayAI Freelance AI / agent hiring](https://payai.network/)
- [x402.rs on crates.io](https://crates.io/crates/x402-facilitator)
- [Solana x402 page](https://solana.com/x402)
- [FintechBrainFood agentic payments map](https://www.fintechbrainfood.com/p/the-agentic-payments-map)
- [Chainstack agentic payments landscape](https://chainstack.com/the-agentic-payments-landscape/)
