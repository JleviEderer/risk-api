import { config } from "dotenv";
import { wrapFetchWithPaymentFromConfig } from "@x402/fetch";
import { ExactEvmScheme } from "@x402/evm";
import { privateKeyToAccount } from "viem/accounts";

config();

const DEFAULT_URL = "https://augurrisk.com";
const DEFAULT_ADDRESS = "0x4200000000000000000000000000000000000006";

function getFlag(name) {
  return process.argv.includes(name);
}

function getArgValue(name, fallback) {
  const prefix = `${name}=`;
  const inline = process.argv.find(arg => arg.startsWith(prefix));
  if (inline) {
    return inline.slice(prefix.length);
  }

  const index = process.argv.indexOf(name);
  if (index !== -1 && process.argv[index + 1]) {
    return process.argv[index + 1];
  }

  return fallback;
}

function buildEndpoint(baseUrl, address) {
  return `${baseUrl.replace(/\/$/, "")}/analyze?address=${address}`;
}

function decodePaymentRequired(header) {
  return JSON.parse(Buffer.from(header, "base64").toString("utf8"));
}

async function runDryRun(endpoint) {
  console.log(`[1] GET ${endpoint}`);
  const response = await fetch(endpoint);
  console.log(`    Status: ${response.status}`);

  if (response.status === 200) {
    console.log("    Endpoint returned 200 without payment. x402 may be disabled.");
    console.log(JSON.stringify(await response.json(), null, 2));
    return;
  }

  if (response.status !== 402) {
    console.error(`    Unexpected status ${response.status}`);
    console.error(await response.text());
    process.exit(1);
  }

  const header = response.headers.get("Payment-Required");
  if (!header) {
    console.error("    Missing Payment-Required header");
    process.exit(1);
  }

  console.log("    Payment requirements:");
  console.log(JSON.stringify(decodePaymentRequired(header), null, 2));
  console.log("\n[dry-run] Stopping before payment.");
}

async function runPaidCall(endpoint, privateKey) {
  const signer = privateKeyToAccount(privateKey);
  const paidFetch = wrapFetchWithPaymentFromConfig(fetch, {
    schemes: [
      {
        network: "eip155:*",
        client: new ExactEvmScheme(signer),
      },
    ],
  });

  console.log(`[1] GET ${endpoint}`);
  console.log(`[2] Paying from wallet ${signer.address}`);

  const response = await paidFetch(endpoint, { method: "GET" });
  console.log(`    Status: ${response.status}`);

  const data = await response.json();
  console.log(JSON.stringify(data, null, 2));
}

async function main() {
  const baseUrl = getArgValue("--url", process.env.AUGUR_URL || DEFAULT_URL);
  const address = getArgValue(
    "--address",
    process.env.AUGUR_ADDRESS || DEFAULT_ADDRESS,
  );
  const dryRun = getFlag("--dry-run");
  const endpoint = buildEndpoint(baseUrl, address);

  if (dryRun) {
    await runDryRun(endpoint);
    return;
  }

  const privateKey = process.env.CLIENT_PRIVATE_KEY;
  if (!privateKey) {
    console.error("Set CLIENT_PRIVATE_KEY or use --dry-run first.");
    process.exit(1);
  }

  await runPaidCall(endpoint, privateKey);
}

main().catch(error => {
  console.error(error?.response?.data?.error ?? error);
  process.exit(1);
});
