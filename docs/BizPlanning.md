# Augur - Business Planning

> Last updated: 2026-03-08

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

**Important distinction:** x402 is the payment layer, not the discovery layer.

Agents do not find Augur just because `/analyze` supports x402. Discovery comes from the surrounding surfaces:
- MCP packaging
- A2A agent card
- OpenAPI schema
- registry and directory listings
- public docs and examples

Strategic implication: treat payment support and discovery support as separate workstreams.

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

---

## Product Scope

### What Augur should be

Augur should be built as **security infrastructure for agentic and onchain decision-making**.

That means:
- agents call Augur before interacting with contracts or submitting risky transactions
- wallets, trading systems, and automation tools can embed Augur as a risk-check layer
- the core asset is the scoring engine, not the website alone and not x402 alone

The right mental model is:
- `x402` is the current payment and distribution wedge
- the bytecode and risk engine is the durable product
- future delivery surfaces can include x402, MCP, direct API plans, and other payment rails if buyer demand justifies them

Just as important: Augur should be **embedded into tools and workflows**, not only exposed as a standalone endpoint.

Best case:
- a trading or treasury agent checks Augur before interacting with a contract
- an MCP client calls Augur as part of a larger flow
- a wallet, executor, or automation framework treats Augur as a guardrail step

This is a better position than relying on users to discover one endpoint and call it manually.

### What Augur should NOT be

Do not turn Augur into a general "agent economy infrastructure" platform.

For a solo founder, that spreads too wide across:
- orchestration
- wallets and payments
- generic agent security
- protocol tooling
- monitoring for everything

The market is already crowded in broad agent tooling. Augur is more differentiated when it stays close to a narrow, high-consequence decision: **should this agent interact with this onchain target or transaction?**

---

## Adjacent Security Services

There are more security services to sell to agents than smart contract risk. The key question is not "what else exists?" but "what shares the same buyer, the same workflow, and the same trust story?"

### Best-fit adjacent services

These fit Augur's current wedge and can reuse the same product story.

1. **Smart contract bytecode risk**
   Current core product. Keep improving this first.

2. **Transaction preflight risk**
   Evaluate a pending transaction before an agent signs or submits it.
   Examples:
   - suspicious approvals
   - risky swap routes
   - bridge interactions
   - proxy upgrade calls
   - unusual calldata patterns

3. **Approval / allowance risk**
   Tell an agent whether it is about to grant dangerous token permissions.
   This is especially good because it is close to the same "should I proceed?" moment as contract scoring.

4. **Continuous monitoring and alerts**
   Watch a contract or allowlist for upgrades, ownership changes, proxy implementation swaps, or risk-score changes.
   This can turn one-off scans into recurring usage.

### Possible later, but not now

- counterparty or endpoint trust for paid agent services
- x402 provider trust scoring
- registry reputation enrichment

These are strategically related, but they are a different trust surface than bytecode analysis. Do not expand here until the core onchain wedge has clear demand.

### Too broad for current scope

- generic prompt-injection defense
- browser security
- full wallet security platform
- generalized "agent security" across every modality
- broad security scoring for all APIs and agents

These may be valid markets, but they do not reuse Augur's core differentiation tightly enough for a solo founder.

---

## Expansion Rule

Only build adjacent services that satisfy all three conditions:

1. **Same buyer**
   The user already wants onchain risk help for an autonomous or semi-autonomous workflow.

2. **Same decision point**
   The service answers the same class of question:
   `Should I interact, sign, approve, pay, or proceed?`

3. **Same trust story**
   The output can still be explained as deterministic, machine-readable risk signal rather than a vague LLM opinion.

If a proposed service fails one of those tests, it is probably a separate product, not an Augur extension.

---

## Solo Founder View

### Is this a reasonable business to build?

Yes, with the right scope.

Augur is more plausible as:
- narrow security infrastructure for agents
- sold through machine-payable and developer-friendly surfaces
- expanded carefully into adjacent onchain risk products

Augur is less plausible as:
- a one-endpoint x402 business by itself
- a broad "agent economy platform"
- a generic security company for every agent threat category

### Why it can work

- the product sits near money movement, which raises willingness to pay
- the risk check can happen before value leaves a wallet
- autonomous systems increase the need for automated guardrails
- the current engine is specific enough to integrate into real workflows

### Why focus matters

- x402 is still early and not enough distribution on its own
- broad agent infrastructure is highly saturated
- security products require trust, repeated usage, and workflow fit
- solo-founder advantage comes from clarity and speed, not surface-area breadth

### Current recommendation

Stay inside **onchain decision security for agents**.

Priority order:
1. make smart contract scoring trustworthy and easy to consume
2. add transaction preflight or approval-risk checks if real users ask for the adjacent step
3. add recurring monitoring only after one-off paid usage exists

Do not branch into broad parallel infrastructure unless it directly increases usage of the current risk engine.

Distribution priority within that scope:
- improve machine-readable discovery and integration surfaces first
- prefer MCP, registries, and workflow embeddings over building more generic standalone infrastructure
