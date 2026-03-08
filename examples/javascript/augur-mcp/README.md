# Augur MCP Server Example

Local stdio MCP server that pays Augur over x402 and exposes the paid API as MCP tools.

This is the minimum viable MCP packaging path for Augur:

- keep Augur itself as the canonical paid HTTP API at `https://augurrisk.com`
- run the MCP bridge locally so wallet signing stays on the operator's machine
- expose one MCP tool that pays Augur and returns structured risk results

## Install

```bash
cd examples/javascript/augur-mcp
npm install
```

## Configure

1. Copy `.env.example` to `.env`
2. Set `CLIENT_PRIVATE_KEY`

Optional overrides:

- `AUGUR_URL` defaults to `https://augurrisk.com`
- `AUGUR_ADDRESS` defaults to `0x4200000000000000000000000000000000000006`

## Run

```bash
npm start
```

The server communicates over stdio, which is the expected transport for local MCP clients such as Claude Desktop.

## Smoke Test

This verifies the server starts and the MCP tool list is reachable from the official SDK client:

```bash
npm run smoke
```

To verify one real paid MCP tool call end-to-end:

```bash
npm run smoke -- --paid
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

Add a local MCP server entry similar to:

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
