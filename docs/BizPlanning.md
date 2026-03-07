# Augur - Business Planning

> Last updated: 2026-03-07

---

## Document Boundaries

Use this file for durable strategy:
- market thesis
- pricing logic
- moat framing
- major prioritization calls

Do not use this file as the operating backlog.

Execution lives in:
- `docs/GrowthExecutionPlan.md` - current workstreams, priorities, metrics, and sequencing
- `docs/DECISIONS.md` - major decisions and ADRs
- `docs/REGISTRATIONS.md` - registry and marketplace state

---

## Conversion Funnel

**Current state:** 200+ visitors, 0 organic paying calls.

**Diagnosis:** discoverability is partially working; conversion and trust are not.

People are finding Augur through directories, crawlers, and registries, but the first-use path still has too much friction:
1. x402 client-side payment is unfamiliar
2. trust breaks if examples, domains, or outputs are confusing
3. buyers must decide to pay before they have enough proof

**Strategic implication:** fix product trust and onboarding before expanding endpoint count.

### Current strategic priorities

| Priority | Action | Why |
|---|---|---|
| 1 | Product trust fixes | Hard-error non-contract/no-bytecode inputs, audit examples, remove Base/mainnet confusion |
| 2 | Domain + registry hygiene | Make `augurrisk.com` the canonical surface across listings and crawlers |
| 3 | MCP distribution | Put Augur directly into the emerging agent toolchain surface |
| 4 | First-class client onboarding | Make the x402 payment flow easy to copy and verify |
| 5 | Intent pages + public reports | Expand SEO/LLM surface without fragmenting the paid API |
| 6 | Targeted community distribution | Push proof and integration assets into Base/x402 communities |

### What NOT to do first

- **Endpoint splitting** - still deferred. `0 x 3 = 0`.
- **Synthetic transaction inflation** - credibility loss is not worth vanity rankings.
- **Second domain for ranking games** - only revisit after the core funnel converts.
- **Multi-rail payment expansion** - watch Stripe/ACP/UCP, but do not fork effort before current demand exists.

### Deferred

- **Framework-specific tool wrappers** - useful later, but MCP is the cleaner initial packaging bet.
- **Free demo endpoint** - consider after correctness, examples, MCP, and onboarding docs are fixed.

---

## Listing Optimization

Enrichment levers completed (2026-03-02):
- Description updated with full keyword set: security analysis, bytecode, 8 detectors, proxy resolution
- Bazaar extension now includes output examples via `OutputConfig(example=...)`
- `/.well-known/x402` instructions enriched with detector names, scoring ranges, and usage examples

### Why NOT endpoint splitting

Splitting `/analyze` into sub-endpoints like `/bytecode-score`, `/deployer-score`, and `/proxy-resolve` would multiply x402list.fun presence. But:
1. **0 x 3 = 0.** Three endpoints with 0 tx each is worse than one endpoint with real usage.
2. **Fragments revenue.** Multiple cheap calls replace one $0.10 call. Net revenue per full analysis drops.
3. **Complicates the codebase.** More routes, middleware, tests, and deployment surface.

### Why NOT transaction inflation

Competitors like x402-secure and CyberCentry show identical tx counts across all endpoints, which strongly suggests self-dealing. We should not do this:
1. **Detectable.** Identical counts are an obvious tell.
2. **Credibility risk.** If directories add fraud detection, inflated providers get flagged.
3. **Real settlements matter more.** Each real CDP settlement is worth more than a large synthetic number.

---

## Pricing Strategy

**Current:** single tier, $0.10/call (USDC on Base)

**Rationale:**
- Price parity with GoPlus `detect-address` ($0.10)
- Half the price of GoPlus `detect-token` ($0.20)
- Below BlockSec premium tier ($1.00) and Hexens ($0.90)
- Above cryptorugmunch floor ($0.04) because we deliver more than rug-only checks
- Break-even at roughly 50-80 calls/month, which covers Fly.io and domain costs

**No free tier.** Free removes the x402 differentiator. GoPlus already serves the free market with binary flags; our value is frictionless paid access plus richer scoring.

**No tiered pricing yet.** Tiering is premature at current volume. Add tiers only after usage data reveals distinct segments.

See also: ADR-005 in `docs/DECISIONS.md`

---

## Competitive Moat

**Moat is x402 frictionlessness, not analysis depth alone.**

GoPlus has large-scale free usage and broad chain coverage, but requires signup and API keys. Autonomous agents cannot rely on that onboarding path. Augur is x402-native and immediately callable by any agent with a wallet.

**Scored risk beats binary flags for agent workflows.** Agents can write `if score > 50: do not interact` instead of parsing many individual booleans.

**No LLM in the scoring pipeline.** Deterministic analysis preserves speed, reliability, and margins.

**Moat is time-bounded:** roughly 6-18 months. If incumbents invest seriously in x402 distribution, they bring credibility and brand reach we cannot match. The right move is to build real usage now while the market is still forming.

See full competitive analysis: `docs/x402-landscape-research.md`
See strategic ADRs: `docs/DECISIONS.md`
