# Augur

> Deterministic Base contract admission control for agents. x402-paid API access for fast pre-transaction decisions.

**Live:** https://augurrisk.com  
**Proof report:** https://augurrisk.com/reports/base-bluechip-bytecode-snapshot  
**Payment guide:** https://augurrisk.com/how-payment-works  
**MCP setup:** https://augurrisk.com/mcp  
**Agent registry:** https://8004scan.io/agents/base/19074

## What Augur Does

Augur accepts a Base mainnet contract address and returns a default first-pass decision, a machine-readable policy recommendation, supporting findings, and a structured 0-100 bytecode score.

The product is designed for agent workflows that need a fast deterministic contract gate before interacting with a contract. It is a deterministic bytecode analysis service, not a full security audit, runtime monitor, or guarantee.

Augur focuses on one job:

- one paid endpoint
- one contract check per request
- 8 deterministic detectors in one response

Screen Base contracts before your agent buys, routes funds, approves, pays, or interacts. If a contract still needs deeper analysis after that first pass, escalate it to a heavier tool.

## Common Use Cases

- Screen a token contract before a trading agent buys or quotes it.
- Screen a contract before a routing or treasury agent sends funds to it.
- Screen a contract before an approval flow grants allowances or permissions.
- Screen a contract before a listing, indexing, or monitoring workflow treats it as acceptable.

## Why It Fits Agents

Augur fits agent workflows because:

- no API key
- no signup
- pay per request via x402 in USDC on Base

That makes it easy to call from agents and automated workflows that do not want account-based API setup.

## Fastest Paid Call

Python quickstart:

```bash
pip install -e ".[dev]"
export CLIENT_PRIVATE_KEY="0xYOUR_PRIVATE_KEY"
python scripts/test_x402_client.py --dry-run
python scripts/test_x402_client.py
```

PowerShell:

```powershell
$env:CLIENT_PRIVATE_KEY = "0xYOUR_PRIVATE_KEY"
python scripts/test_x402_client.py --dry-run
python scripts/test_x402_client.py
```

Node example:

```bash
cd examples/javascript/augur-paid-call
npm install
npm run dry-run
```

For the protocol flow without code, use the live guide at `https://augurrisk.com/how-payment-works`.

## MCP Setup

Augur also ships a working local stdio MCP wrapper for Claude Desktop, Codex-compatible clients, and other MCP tooling.

Public setup page:

`https://augurrisk.com/mcp`

Fastest install path:

```bash
npx -y augurrisk-mcp
```

Published package:

`https://www.npmjs.com/package/augurrisk-mcp`

## API

### `GET /analyze?address={base_contract_address}`

Price: `$0.10` per call via x402 in USDC on Base.

If the address is missing, malformed, or has no bytecode on Base, Augur returns `422` before payment is processed.

Example response:

```json
{
  "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
  "score": 50,
  "level": "medium",
  "decision": "manual_review",
  "recommended_policy": {
    "action": "manual_review",
    "summary": "Escalate before interaction. Use a human review step or a heavier tool before the workflow proceeds.",
    "reason_codes": [
      "elevated_risk_score",
      "upgradeable_proxy",
      "selfdestruct_signal",
      "delegatecall_surface"
    ]
  },
  "bytecode_size": 234,
  "findings": [
    {
      "detector": "delegatecall",
      "severity": "info",
      "title": "DELEGATECALL in proxy pattern",
      "description": "Contract uses DELEGATECALL with standard proxy storage slots (EIP-1967/1822). This is expected proxy behavior.",
      "points": 10
    },
    {
      "detector": "proxy",
      "severity": "info",
      "title": "Proxy contract detected",
      "description": "Contract uses standard proxy storage slots (EIP-1967 or EIP-1822). The implementation contract should also be analyzed.",
      "points": 10
    },
    {
      "detector": "impl_selfdestruct",
      "severity": "critical",
      "title": "SELFDESTRUCT opcode found",
      "description": "Contract contains SELFDESTRUCT which allows the owner to destroy the contract and drain all funds.",
      "points": 30
    }
  ],
  "category_scores": {
    "delegatecall": 10,
    "proxy": 10,
    "impl_selfdestruct": 30
  },
  "implementation": {
    "address": "0x2cE6409Bc2Ff3E36834E44e15bbE83e4aD02d779",
    "bytecode_size": 201,
    "findings": [
      {
        "detector": "impl_selfdestruct",
        "severity": "critical",
        "title": "SELFDESTRUCT opcode found",
        "description": "Contract contains SELFDESTRUCT which allows the owner to destroy the contract and drain all funds.",
        "points": 30
      }
    ],
    "category_scores": {
      "selfdestruct": 30
    }
  }
}
```

Risk levels:

| Score | Level |
|-------|-------|
| 0-15 | safe |
| 16-35 | low |
| 36-55 | medium |
| 56-75 | high |
| 76-100 | critical |

`safe` means no major bytecode-level risk signals were detected in that scan. It does not guarantee the contract is safe.

Default first-pass policy actions:

| Condition | Decision |
|-------|----------|
| `safe` with no reason codes | allow |
| `low`, or `safe` with non-blocking signals such as fee controls or suspicious selectors | warn |
| `medium`, unresolved proxy logic, raw `DELEGATECALL`, or `SELFDESTRUCT` | manual_review |
| `high` / `critical`, hidden mint, or honeypot signals | block |

## Public Pages And Machine Docs

- `/` landing page
- `/skill.md` agent-first integration doc
- `/how-payment-works` payment explainer
- `/mcp` MCP setup page
- `/reports/base-bluechip-bytecode-snapshot` proof-of-work report
- `/honeypot-detection-api`
- `/proxy-risk-api`
- `/deployer-reputation-api`
- `/openapi.json`
- `/llms.txt`
- `/llms-full.txt`
- `/.well-known/x402`
- `/.well-known/agent-card.json`
- `/agent-metadata.json`

## Detector Coverage

Augur's narrow admission-control product currently evaluates contracts across these high-level categories:

- proxy behavior
- reentrancy risk
- selfdestruct capability
- honeypot-style transfer restrictions
- hidden mint capability
- fee manipulation
- delegatecall usage
- deployer reputation

These detectors are not separate products. They are the current deterministic checks that feed the same paid `/analyze` screening workflow.

For proxy contracts, the response can also include nested `implementation` analysis.

## Examples

- Python paid-call example: [`scripts/test_x402_client.py`](scripts/test_x402_client.py)
- JavaScript paid-call example: [`examples/javascript/augur-paid-call`](examples/javascript/augur-paid-call)
- MCP wrapper package: [`augurrisk-mcp`](https://www.npmjs.com/package/augurrisk-mcp)
- MCP wrapper source: [`examples/javascript/augur-mcp`](examples/javascript/augur-mcp)
- Public MCP install page: [`/mcp`](https://augurrisk.com/mcp)

## Minimal Local Development

```bash
pip install -e ".[dev]"
flask --app risk_api.app:create_app run
python -m pytest tests/test_app.py -q
```

## Deploy

Push to `master` to trigger the Fly deploy workflow, or deploy manually with:

```bash
fly deploy
```

## License

MIT
