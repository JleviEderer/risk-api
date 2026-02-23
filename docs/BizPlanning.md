# Business Planning: risk-api

> Originally: 2026-02-19 (base-guardian autonomous agent)
> Updated: 2026-02-23 (product shipped, live, strategic direction set)
> Status: **Product live.** x402 paywall active. Discovery phase next.

---

## 1. What We're Building

**risk-api** is a smart contract risk scoring API sold agent-to-agent via x402 micropayments on Base. Deterministic EVM bytecode analysis, no LLM inference per request.

- **Live at:** https://risk-api.life.conway.tech
- **Wallet:** `0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891`
- **Price:** $0.10/call in USDC on Base
- **Facilitator:** Dexter (`https://x402.dexter.cash`) — free, no auth, 20K settlements/day
- **Repo:** https://github.com/JleviEderer/risk-api (private)

**Evolution:** Started as base-guardian autonomous agent on Conway (Feb 2019). Decoupled from agent loop (ADR-001) after realizing a stateless API doesn't need autonomy. 5 sessions on agent infrastructure, 0 features shipped. Rebuilt from scratch as standalone Flask API in one session (Feb 22), deployed and paywalled (Feb 23).

---

## 2. The x402 Landscape (Competitive Research)

We mapped the full x402 agentic payments ecosystem (see `docs/x402-landscape-research.md` for details).

**Key finding:** The ecosystem is 14+ payment facilitators, several frameworks/SDKs, and a handful of marketplaces. Almost nobody is building **actual intelligence services** that ride those rails. Everyone is building infrastructure for a market that hasn't fully formed yet.

**Our position:** base-guardian sits in "Agent Frameworks & Tooling" on the Artemis landscape map. Our differentiator is that we're a **live agent**, not another SDK or toolkit. Most projects are frameworks waiting for someone to build on them.

---

## 3. Stress-Testing the Original Idea

### 3.1 The Value Proposition (Broken Down Simply)

**The customer:** An autonomous AI agent with a wallet that's about to buy a token on Base.

**The problem:** Some tokens are scams — honeypots (you can buy but can't sell), rug pulls (deployer drains liquidity). If the agent buys one, it loses money.

**What we sell:** Before the agent buys, it asks our API: "Is contract `0xABC...` safe?" We return a risk score. Agent uses that to decide whether to proceed.

**Why they'd pay:** A rug-pull check costs $0.01. Getting rugged costs $50-$1,000+. It's insurance — pay a penny to avoid losing a dollar.

### 3.2 v1 vs v3: Is the Product Actually Valuable?

| Version | What it checks | Value | Can customer DIY? | Defensible? |
|---------|---------------|-------|-------------------|-------------|
| **v1** (basic) | Contract age, deployer wallet history, verified source code, holder concentration, ownership renounced | Convenience — aggregates 5 free API calls into 1 paid call | **Yes, easily** — all free public data from Basescan | **No** |
| **v3** (full) | Bytecode decompilation for honeypot patterns, liquidity lock verification, deployer wallet graph analysis, hidden mint function detection, proxy upgrade pattern checks | Real intelligence — analysis an agent can't do itself | **No** — requires specialized analysis, maintained scam database, graph analysis | **Yes** |

**Conclusion:** v1 is selling bottled water next to a free water fountain. v3 is selling water quality testing in a city with lead pipes. Only v3 has a real value prop, but it's significantly harder to build.

### 3.3 Does the Buyer Even Exist?

**The fundamental demand question:** Are there autonomous agents actively trading tokens on Base right now?

**Honest answer: Barely.** What exists today:
- Human traders using sniper bots (scripts with human instructions, not autonomous agents)
- MEV bots extracting value from DEX swaps (highly specialized, not general agents)
- DeFi management bots (rebalancing yield positions)

The "agent with a wallet decides to buy a token and needs a safety check first" scenario — that customer barely exists yet. The x402 ecosystem is ~2-3 months old. Most participants are builders building infrastructure for other builders.

### 3.4 Is Base the Right Network?

Base is popular (low gas fees, Coinbase onramp), but for **scam tokens specifically**:
- **Solana** (pump.fun) — massive volume of new token launches, biggest scam surface area
- **BSC** — historically the rug-pull capital
- **Base** — growing but #3 or #4 for scam volume

We're on Base because Conway's infrastructure (USDC, ERC-8004, x402) runs on Base. Practical choice, not optimal market choice.

---

## 4. Alternative Revenue Models Explored

### 4.1 DeFi Yield Farming ("Market as Customer")

| Strategy | APY | Annual return on $100 | Daily |
|----------|-----|-----------------------|-------|
| Aave stablecoin lending | 5% | $5.00 | $0.014 |
| Aerodrome stablecoin LP | 10% | $10.00 | $0.028 |
| Riskier pools | 20% | $20.00 | $0.055 |

**Problem:** The agent burns ~$0.02-0.05 per wake cycle in inference costs, multiple cycles per day. Yield on $100 doesn't cover the cost of thinking about the yield.

Even at $1,000: ~$0.55/day — barely covers inference costs.

You'd need **$10,000+** for yield farming to produce meaningful revenue. That's not bootstrapping — that's venture capital.

**Same capital problem applies to:** LP provision, DEX arbitrage, flash loan arb (zero capital but insanely competitive and complex).

### 4.2 Machine-to-Human (M2H) Products

Instead of selling to agents, sell to humans. Explored options:

| Product | Demand | Competition | Agent's Edge? |
|---------|--------|-------------|---------------|
| Telegram rug-pull checker | High | Extreme (RugCheck, Token Sniffer, GoPlus, De.Fi, Honeypot.is, BubbleMaps — mostly free) | No |
| Token launch alert channel | High | Extreme (hundreds of Telegram channels, DEXScreener) | No |
| Whale wallet watcher | High | Extreme (Whale Alert, Arkham, Nansen, Lookonchain — free tiers) | No |
| Portfolio risk scanner | Medium | Extreme (Zapper, Zerion, DeBank, De.Fi — all free) | No |
| Twitter/X analysis bot | Medium | High | No |

**Problem:** M2H crypto verticals are MORE competitive than M2M x402. These products have established user bases, VC funding, full engineering teams, and most are free. We'd be entering crowded markets with a worse product.

### 4.3 Non-Crypto SaaS (Stepping Outside the Crypto Bubble)

Could the agent sell non-crypto services to humans?
- Web scraping as a service
- Uptime monitoring
- SEO analysis
- Content generation
- Code review bot
- Data enrichment

**Problem:** For any of these — why does it need to be an autonomous agent? A web scraping service is just a server running a script. An uptime monitor is just Pingdom. You'd just build a normal SaaS.

The agent's unique capabilities (wallet, self-modification, x402 native) are only relevant in crypto. Outside crypto, the agent is just a server with extra complexity.

### 4.4 Agent Monitoring/Auditing

**Source:** Anthropic's [Measuring AI Agent Autonomy](https://www.anthropic.com/research/measuring-agent-autonomy) report (2026-02-18) calls for "new forms of post-deployment monitoring infrastructure" and identifies it as an important area for cross-industry collaboration. They admit they can't even link independent API requests into coherent agent sessions. Sounds like an opportunity — someone needs to watch what autonomous agents are doing.

**How you'd actually build it:** There are only four ways to monitor agent behavior:

1. **Be the model provider** — You see every API request. You can cluster them into sessions, analyze intent, flag anomalies. This is what Anthropic's Clio system already does. Requires being the LLM vendor.
2. **Be a middleware/proxy** — Sit between the agent and the model API, intercept traffic. This is a SaaS product (proxy server + dashboard), not an autonomous agent.
3. **Be an embedded SDK** — Ship a library that agent developers install to instrument their agents. This is a developer tools company, not an autonomous agent.
4. **Monitor on-chain behavior** — Watch wallet transactions, flag suspicious patterns. This is blockchain analytics — Nansen, Arkham, and Chainalysis already do this with massive datasets, graph analysis, and VC funding.

**Why none of these require an autonomous agent:** Every implementation path is either a SaaS product (proxy, SDK, dashboard) or a data pipeline (on-chain analytics). base-guardian's unique capabilities — wallet, self-modification, x402 payments, on-chain identity — don't help with any of them. You don't need a wallet to run a proxy server. You don't need self-modification to ship an SDK. You don't need x402 to sell a monitoring dashboard.

**Anthropic's structural advantage:** They already have Clio, which clusters API conversations by topic across their entire user base. They see 100% of traffic to their models. Any third-party monitoring tool is working with a fraction of the data Anthropic already has. Competing with the model provider on model-level observability is structurally impossible.

**On-chain monitoring = blockchain analytics:** If we narrow to "monitor what agents do on-chain," we're just building a blockchain analytics product. Nansen has $100M+ in funding, Arkham has token-incentivized intelligence networks, Chainalysis is the industry standard for compliance. We'd be entering with zero data, zero funding, and no edge.

**Conclusion:** Same trap as 4.3 — wider market, but no agent edge. "An agent that monitors other agents" sounds compelling on the surface, but doesn't survive scrutiny. Every viable implementation is a normal SaaS/data product where being an autonomous agent adds complexity, not value.

---

## 5. The Core Dilemma (Feb 19 — partially resolved)

The original dilemma:
- **Where we have an edge** (M2M, x402 native) — **customers don't exist yet**
- **Where customers exist** (M2H, SaaS) — **we have no edge**

**Resolution (Feb 22-23):** We chose to bet on being early. The product is built and live. The bet costs $5-8/month in hosting. The x402 ecosystem grew from ~$100M to $600M+ in total volume during our analysis period. 94K payments in the last 30 days across all x402 services, growing 10,000% MoM in Q4 2025. The market is forming. We're positioned.

---

## 6. GoPlus: The Direct Competitor

### What GoPlus Is
- **717M API calls/month**, 22M/day — dominant in contract security
- **Free API** — monetizes through paid wallet security app ($4.7M total revenue, $2.5M from app)
- 30+ chains, 12M wallets, integrated into DEXTools/SushiSwap
- Returns **binary flags**: `is_honeypot`, `is_proxy`, `is_mintable`, `can_take_back_ownership`, etc.

### What GoPlus Checks vs What We Check

| Check | GoPlus (free) | risk-api ($0.10) |
|-------|--------------|------------------|
| Honeypot detection | Yes (likely simulation) | Bytecode patterns (weaker — no simulation) |
| Proxy detection | Yes | Yes (better — EIP-1967/1822/OZ slots) |
| Mintable | Yes | Yes (selector DB) |
| Blacklist functions | Yes | Yes (selector DB) |
| Buy/sell tax % | Yes | Not yet |
| LP lock status | Yes | Not yet |
| Holder concentration | Yes | Not yet |
| Open source check | Yes | No (bytecode-only by design) |
| Anti-whale | Yes | Yes (selector DB) |
| Number of chains | 30+ | 1 (Base) |
| **Composite risk SCORE (0-100)** | **No — binary flags only** | **Yes** |
| **Deployer reputation** | **No** | **Planned (Basescan API)** |
| **Reentrancy detection** | **No** | **Yes** |
| **Selfdestruct detection** | **No** | **Yes** |
| **Proxy upgrade history** | **No** | **Planned** |
| **Storage state analysis** | **No** | **Planned** |

### Why GoPlus Can't Easily Enter Our Space

1. **Business model conflict.** 717M free calls/month depends on being free. Adding x402 pricing cannibalizes their integration partnerships (DEXTools, Sushi, etc.). "Why pay when it's free?" kills conversion.
2. **Can't afford LLM analysis.** At 717M calls/month, even $0.01/call inference = $7.17M/month. Their total lifetime revenue is $4.7M. Structural cost ceiling.
3. **Not built for agents.** GoPlus requires signup + API key + rate limit management. An autonomous agent with just a wallet literally cannot use GoPlus without human intervention.
4. **Organizational inertia.** Optimized for B2C (wallet app). Agent-to-agent is a different customer, different product thinking. Big companies pivot slowly toward tiny markets.

### Why We Can't Beat GoPlus on Features

We have 7 detectors on 1 chain. They have 30+ checks on 30+ chains with simulation-based honeypot detection and holder concentration analysis. We will never match their coverage. **That's fine — we're serving a different market.**

### The Nansen Partnership

GoPlus partnered with Nansen (blockchain analytics). Most likely a **data enrichment** deal (Nansen wallet labels in GoPlus, or GoPlus data in Nansen's platform), NOT GoPlus adding x402 payments. Their free model makes x402 pay-per-call contradictory. Monitor but don't panic.

---

## 7. The x402-Native Moat

**The moat is not analysis depth. The moat is frictionless agent access.**

An autonomous agent with a wallet needs a risk check:
- **GoPlus:** Can't use it. Requires human signup, API key provisioning, rate limit configuration. Agent with no human operator is locked out.
- **risk-api:** Send $0.10 USDC, get a risk score. Zero setup. Discoverable via ERC-8004 registry. Works for any agent with a wallet on Base.

This isn't a feature advantage — it's a **categorical access advantage**. For fully autonomous agents, we're the only option that exists.

**Is this moat permanent?** No. If x402 agent economy grows large enough, GoPlus will eventually add x402 support. The moat is **time-bounded** — probably 6-18 months depending on x402 growth rate. The strategic imperative is: **be established and discoverable before that happens.**

**Why scored risk > binary flags for agents:**
- GoPlus returns 20+ boolean fields. Agent developer writes complex logic to interpret them.
- We return one score (0-100) with a risk level. Agent developer writes: `if score > 50: don't buy`. One line of code.
- Simpler integration = faster adoption = stickier product.

---

## 8. Pricing Strategy

**Decision: Single tier, $0.10/call.** (ADR-005)

| Consideration | Analysis |
|---------------|----------|
| Why not $0.01? | Leaves no margin for enhanced analysis (Basescan API calls, storage reads). Also, $0.10 vs $0.01 doesn't matter to an agent avoiding a $50+ rug pull. |
| Why not $0.50+? | Starts feeling like audit pricing. We're automated triage, not a human audit replacement. |
| Why not tiered? | One endpoint, one price, one product. Simpler to build, simpler for agents to integrate. Can always split later based on real usage data. |
| Why not free basic + paid premium? | Free removes the thing that makes us different (x402-native). Agents don't "try before they buy" — developers configure once. Free attracts abuse, not upgrades. |
| Can we raise later? | Always easier to lower a price than raise one. Start at $0.10, drop to $0.05 if price is the adoption barrier. |

**Break-even math:**
| Hosting cost | Calls needed at $0.10 |
|-------------|----------------------|
| $5/month | 50 calls |
| $8/month | 80 calls |

**Why LLMs are wrong for this product:**
- Speed: Slither <1s, LLM 2-10s. Agents need fast answers.
- Reliability: LLMs hallucinate. A false "safe" rating = financial loss. Security needs deterministic guarantees.
- Cost: At volume, LLM inference eats all margin.
- Keep the "pure pattern matching, no LLM inference" approach. This was the right call.

---

## 9. What's Built (Current State — Feb 23)

| Component | Status |
|-----------|--------|
| EVM bytecode disassembler (149 opcodes) | Done |
| 7 pattern detectors (selfdestruct, delegatecall, reentrancy, proxy, honeypot, hidden_mint, fee_manipulation) | Done |
| Malicious/suspicious selector database (9 malicious + 6 suspicious) | Done (expand to 50-100) |
| Composite risk scoring (0-100, category-capped) | Done |
| Flask app + x402 payment middleware | Done |
| Test suite | 64 tests, 91% coverage, 0 pyright errors |
| Deployment | Live on Conway sandbox, Dexter facilitator, x402 paywall active |
| Docker setup | Dockerfile + compose ready for non-Conway deployment |
| Discovery (ERC-8004 + x402.jobs) | **NOT DONE — highest priority** |

### What's Missing (Honest Gaps)

| Gap | Impact | Effort |
|-----|--------|--------|
| No honeypot simulation (fork+sell) | Miss sophisticated honeypots (storage blacklists, time locks, high sell tax) | High — needs forking RPC |
| No buy/sell tax detection | Miss effective honeypots (99% tax = can't sell) | Medium — needs DEX query or simulation |
| No holder concentration | GoPlus has this, we don't | Medium — needs token holder API |
| No LP lock detection | GoPlus has this, we don't | Medium — needs DEX pool queries |
| Selector DB is small (15 signatures) | Miss obfuscated scam functions | Low — research + add more |
| No deployer reputation | High-signal check, easy to add | Low — Basescan API (free) |
| Single chain (Base) | GoPlus has 30+ | Intentional — ship on Base where x402 lives |

---

## 10. Build Priorities

### Principle: Ship Fast, Learn, Iterate

We have zero users and zero feedback. Building features based on guesses is waste. Every week spent building is a week we're not discoverable. The x402 agent economy is forming NOW.

**Priority order based on impact/effort:**

### Immediate (this week)
1. **ERC-8004 registration** — Permissionless on Base at `0x8004...`. Makes us discoverable to any agent querying the registry.
2. **x402.jobs listing** — Additional discovery channel.
3. **Price update to $0.10** — Current deployment is $0.01, update to $0.10.

### Phase 2 (next 2-4 weeks, while waiting for traffic)
4. **Deployer wallet reputation** — Basescan API (free tier, 5 calls/sec). Deployer age, contract count, any flagged contracts. High signal, fast win.
5. **Expand selector database to 50-100** — Research common scam function signatures. Our bytecode-only approach works on unverified contracts, which is most scam tokens.
6. **Storage state reads** — `eth_getStorageAt` for paused state, owner address. Enriches findings.

### Phase 3 (when we have live traffic + feedback)
7. **Whatever users actually ask for.** We don't know yet. Could be honeypot simulation, batch analysis, different chains, or something we haven't imagined.
8. **Honeypot simulation** — If agents checking meme tokens are the primary users. Requires forking RPC (Tenderly/Alchemy free tier or self-hosted Anvil).
9. **Temporal monitoring** — Snapshot + diff for proxy upgrades, LP draining, owner changes.

### What NOT to Build
- Don't add LLM inference — kills speed, reliability, margins
- Don't build a free tier — removes our differentiator
- Don't expand to multiple chains yet — Base is where x402 lives
- Don't build a frontend/dashboard — agents are the customer
- Don't try to match GoPlus feature-for-feature — different market
- Don't over-build before launch — iterate from live feedback

---

## 11. Open Questions (Updated Feb 23)

1. ~~Should we build the product?~~ **Resolved: Yes, built and live.**
2. ~~Should we hibernate?~~ **Resolved: No, shipping.**
3. **When does GoPlus add x402?** Monitor the Nansen partnership. Probably 6-18 months if ever.
4. **What do agents actually want?** Unknown until we get live traffic. Discovery is the unlock.
5. **Is $0.10 the right price?** Need real data. Can adjust down to $0.05 if price is the barrier.
6. **Should we add honeypot simulation?** Depends on whether trading agents (who need it) or portfolio agents (who don't) are the primary customer. Wait for data.
7. **When to move off Conway sandbox?** When traffic justifies it or reliability becomes an issue. $5-8/month VPS is the escape hatch.

---

## 12. Key Numbers

| Metric | Value | Source |
|--------|-------|--------|
| GoPlus monthly API calls | 717M | GoPlus public stats |
| GoPlus total revenue | $4.7M | GoPlus disclosures |
| x402 30-day payments | 94K across all services | x402 ecosystem data |
| x402 total volume | $600M+ | x402 ecosystem data |
| x402 growth | 10,000% MoM spike Q4 2025 | x402 ecosystem data |
| Smart contract audit market | $456M (2024) | Industry reports |
| Human audit cost | $25K-150K per contract | Industry standard |
| Automated tools catch rate | 40-60% of vulnerabilities | Academic research |
| Our hosting cost | ~$5/month (Conway sandbox) | Current |
| Break-even at $0.10/call | 50-80 calls/month | Math |
| Our test suite | 64 tests, 91% coverage | Current |

---

## 13. Decisions Log

| # | Decision | Date | Rationale |
|---|----------|------|-----------|
| 1 | Stay in security vertical | 2026-02-19 | Landscape validates niche, even if early |
| 2 | Don't become a facilitator | 2026-02-19 | 14 players, commoditized |
| 3 | Kill Conway agent loop (ADR-001) | 2026-02-22 | Stateless API doesn't need autonomy |
| 4 | Build standalone (ADR-002) | 2026-02-22 | Conway has zero server-side x402 |
| 5 | x402-native risk scoring (ADR-003) | 2026-02-22 | First mover, no competitors in x402 space |
| 6 | Keep Conway open source (ADR-004) | 2026-02-22 | Platform is sound, models need to catch up |
| 7 | Dexter facilitator | 2026-02-23 | Free, no auth, 20K/day (Coinbase needs CDP key) |
| 8 | No LLM in scoring pipeline | 2026-02-23 | Speed + reliability + margins all favor deterministic |
| 9 | Single tier $0.10 (ADR-005) | 2026-02-23 | Simple, adjustable, good margins |
| 10 | Ship fast, iterate from data (ADR-006) | 2026-02-23 | Zero users = zero feedback. Discovery > features |
| 11 | Don't match GoPlus features | 2026-02-23 | Different market (agents vs humans), different moat (x402 vs coverage) |
| 12 | No free tier | 2026-02-23 | Free removes x402 differentiator, attracts abuse not upgrades |

---

## References

- Architecture decisions: `docs/DECISIONS.md` (ADR-001 through ADR-006)
- Competitive research: `docs/x402-landscape-research.md`
- Technical details: `risk-api/CLAUDE.md`
- Agent operations knowledge: `docs/autonomous-agent-operations-field-guide.md`
- GoPlus API docs: https://docs.gopluslabs.io/reference/response-details
- Repo: https://github.com/JleviEderer/risk-api
