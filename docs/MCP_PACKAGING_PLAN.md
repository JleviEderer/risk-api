# MCP Packaging Plan

## Decision

Use a local stdio MCP server in Node.js that acts as an x402-paying client for Augur's existing HTTP API.

Do not build:

- a separate remote MCP service
- a Python-first MCP adapter inside the Flask app
- framework-specific wrappers before the MCP path is working

## Why This Path

1. Augur already has a canonical paid HTTP surface at `https://augurrisk.com/analyze`.
2. x402 payment client examples in this repo already exist in JavaScript and Python, so the MCP bridge should reuse that path rather than duplicate business logic.
3. Coinbase's current x402 MCP guidance uses a local MCP server as a bridge that handles payment client-side.
4. Local stdio transport is the simplest fit for Claude Desktop and similar spawned MCP clients.
5. Keeping signing local avoids pushing wallet secrets into a hosted MCP layer.

## Chosen Shape

- Transport: local stdio MCP server
- Runtime: Node.js
- Payment path: existing Augur x402 HTTP endpoint
- Initial tool surface:
  - `analyze_base_contract_risk`
  - `describe_augur_service`

## File Targets

- `examples/javascript/augur-mcp/package.json`
- `examples/javascript/augur-mcp/index.mjs`
- `examples/javascript/augur-mcp/smoke-test.mjs`
- `examples/javascript/augur-mcp/README.md`
- `README.md`

## Expected UX

1. Developer installs the example dependencies.
2. Developer provides `CLIENT_PRIVATE_KEY`.
3. Claude Desktop or another MCP client spawns the local server over stdio.
4. The model calls `analyze_base_contract_risk`.
5. The MCP server pays Augur over x402 and returns structured risk output.

## Explicit Non-Goals For This Step

- running MCP over a public remote transport
- adding prompts/resources beyond what is needed for tool-first usage
- supporting multiple payment rails
- embedding MCP server code into Flask routes

## Discovery Reality

This local MCP server is not automatically discoverable just because it exists in the repo.

Current practical discovery paths are:

- the public GitHub repo and README
- the live site and docs linking to the repo
- direct outbound sharing with developers using Claude Desktop or similar MCP-capable hosts
- MCP directories that allow open-source local servers to be listed by repo/example

Important constraint:

- Anthropic's current Connectors Directory policy excludes MCP servers that transfer money, cryptocurrency, or execute financial transactions on behalf of users.
- Because Augur's MCP wrapper signs and sends x402 payments to use the paid API, do not assume it is a fit for Anthropic's official directory in its current form.

Practical implication:

- treat this wrapper primarily as a developer-installable MCP example and packaging surface, not as a connector that will automatically gain distribution through Anthropic's official directory.

## Future Expansion Notes

If MCP usage proves valuable, expand in this order:

1. Add richer tool annotations and prompt examples for the current local server.
2. Add more read-only Augur tools around report formatting, detector summaries, or comparison flows.
3. Add install docs for more hosts only after real demand appears.
4. Consider a remote MCP surface only if there is clear user demand and a secure auth/payment story that does not require shipping wallet secrets into a hosted layer.
5. Evaluate directory submissions case-by-case, but only for directories whose policies permit paid or transaction-triggering MCP tools.
