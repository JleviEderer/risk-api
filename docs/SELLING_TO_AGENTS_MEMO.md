# Selling To Agents Memo

> Date: 2026-03-19
> Source: Brian Flynn's X article "How to Sell to Agents" (published 2026-02-16), reviewed from the local Obsidian clip.
> Related docs: `docs/PRODUCT_DIRECTION_UPDATE.md`, `docs/PRODUCT_WEDGE_MEMO.md`, `docs/agent-economy-primer.md`

## Bottom Line

The article supports Augur's current direction, but only in its stronger form.

It validates:

- machine-readable discovery
- protocol-level pricing
- narrow specialist services
- agent-native buying flows

It also raises a hard bar:

> Augur has to be a service an agent is rational to call before touching money, not just an interesting contract-scoring endpoint.

That means the right product is not "risk reporting."

It is:

- a high-trust pre-transaction contract decision service
- sold as admission control
- measurably faster, cheaper, and more reliable than self-computing the same judgment inside the agent

## What The Article Says

The article's core claim is that agents collapse transaction costs around:

- discovery
- price evaluation
- service selection
- purchase execution

Agents do not browse like humans.

They query for:

- what a service does
- how much it costs
- whether it is reliable
- whether it is allowed
- whether it is better than doing the work themselves

The article argues that winning agent-native services share a common shape:

- machine-readable capabilities
- pricing in the protocol
- automatable onboarding
- provable reliability
- a cost/speed advantage over self-computation

For reliability, the article is concrete rather than abstract:

- publish uptime history
- publish latency percentiles
- publish accuracy metrics or benchmarks
- expose output provenance where possible
- return confidence scores with responses when the output is probabilistic or heuristic

## What This Validates About Augur

Augur already matches a surprising amount of this shape.

### 1. Machine-readable discovery already matters

The article says that if a service cannot be discovered by a machine, it does not exist to agents.

Augur already has:

- `skill.md`
- `openapi.json`
- `llms.txt`
- `llms-full.txt`
- `/.well-known/x402`
- `/.well-known/agent-card.json`
- `agent-metadata.json`

That is the right posture for agent-native discovery.

### 2. Pricing in the protocol is a real advantage

The article strongly favors protocol-level pricing over human-facing pricing pages.

Augur already fits this well:

- x402 exposes price in the request flow
- payment is machine-readable
- onboarding is account-light
- no API key or signup is required

This is not a side detail. It is part of the product's fit.

### 3. Narrow specialist endpoints can win

The article argues that agent markets create room for single-purpose services that are:

- fast
- cheap
- specialized

That supports Augur's narrow wedge more than a broad platform move.

### 4. Runtime trust matters more than attention

The article says agents optimize for:

- outcomes
- price
- speed
- reliability

not:

- brand theater
- attention capture
- human-style conversion funnels

That supports the recent move to frame Augur as an enforceable gate rather than an informational report.

## The Hard Warning For Augur

The article makes one risk much clearer:

If an agent can cheaply reproduce Augur's judgment on its own, Augur is in danger.

The article's buy-vs-build rule is brutal:

- if a specialized service is faster and cheaper than self-computation, buy
- if not, build or compute locally

Applied to Augur, this means the weak version of the product is vulnerable:

- "here is a contract score"
- "here are some findings"
- "you should probably think about this"

That is not enough if the same result can be approximated by:

- a prompt
- open-source detectors
- a cheap model
- a bit of in-house glue

So the real product asset cannot just be:

- bytecode access
- detector existence
- score calculation

It has to be:

- maintained judgment
- reliable policy output
- edge-case coverage that keeps improving
- trust strong enough that an agent stack prefers to delegate the decision

## What This Means For Product Direction

The article does **not** push Augur toward:

- a full wallet
- a broad agent platform
- a generic MCP layer
- a giant simulation suite

It pushes Augur toward being a stronger version of its current path.

Specifically:

### 1. Sell the decision, not the score

Agents want:

- should I proceed
- how much confidence should I have
- why is this blocked or escalated

The score is supporting data, not the core value.

### 2. Be obviously worth delegating to

The product must be:

- faster than self-computation
- cheaper than self-computation
- easier to trust than self-computation

This is a product requirement, not just a go-to-market preference.

### 3. Keep compounding on trust

The strongest moat implied by the article is not branding.

It is:

- uptime
- latency discipline
- measurable accuracy
- consistency
- clarity
- reproducibility
- verifiable output quality

The article's standard is that trust should be machine-evaluable.

That means Augur should not stop at saying "reliable."

It should make reliability legible through things like:

- public uptime and health history
- latency percentile reporting
- benchmark or replay-backed accuracy evidence
- confidence metadata where the output is not purely deterministic
- machine-readable provenance and explanation surfaces

If Augur is flaky, noisy, or operationally confusing, an agent will not keep buying from it.

### 4. Keep the product close to the moment of action

The article favors services that slot directly into a workflow decision.

For Augur that means:

- before buy
- before approve
- before route
- before bridge
- before pay

Potentially also:

- before deposit, when the agent needs to know whether the claimed protocol, chain, and destination are consistent enough to trust

That does not require Augur to become a broad anti-phishing suite.

It is still consistent with the same core shape:

- a narrow pre-transaction decision service
- called at the moment of action
- returning a machine-readable go / no-go recommendation

This is consistent with the current move from contract scoring toward admission control.

## What This Suggests We Should Build

The article strengthens the case for:

- decision-first output
- action-aware policy inputs
- narrow destination-aware preflight checks for actions like deposit or approval when the claimed recipient matters
- machine-readable reason codes
- public proof artifacts
- clear reliability and liveness surfaces
- published uptime, latency, and accuracy metrics
- confidence scores or confidence bands where they honestly reflect uncertainty
- integration paths that make Augur easy to call in real workflows

It also suggests a new standard for evaluating roadmap ideas:

> Does this make Augur more likely to be the service an agent buys instead of computing around it?

If the answer is no, it is probably not top priority.

## What It Does Not Justify

This article should **not** be read as support for:

- building a wallet company
- becoming a broad autonomous-finance operating system
- adding simulation just because simulation is adjacent
- turning Augur into generic agent infrastructure

The article supports specialist services with clear mechanical value.

That is much closer to Augur's current wedge than to a platform sprawl move.

## Relationship To Existing Strategy Docs

This memo does not replace the current product-direction memo.

Use the docs this way:

- `docs/PRODUCT_WEDGE_MEMO.md`: why the narrow wedge is defensible
- `docs/PRODUCT_DIRECTION_UPDATE.md`: the current strategy call
- `docs/agent-economy-primer.md`: how the payment/discovery stack works
- `docs/SELLING_TO_AGENTS_MEMO.md`: why agent-native service economics favor a stronger, more decision-native Augur

## Practical Takeaway

The article makes me more confident in the market for Augur, but less forgiving about weak product shape.

It says the market exists for agent-native services like Augur.

It also says Augur only really wins if it becomes:

- narrow
- reliable
- machine-discoverable
- protocol-priced
- faster and cheaper than self-computation
- trusted enough to sit in front of money-moving actions

That is the standard.
