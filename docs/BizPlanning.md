# Augur — Business Planning

> Last updated: 2026-03-02

---

## Listing Optimization (x402list.fun)

### Problem

Our x402list.fun listing is weak:
- **Category:** "Other" (invisible in filtered searches)
- **Description:** "Smart contract risk scoring" (bare, no keywords)
- **Transactions:** 6 (bottom of sort rankings)
- **Endpoints:** 1 (vs competitors with 4-8)
- **Output examples:** None (agents can't preview what they'd get)

Competitors are gaming discovery surface — CyberCentry has 5 separate domains, x402-secure has 8 endpoints across 4 categories, and even cryptorugmunch has 4 endpoints.

### Lever 1: Description Enrichment (DONE)

x402list.fun likely infers category from description text. The x402 SDK's `RouteConfig` has no `category` field, so the description IS the primary classification signal.

**Before:** `"Smart contract risk scoring"`

**After:** `"EVM smart contract security analysis — bytecode risk scoring with 8 detectors (delegatecall, hidden mint, fee-on-transfer, selfdestruct, proxy, deployer reputation). Returns 0-100 risk score with proxy resolution."`

**Goal:** Trigger "Security" or "Data & Analytics" category instead of "Other." Keywords chosen to match category classifiers: "security analysis", "risk scoring", "detectors", "bytecode."

### Lever 2: Output Examples in Bazaar Extension (DONE)

The Bazaar SDK's `declare_discovery_extension` supports `output=OutputConfig(example=...)`. We weren't using it. Now we include a representative response so agents can see the output shape before paying.

### Lever 3: Enriched /.well-known/x402 Instructions (DONE)

The x402 discovery document's `instructions` field was generic. Now includes: all 8 detector names, scoring ranges, usage examples (GET + POST), output field descriptions, pricing.

### Why NOT Endpoint Splitting (Yet)

Splitting `/analyze` into sub-endpoints (e.g., `/bytecode-score`, `/deployer-score`, `/proxy-resolve`) would multiply our x402list.fun presence like x402-secure does. But:

1. **0 × 3 = 0.** Splitting doesn't solve the zero-transactions problem. Three endpoints with 0 tx each is worse than one endpoint with real usage.
2. **Fragments revenue.** Each sub-endpoint at $0.02-$0.05 means agents make multiple calls for what's currently one $0.10 call. Net revenue per full analysis drops.
3. **Complicates the codebase.** More routes, more middleware config, more tests, more deployment surface.
4. **Save for later.** Once the basic listing is optimized and we have real traffic data, splitting can be a calculated growth tactic.

### Why NOT Transaction Inflation

Several competitors show identical tx counts across all endpoints (x402-secure: 1.48M everywhere, CyberCentry: 63 everywhere). This is clearly self-dealing. We won't do this because:

1. **Detectable.** Identical counts across endpoints is an obvious tell.
2. **Credibility risk.** If x402list.fun adds fraud detection, inflated providers get flagged.
3. **Real settlements are better.** 6 confirmed CDP settlements on the books. Each real transaction is worth more for credibility than 1000 self-dealt ones.

### Future Considerations

- **Endpoint splitting** — after real traffic validates demand, split detectors into cheap sub-endpoints ($0.02-$0.05) to multiply discovery surface
- **Second domain** — GoPlus's dual-domain tactic gives double x402list.fun presence for free. Could deploy a second domain (e.g., `augur-security.app`) pointing to the same backend.
- **Richer Bazaar metadata** — as the SDK evolves, add output schemas, input validation hints, usage examples
- **Category targeting** — if x402list.fun exposes category selection, explicitly set "Security" and "Data & Analytics"

---

## Pricing Strategy

**Current:** Single tier, $0.10/call (USDC on Base)

**Rationale:**
- Price parity with GoPlus `detect-address` ($0.10)
- Half the price of GoPlus `detect-token` ($0.20)
- Below BlockSec premium tier ($1.00) and Hexens ($0.90)
- Above cryptorugmunch floor ($0.04) — we deliver more (8 detectors vs rug-only)
- Break-even: ~50-80 calls/month (covers Conway sandbox + domain costs)

**No free tier.** Free removes the differentiator vs GoPlus (717M free calls). If agents can get security data for free from GoPlus, paying us $0.10 is a harder sell. But GoPlus gives binary flags; we give scored risk with 8 detectors. The premium is justified.

**No tiered pricing.** Over-engineering for 6 transactions. Can add tiers (basic/detailed/full) after usage data shows what agents actually want.

See also: ADR-005 in `docs/DECISIONS.md`

---

## Competitive Moat

**Moat is x402 frictionlessness, NOT analysis depth.**

GoPlus has 717M calls/month and 30+ chains but requires signup + API key. Autonomous agents can't use GoPlus without human onboarding. We're the only x402-native risk scoring option that works with zero setup.

**Scored risk > binary flags.** Agents write `if score > 50: don't buy` (one line) vs parsing 20+ GoPlus booleans. Simpler integration = faster adoption.

**No LLM in scoring pipeline.** Speed + reliability + margins all favor deterministic pattern matching. Sub-second response time, zero inference costs.

**Moat is time-bounded:** 6-18 months. When GoPlus or BlockSec invest in their x402 listings, they bring brand credibility and chain coverage we can't match. Build usage now while the window is open.

See full competitive analysis: `docs/x402-landscape-research.md`
See strategic ADRs 001-006: `docs/DECISIONS.md`
