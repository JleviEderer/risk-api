# Architecture Decisions

## ADR-001: Decouple product from Conway automaton agent loop (2026-02-22)

**Status:** Accepted

**Context:** After 5 sessions operating base-guardian on Conway Cloud, we spent 90% of time on agent loop infrastructure (hardening, debugging, guardrails) and 0% on the actual product (smart contract risk scoring). The agent loop adds wake/sleep cycles, heartbeat, self-modification, and idle detection — none of which a request-response API needs. The agent burned ~$18+ in credits with $0 revenue and 0 product features shipped.

**Decision:** Kill the automaton agent loop permanently for this product. The risk scoring API is stateless request-response — it does not need autonomy.

**Consequences:**
- No more credit burn from wake cycles
- No more guardrail maintenance (9 guardrails built, none needed for a Flask API)
- Agent loop knowledge preserved in `docs/autonomous-agent-operations-field-guide.md`
- Conway sandbox kept alive only if needed as thin proxy; not required

---

## ADR-002: Build standalone x402 API on own infrastructure (2026-02-22)

**Status:** Accepted

**Context:** Research revealed Conway's x402 tools (`x402_discover`, `x402_check`, `x402_fetch`) are CLIENT-side only — they help agents pay for services, not serve them. Conway provides zero server-side x402 infrastructure. The official x402 Python SDK (`pip install "x402[flask]"`) is ~20 lines of integration code. Coinbase hosts a free facilitator (1K tx/month). ERC-8004 registry is a permissionless public smart contract — no Conway involvement needed.

**Decision:** Deploy the risk scoring API on a simple VPS (EC2 or equivalent) with:
- Flask/FastAPI + x402 Python SDK for payment middleware
- Coinbase hosted facilitator for payment verification/settlement
- ERC-8004 registration from our existing wallet (`0x1358...`) on Base
- x402.jobs listing for additional discovery

**Consequences:**
- Hosting cost: ~$5-8/month (transparent, predictable)
- No platform dependency on a 6-day-old startup
- Full SSH access for debugging (vs Conway's buggy sandbox API)
- Portable — can move to any host, add more discovery channels
- Lose Conway ERC-8004 ecosystem presence (mitigated: can still register on the public contract from anywhere)

---

## ADR-003: Smart contract risk scoring sold agent-to-agent via x402 (2026-02-22)

**Status:** Accepted

**Context:** Exhaustive analysis of alternatives in `docs/BizPlanning.md`:
- M2H crypto tools → extreme competition from VC-funded free products
- Non-crypto SaaS → agent wrapper adds complexity not value
- DeFi yield → need $10K+ capital to cover inference costs
- Agent monitoring → structurally impossible to compete with model providers
- Facilitator → commoditized (14+ players)

The agent-to-agent angle via x402 is the actual moat: no existing competitor has an x402-native risk scoring endpoint. MythX/Slither/Forta require human signup and API keys. Our service is immediately consumable by any agent with a wallet.

**Decision:** Build v3 analysis (bytecode decompilation, honeypot detection, proxy patterns, deployer history, fee manipulation, composite risk score) as a deterministic Python service. Sell at $0.01/call via x402. Deploy as "build once, run passively" — no agent loop, minimal maintenance.

**Consequences:**
- TAM is near-zero today (bet on agent economy growth)
- Downside: $5-8/month hosting if nobody calls it
- Upside: first-mover in x402-native risk scoring if market develops
- Analysis engine is portable — same logic works as regular API, Telegram bot, or browser extension if x402 doesn't pan out

---

## ADR-004: Maintain Conway open source involvement without platform dependency (2026-02-22)

**Status:** Accepted

**Context:** We have 3 merged PRs in Conway-Research/automaton (#149, #155, #156), deep understanding of the codebase, and operational knowledge documented in the field guide. The automaton platform is architecturally sound — the models just aren't capable enough yet for reliable autonomous operation.

**Decision:** Continue contributing to Conway open source. Don't couple our product to their infrastructure. The platform will become valuable when LLMs improve at multi-step autonomous planning.

**Consequences:**
- Community reputation maintained
- Ready to build on Conway when models catch up
- No ongoing infrastructure costs from Conway
- Upstream changes (security fixes, loop detection improvements) remain available to study/learn from

---

## ADR-005: Single-tier pricing at $0.10/call (2026-02-23)

**Status:** Accepted

**Context:** Evaluated three pricing models:
1. **Tiered** ($0.01 basic + $0.10-0.25 deep async) — two different products for two segments (trading agents vs portfolio agents). More engineering complexity (job queue, polling), unclear if both segments exist yet.
2. **Free basic + paid premium** — free as discovery funnel, premium for deep analysis. Removes the x402-native differentiator (frictionless payment IS the product). Agents don't "try then upgrade" — developers configure once.
3. **Single tier** ($0.05-0.10) — one endpoint, one price, everything we can compute in <5 seconds. Simplest to build, simplest to integrate, best margins.

Considered GoPlus comparison: they offer more checks for free, but can't serve autonomous agents (requires signup + API key). We serve a market they can't reach. No need to compete on their features — compete on access model.

**Decision:** Single tier at $0.10/call. Includes all current and future deterministic analysis. Synchronous response. Can always lower to $0.05 if price is the adoption barrier. Can split tiers later if real usage data shows distinct segments.

**Consequences:**
- One endpoint, one price — minimal engineering complexity
- $0.10 gives margin for Basescan API calls and storage reads
- Break-even at 50-80 calls/month (trivially achievable with any real traffic)
- Can't price-discriminate between casual and power users (acceptable tradeoff for simplicity)
- Easy to adjust — lowering price is always easier than raising it

---

## ADR-006: Ship fast, iterate from live data (2026-02-23)

**Status:** Accepted

**Context:** Strategic analysis revealed two competing instincts:
1. **Build robust now** — assume GoPlus is future competition, match their feature coverage before launching. Risk: building features no one needs, delaying discovery while the x402 market forms without us.
2. **Ship fast, learn, iterate** — launch with current 7 detectors + composite scoring, get discoverable (ERC-8004 + x402.jobs), add features based on what real agents actually request. Risk: thin product, bad first impressions.

Key insight: we have **zero users and zero feedback**. Every feature built before launch is a guess. The x402 agent economy is forming now (94K payments/month, 10,000% growth). Being absent from ERC-8004 and x402.jobs while building features for hypothetical customers is the biggest risk.

Our current product is not thin — it's 7 real detectors, composite scoring, tested against real contracts (USDC, WETH). It gives genuinely useful signal. It's not comprehensive, but it's not embarrassing.

GoPlus adding x402 is a future threat (6-18 months if ever), not an immediate one. Their business model (free API, 717M calls/month) makes x402 pay-per-call contradictory.

**Decision:** Launch now with current product. Priority order: discovery (ERC-8004 + x402.jobs) → deployer reputation → expanded selectors → iterate from live traffic data. Don't build honeypot simulation, cross-contract analysis, or other expensive features until real users ask for them.

**Consequences:**
- Discoverable within days, not weeks
- Real usage data to guide feature investment
- Risk of missing edge cases that GoPlus catches (holder concentration, LP lock, sell tax)
- Mitigated by: our product serves a market GoPlus can't reach (autonomous agents), scored risk is more actionable than binary flags, and features can be added rapidly once we know what matters
