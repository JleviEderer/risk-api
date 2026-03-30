# Augur Product Direction Update

> Date: 2026-03-19
> Context: follow-up to `docs/PRODUCT_WEDGE_MEMO.md` after reviewing recent agent-market signals from X bookmarks and pressure-testing Augur's current product shape. For an external market-read that supports this direction, also read `docs/SELLING_TO_AGENTS_MEMO.md`.

## Bottom Line

Do not pivot away from Augur's contract screening engine.

Do not freeze at the current product shape either.

The right move is:

- keep the deterministic Base contract screening engine
- keep the current policy output layer
- move the product one step closer to the moment of action
- position Augur as `pre-transaction contract admission control for agents on Base`

The core is still right. The main risk is stopping one layer too early.

## What Changed In This Read

The earlier wedge memo already argued for `Base contract admission control for agents`.

This update sharpens that into a more specific product call:

- the market signal is strongest around agents with wallets, budgets, spend controls, and permissions
- the strongest pull is not toward raw contract scoring
- the strongest pull is toward products that directly constrain or govern action

That does **not** mean Augur should become a wallet, a card product, or a broad agent platform.

It means Augur should become more clearly usable as the decision layer that those systems call before acting.

## What The Bookmark Review Validated

Recent bookmarks repeatedly pointed to the same pattern:

- agents are getting wallets, budgets, cards, and payment ability
- once agents can spend or move money, people immediately want limits and controls
- trust is earned through rigor, determinism, auditability, and least-privilege design
- products closer to enforcement are seeing stronger pull than products that only generate analysis

Representative examples from the review:

- Ramp framed agent spending around spend limits, merchant controls, and visibility
- Slash framed agent payments around controls inside the workflow
- Aaron Levie highlighted agents with budgets paying for APIs and data inside a task flow
- Brian Armstrong pointed to a near future with more agents than humans making transactions
- Anthropic highlighted monitoring as autonomy rises
- Elvis Sun emphasized least privilege, billing caps, sandboxing, and audit trails
- Austen Allred emphasized deterministic quality gates agents cannot bypass
- FundamentEdge emphasized rigor over speed

The practical read is simple:

> A fast, deterministic, machine-readable "should this agent touch this contract?" check fits the emerging market.

## What This Means For Augur

Augur is not disproved.

Augur is validated as infrastructure, but only partly validated as the end product in its current form.

Today Augur is strongest as:

- a deterministic contract screening engine
- a first-pass policy layer
- a cheap pre-action check

But the strongest product shape is not:

- `look up risk on this contract`

It is:

- `given the action this agent is about to take, should the system proceed`

That is the difference between:

- screening as information
- screening as admission control

## Current State Vs Next Step

### What Augur already does

Augur has already moved beyond pure scoring.

The current product now returns:

- `decision`
- `recommended_policy`
- `allow`, `warn`, `manual_review`, or `block`

The public framing is also already close to the right use case:

- screen Base contracts before an agent buys, routes funds, approves, or interacts

That was the right turn.

### What the next step is

The next step is **not** "build a wallet."

The next step is to make Augur usable as the rule a wallet, trading agent, or payment system follows.

That means moving from:

- `what do we think of this contract by default?`

to:

- `given that this agent is about to buy, approve, route, bridge, or pay, should this action proceed?`

This is an action-aware layer on top of the existing contract engine, not a replacement for it.

One plausible narrow extension inside this same wedge is destination-aware preflight.

That means checks such as:

- `deposit`: is this destination consistent with the claimed protocol and chain?
- `approve`: is this spender the one the workflow claims it is?
- `pay` or `route`: is the recipient or target contract structurally the one the agent thinks it is touching?

The key is that this should stay a pre-transaction policy check tied to a claimed action, not drift into a generic scam-scanning product.

## Product Call

The product sentence should now be:

> Augur is the contract admission layer for autonomous finance on Base.

More concretely:

- keep the engine
- stop selling a score as the main thing
- sell a gate
- make policy the main output
- tie the product to real action types like `buy`, `approve`, `route`, `bridge`, or `pay`
- allow narrow destination-aware checks where they sharpen those action decisions, such as validating a claimed protocol + chain + recipient before a deposit or approval proceeds
- stay independent of any one wallet or payment provider

## What Not To Build

Do not respond to this market signal by trying to become:

- a full agent wallet
- a card or spend-management company
- a general finance agent platform
- a broad multi-agent operating system
- a giant all-purpose security suite
- a generic anti-phishing browser or wallet-protection product

Those are larger markets, but worse starting positions from where Augur sits today.

## Moat And Copy Risk

There is real platform risk here.

If Augur becomes just:

- a wallet feature
- a green-light/red-light button inside another product

then large wallet or payment providers can absorb the feature and erase the company.

The safer position is:

- independent decision engine
- narrow category ownership
- multi-surface integration across wallets, trading agents, treasury agents, x402 tools, and internal approval systems

The defensible product is not:

- `agent wallet with built-in contract checks`

The more defensible product is:

- `independent contract policy engine that agent wallets and autonomous finance systems call before acting`

So the right move is:

- go closer to the wallet
- without becoming just a wallet feature

## Trust Implications

This direction raises the bar.

An action-linked product will be more scrutinized than a general analysis API because it sits closer to real money movement.

That is acceptable.

More scrutiny is not a reason to avoid the product if it also makes the product:

- more important
- more embedded
- more likely to be enforced
- more likely to be paid for

Trust should be earned in stages:

1. Start with smaller agent wallets, trading tools, x402 services, and teams already wiring in external checks.
2. Make Augur easy to run in advice mode before blocking mode.
3. Prove the product in public with exact examples, clear rules, known limits, and proof artifacts.
4. Stay narrow enough that the claim is believable.

The key trust bar is not "is Augur magical?"

It is:

- is it good at one narrow job
- does it fail in understandable ways
- does it give clear reasons
- is it conservative when unsure
- can partners test it safely before depending on it

## Product Ladder

### V1: current shape

- contract scoring
- machine-readable findings
- default policy decision
- Base-first deterministic first pass

### V2: next shape

- action-aware admission control on top of the existing engine
- explicit action context such as `approve`, `buy`, `route`, `bridge`, or `pay`
- narrow destination-aware validation where the action depends on trusting the claimed recipient, spender, or protocol endpoint
- policy output phrased as a system decision, not just a contract summary
- easy embed path for wallets, trading agents, and payment systems

### Too far, too early

- full wallet product
- full transaction simulation platform
- broad runtime monitoring suite
- generic autonomous-finance control plane

## Strategic Conclusion

The right answer is not to pivot away from contract screening.

The right answer is to finish the turn that Augur has already started:

- from score to decision
- from decision to enforceable policy
- from contract-centric output to action-aware admission control

So the recommended direction is:

1. Keep the current engine.
2. Keep tightening trust, clarity, and correctness.
3. Make policy the real product surface.
4. Move one step closer to the action point.
5. Stay independent of wallets rather than trying to become one.

If Augur can become the default pre-transaction contract gate that other agent-finance systems call, the product direction is sound.
