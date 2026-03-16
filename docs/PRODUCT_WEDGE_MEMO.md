# Augur Product Wedge Memo

> Date: 2026-03-11

## Bottom Line

Augur should stay a narrow product.

The defensible wedge is:

- `Base contract admission control for agents`
- a deterministic, cheap, policy-ready first pass before an agent buys, routes funds, approves, lists, or integrates with a contract
- a screen for large numbers of Base contracts that decides which ones to allow, warn on, block, or escalate to a deeper tool

Augur should not pivot into a full execution-security platform.

That means:

- no near-term attempt to become Blockaid
- no near-term attempt to become Tenderly
- no near-term attempt to become a broad simulation, monitoring, or wallet-protection suite

The right move is to strengthen the current wedge, not broaden it.

## Why This Is Defensible

### 1. It matches the repo's own research

The LLM discoverability work consistently resolved Augur as:

- Base-only
- deterministic
- bytecode triage
- cheap first-pass screen
- agent-friendly packaging

The research explicitly did **not** support a broad pivot into simulation or a general execution-security stack.

### 2. It fits how agents actually buy risk tooling

A full execution-security stack is usually:

- more expensive
- slower
- heavier to integrate
- harder to explain in policy terms

A pre-interaction admission gate has a simpler buying motion:

- screen many contracts cheaply
- reject obvious or structurally uncomfortable candidates
- escalate only a small subset to more expensive analysis

That is a real workflow, especially for:

- autonomous trading agents
- routing agents
- token listing / index inclusion workflows
- marketplaces or agent registries that need a baseline contract screen

### 3. It gives Augur a clearer category than "smart contract security"

If Augur tries to compete in the broad category, it is compared against incumbents with stronger claims in:

- simulation
- runtime monitoring
- transaction safety
- wallet/session protection
- decompiler-heavy deep review

That is a worse battlefield.

If Augur instead owns:

- `Base contract admission control`
- `deterministic Base contract prefilter`
- `policy-ready bytecode gate for Base agents`

then it can be retrieved and purchased for a narrower, clearer job.

## The Honest Risk

This wedge is only strong if the product is very good at the narrow job.

That means Augur cannot afford to feel:

- noisy on canonical contracts
- repetitive on contract families
- technically correct but operationally unhelpful

The recent paid traffic is a good example.

A real evaluator appears to have:

- started with Base WETH
- then tested multiple Beefy vault contracts

Operationally, Augur passed:

- x402 worked
- the retry loop worked
- the API returned consistent results

Product-wise, the signal was mixed:

- WETH produced a result that can read as surprising or noisy
- multiple Beefy vaults collapsed to nearly identical low-score outputs

That does **not** mean "build simulation."

It means the current admission-gate output is not yet decision-native enough for that evaluator's workflow.

## What Not To Build

Do not broaden the category prematurely.

Avoid near-term roadmap drift into:

- pre-sign transaction simulation
- wallet malware / signature safety
- generalized monitoring and alerting
- cross-chain everything
- broad human security dashboard software

Those markets are real, but they are already occupied and harder to win from Augur's current position.

## What To Build Instead

### 1. Better decision outputs

The most important product expansion is thin, not broad.

Add outputs such as:

- `recommended_policy`
- `decision`: `allow`, `warn`, `block`, `manual_review`
- machine-readable reasons
- more explicit "why escalate" text

This makes Augur more usable without changing the category.

### 2. Better clone / proxy / wrapper interpretation

If several contracts are materially the same wrapper family, Augur should say so clearly.

The output should help the user understand:

- this is a minimal proxy or clone
- the implementation or family is shared
- the result is similar because the relevant logic is shared
- what Augur can and cannot conclude from wrapper-level bytecode alone

That preserves trust while staying narrow.

### 3. Better treatment of canonical blue-chip contracts

If a result on a well-known contract is technically true but easy to read as nonsense, the wedge weakens.

The product does not need a central whitelist.

It does need:

- clearer explanation text
- better severity wording
- more careful framing around findings that often appear on legitimate blue-chip contracts

### 4. Better batch ergonomics

If the wedge is "cheaply screen large numbers of Base contracts," the product should support that directly.

That can mean:

- better bulk-call patterns
- clearer MCP batch workflows
- queue-friendly usage patterns
- stronger examples for screening candidate sets before deeper analysis

### 5. Better source attribution and telemetry

For product learning, Augur needs to know whether usage came from:

- docs
- MCP
- direct script integration
- a proof page
- a third-party registry or directory

That is a telemetry problem, not a strategy problem, but it matters for defending the wedge.

## Moat And Mimicry

This wedge is easier to describe than to own.

That means it is easy to copy the slogan.

It is harder to copy the full product if Augur compounds on:

- fast deterministic scoring that works reliably
- clean machine-readable outputs
- x402 payment with no signup friction
- MCP / OpenAPI / agent-native integration
- strong category ownership around Base contract admission control
- proof artifacts and public examples that make the product legible

So the moat is **not** "nobody can build a prefilter."

The moat is:

- speed of integration
- agent-native packaging
- operational simplicity
- high-trust decision outputs
- owning the narrow category in public retrieval surfaces

This is a distribution-plus-product moat, not a deep algorithmic monopoly.

That is still defendable.

## Revenue Read

As a standalone product category, admission control is usually lower-ticket than a broad execution-security suite.

That is the main weakness of the wedge.

But it also has real strengths:

- easier to try
- easier to buy
- easier to integrate
- easier to price per call
- better fit for high-volume screening

So the question is not "is it higher ACV than a broad security platform?"

It usually is not.

The question is:

- can Augur become the default first paid check before deeper analysis?

If yes, the revenue shape can still be strong because the workflow is:

- high frequency
- naturally API-native
- naturally usage-priced
- upstream of more expensive decisions

That is a credible business if Augur becomes the default first gate for a meaningful slice of Base agent activity.

## Strategic Conclusion

The wedge is defensible.

It is narrower and probably lower-ceiling than a full-stack security platform, but it is also:

- clearer
- more realistic from Augur's current position
- more consistent with the existing product and research
- better matched to x402 and agent-native integration

The right strategy is:

1. Keep Augur narrow.
2. Make the narrow output much more decision-native.
3. Own the phrase `Base contract admission control for agents`.
4. Optimize for high-volume first-pass screening, not deep all-in-one security.
5. Use deeper tools as complements, not enemies.

## Near-Term Product Test

The key test for the wedge is:

> Can an agent or operator cheaply screen a large set of Base contracts and confidently decide which ones to ignore, block, or escalate?

If Augur can do that well, the wedge is real.

If not, broadening the category will not save it.
