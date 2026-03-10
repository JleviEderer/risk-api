"""Static proof-of-work report pages."""

from __future__ import annotations

import json
from html import escape

REPORT_PAGES: dict[str, dict[str, object]] = {
    "/reports/base-bluechip-bytecode-snapshot": {
        "title": "Base Blue-Chip Bytecode Snapshot",
        "meta_description": (
            "Proof-of-work report showing how Augur scores three notable Base "
            "contracts: WETH, USDC, and cbBTC."
        ),
        "eyebrow": "Proof of Work",
        "snapshot_date": "2026-03-09",
        "summary": (
            "This report publishes a point-in-time Augur snapshot on three notable "
            "Base contracts so buyers can inspect exact live-response payloads instead "
            "of marketing claims. The goal is not to call blue-chip assets scams. "
            "The goal is to show what a bytecode-first screen actually surfaces."
        ),
        "methodology": [
            "Contracts were analyzed on 2026-03-09 against Base mainnet using the current Augur engine.",
            "The embedded JSON below is intentionally shaped like the live /analyze response contract.",
            "This is bytecode triage, not a final trust verdict or a substitute for issuer, governance, or audit review.",
            "Future detector changes can move these scores; this page is a snapshot, not a permanent benchmark.",
        ],
        "takeaways": [
            "Augur is sensitive to upgradeability, mint authority, and transfer-guard patterns, even on legitimate widely used assets.",
            "That behavior is useful for agent guardrails because centrally controlled or mutable contracts really do carry code-level powers.",
            "At the same time, the output still needs context. High score does not mean fraud, and low score does not mean audited safety.",
        ],
        "contracts": [
            {
                "name": "Base WETH",
                "snapshot": {
                    "address": "0x4200000000000000000000000000000000000006",
                    "score": 25,
                    "level": "low",
                    "findings": [
                        {
                            "detector": "honeypot",
                            "severity": "high",
                            "title": "Potential honeypot: conditional REVERT in transfer path",
                            "description": (
                                "Contract has transfer functions with conditional REVERT "
                                "patterns that could selectively block token transfers "
                                "for certain addresses."
                            ),
                            "points": 25,
                            "offset": 361,
                        }
                    ],
                    "category_scores": {"honeypot": 25},
                    "bytecode_size": 2041,
                    "implementation": None,
                },
                "interpretation": (
                    "Augur assigns a low score, not a clean zero. That matters because it "
                    "shows the engine is conservative around transfer-path control flow. "
                    "For a blue-chip wrapped asset, this should trigger human review rather "
                    "than automatic rejection."
                ),
            },
            {
                "name": "Base USDC",
                "snapshot": {
                    "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                    "score": 90,
                    "level": "critical",
                    "findings": [
                        {
                            "detector": "delegatecall",
                            "severity": "info",
                            "title": "DELEGATECALL in proxy pattern",
                            "description": (
                                "Contract uses DELEGATECALL with standard proxy storage "
                                "slots (EIP-1967/1822). This is expected proxy behavior."
                            ),
                            "points": 10,
                            "offset": 1325,
                        },
                        {
                            "detector": "proxy",
                            "severity": "info",
                            "title": "Proxy contract detected",
                            "description": (
                                "Contract uses standard proxy storage slots (EIP-1967 or "
                                "EIP-1822). The implementation contract should also be analyzed."
                            ),
                            "points": 10,
                            "offset": None,
                        },
                        {
                            "detector": "impl_delegatecall",
                            "severity": "high",
                            "title": "Raw DELEGATECALL without proxy pattern",
                            "description": (
                                "Contract uses DELEGATECALL without recognized proxy "
                                "storage slots. This could allow arbitrary code execution."
                            ),
                            "points": 15,
                            "offset": 18607,
                        },
                        {
                            "detector": "impl_honeypot",
                            "severity": "high",
                            "title": "Potential honeypot: conditional REVERT in transfer path",
                            "description": (
                                "Contract has transfer functions with conditional REVERT "
                                "patterns that could selectively block token transfers "
                                "for certain addresses."
                            ),
                            "points": 25,
                            "offset": 872,
                        },
                        {
                            "detector": "impl_hidden_mint",
                            "severity": "critical",
                            "title": "Hidden mint capability detected",
                            "description": (
                                "Contract contains mint function selectors "
                                "(mint(address,uint256)) that could allow unlimited token minting."
                            ),
                            "points": 25,
                            "offset": None,
                        },
                    ],
                    "category_scores": {
                        "delegatecall": 10,
                        "proxy": 10,
                        "impl_delegatecall": 15,
                        "impl_honeypot": 25,
                        "impl_hidden_mint": 25,
                        "impl_suspicious_selector": 5,
                    },
                    "bytecode_size": 1852,
                    "implementation": {
                        "address": "0x2ce6311ddae708829bc0784c967b7d77d19fd779",
                        "bytecode_size": 23464,
                        "findings": [
                            {
                                "detector": "impl_delegatecall",
                                "severity": "high",
                                "title": "Raw DELEGATECALL without proxy pattern",
                                "description": (
                                    "Contract uses DELEGATECALL without recognized proxy "
                                    "storage slots. This could allow arbitrary code execution."
                                ),
                                "points": 15,
                                "offset": 18607,
                            },
                            {
                                "detector": "impl_honeypot",
                                "severity": "high",
                                "title": "Potential honeypot: conditional REVERT in transfer path",
                                "description": (
                                    "Contract has transfer functions with conditional REVERT "
                                    "patterns that could selectively block token transfers "
                                    "for certain addresses."
                                ),
                                "points": 25,
                                "offset": 872,
                            },
                            {
                                "detector": "impl_hidden_mint",
                                "severity": "critical",
                                "title": "Hidden mint capability detected",
                                "description": (
                                    "Contract contains mint function selectors "
                                    "(mint(address,uint256)) that could allow unlimited token minting."
                                ),
                                "points": 25,
                                "offset": None,
                            },
                        ],
                        "category_scores": {
                            "delegatecall": 15,
                            "honeypot": 25,
                            "hidden_mint": 25,
                            "suspicious_selector": 5,
                        },
                    },
                },
                "interpretation": (
                    "USDC scores as critical because Augur is measuring bytecode powers, "
                    "not issuer reputation. Upgradeability, delegatecall, and mint-related "
                    "selectors are real control surfaces. For agent policy, that means "
                    "USDC should be treated as centrally managed and mutable, not as an "
                    "immutable ERC-20."
                ),
            },
            {
                "name": "Base cbBTC",
                "snapshot": {
                    "address": "0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf",
                    "score": 75,
                    "level": "high",
                    "findings": [
                        {
                            "detector": "delegatecall",
                            "severity": "info",
                            "title": "DELEGATECALL in proxy pattern",
                            "description": (
                                "Contract uses DELEGATECALL with standard proxy storage "
                                "slots (EIP-1967/1822). This is expected proxy behavior."
                            ),
                            "points": 10,
                            "offset": 1062,
                        },
                        {
                            "detector": "proxy",
                            "severity": "info",
                            "title": "Proxy contract detected",
                            "description": (
                                "Contract uses standard proxy storage slots (EIP-1967 or "
                                "EIP-1822). The implementation contract should also be analyzed."
                            ),
                            "points": 10,
                            "offset": None,
                        },
                        {
                            "detector": "impl_honeypot",
                            "severity": "high",
                            "title": "Potential honeypot: conditional REVERT in transfer path",
                            "description": (
                                "Contract has transfer functions with conditional REVERT "
                                "patterns that could selectively block token transfers "
                                "for certain addresses."
                            ),
                            "points": 25,
                            "offset": 721,
                        },
                        {
                            "detector": "impl_hidden_mint",
                            "severity": "critical",
                            "title": "Hidden mint capability detected",
                            "description": (
                                "Contract contains mint function selectors "
                                "(mint(address,uint256)) that could allow unlimited token minting."
                            ),
                            "points": 25,
                            "offset": None,
                        },
                    ],
                    "category_scores": {
                        "delegatecall": 10,
                        "proxy": 10,
                        "impl_honeypot": 25,
                        "impl_hidden_mint": 25,
                        "impl_suspicious_selector": 5,
                    },
                    "bytecode_size": 1550,
                    "implementation": {
                        "address": "0x7458bfdc30034eb860b265e6068121d18fa5aa72",
                        "bytecode_size": 16328,
                        "findings": [
                            {
                                "detector": "impl_honeypot",
                                "severity": "high",
                                "title": "Potential honeypot: conditional REVERT in transfer path",
                                "description": (
                                    "Contract has transfer functions with conditional REVERT "
                                    "patterns that could selectively block token transfers "
                                    "for certain addresses."
                                ),
                                "points": 25,
                                "offset": 721,
                            },
                            {
                                "detector": "impl_hidden_mint",
                                "severity": "critical",
                                "title": "Hidden mint capability detected",
                                "description": (
                                    "Contract contains mint function selectors "
                                    "(mint(address,uint256)) that could allow unlimited token minting."
                                ),
                                "points": 25,
                                "offset": None,
                            },
                        ],
                        "category_scores": {
                            "honeypot": 25,
                            "hidden_mint": 25,
                            "suspicious_selector": 5,
                        },
                    },
                },
                "interpretation": (
                    "cbBTC lands below USDC but still high for the same structural reason: "
                    "it is an upgradeable, admin-controlled asset rather than an immutable "
                    "token. The report is useful precisely because it separates that code-level "
                    "reality from the market assumption that a known issuer automatically means low technical risk."
                ),
            },
        ],
    }
}


def _score_class(level: str) -> str:
    return {
        "safe": "score-safe",
        "low": "score-low",
        "medium": "score-medium",
        "high": "score-high",
        "critical": "score-critical",
    }.get(level, "score-low")


def render_report_page(base_url: str, path: str) -> str:
    """Render a static proof-of-work report page."""
    report = REPORT_PAGES[path]
    title = str(report["title"])
    meta_description = str(report["meta_description"])
    eyebrow = str(report["eyebrow"])
    snapshot_date = str(report["snapshot_date"])
    summary = str(report["summary"])
    methodology = "\n".join(
        f"<li>{escape(str(item))}</li>" for item in report["methodology"]
    )
    takeaways = "\n".join(
        f"<li>{escape(str(item))}</li>" for item in report["takeaways"]
    )

    contract_sections: list[str] = []
    for contract in report["contracts"]:
        contract_name = str(contract["name"])
        snapshot = dict(contract["snapshot"])
        address = str(snapshot["address"])
        score = int(snapshot["score"])
        level = str(snapshot["level"])
        bytecode_size = int(snapshot["bytecode_size"])
        implementation = snapshot.get("implementation")
        interpretation = str(contract["interpretation"])
        findings = snapshot["findings"]
        finding_items = "\n".join(
            (
                f"<li><strong>{escape(str(finding['title']))}</strong> "
                f"<span class=\"muted\">{escape(str(finding['detector']))} - "
                f"{escape(str(finding['severity']))} - +{int(finding['points'])} points</span><br>"
                f"{escape(str(finding['description']))}</li>"
            )
            for finding in findings
        )
        implementation_html = ""
        if implementation:
            implementation_html = (
                "<p class=\"muted\" style=\"margin-top:8px\">"
                f"Resolved implementation: <code>{escape(str(implementation['address']))}</code>"
                "</p>"
            )

        contract_sections.append(
            f"""
<div class="section">
  <div class="contract-header">
    <div>
      <h2>{escape(contract_name)}</h2>
      <p class="muted"><code>{escape(address)}</code></p>
    </div>
    <div class="score-pill {_score_class(level)}">{escape(level)} - {score}/100</div>
  </div>
  <p class="muted">Bytecode size: {bytecode_size} bytes</p>
  {implementation_html}
  <h3>Key findings</h3>
  <ul>
    {finding_items}
  </ul>
  <p style="margin-top:12px">{escape(interpretation)}</p>
  <h3>Exact snapshot JSON</h3>
  <p class="muted">Snapshot captured on {escape(snapshot_date)}. This block mirrors the live <code>/analyze</code> response shape but is not recomputed on page load.</p>
  <pre>{escape(json.dumps(snapshot, indent=2))}</pre>
</div>"""
        )

    json_ld = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": title,
            "description": meta_description,
            "datePublished": snapshot_date,
            "dateModified": snapshot_date,
            "mainEntityOfPage": f"{base_url}{path}",
            "author": {"@type": "Organization", "name": "Augur"},
        }
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} | Augur</title>
<meta name="description" content="{escape(meta_description)}">
<meta name="robots" content="index, follow">
<meta property="og:title" content="{escape(title)}">
<meta property="og:description" content="{escape(meta_description)}">
<meta property="og:type" content="article">
<meta property="og:url" content="{base_url}{path}">
<meta property="og:image" content="{base_url}/og/base-bluechip-bytecode-snapshot.png">
<link rel="icon" type="image/png" href="{base_url}/favicon.png">
<script type="application/ld+json">{json_ld}</script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  background:#0f1117;color:#e0e0e0;padding:24px;max-width:960px;margin:0 auto;line-height:1.65}}
.topnav{{display:flex;gap:10px;justify-content:flex-end;flex-wrap:wrap;margin-bottom:18px}}
.topnav a{{display:inline-block;background:#1a1d29;border:1px solid #2d3148;border-radius:999px;
  padding:6px 12px;color:#90cdf4;text-decoration:none;font-size:.82rem;transition:border-color .2s}}
.topnav a:hover{{border-color:#63b3ed}}
a{{color:#f6ad55}}
a:hover{{color:#fbd38d}}
.eyebrow{{display:inline-block;background:#1a365d;color:#63b3ed;padding:4px 12px;border-radius:6px;font-size:.85rem;margin-bottom:16px}}
h1{{font-size:1.95rem;color:#e2e8f0;margin-bottom:10px;font-weight:600}}
h2{{font-size:1.15rem;color:#e2e8f0;margin-bottom:8px;font-weight:600}}
h3{{font-size:1rem;color:#a0aec0;margin:18px 0 10px;font-weight:500}}
p{{margin-bottom:10px}}
ul{{margin:8px 0 0 18px}}
code{{background:#0f1117;border:1px solid #2d3148;border-radius:4px;padding:2px 6px}}
pre{{background:#0f1117;border:1px solid #2d3148;border-radius:6px;padding:14px;overflow-x:auto;font-size:.82rem;color:#68d391;margin-top:8px}}
.section{{background:#1a1d29;border:1px solid #2d3148;border-radius:10px;padding:20px;margin-bottom:16px}}
.muted{{color:#718096}}
.contract-header{{display:flex;gap:12px;justify-content:space-between;align-items:flex-start;flex-wrap:wrap}}
.score-pill{{border-radius:999px;padding:8px 12px;font-size:.85rem;font-weight:600;text-transform:uppercase;letter-spacing:.03em}}
.score-safe{{background:#123524;color:#68d391}}
.score-low{{background:#2a2f14;color:#d6bcfa}}
.score-medium{{background:#3a2b12;color:#f6ad55}}
.score-high{{background:#3b1f1f;color:#fc8181}}
.score-critical{{background:#4a1a1a;color:#feb2b2}}
.links{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:8px;margin-top:10px}}
.links a{{display:block;background:#0f1117;border:1px solid #2d3148;border-radius:6px;padding:10px 14px;
  color:#90cdf4;text-decoration:none;font-size:.85rem;transition:border-color .2s}}
.links a:hover{{border-color:#63b3ed}}
.links a .path{{color:#68d391;font-family:monospace;font-size:.8rem}}
</style>
</head>
<body>
<nav class="topnav">
  <a href="{base_url}/">Augur Home</a>
  <a href="{base_url}/how-payment-works">How Payment Works</a>
  <a href="{base_url}/openapi.json">OpenAPI</a>
</nav>
<span class="eyebrow">{escape(eyebrow)}</span>
<h1>{escape(title)}</h1>
<p>{escape(summary)}</p>

<div class="section">
  <h2>Scope</h2>
  <p>This snapshot was generated on <strong>{escape(snapshot_date)}</strong> for three notable Base contracts: WETH, USDC, and cbBTC.</p>
  <ul>
    {methodology}
  </ul>
</div>

{''.join(contract_sections)}

<div class="section">
  <h2>What this report proves</h2>
  <ul>
    {takeaways}
  </ul>
</div>

<div class="section">
  <h2>Reuse the live API</h2>
  <p>If you want the same response shape for your own contract list, call the canonical paid endpoint:</p>
  <pre>curl -s "{base_url}/analyze?address=0x4200000000000000000000000000000000000006" \\
  -H "PAYMENT-SIGNATURE: &lt;x402-payment-proof&gt;" | jq</pre>
  <p>Payment is per-call in USDC on Base via x402. For the payment flow details, see <a href="{base_url}/how-payment-works">How Augur payment works</a>.</p>
  <div class="links">
    <a href="{base_url}/honeypot-detection-api">Honeypot Detection API<div class="path">/honeypot-detection-api</div></a>
    <a href="{base_url}/proxy-risk-api">Proxy Risk API<div class="path">/proxy-risk-api</div></a>
    <a href="{base_url}/deployer-reputation-api">Deployer Reputation API<div class="path">/deployer-reputation-api</div></a>
  </div>
</div>
</body>
</html>"""
