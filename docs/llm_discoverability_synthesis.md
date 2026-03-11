# LLM Discoverability Synthesis

Internal research memo based on 12 fresh ChatGPT conversations run on 2026-03-10.

The raw sources are archived locally in `.codex/research.local/llm-discoverability/`.

## Bottom Line

Augur was not surfaced unprompted in any of the 12 blind runs.

That headline still holds.

The more precise read is:

- `0/12` blind runs surfaced Augur unprompted
- `0/10` clean blind runs surfaced Augur unprompted
- 2 runs were methodology-noisy enough that they should not carry the same weight as the cleaner misses:
  - Prompt `9` was contaminated by two merged prompt formulations
  - Prompt `11` drifted into legal contract AI because `contract risk API` was too ambiguous without `smart contract`

After direct inspection, the model was fairly consistent:

- Augur is real, serious, and unusually agent-friendly
- Augur is narrow by design
- Augur reads as a Base-only deterministic bytecode prefilter
- Augur is not read as a standalone execution-time guard

So the current issue is not mainly category confusion after inspection.

The current issue is retrieval and entity resolution before inspection.

## Dataset Notes

- 12 blind prompts were run in fresh chats
- each conversation then included structured follow-up comparison prompts
- the runs CSV now distinguishes `clean`, `ambiguous`, and `contaminated` blind prompts
- the runs CSV also distinguishes generic discoverability misses from `entity_resolution_failure`
- source URLs were only explicitly captured in one transcript; the raw transcripts remain the source of truth

## Main Findings

### 1. Augur is not retrievable in blind discovery

Across all 12 blind runs:

- `Augur mentioned unprompted`: `0/12`
- `Augur top-ranked unprompted`: `0/12`

Across the 10 clean blind runs:

- `Augur mentioned unprompted`: `0/10`
- `Augur top-ranked unprompted`: `0/10`

That is enough to treat blind discoverability as a real problem, not a one-off miss.

### 2. Some of the problem is name resolution, not only category positioning

Two blind runs surfaced a sharper failure mode:

- the model could not confidently verify `Augur Risk` from public sources
- public search appeared to resolve `Augur` to the prediction-market protocol rather than this product

That matters because it suggests two distinct problems:

1. Augur is not a retrieved category winner
2. Augur is sometimes not even resolved as the intended product

This is more actionable than a generic "discoverability" label.

### 3. After inspection, Augur lands in a stable narrow category

When directly compared, ChatGPT repeatedly described Augur as:

- `Base-only`
- `deterministic`
- `bytecode triage`
- `cheap first-pass screen`
- `agent-friendly packaging`
- `serious but narrow`

This is good news.

It means the product is fairly legible once the model is looking at the right site.

### 4. The strongest blind-run pattern is slot ownership by other products

The recurring competitor pattern was fairly stable:

- `GoPlus` owns the broad self-serve screening slot
- `Blockaid` owns the execution-time safety slot
- `Tenderly` owns the simulation primitive slot
- `Dedaub` owns the deeper bytecode/decompiler slot

That suggests the near-term strategic problem is not "become broader at all costs."

It is "win a smaller slot strongly enough that the model retrieves Augur there."

### 5. Packaging is a real strength, but mostly after direct inspection

The repeated positives were:

- no signup
- no API key
- x402 payment
- OpenAPI
- MCP wrapper
- machine-readable docs / metadata

This matters, but the current research suggests packaging is more of a conversion and categorization strength than a blind-discovery strength.

### 6. Missing capability feedback is real, but secondary

The same missing capabilities came up repeatedly in the follow-up comparisons:

1. no pre-sign transaction simulation
2. no broader runtime or interaction-risk layer

That is useful perception research, but it should not be over-read.

The stronger conclusion is not "build simulation next."

The stronger conclusion is:

- once compared directly, the model sees Augur as a prefilter
- broader execution-time tools already own the wider slot
- the next move should reinforce Augur's wedge rather than collapse it into a broad platform build

## Method Notes

Two runs should be treated cautiously in any headline metric:

- Prompt `9`: contaminated by merged prompt text, so it is still informative but not a clean single-prompt test
- Prompt `11`: drifted into legal contract AI, so it is useful as ambiguity evidence but weak as smart-contract discoverability evidence

Those runs do not overturn the headline result.

They do change how strongly specific claims should be made from them.

## What This Means

### Product

The research does not justify a broad product pivot.

It supports:

- keeping Augur as a narrow Base-first contract-admission layer
- making the output more decision-native
- avoiding premature expansion into a general transaction-safety platform

The most plausible near-term product improvement is still a thin decision layer such as:

- `recommended_policy`
- explicit action reasons
- clearer interpretation of what should block, warn, or escalate

### Messaging

The strongest messaging takeaway is to repeat one narrow category phrase much more aggressively.

Candidate positioning:

- `Base contract admission control for agents`
- `deterministic Base contract prefilter`
- `policy-ready bytecode gate for Base agents`

This is stronger than trying to sound adjacent to a broader transaction-security category already owned by others.

### Discoverability

This should be treated as a retrieval and disambiguation project before it is treated as a capability-expansion project.

The next work should likely be:

1. improve entity disambiguation around `Augur Risk` and `augurrisk.com`
2. repeat one narrow category phrase across site copy, metadata, and third-party mentions
3. get Augur cited in third-party pages, ecosystem lists, docs, examples, and directories that LLMs are likely to read
4. rerun the study with cleaner prompt methodology

## Recommended Actions

### 1. Treat this as a retrieval problem before a capability problem

The data does not yet justify a large buildout toward simulation or broad wallet security.

It justifies:

- better entity resolution
- better category ownership
- more third-party retrieval surfaces

### 2. Keep the current wedge, but sharpen it

Suggested direction:

- stay `Base-only`
- stay `deterministic`
- stay `agent-first`
- be explicit that Augur is a first-pass contract admission gate

### 3. Add one thin decision-layer improvement

The best product expansion supported by this research is still a narrow one:

- `recommended_policy`
- machine-readable reasons
- clearer default actions like `allow`, `warn`, `block`, or `manual_review`

That strengthens the current wedge without pretending Augur is already the full execution stack.

### 4. Verify only the competitor claims that matter

You do not need to fact-check every claim in the transcripts.

You do need to verify the claims that affect positioning:

- GoPlus official MCP and Base support
- Blockaid's AI-agent and Base positioning
- Dedaub's Base bytecode/decompiler story

## Most Important Single Takeaway

If ChatGPT is the discovery surface, Augur currently has a retrieval problem before it has a capability problem.

It is a hidden specialist, and in some runs not even a clearly resolved entity.

That is fixable, but the first fix is better retrieval, sharper category ownership, and one more decision-native output layer rather than a broad product pivot.
