# Augur (risk-api)

Smart contract risk scoring API on Base, sold agent-to-agent via [x402](https://x402.org).

**Live:** https://risk-api.life.conway.tech

## What it does

Analyzes EVM smart contract bytecode with 8 detectors:

- **Proxy detection** — EIP-1967, EIP-1822, OpenZeppelin slots; auto-resolves implementation (1 hop)
- **Reentrancy** — external calls before state changes
- **Selfdestruct** — contract can be destroyed
- **Honeypot patterns** — transfer restrictions and traps
- **Hidden mint** — unauthorized token minting capability
- **Fee manipulation** — dynamic fee extraction
- **Delegatecall** — arbitrary code execution risk
- **Deployer reputation** — on-chain deployer history via Basescan

Returns a composite **0-100 risk score** with severity levels: `safe` (0-15), `low` (16-35), `medium` (36-55), `high` (56-75), `critical` (76-100).

## Agent integration

The `/analyze` endpoint is behind an [x402](https://x402.org) paywall. Agents pay $0.10 USDC on Base per call — no API keys, no signup.

### Flow

```
1. GET /analyze?address=0x...
   → 402 Payment Required (with payment details in response)

2. Agent constructs x402 payment using USDC on Base

3. GET /analyze?address=0x...
   Header: PAYMENT-SIGNATURE: <x402 payment proof>
   → 200 OK (risk analysis result)
```

### Example request

```bash
# Without payment (returns 402 with payment requirements)
curl https://risk-api.life.conway.tech/analyze?address=0x4200000000000000000000000000000000000006
```

### Example response (200)

```json
{
  "address": "0x4200000000000000000000000000000000000006",
  "score": 0,
  "level": "safe",
  "bytecode_size": 2438,
  "findings": [],
  "category_scores": {
    "access_control": 0,
    "code_quality": 0,
    "external_calls": 0,
    "value_extraction": 0
  }
}
```

### Proxy contracts

Proxy contracts include a nested `implementation` object with the resolved implementation's findings:

```json
{
  "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
  "score": 60,
  "level": "high",
  "findings": [...],
  "implementation": {
    "address": "0x2ce6...",
    "bytecode_size": 12847,
    "findings": [...],
    "category_scores": {...}
  }
}
```

## x402 payment details

| Field | Value |
|-------|-------|
| Network | Base mainnet (`eip155:8453`) |
| Price | $0.10 USDC |
| Pay to | `0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891` |
| Facilitator | Mogami (`https://v2.facilitator.mogami.tech`) |
| Payment header | `PAYMENT-SIGNATURE` |

## Discovery endpoints

All free (no x402 payment required):

| Endpoint | Description |
|----------|-------------|
| [`/health`](https://risk-api.life.conway.tech/health) | Health check |
| [`/agent-metadata.json`](https://risk-api.life.conway.tech/agent-metadata.json) | ERC-8004 agent metadata |
| [`/openapi.json`](https://risk-api.life.conway.tech/openapi.json) | OpenAPI 3.0 specification |
| [`/.well-known/ai-plugin.json`](https://risk-api.life.conway.tech/.well-known/ai-plugin.json) | AI plugin manifest |
| [`/avatar.png`](https://risk-api.life.conway.tech/avatar.png) | Agent avatar image |
| [`/dashboard`](https://risk-api.life.conway.tech/dashboard) | Analytics dashboard |

## Registry listings

- [ERC-8004 #19074](https://8004scan.io/agents/base/19074) — on-chain agent registry on Base
- [x402.jobs](https://x402.jobs/resources/risk-api-life-conway-tech/smart-contract-risk-scorer-base) — x402 resource directory
- [MoltMart](https://moltmart.app) — AI agent marketplace
- [Work402](https://work402.com) — agent hiring marketplace (testnet)

See [`docs/REGISTRATIONS.md`](docs/REGISTRATIONS.md) for the full tracker including pending registrations, discovery endpoints, and IPFS pinning workflow.

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## License

MIT
