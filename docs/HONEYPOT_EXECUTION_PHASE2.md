# Honeypot Execution Phase 2

## Purpose

This document defines the smallest viable execution-based honeypot expansion for Augur after `G-014`.

Current Augur is a deterministic bytecode risk screen. That remains the core product. Phase 2 adds a narrow execution-based signal for sell-blocking and extreme transfer-tax behavior without turning Augur into a full trading simulator.

## Decision

Do not build broad swap simulation first.

Build a minimal execution layer that:
- simulates one buy path
- simulates one sell path
- estimates transfer restriction or effective tax from the simulated results
- reports the reason a path failed

Everything else stays out of scope until this version proves useful.

## Goals

- Detect obvious sell-blocking behavior that bytecode heuristics can miss.
- Detect extreme effective buy or sell taxes from simulated outcomes.
- Keep the current bytecode score intact and add execution signals alongside it.
- Limit chain, router, and token-type scope so the system stays understandable and testable.

## Non-Goals

- Real transaction execution
- Multi-DEX optimization
- Broad router abstraction across the Base ecosystem
- Full liquidity forensics
- Generic storage-tracing or symbolic execution
- Automatic support for rebasing, fee-on-transfer edge cases, and unusual tokenomics on day one

## Product Shape

Phase 2 should be exposed as one of these:

1. Preferred: a separate endpoint, `GET /analyze-execution?address=...`
2. Acceptable: an opt-in flag on `/analyze`, such as `include_execution=true`

Preferred choice: separate endpoint.

Reason:
- keeps current bytecode service stable
- keeps pricing and latency decisions separate
- avoids conflating heuristic bytecode risk with simulation-based outcomes

## Scope

Initial scope:
- chain: Base mainnet only
- asset type: ERC-20 style tokens only
- routers: one or two common Base routers, explicitly pinned
- path shape: token <-> WETH and token <-> USDC where available
- liquidity source: first supported pool found from the supported router set

Out of scope for v1:
- route aggregation
- multi-hop best execution
- NFT or ERC-1155 behavior
- long-tail DEX support

## Output Shape

The execution result should be returned separately from bytecode scoring.

Suggested response fragment:

```json
{
  "execution": {
    "status": "analyzed",
    "buy_path": {
      "status": "success",
      "router": "uniswap_v3",
      "pair_asset": "WETH",
      "expected_out": "1000000",
      "actual_out": "970000",
      "effective_tax_bps": 300
    },
    "sell_path": {
      "status": "blocked",
      "router": "uniswap_v3",
      "pair_asset": "WETH",
      "failure_reason": "sell_revert"
    },
    "signals": [
      "sell_blocked",
      "extreme_sell_tax"
    ],
    "summary": "Sell path reverted while buy path succeeded."
  }
}
```

## Failure Taxonomy

Keep the failure taxonomy explicit and machine-readable.

Suggested values:
- `no_supported_pool`
- `router_not_supported`
- `quote_failed`
- `buy_revert`
- `sell_revert`
- `buy_slippage_exceeded`
- `sell_slippage_exceeded`
- `insufficient_liquidity`
- `tax_estimate_unreliable`
- `token_behavior_unsupported`
- `simulation_error`

Important rule:
- distinguish "could not analyze" from "analyzed and found no issue"

## Simulation Flow

### Buy Path

1. Confirm the token has bytecode and looks like an ERC-20 candidate.
2. Check for a supported pool against WETH, then USDC.
3. Simulate a small buy using `eth_call` through the chosen router or quoter path.
4. Record expected output and actual received amount when the protocol supports both.
5. Estimate effective buy tax or transfer loss.

### Sell Path

1. Use the bought amount or a pinned nominal token amount.
2. Simulate approval if the router path needs it.
3. Simulate a sell back through the same supported router.
4. Record whether the sell path succeeds, reverts, or returns materially less than expected.
5. Estimate effective sell tax or classify the sell as blocked.

## Scoring Integration

Do not collapse the execution result blindly into the current 0-100 score.

Recommended approach:
- keep `score` as the bytecode score
- add `execution` as a parallel section
- optionally add a separate `execution_risk` bucket later

Only after real usage should Augur consider a composite score such as:
- bytecode score
- execution outcome severity
- confidence level of the execution analysis

## Confidence Rules

Execution output should carry confidence metadata.

Examples:
- `high`: buy and sell both simulated on a supported router with stable quotes
- `medium`: only one side simulated cleanly, or tax estimate has caveats
- `low`: analysis inconclusive because the token behavior or pool shape is unsupported

Never present low-confidence execution analysis as definitive honeypot proof.

## Testing Strategy

Build tests in layers.

### Unit

- router-selection logic
- failure taxonomy mapping
- tax calculation helpers
- response-shape and confidence classification

### Fixture-Based Integration

Use a pinned set of known Base contracts covering:
- normal token with tradable buy and sell
- token with blacklist or transfer restriction signals
- token with high fee behavior
- token with no supported pool
- proxy token

### Report Harness

Add one small report-generation harness that:
- calls the real API surface intended for G-014
- stores the exact addresses used
- stores the JSON output used in the report
- fails if the pipeline accidentally bypasses route-level validation

## Rollout Plan

### Phase 0

- publish `G-014` using the current bytecode product honestly
- do not claim definitive honeypot detection

### Phase 1

- implement the execution endpoint behind a feature flag
- support one router family only
- return raw execution results without score fusion

### Phase 2

- add a second supported router if the first implementation proves useful
- refine tax and block classifications using observed results

### Phase 3

- decide whether execution analysis should become a paid default or remain opt-in

## What Not To Build Yet

Do not build these before the minimal path exists and shows value:
- generic multi-router swap engine
- automatic route search
- liquidity-state analytics dashboard
- storage-diff or trace-heavy execution analysis
- cross-chain or multi-network support

## Exit Criteria

Phase 2 is successful when:
- Augur can identify at least one real sell-blocked token case that the bytecode path alone would understate
- the execution result is explainable in plain English
- latency and complexity remain acceptable for a paid API
- the service claims stay narrower than the implementation reality
