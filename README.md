# Augur

> Base mainnet smart contract bytecode risk scoring API for agents and the developers building them.

**Live:** https://augurrisk.com  
**Proof report:** https://augurrisk.com/reports/base-bluechip-bytecode-snapshot  
**Payment guide:** https://augurrisk.com/how-payment-works  
**MCP setup:** https://augurrisk.com/mcp  
**Agent registry:** https://8004scan.io/agents/base/19074

## What Augur Does

Augur accepts a Base mainnet contract address and returns a structured 0-100 bytecode risk score with findings.

The product is designed for agent workflows that need a fast screen before interacting with a contract. It is a deterministic bytecode analysis service, not a full security audit or guarantee.

## Why It Exists

Augur is built for machine-native usage:

- no API key
- no signup
- pay per request via x402 in USDC on Base

That makes it usable by agents and automated workflows that cannot rely on traditional account-based APIs.

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
  "score": 60,
  "level": "high",
  "bytecode_size": 1485,
  "findings": [
    {
      "detector": "proxy",
      "severity": "medium",
      "title": "EIP-1967 Proxy Detected",
      "description": "Contract uses the EIP-1967 transparent proxy pattern. Logic resides in a separate implementation contract that can be upgraded.",
      "points": 20
    }
  ],
  "category_scores": {
    "proxy": 20
  },
  "implementation": {
    "address": "0x2cE6409Bc2Ff3E36834E44e15bbE83e4aD02d779",
    "bytecode_size": 24576,
    "findings": [],
    "category_scores": {}
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

Augur scores contracts across these high-level categories:

- proxy behavior
- reentrancy risk
- selfdestruct capability
- honeypot-style transfer restrictions
- hidden mint capability
- fee manipulation
- delegatecall usage
- deployer reputation

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
