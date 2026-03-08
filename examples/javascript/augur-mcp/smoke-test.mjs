import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const DEFAULT_ADDRESS = process.env.AUGUR_ADDRESS || "0x4200000000000000000000000000000000000006";

function hasFlag(flag) {
  return process.argv.includes(flag);
}

async function main() {
  const paid = hasFlag("--paid");
  const transport = new StdioClientTransport({
    command: process.execPath,
    args: ["index.mjs"],
    cwd: process.cwd(),
    env: process.env,
  });

  const client = new Client({
    name: "augur-mcp-smoke-test",
    version: "1.0.0",
  });

  await client.connect(transport);

  const tools = await client.listTools();
  const toolNames = tools.tools.map(tool => tool.name).sort();
  console.log("tools", JSON.stringify(toolNames));

  const description = await client.callTool({
    name: "describe_augur_service",
    arguments: {},
  });
  console.log("describe_augur_service", JSON.stringify(description.structuredContent));

  if (paid) {
    const analysis = await client.callTool({
      name: "analyze_base_contract_risk",
      arguments: { address: DEFAULT_ADDRESS },
    });
    console.log("analyze_base_contract_risk", JSON.stringify(analysis.structuredContent));
  }

  await client.close();
}

main().catch(error => {
  console.error(error);
  process.exit(1);
});
