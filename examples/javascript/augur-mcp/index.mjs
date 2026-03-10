#!/usr/bin/env node

import { config } from "dotenv";
import { wrapFetchWithPaymentFromConfig } from "@x402/fetch";
import { ExactEvmScheme } from "@x402/evm";
import { privateKeyToAccount } from "viem/accounts";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { pathToFileURL } from "node:url";
import { z } from "zod";

config();

const DEFAULT_URL = "https://augurrisk.com";
const DEFAULT_ADDRESS = "0x4200000000000000000000000000000000000006";
const ADDRESS_RE = /^0x[0-9a-fA-F]{40}$/;

function normalizeBaseUrl(url) {
  return url.replace(/\/$/, "");
}

function buildAnalyzeUrl(baseUrl, address) {
  const endpoint = new URL("/analyze", normalizeBaseUrl(baseUrl));
  endpoint.searchParams.set("address", address);
  return endpoint.toString();
}

function createPaidFetch(privateKey) {
  const signer = privateKeyToAccount(privateKey);
  return {
    paidFetch: wrapFetchWithPaymentFromConfig(fetch, {
      schemes: [
        {
          network: "eip155:8453",
          client: new ExactEvmScheme(signer),
        },
      ],
    }),
  };
}

function summarizeFindings(findings) {
  if (!Array.isArray(findings) || findings.length === 0) {
    return "No findings reported.";
  }

  return findings
    .slice(0, 6)
    .map(finding => {
      const title = finding?.title ?? finding?.detector ?? "finding";
      const severity = finding?.severity ?? "unknown";
      const points = finding?.points ?? 0;
      return `- ${title} [${severity}, ${points} pts]`;
    })
    .join("\n");
}

function jsonText(value) {
  return JSON.stringify(value, null, 2);
}

async function callAugur(paidFetch, baseUrl, address) {
  const response = await paidFetch(buildAnalyzeUrl(baseUrl, address), { method: "GET" });
  const data = await response.json();

  if (!response.ok) {
    const error = new Error(
      typeof data?.error === "string"
        ? data.error
        : `Augur returned HTTP ${response.status}.`,
    );
    error.name = "AugurApiError";
    error.status = response.status;
    error.body = data;
    throw error;
  }

  if (
    typeof data?.address !== "string"
    || typeof data?.score !== "number"
    || typeof data?.level !== "string"
  ) {
    const error = new Error("Augur returned an unexpected success payload.");
    error.name = "AugurResponseShapeError";
    error.body = data;
    throw error;
  }

  return data;
}

export async function main() {
  const privateKey = process.env.CLIENT_PRIVATE_KEY;
  if (!privateKey) {
    throw new Error("Set CLIENT_PRIVATE_KEY before starting the Augur MCP server.");
  }

  const baseUrl = normalizeBaseUrl(process.env.AUGUR_URL || DEFAULT_URL);
  const defaultAddress = process.env.AUGUR_ADDRESS || DEFAULT_ADDRESS;
  const { paidFetch } = createPaidFetch(privateKey);

  const server = new McpServer({
    name: "augur-mcp",
    version: "1.0.0",
  });

  server.registerTool(
    "analyze_base_contract_risk",
    {
      title: "Analyze Base Contract Risk",
      description:
        "Pay Augur via x402 and return a bytecode-level risk score for a Base mainnet contract.",
      inputSchema: {
        address: z
          .string()
          .regex(ADDRESS_RE, "Expected a 0x-prefixed 40-byte hex address")
          .default(defaultAddress),
      },
      outputSchema: {
        address: z.string(),
        score: z.number(),
        level: z.string(),
        bytecode_size: z.number().optional(),
        findings: z.array(z.unknown()).optional(),
        category_scores: z.record(z.number()).optional(),
        implementation: z.unknown().optional(),
      },
    },
    async ({ address }) => {
      try {
        const analysis = await callAugur(paidFetch, baseUrl, address);
        const findingsSummary = summarizeFindings(analysis.findings);
        const text = [
          `Augur risk score for ${analysis.address}: ${analysis.score}/100 (${analysis.level}).`,
          findingsSummary,
        ].join("\n");

        return {
          content: [{ type: "text", text }],
          structuredContent: analysis,
        };
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        const status =
          error && typeof error === "object" && "status" in error
            ? error.status
            : null;
        const body =
          error && typeof error === "object" && "body" in error
            ? error.body
            : null;
        return {
          content: [
            {
              type: "text",
              text:
                typeof status === "number"
                  ? `Augur MCP tool failed with HTTP ${status}: ${message}`
                  : `Augur MCP tool failed: ${message}`,
            },
          ],
          structuredContent: {
            base_url: baseUrl,
            attempted_address: address,
            status,
            error: message,
            body,
          },
          isError: true,
        };
      }
    },
  );

  server.registerTool(
    "describe_augur_service",
    {
      title: "Describe Augur Service",
      description: "Return the MCP wrapper's current Augur configuration and payment path.",
      inputSchema: {},
      outputSchema: {
        base_url: z.string(),
        default_address: z.string(),
        payment_network: z.string(),
        payment_asset: z.string(),
        pricing: z.string(),
        wallet_required: z.boolean(),
      },
    },
    async () => {
      const details = {
        base_url: baseUrl,
        default_address: defaultAddress,
        payment_network: "Base mainnet (eip155:8453)",
        payment_asset: "USDC",
        pricing: "$0.10 per /analyze call via x402",
        wallet_required: true,
      };

      return {
        content: [{ type: "text", text: jsonText(details) }],
        structuredContent: details,
      };
    },
  );

  const transport = new StdioServerTransport();
  await server.connect(transport);
}

const isEntrypoint = process.argv[1]
  && pathToFileURL(process.argv[1]).href === import.meta.url;

if (isEntrypoint) {
  main().catch(error => {
    console.error(error);
    process.exit(1);
  });
}
