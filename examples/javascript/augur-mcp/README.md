# Augur MCP Server

Local stdio MCP server that pays Augur over x402 and exposes Augur's paid Base contract risk API as MCP tools.

This package keeps Augur itself as the canonical HTTP product at `https://augurrisk.com` and uses a local MCP bridge so wallet signing stays on the operator's machine.

## What You Get

- local stdio MCP server
- x402 payment stays client-side
- no API key or signup for Augur itself
- two tools out of the box: `analyze_base_contract_risk` and `describe_augur_service`

## Package Surface

Package name:

```bash
augurrisk-mcp
```

Fastest install path:

```bash
npx -y augurrisk-mcp
```

## Local Install

```bash
cd examples/javascript/augur-mcp
npm install
cp .env.example .env
```

Required env:

- `CLIENT_PRIVATE_KEY`: wallet key used for the x402 payment handshake

Optional env:

- `AUGUR_URL`: defaults to `https://augurrisk.com`
- `AUGUR_ADDRESS`: defaults to `0x4200000000000000000000000000000000000006`

## Run

```bash
npm start
```

The server communicates over stdio, which is the expected transport for local MCP clients such as Claude Desktop and Codex-compatible clients.

## Smoke Test

Verify the server starts and the MCP tool list is reachable:

```bash
npm run smoke
```

Verify one real paid MCP tool call end-to-end:

```bash
npm run smoke -- --paid
```

Preview the publish payload:

```bash
npm run pack:preview
```

## Tools

### `analyze_base_contract_risk`

Inputs:

- `address`: Base mainnet contract address

Behavior:

- calls Augur's paid `/analyze` endpoint
- handles the x402 payment handshake locally with your wallet
- returns both text output and structured JSON content

### `describe_augur_service`

Returns the configured Augur base URL, default example address, and payment path details without exposing the local payer wallet address.

## Claude Desktop Wiring

### Current Local-Repo Setup

```json
{
  "mcpServers": {
    "augur": {
      "command": "npm",
      "args": ["start", "--prefix", "/absolute/path/to/risk-api/examples/javascript/augur-mcp"],
      "env": {
        "CLIENT_PRIVATE_KEY": "0xYOUR_PRIVATE_KEY",
        "AUGUR_URL": "https://augurrisk.com"
      }
    }
  }
}
```

### Package-Based Setup After Publish

```json
{
  "mcpServers": {
    "augur": {
      "command": "npx",
      "args": ["-y", "augurrisk-mcp"],
      "env": {
        "CLIENT_PRIVATE_KEY": "0xYOUR_PRIVATE_KEY",
        "AUGUR_URL": "https://augurrisk.com"
      }
    }
  }
}
```

If you prefer not to place the private key directly in the Claude config, start the server from a shell where `CLIENT_PRIVATE_KEY` is already set.

On Windows, Claude Desktop config typically lives at:

```text
%APPDATA%\Claude\claude_desktop_config.json
```

Example Windows entry for this repo:

```json
{
  "mcpServers": {
    "augur": {
      "command": "npm",
      "args": [
        "start",
        "--prefix",
        "C:\\Users\\justi\\dev\\risk-api\\examples\\javascript\\augur-mcp"
      ],
      "env": {
        "CLIENT_PRIVATE_KEY": "0xYOUR_PRIVATE_KEY",
        "AUGUR_URL": "https://augurrisk.com",
        "AUGUR_ADDRESS": "0x4200000000000000000000000000000000000006"
      }
    }
  }
}
```
