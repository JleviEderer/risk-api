"""Flask application with x402 payment middleware."""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

from flask import Flask, Response, current_app, jsonify, redirect, request

from risk_api.analytics import (
    append_sqlite_entry,
    build_stats_payload,
    empty_stats_payload,
    init_sqlite_store,
    iter_jsonl_entries,
    iter_sqlite_entries,
)
from risk_api.analysis.engine import NoBytecodeError, analyze_contract
from risk_api.chain.rpc import RPCError, get_code
from risk_api.config import Config, load_config
from risk_api.proof_reports import REPORT_PAGES, render_report_page

logger = logging.getLogger(__name__)
request_logger = logging.getLogger("risk_api.requests")

# Ethereum address pattern: 0x followed by 40 hex chars
ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")

# Routes that require x402 payment
PROTECTED_ROUTES = {"/analyze"}

SAFE_EXAMPLE_ADDRESS = "0x4200000000000000000000000000000000000006"
PROXY_EXAMPLE_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
PROXY_IMPLEMENTATION_EXAMPLE_ADDRESS = "0x2cE6409Bc2Ff3E36834E44e15bbE83e4aD02d779"
NO_BYTECODE_ERROR_TEMPLATE = "No contract bytecode found at Base address: {address}"
BASE_ADDRESS_DESCRIPTION = "Base mainnet contract address (0x-prefixed, 40 hex chars)"


def _extract_requested_address() -> str:
    """Read the requested address from query params or JSON body."""
    address = request.args.get("address", "").strip()
    if not address and request.is_json:
        body = request.get_json(silent=True)
        if body and isinstance(body, dict):
            address = str(body.get("address", "")).strip()
    return address


def _bytecode_size(bytecode_hex: str) -> int:
    hex_body = bytecode_hex[2:] if bytecode_hex.startswith("0x") else bytecode_hex
    return len(hex_body) // 2


def _no_bytecode_error(address: str) -> str:
    return NO_BYTECODE_ERROR_TEMPLATE.format(address=address)


def _canonical_redirect_target(public_url: str) -> str | None:
    parsed = urlsplit(public_url)
    canonical_host = (parsed.hostname or "").lower()
    if not canonical_host:
        return None

    request_host = request.host.split(":", 1)[0].lower()
    if request_host == canonical_host:
        return None

    return urlunsplit(
        (
            parsed.scheme or request.scheme,
            parsed.netloc,
            request.path,
            request.query_string.decode(),
            "",
        )
    )


# Load avatar image bytes at module level
_AVATAR_BYTES: bytes | None = None
for _avatar_path in [
    Path(__file__).resolve().parent / "x402JobsAvatar.png",
    Path(__file__).resolve().parent.parent.parent / "x402JobsAvatar.png",
]:
    if _avatar_path.exists():
        _AVATAR_BYTES = _avatar_path.read_bytes()
        break

# OpenAPI 3.0.3 specification for the risk scoring API
OPENAPI_SPEC: dict[str, object] = {
    "openapi": "3.0.3",
    "info": {
        "title": "Augur",
        "version": "1.0.0",
        "description": (
            "Base mainnet smart contract bytecode risk scoring API for agents "
            "and the developers building them. "
            "Analyzes Base bytecode patterns (proxy detection, reentrancy, "
            "selfdestruct, honeypot, hidden mint, fee manipulation, "
            "delegatecall, deployer reputation) and returns a composite 0-100 "
            "risk score with findings. Pay $0.10/call via x402 in USDC on Base. "
            '"safe" means no major bytecode-level risk signals detected in this '
            "scan, not a security audit or guarantee."
        ),
        "contact": {
            "url": "https://github.com/JleviEderer/risk-api",
        },
    },
    "paths": {
        "/analyze": {
            "get": {
                "operationId": "analyzeContract",
                "summary": "Analyze a Base smart contract for bytecode risk",
                "description": (
                    "Fetches on-chain bytecode for the given Base mainnet "
                    "contract address and runs 8 detectors (proxy, reentrancy, selfdestruct, "
                    "honeypot, hidden mint, fee manipulation, delegatecall, "
                    "deployer reputation). Returns a composite 0-100 risk score "
                    'with findings. "safe" is a low-risk bytecode bucket, not a '
                    "security guarantee."
                ),
                "parameters": [
                    {
                        "name": "address",
                        "in": "query",
                        "required": True,
                        "schema": {
                            "type": "string",
                            "pattern": "^0x[0-9a-fA-F]{40}$",
                        },
                        "description": BASE_ADDRESS_DESCRIPTION,
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Risk analysis result",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/AnalysisResult"},
                                "examples": {
                                    "safe_contract": {
                                        "summary": (
                                            "Simple Base contract - no risk findings in this scan"
                                        ),
                                        "value": {
                                            "address": SAFE_EXAMPLE_ADDRESS,
                                            "score": 0,
                                            "level": "safe",
                                            "bytecode_size": 4632,
                                            "findings": [],
                                            "category_scores": {},
                                        },
                                    },
                                    "proxy_contract": {
                                        "summary": (
                                            "Proxy contract - high risk with implementation analysis"
                                        ),
                                        "value": {
                                            "address": PROXY_EXAMPLE_ADDRESS,
                                            "score": 60,
                                            "level": "high",
                                            "bytecode_size": 1485,
                                            "findings": [
                                                {
                                                    "detector": "proxy",
                                                    "severity": "medium",
                                                    "title": "EIP-1967 Proxy Detected",
                                                    "description": "Contract uses the EIP-1967 transparent proxy pattern. Logic resides in a separate implementation contract that can be upgraded.",
                                                    "points": 20,
                                                },
                                                {
                                                    "detector": "delegatecall",
                                                    "severity": "medium",
                                                    "title": "Delegatecall Usage",
                                                    "description": "Contract uses DELEGATECALL to execute code from another contract.",
                                                    "points": 15,
                                                },
                                            ],
                                            "category_scores": {
                                                "proxy": 20,
                                                "delegatecall": 15,
                                                "impl_delegatecall": 15,
                                                "impl_hidden_mint": 10,
                                            },
                                            "implementation": {
                                                "address": PROXY_IMPLEMENTATION_EXAMPLE_ADDRESS,
                                                "bytecode_size": 24576,
                                                "findings": [
                                                    {
                                                        "detector": "impl_delegatecall",
                                                        "severity": "medium",
                                                        "title": "Implementation Uses Delegatecall",
                                                        "description": "The implementation contract also uses DELEGATECALL.",
                                                        "points": 15,
                                                    },
                                                    {
                                                        "detector": "impl_hidden_mint",
                                                        "severity": "medium",
                                                        "title": "Implementation Has Hidden Mint",
                                                        "description": "The implementation contract contains patterns consistent with unauthorized token minting.",
                                                        "points": 10,
                                                    },
                                                ],
                                                "category_scores": {
                                                    "impl_delegatecall": 15,
                                                    "impl_hidden_mint": 10,
                                                },
                                            },
                                        },
                                    },
                                },
                            }
                        },
                    },
                    "402": {
                        "description": "Payment required - send x402 payment and retry",
                    },
                    "422": {
                        "description": "Invalid, missing, or non-contract Base mainnet address",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "error": {"type": "string"},
                                    },
                                },
                                "examples": {
                                    "missing_address": {
                                        "value": {
                                            "error": "Missing 'address' query parameter",
                                        },
                                    },
                                    "invalid_address": {
                                        "value": {
                                            "error": "Invalid Ethereum address: 0x1234",
                                        },
                                    },
                                    "no_bytecode": {
                                        "value": {
                                            "error": _no_bytecode_error(
                                                SAFE_EXAMPLE_ADDRESS
                                            ),
                                        },
                                    },
                                },
                                "example": {
                                    "error": "Missing 'address' query parameter",
                                },
                            }
                        },
                    },
                },
                "x-x402-price": "$0.10",
                "x-x402-network": "eip155:8453",
                "x-x402-pay-to": "0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891",
                "x-payment-info": {
                    "protocols": ["x402"],
                    "pricingMode": "fixed",
                    "price": "0.10",
                    "currency": "USDC",
                    "network": "eip155:8453",
                    "payTo": "0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891",
                },
                "security": [{"x402": []}],
            },
            "post": {
                "operationId": "analyzeContractPost",
                "summary": "Analyze a Base smart contract for bytecode risk (POST)",
                "description": (
                    "Same as GET but accepts a Base mainnet contract address in the JSON body."
                ),
                "parameters": [
                    {
                        "name": "address",
                        "in": "query",
                        "required": False,
                        "schema": {
                            "type": "string",
                            "pattern": "^0x[0-9a-fA-F]{40}$",
                        },
                        "description": BASE_ADDRESS_DESCRIPTION,
                    }
                ],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "address": {
                                        "type": "string",
                                        "pattern": "^0x[0-9a-fA-F]{40}$",
                                        "description": BASE_ADDRESS_DESCRIPTION,
                                    },
                                },
                            },
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Risk analysis result",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/AnalysisResult"},
                                "example": {
                                    "address": SAFE_EXAMPLE_ADDRESS,
                                    "score": 0,
                                    "level": "safe",
                                    "bytecode_size": 4632,
                                    "findings": [],
                                    "category_scores": {},
                                },
                            }
                        },
                    },
                    "402": {
                        "description": "Payment required - send x402 payment and retry",
                    },
                    "422": {
                        "description": "Invalid, missing, or non-contract Base mainnet address",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "error": {"type": "string"},
                                    },
                                },
                                "examples": {
                                    "missing_address": {
                                        "value": {
                                            "error": "Missing 'address' query parameter",
                                        },
                                    },
                                    "invalid_address": {
                                        "value": {
                                            "error": "Invalid Ethereum address: 0x1234",
                                        },
                                    },
                                    "no_bytecode": {
                                        "value": {
                                            "error": _no_bytecode_error(
                                                SAFE_EXAMPLE_ADDRESS
                                            ),
                                        },
                                    },
                                },
                                "example": {
                                    "error": "Missing 'address' query parameter",
                                },
                            }
                        },
                    },
                },
                "x-x402-price": "$0.10",
                "x-x402-network": "eip155:8453",
                "x-x402-pay-to": "0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891",
                "x-payment-info": {
                    "protocols": ["x402"],
                    "pricingMode": "fixed",
                    "price": "0.10",
                    "currency": "USDC",
                    "network": "eip155:8453",
                    "payTo": "0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891",
                },
                "security": [{"x402": []}],
            },
        },
    },
    "components": {
        "schemas": {
            "Finding": {
                "type": "object",
                "description": "A risk finding from one of the 8 detectors.",
                "properties": {
                    "detector": {
                        "type": "string",
                        "description": (
                            "Detector that produced this finding: proxy, reentrancy, "
                            "selfdestruct, honeypot, hidden_mint, fee_manipulation, "
                            "delegatecall, or deployer_reputation. Prefixed with impl_ "
                            "for findings from a proxy's implementation contract."
                        ),
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["info", "low", "medium", "high", "critical"],
                        "description": "Finding severity level.",
                    },
                    "title": {
                        "type": "string",
                        "description": "Human-readable title of the finding.",
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed explanation of what was detected and why it matters.",
                    },
                    "points": {
                        "type": "integer",
                        "description": "Risk points this finding contributes to the composite score.",
                    },
                },
            },
            "ImplementationResult": {
                "type": "object",
                "nullable": True,
                "properties": {
                    "address": {"type": "string"},
                    "bytecode_size": {"type": "integer"},
                    "findings": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/Finding"},
                    },
                    "category_scores": {
                        "type": "object",
                        "additionalProperties": {"type": "number"},
                    },
                },
            },
            "AnalysisResult": {
                "type": "object",
                "properties": {
                    "address": {"type": "string", "description": "The analyzed contract address."},
                    "score": {
                        "type": "integer", "minimum": 0, "maximum": 100,
                        "description": "Composite risk score from 0 (safest) to 100 (riskiest).",
                    },
                    "level": {
                        "type": "string",
                        "enum": ["safe", "low", "medium", "high", "critical"],
                        "description": (
                            "Risk level derived from score, not an audit or guarantee: "
                            "safe (0-15), low (16-35), medium (36-55), "
                            "high (56-75), critical (76-100)."
                        ),
                    },
                    "bytecode_size": {
                        "type": "integer",
                        "description": "Size of the contract bytecode in bytes.",
                    },
                    "findings": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/Finding"},
                        "description": "List of risk findings from all detectors.",
                    },
                    "category_scores": {
                        "type": "object",
                        "additionalProperties": {"type": "number"},
                        "description": (
                            "Risk points broken down by detector category "
                            "(e.g. proxy, reentrancy, delegatecall)."
                        ),
                    },
                    "implementation": {
                        "$ref": "#/components/schemas/ImplementationResult",
                        "description": (
                            "Analysis of the proxy's implementation contract. "
                            "Only present for proxy contracts."
                        ),
                    },
                },
                "required": [
                    "address", "score", "level", "bytecode_size",
                    "findings", "category_scores",
                ],
            },
        },
        "securitySchemes": {
            "x402": {
                "type": "apiKey",
                "in": "header",
                "name": "PAYMENT-SIGNATURE",
                "description": "x402 payment proof. Send USDC via the x402 protocol.",
            },
        },
    },
}

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>risk-api dashboard</title>
<style>
:root{
  --bg:#09111f;
  --panel:#0f1b2d;
  --border:#223554;
  --text:#e5edf8;
  --muted:#8ea3bf;
  --blue:#7dd3fc;
  --teal:#5eead4;
  --green:#86efac;
  --amber:#fbbf24;
  --red:#fca5a5;
  --purple:#c4b5fd;
  --shadow:0 18px 48px rgba(0,0,0,.26);
}
*{margin:0;padding:0;box-sizing:border-box}
body{
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  color:var(--text);
  margin:0;
  background:
    radial-gradient(circle at top left, rgba(34,211,238,.12), transparent 30%),
    radial-gradient(circle at top right, rgba(196,181,253,.10), transparent 24%),
    linear-gradient(180deg, #08101d 0%, #0a1220 54%, #08111d 100%);
  min-height:100vh;
}
.shell{max-width:1380px;margin:0 auto;padding:28px 22px 40px}
.hero{
  background:linear-gradient(135deg, rgba(18,33,56,.95), rgba(8,18,33,.98));
  border:1px solid var(--border);
  border-radius:24px;
  box-shadow:var(--shadow);
  padding:24px;
  margin-bottom:20px;
}
.hero-top{display:flex;justify-content:space-between;gap:18px;align-items:flex-start;flex-wrap:wrap}
.eyebrow{
  display:inline-block;
  border:1px solid rgba(125,211,252,.35);
  color:var(--blue);
  background:rgba(17,30,50,.75);
  border-radius:999px;
  padding:6px 12px;
  font-size:.72rem;
  text-transform:uppercase;
  letter-spacing:.08em;
}
h1{font-size:2rem;line-height:1.05;margin-top:14px;font-weight:650;letter-spacing:-.03em}
h1 span{color:var(--blue)}
.hero p{max-width:760px;color:#b8c8de;margin-top:12px;font-size:.98rem;line-height:1.6}
.hero-meta{display:grid;gap:10px;min-width:260px}
.pill{
  background:rgba(11,20,34,.78);
  border:1px solid var(--border);
  border-radius:16px;
  padding:12px 14px;
}
.pill .label{font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}
.pill .value{font-size:.98rem;color:var(--text);margin-top:4px}
.layout{display:grid;grid-template-columns:2.15fr 1fr;gap:20px}
.maincol,.sidecol{min-width:0}
.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin-bottom:20px}
.card{
  background:linear-gradient(180deg, rgba(18,31,51,.96), rgba(12,22,37,.96));
  border:1px solid var(--border);
  border-radius:18px;
  padding:18px;
  box-shadow:var(--shadow);
  min-height:138px;
}
.card .label{font-size:.72rem;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}
.card .value{font-size:2rem;font-weight:700;margin-top:10px;letter-spacing:-.04em}
.card .sub{margin-top:8px;color:#9fb0c8;font-size:.84rem;line-height:1.45}
.card.blue .value{color:var(--blue)}
.card.green .value{color:var(--green)}
.card.amber .value{color:var(--amber)}
.card.teal .value{color:var(--teal)}
.section{
  background:linear-gradient(180deg, rgba(16,28,46,.95), rgba(11,20,34,.97));
  border:1px solid var(--border);
  border-radius:20px;
  padding:20px;
  box-shadow:var(--shadow);
  margin-bottom:20px;
}
.section h2{font-size:1rem;color:#d7e3f4;margin-bottom:4px;font-weight:620}
.section .intro{color:var(--muted);font-size:.86rem;margin-bottom:16px;line-height:1.5}
.chart-grid{display:grid;grid-template-columns:1.35fr .95fr;gap:16px}
.chart-shell{background:rgba(7,14,24,.55);border:1px solid rgba(34,53,84,.8);border-radius:18px;padding:16px}
.chart-shell h3,.mini h3,.table-header h3{
  font-size:.82rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-bottom:12px
}
.chart-wrap{position:relative;height:290px}
.chart-fallback{display:none;color:var(--muted);padding:48px 24px;text-align:center}
.mini-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.mini{
  background:rgba(9,18,31,.72);
  border:1px solid rgba(34,53,84,.8);
  border-radius:16px;
  padding:14px;
}
.mini .big{font-size:1.6rem;font-weight:700;letter-spacing:-.03em}
.mini .muted{margin-top:6px;color:var(--muted);font-size:.82rem;line-height:1.45}
.progress-cluster{display:grid;gap:10px}
.progress-row{display:grid;gap:6px}
.progress-label{display:flex;justify-content:space-between;gap:12px;font-size:.84rem;color:#d6e1f2}
.progress-track{height:10px;border-radius:999px;background:#0a1322;overflow:hidden;border:1px solid rgba(34,53,84,.8)}
.progress-fill{height:100%;border-radius:999px;background:linear-gradient(90deg, var(--blue), var(--teal))}
.list{display:grid;gap:10px}
.list-item{
  display:flex;justify-content:space-between;gap:12px;align-items:flex-start;
  background:rgba(13,24,40,.72);border:1px solid rgba(34,53,84,.65);border-radius:14px;padding:10px 12px
}
.list-item .name{font-size:.86rem;line-height:1.4;color:#dfe8f5;word-break:break-word}
.list-item .count{font-size:.78rem;color:var(--blue);white-space:nowrap}
.empty{color:var(--muted);font-size:.84rem;padding:8px 0}
.table-header{display:flex;justify-content:space-between;gap:12px;align-items:flex-end;margin-bottom:12px;flex-wrap:wrap}
.table-note{font-size:.78rem;color:var(--muted)}
.table-wrap{overflow:auto;border-radius:16px;border:1px solid rgba(34,53,84,.8)}
table{width:100%;border-collapse:collapse;font-size:.84rem;min-width:980px;background:rgba(7,14,24,.45)}
th{text-align:left;color:var(--muted);font-weight:520;padding:11px 12px;border-bottom:1px solid rgba(34,53,84,.95);background:rgba(10,18,31,.92)}
td{padding:10px 12px;border-bottom:1px solid rgba(23,37,60,.9);vertical-align:top}
tr:hover td{background:rgba(17,29,47,.45)}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.79rem}
.path{color:var(--blue)}
.host{color:var(--purple)}
.referer{max-width:260px;word-break:break-word;color:#c7d4e7}
.badge{
  display:inline-flex;align-items:center;gap:6px;padding:4px 8px;border-radius:999px;
  font-size:.69rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em
}
.badge.stage{background:#16263f;color:#9edcff;border:1px solid rgba(125,211,252,.2)}
.badge.safe{background:#173b2c;color:var(--green)}
.badge.low{background:#16334c;color:var(--blue)}
.badge.medium{background:#4d330d;color:#ffd17c}
.badge.high{background:#4d1d21;color:#ffb2b2}
.badge.critical{background:#511117;color:#ffc0cb}
.badge.paid{background:#103b2d;color:var(--green)}
.badge.free{background:#273347;color:#b0bfd2}
.status{font-weight:700}
.status.good{color:var(--green)}
.status.warn{color:var(--amber)}
.status.bad{color:var(--red)}
.insight-list{display:grid;gap:10px}
.insight{
  padding:12px 14px;border-radius:16px;border:1px solid rgba(34,53,84,.8);
  background:rgba(7,14,24,.58)
}
.insight strong{display:block;color:#e5edf8;font-size:.88rem}
.insight span{display:block;margin-top:5px;color:var(--muted);font-size:.82rem;line-height:1.45}
.status-bar{display:flex;justify-content:space-between;gap:10px;align-items:center;color:var(--muted);font-size:.78rem;margin-top:10px;flex-wrap:wrap}
@media (max-width:1120px){
  .layout{grid-template-columns:1fr}
  .cards{grid-template-columns:repeat(2,minmax(0,1fr))}
  .chart-grid{grid-template-columns:1fr}
}
@media (max-width:720px){
  .shell{padding:18px 14px 28px}
  .hero,.section,.card{border-radius:18px}
  .cards,.mini-grid{grid-template-columns:1fr}
  h1{font-size:1.7rem}
}
</style>
</head>
<body>
<div class="shell">
  <section class="hero">
    <div class="hero-top">
      <div>
        <span class="eyebrow">risk-api dashboard</span>
        <h1><span>Augur</span> Traffic and User Quality</h1>
        <p>
          Use this page to separate crawler noise from valuable traffic signals. The dashboard highlights intent-page visits,
          machine-readable discovery fetches, unpaid <code>402</code> attempts, and paid calls so you can tell whether growth work is
          moving real users toward Augur's paid API.
        </p>
      </div>
      <div class="hero-meta">
        <div class="pill">
          <div class="label">Telemetry Scope</div>
          <div class="value">Per-instance app telemetry</div>
        </div>
        <div class="pill">
          <div class="label">Use Better Stack For</div>
          <div class="value">Uptime, health checks, and alerting</div>
        </div>
      </div>
    </div>
    <div class="status-bar">
      <span>Auto-refreshes every 30s. Source: <code>/stats</code>. Old-domain <code>403</code> traffic may still require edge-layer visibility.</span>
      <span id="analytics-source">Analytics backend: waiting...</span>
      <span id="updated">Waiting for data...</span>
    </div>
  </section>

  <div class="cards">
    <div class="card blue">
      <div class="label">Tracked Events</div>
      <div class="value" id="total">-</div>
      <div class="sub" id="total-sub">All logged public GET routes plus <code>/analyze</code>.</div>
    </div>
    <div class="card teal">
      <div class="label">Valuable Signals</div>
      <div class="value" id="valuable">-</div>
      <div class="sub" id="valuable-sub">Intent views, unpaid 402 attempts, and paid requests.</div>
    </div>
    <div class="card amber">
      <div class="label">Crawler / Doc Fetches</div>
      <div class="value" id="docs">-</div>
      <div class="sub" id="docs-sub">Machine-readable discovery traffic, not buyer intent.</div>
    </div>
    <div class="card green">
      <div class="label">Paid Requests</div>
      <div class="value" id="paid">-</div>
      <div class="sub" id="paid-sub">Confirmed paid calls visible on this instance.</div>
    </div>
    <div class="card blue">
      <div class="label">Landing Views</div>
      <div class="value" id="landing">-</div>
      <div class="sub" id="landing-sub">Homepage traffic. Good for awareness, weak for conversion on its own.</div>
    </div>
    <div class="card teal">
      <div class="label">Intent Page Views</div>
      <div class="value" id="intent">-</div>
      <div class="sub" id="intent-sub">High-signal SEO / use-case traffic.</div>
    </div>
    <div class="card amber">
      <div class="label">402 Attempts</div>
      <div class="value" id="attempts">-</div>
      <div class="sub" id="attempts-sub">People close enough to payment to request the paid endpoint.</div>
    </div>
    <div class="card amber">
      <div class="label">Avg Response</div>
      <div class="value" id="avgdur">-</div>
      <div class="sub" id="avgdur-sub">Mean response time for logged requests.</div>
    </div>
  </div>

  <div class="layout">
    <main class="maincol">
      <section class="section">
        <h2>Traffic Mix</h2>
        <div class="intro">See whether this instance is getting discovery fetches, broad awareness traffic, or higher-intent interactions closer to payment.</div>
        <div class="chart-grid">
          <div class="chart-shell">
            <h3>Hourly traffic composition</h3>
            <div class="chart-wrap"><canvas id="traffic-chart"></canvas></div>
            <div class="chart-fallback" id="traffic-fallback">Chart unavailable (Chart.js CDN unreachable)</div>
          </div>
          <div class="chart-shell">
            <h3>Quality summary</h3>
            <div class="mini-grid">
              <div class="mini">
                <h3>Value share</h3>
                <div class="big" id="value-share">-</div>
                <div class="muted" id="value-share-sub">Share of tracked traffic that looks closer to real buyer intent.</div>
              </div>
              <div class="mini">
                <h3>Paid conversion</h3>
                <div class="big" id="paid-conv">-</div>
                <div class="muted" id="paid-conv-sub">Paid requests divided by unpaid 402 attempts.</div>
              </div>
              <div class="mini">
                <h3>Best signal</h3>
                <div class="big" id="best-signal">-</div>
                <div class="muted" id="best-signal-sub">Which stage currently stands out the most.</div>
              </div>
              <div class="mini">
                <h3>Page mix</h3>
                <div class="big" id="page-mix">-</div>
                <div class="muted" id="page-mix-sub">Intent versus landing page volume.</div>
              </div>
            </div>
            <div style="margin-top:16px">
              <h3>Funnel posture</h3>
              <div class="progress-cluster" id="funnel-bars"></div>
            </div>
          </div>
        </div>
      </section>

      <section class="section">
        <div class="table-header">
          <div>
            <h3 style="margin:0 0 4px">Recent events</h3>
            <div class="table-note">Latest logged requests on this instance, newest first.</div>
          </div>
          <div class="table-note">Includes stage, host, referer, request ID, and response outcome.</div>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Time</th>
                <th>Stage</th>
                <th>Path</th>
                <th>Host</th>
                <th>Referer</th>
                <th>UA</th>
                <th>Status</th>
                <th>Score</th>
                <th>Risk</th>
                <th>Payment</th>
                <th>Request</th>
              </tr>
            </thead>
            <tbody id="recent"></tbody>
          </table>
        </div>
      </section>
    </main>

    <aside class="sidecol">
      <section class="section">
        <h2>What matters</h2>
        <div class="intro">Quick interpretation layer over the raw stats so you can judge whether recent changes are attracting valuable traffic.</div>
        <div class="insight-list" id="insights"></div>
      </section>

      <section class="section">
        <h2>Top paths</h2>
        <div class="intro">Which routes are actually getting attention.</div>
        <div class="list" id="top-paths"></div>
      </section>

      <section class="section">
        <h2>Top hosts</h2>
        <div class="intro">Only includes traffic that reaches Flask.</div>
        <div class="list" id="top-hosts"></div>
      </section>

      <section class="section">
        <h2>Top referrers</h2>
        <div class="intro">External or internal navigation sources when browsers send them.</div>
        <div class="list" id="top-referers"></div>
      </section>

      <section class="section">
        <h2>Stage counts</h2>
        <div class="intro">Raw stage totals across the current request log.</div>
        <div class="list" id="stage-counts"></div>
      </section>
    </aside>
  </div>
</div>

<script>
var trafficChart=null,chartLoaded=false;
function loadChart(){
  return new Promise(function(resolve){
    if(window.Chart){chartLoaded=true;resolve();return}
    var s=document.createElement('script');
    s.src='https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js';
    s.onload=function(){chartLoaded=true;resolve()};
    s.onerror=function(){
      document.getElementById('traffic-chart').style.display='none';
      document.getElementById('traffic-fallback').style.display='block';
      resolve();
    };
    document.head.appendChild(s);
  });
}
function relTime(ts){
  if(!ts)return '';
  var d=new Date(ts),now=new Date(),s=Math.floor((now-d)/1000);
  if(s<60)return s+'s ago';if(s<3600)return Math.floor(s/60)+'m ago';
  if(s<86400)return Math.floor(s/3600)+'h ago';return Math.floor(s/86400)+'d ago';
}
function truncText(v,n){
  if(!v)return '';
  if(v.length<=n)return v;
  return v.slice(0,n-1)+'\\u2026';
}
function pct(part,total){
  if(!total)return '0%';
  return Math.round((part/total)*100)+'%';
}
function fmtNumber(v){
  return (v==null?0:v).toLocaleString();
}
function stageLabel(stage){
  var labels={
    landing_view:'landing',
    how_payment_view:'payment explainer',
    intent_honeypot_view:'intent: honeypot',
    intent_proxy_view:'intent: proxy',
    intent_deployer_view:'intent: deployer',
    openapi_fetch:'openapi fetch',
    llms_txt_fetch:'llms.txt fetch',
    llms_full_fetch:'llms-full fetch',
    x402_doc_fetch:'x402 doc',
    agent_card_fetch:'agent card',
    agent_metadata_fetch:'agent metadata',
    robots_fetch:'robots',
    sitemap_fetch:'sitemap',
    unpaid_402:'402 attempt',
    invalid_address:'invalid',
    no_bytecode:'no bytecode',
    paid_request:'paid',
    analyze_success:'success',
    rpc_error:'rpc error'
  };
  return labels[stage]||stage||'';
}
function stageBadge(stage){
  var text=stageLabel(stage);
  return text?'<span class="badge stage">'+text+'</span>':'';
}
function levelBadge(level){
  return level?'<span class="badge '+level+'">'+level+'</span>':'';
}
function paymentBadge(paid){
  return paid?'<span class="badge paid">paid</span>':'<span class="badge free">free</span>';
}
function statusClass(code){
  if(code>=500)return 'bad';
  if(code>=400)return 'warn';
  return 'good';
}
function requestShort(id){
  if(!id)return '';
  return id.slice(0,8);
}
function topItemRow(label,count){
  return '<div class="list-item"><div class="name">'+label+'</div><div class="count">'+fmtNumber(count)+'</div></div>';
}
function renderList(id,items,labelKey,emptyText){
  var el=document.getElementById(id);
  if(!items||!items.length){
    el.innerHTML='<div class="empty">'+emptyText+'</div>';
    return;
  }
  el.innerHTML=items.map(function(item){
    var label=item[labelKey]||'(blank)';
    return topItemRow(truncText(label,58),item.count||0);
  }).join('');
}
function renderStageCounts(stageCounts){
  var el=document.getElementById('stage-counts');
  var entries=Object.entries(stageCounts||{}).sort(function(a,b){return b[1]-a[1]});
  if(!entries.length){
    el.innerHTML='<div class="empty">No stages logged yet.</div>';
    return;
  }
  el.innerHTML=entries.map(function(pair){
    return topItemRow(stageLabel(pair[0]),pair[1]);
  }).join('');
}
function renderInsights(data){
  var funnel=data.funnel||{};
  var total=data.total_requests||0;
  var landing=funnel.landing_views||0;
  var intent=funnel.intent_page_views||0;
  var docs=funnel.machine_doc_fetches||0;
  var attempts=funnel.valid_unpaid_402_attempts||0;
  var paid=funnel.paid_requests||0;
  var items=[];

  if(intent>0){
    items.push('<div class="insight"><strong>Intent traffic is finally showing up.</strong><span>'+fmtNumber(intent)+' tracked intent-page views means people are landing on use-case pages, not just the homepage.</span></div>');
  }else{
    items.push('<div class="insight"><strong>No intent-page traffic yet.</strong><span>Current tracked traffic is still mostly homepage and machine-readable discovery fetches. Growth work has not yet driven visible use-case visits on this instance.</span></div>');
  }

  if(attempts>0||paid>0){
    items.push('<div class="insight"><strong>People are touching the paid API.</strong><span>'+fmtNumber(attempts)+' unpaid 402 attempts and '+fmtNumber(paid)+' paid requests are the strongest conversion signals in this dashboard.</span></div>');
  }else{
    items.push('<div class="insight"><strong>No payment-adjacent traffic visible yet.</strong><span>There are no unpaid 402 attempts or paid requests in this instance log, so discovery is not yet turning into measurable API demand here.</span></div>');
  }

  if(docs>landing&&docs>0){
    items.push('<div class="insight"><strong>Machine discovery currently outweighs human demand.</strong><span>'+fmtNumber(docs)+' machine-doc fetches versus '+fmtNumber(landing)+' landing views suggests crawlers and agent registries are still a large share of traffic.</span></div>');
  }else{
    items.push('<div class="insight"><strong>Homepage awareness is carrying the current traffic mix.</strong><span>'+fmtNumber(landing)+' landing views account for '+pct(landing,total)+' of tracked traffic on this instance.</span></div>');
  }

  document.getElementById('insights').innerHTML=items.join('');
}
function renderFunnelBars(data){
  var funnel=data.funnel||{};
  var total=data.total_requests||0;
  var rows=[
    ['Landing views',funnel.landing_views||0],
    ['Intent pages',funnel.intent_page_views||0],
    ['Payment explainer',funnel.how_payment_views||0],
    ['Machine docs',funnel.machine_doc_fetches||0],
    ['402 attempts',funnel.valid_unpaid_402_attempts||0],
    ['Paid requests',funnel.paid_requests||0]
  ];
  document.getElementById('funnel-bars').innerHTML=rows.map(function(row){
    var count=row[1],width=total?Math.max((count/total)*100,(count?4:0)):0;
    return '<div class="progress-row">'
      +'<div class="progress-label"><span>'+row[0]+'</span><span>'+fmtNumber(count)+' <span style="color:var(--muted)">('+pct(count,total)+')</span></span></div>'
      +'<div class="progress-track"><div class="progress-fill" style="width:'+width+'%"></div></div>'
      +'</div>';
  }).join('');
}
function setMetric(id,value,sub){
  document.getElementById(id).textContent=value;
  if(sub){document.getElementById(id+'-sub').innerHTML=sub}
}
function renderTrafficChart(data){
  if(!(chartLoaded&&window.Chart&&data.hourly))return;
  var labels=data.hourly.map(function(h){return h.hour.slice(11,16)});
  var landing=data.hourly.map(function(h){return h.landing_views||0});
  var intent=data.hourly.map(function(h){return h.intent_page_views||0});
  var docs=data.hourly.map(function(h){return h.machine_doc_fetches||0});
  var attempts=data.hourly.map(function(h){return h.valid_unpaid_402_attempts||0});
  var paid=data.hourly.map(function(h){return h.paid_requests||0});
  if(trafficChart){trafficChart.destroy()}
  trafficChart=new Chart(document.getElementById('traffic-chart').getContext('2d'),{
    type:'bar',
    data:{labels:labels,datasets:[
      {label:'Landing',data:landing,backgroundColor:'rgba(125,211,252,.88)',borderRadius:5},
      {label:'Intent',data:intent,backgroundColor:'rgba(94,234,212,.9)',borderRadius:5},
      {label:'Docs',data:docs,backgroundColor:'rgba(196,181,253,.88)',borderRadius:5},
      {label:'402 attempts',data:attempts,backgroundColor:'rgba(251,191,36,.88)',borderRadius:5},
      {label:'Paid',data:paid,backgroundColor:'rgba(134,239,172,.92)',borderRadius:5}
    ]},
    options:{
      responsive:true,
      maintainAspectRatio:false,
      plugins:{legend:{labels:{color:'#bcd0e6',boxWidth:12}}},
      scales:{
        x:{stacked:true,ticks:{color:'#8ea3bf'},grid:{color:'rgba(34,53,84,.42)'}},
        y:{stacked:true,beginAtZero:true,ticks:{color:'#8ea3bf',stepSize:1},grid:{color:'rgba(34,53,84,.42)'}}
      }
    }
  });
}
function refresh(){
  fetch('/stats').then(function(r){return r.json()}).then(function(d){
    var funnel=d.funnel||{};
    var total=d.total_requests||0;
    var paid=funnel.paid_requests||d.paid_requests||0;
    var attempts=funnel.valid_unpaid_402_attempts||0;
    var docs=funnel.machine_doc_fetches||0;
    var landing=funnel.landing_views||0;
    var intent=funnel.intent_page_views||0;
    var valuable=intent+attempts+paid;
    var intentBreakdown=(funnel.intent_honeypot_views||0)+' / '+(funnel.intent_proxy_views||0)+' / '+(funnel.intent_deployer_views||0);
    var backend=d.storage_backend||'unknown';
    var durable=!!d.storage_durable;
    var backendLabel=durable?('Persistent '+backend):('Ephemeral '+backend);

    setMetric('total',fmtNumber(total),durable?'Current durable event count visible to this app.':'Current instance log size. Use trends, not absolute lifetime counts.');
    setMetric('valuable',fmtNumber(valuable),pct(valuable,total)+' of tracked traffic is closer to commercial value.');
    setMetric('docs',fmtNumber(docs),pct(docs,total)+' of tracked traffic is machine-readable discovery or crawler fetches.');
    setMetric('paid',fmtNumber(paid),paid?(durable?'Visible paid traffic in durable analytics.':'Visible paid traffic on this instance.'):('No paid requests visible '+(durable?'in durable analytics yet.':'on this instance yet.')));
    setMetric('landing',fmtNumber(landing),pct(landing,total)+' of tracked traffic is homepage awareness.');
    setMetric('intent',fmtNumber(intent),'Honeypot / proxy / deployer = '+intentBreakdown);
    setMetric('attempts',fmtNumber(attempts),attempts?('Paid conversion so far: '+pct(paid,attempts)):'No unpaid 402 attempts logged yet.');
    setMetric('avgdur',d.avg_duration_ms?d.avg_duration_ms+'ms':'-','Lower is better, but quality of traffic matters more than speed here.');

    document.getElementById('value-share').textContent=pct(valuable,total);
    document.getElementById('paid-conv').textContent=attempts?pct(paid,attempts):'0%';
    document.getElementById('best-signal').textContent=paid?('paid x '+paid):(attempts?('402 x '+attempts):(intent?('intent x '+intent):'docs'));
    document.getElementById('page-mix').textContent=intent+' : '+landing;
    document.getElementById('page-mix-sub').textContent=durable?'Intent views versus homepage views in the durable store.':'Intent views versus homepage views on this instance.';
    document.getElementById('analytics-source').textContent=backendLabel+(d.storage_path?(' ('+d.storage_path+')'):'');
    document.getElementById('updated').textContent='Updated '+new Date().toLocaleTimeString();
    renderTrafficChart(d);
    renderFunnelBars(d);
    renderInsights(d);
    renderList('top-paths',d.top_paths,'path','No paths logged yet.');
    renderList('top-hosts',d.top_hosts,'host','No hosts logged yet.');
    renderList('top-referers',d.top_referers,'referer','No referers logged yet.');
    renderStageCounts(d.stage_counts||{});

    var tbody=document.getElementById('recent');
    tbody.innerHTML='';
    var rows=(d.recent||[]).slice().reverse();
    rows.forEach(function(e){
      var tr=document.createElement('tr');
      var lvl=e.level||'';
      tr.innerHTML='<td class="ts">'+relTime(e.ts)+'</td>'
        +'<td>'+stageBadge(e.funnel_stage)+'</td>'
        +'<td class="mono path" title="'+(e.path||'')+'">'+truncText(e.path||'',28)+'</td>'
        +'<td class="mono host" title="'+(e.host||'')+'">'+truncText(e.host||'',22)+'</td>'
        +'<td class="referer" title="'+(e.referer||'')+'">'+truncText(e.referer||'',42)+'</td>'
        +'<td title="'+(e.user_agent||'')+'">'+truncText(e.user_agent||'',34)+'</td>'
        +'<td class="status '+statusClass(e.status||0)+'">'+(e.status||'')+'</td>'
        +'<td>'+(e.score!=null?e.score:'')+'</td>'
        +'<td>'+levelBadge(lvl)+'</td>'
        +'<td>'+paymentBadge(e.paid)+'</td>'
        +'<td class="mono" title="'+(e.request_id||'')+'">'+requestShort(e.request_id||'')+'</td>';
      tbody.appendChild(tr);
    });
  }).catch(function(){});
}
loadChart().then(refresh);
setInterval(refresh,30000);
</script>
</body>
</html>"""

LANDING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Augur - Base Contract Risk Scoring API</title>
<meta name="description" content="Base mainnet smart contract bytecode risk scoring API for agents. 8 deterministic detectors, 0-100 score, $0.10/call via x402 in USDC on Base.">
<meta name="robots" content="index, follow">
<meta property="og:title" content="Augur">
<meta property="og:description" content="Base mainnet smart contract bytecode risk scoring API. 8 deterministic detectors, 0-100 risk score, $0.10/call via x402 on Base.">
<meta property="og:type" content="website">
<meta property="og:url" content="__BASE_URL__">
<meta property="og:image" content="__BASE_URL__/avatar.png">
<script type="application/ld+json">__JSON_LD__</script>
<script type="application/ld+json">__FAQ_JSON_LD__</script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  background:#0f1117;color:#e0e0e0;padding:24px;max-width:900px;margin:0 auto;line-height:1.6}
.topnav{display:flex;gap:10px;justify-content:flex-end;flex-wrap:wrap;margin-bottom:18px}
.topnav a{display:inline-block;background:#1a1d29;border:1px solid #2d3148;border-radius:999px;
  padding:6px 12px;color:#90cdf4;text-decoration:none;font-size:.82rem;transition:border-color .2s}
.topnav a:hover{border-color:#63b3ed}
h1{font-size:1.8rem;color:#e2e8f0;margin-bottom:4px;font-weight:600}
h2{font-size:1.1rem;color:#a0aec0;margin:28px 0 12px;font-weight:500}
.subtitle{color:#718096;font-size:1rem;margin-bottom:16px}
.badge{display:inline-block;background:#1a365d;color:#63b3ed;padding:4px 12px;border-radius:6px;font-size:.85rem;margin-bottom:24px}
.section{background:#1a1d29;border:1px solid #2d3148;border-radius:10px;padding:20px;margin-bottom:16px}
.detectors{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:8px;margin-top:8px}
.detector{background:#0f1117;border:1px solid #2d3148;border-radius:6px;padding:10px 14px;font-size:.85rem}
.detector .name{color:#90cdf4;font-weight:500}
.detector .desc{color:#718096;font-size:.78rem;margin-top:2px}
pre{background:#0f1117;border:1px solid #2d3148;border-radius:6px;padding:14px;overflow-x:auto;font-size:.82rem;color:#68d391;margin-top:8px}
.links{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:8px;margin-top:8px}
.links a{display:block;background:#0f1117;border:1px solid #2d3148;border-radius:6px;padding:10px 14px;
  color:#90cdf4;text-decoration:none;font-size:.85rem;transition:border-color .2s}
.links a:hover{border-color:#63b3ed}
.links a .path{color:#68d391;font-family:monospace;font-size:.8rem}
.price{font-size:2rem;font-weight:700;color:#68d391}
.price-note{color:#718096;font-size:.85rem}
footer{margin-top:28px;padding-top:16px;border-top:1px solid #2d3148;color:#4a5568;font-size:.78rem;text-align:center}
</style>
</head>
<body>
<nav class="topnav">
  <a href="__BASE_URL__/openapi.json">OpenAPI</a>
  <a href="__BASE_URL__/.well-known/x402">x402</a>
  <a href="__BASE_URL__/mcp">MCP</a>
  <a href="__BASE_URL__/how-payment-works">How Payment Works</a>
</nav>
<h1>Augur</h1>
<p class="subtitle">Score Base contract bytecode before your agent interacts with it.</p>
<span class="badge">$0.10/call via x402 &middot; No API key needed</span>

<div class="section">
<h2>What it does</h2>
<p>Fetches on-chain bytecode for a Base mainnet contract address and runs 8 deterministic detectors to produce a composite 0&ndash;100 risk score with detailed findings.</p>
<p style="margin-top:8px;color:#718096;font-size:.82rem">Scores are bytecode heuristics, not a full audit or guarantee. A <code>safe</code> result means no major bytecode-level risk signals were detected in this scan.</p>
<div class="detectors">
  <div class="detector"><div class="name">Proxy Detection</div><div class="desc">EIP-1967, EIP-1822, OpenZeppelin slots</div></div>
  <div class="detector"><div class="name">Reentrancy</div><div class="desc">CALL before state update patterns</div></div>
  <div class="detector"><div class="name">Selfdestruct</div><div class="desc">Contract destruction capability</div></div>
  <div class="detector"><div class="name">Honeypot</div><div class="desc">Transfer restriction patterns</div></div>
  <div class="detector"><div class="name">Hidden Mint</div><div class="desc">Unauthorized token creation</div></div>
  <div class="detector"><div class="name">Fee Manipulation</div><div class="desc">Dynamic fee extraction patterns</div></div>
  <div class="detector"><div class="name">Delegatecall</div><div class="desc">External code execution risk</div></div>
  <div class="detector"><div class="name">Deployer Reputation</div><div class="desc">Basescan deployer history</div></div>
</div>
</div>

<div class="section">
<h2>Try it</h2>
<pre>curl -s "__BASE_URL__/analyze?address=0x4200000000000000000000000000000000000006" \\
  -H "PAYMENT-SIGNATURE: &lt;x402-payment-proof&gt;" | jq</pre>
<p style="margin-top:8px;color:#718096;font-size:.82rem">
Pay with any x402-compatible client. Returns JSON with score, level, findings, and category_scores for a Base mainnet contract.
</p>
</div>

<div class="section">
<h2>Pricing</h2>
<div class="price">$0.10 <span style="font-size:1rem;color:#a0aec0;font-weight:400">per call</span></div>
<p class="price-note">USDC &middot; Settled via x402 protocol &middot; No API key, no signup</p>
<p style="margin-top:10px;color:#718096;font-size:.82rem">x402 is an HTTP-native payment protocol - your agent pays per call automatically, no API key or signup needed.</p>
<p style="margin-top:10px"><a href="__BASE_URL__/how-payment-works" style="color:#90cdf4">How Augur payment works</a></p>
</div>

<div class="section">
<h2>Use Augur For</h2>
<p style="color:#718096;font-size:.85rem">These public pages target common contract-triage jobs while pointing back to the same paid <code>/analyze</code> endpoint.</p>
<div class="links">
  <a href="__BASE_URL__/honeypot-detection-api">Honeypot Detection API <div class="path">/honeypot-detection-api</div></a>
  <a href="__BASE_URL__/proxy-risk-api">Proxy Risk API <div class="path">/proxy-risk-api</div></a>
  <a href="__BASE_URL__/deployer-reputation-api">Deployer Reputation API <div class="path">/deployer-reputation-api</div></a>
</div>
</div>

<div class="section">
<h2>Proof of Work</h2>
<p style="color:#718096;font-size:.85rem">See exact Augur output on notable Base contracts before you wire the API into an agent policy.</p>
<div class="links">
  <a href="__BASE_URL__/reports/base-bluechip-bytecode-snapshot">Base Blue-Chip Bytecode Snapshot <div class="path">/reports/base-bluechip-bytecode-snapshot</div></a>
</div>
</div>

<div class="section">
<h2>Discovery &amp; Integration</h2>
<div class="links">
  <a href="__BASE_URL__/mcp">MCP Setup<div class="path">/mcp</div></a>
  <a href="__BASE_URL__/openapi.json">OpenAPI Spec <div class="path">/openapi.json</div></a>
  <a href="__BASE_URL__/.well-known/agent-card.json">A2A Agent Card <div class="path">/.well-known/agent-card.json</div></a>
  <a href="__BASE_URL__/.well-known/x402">x402 Discovery <div class="path">/.well-known/x402</div></a>
  <a href="__BASE_URL__/.well-known/ai-plugin.json">AI Plugin Manifest <div class="path">/.well-known/ai-plugin.json</div></a>
  <a href="__BASE_URL__/.well-known/api-catalog">API Catalog (RFC 9727) <div class="path">/.well-known/api-catalog</div></a>
  <a href="__BASE_URL__/agent-metadata.json">Agent Metadata <div class="path">/agent-metadata.json</div></a>
  <a href="__BASE_URL__/llms.txt">LLM Documentation <div class="path">/llms.txt</div></a>
  <a href="https://8004scan.io/agents/base/19074">ERC-8004 Registry <div class="path">8004scan.io/agents/base/19074</div></a>
</div>
</div>

<footer>
Augur &middot; ERC-8004 Agent #19074 &middot; Powered by x402
</footer>
</body>
</html>"""

MCP_GUIDE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Augur MCP Setup</title>
<meta name="description" content="Install Augur as a local stdio MCP server for Claude Desktop, Codex-compatible clients, and other MCP tooling.">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  background:#0f1117;color:#e0e0e0;padding:24px;max-width:860px;margin:0 auto;line-height:1.65}
h1{font-size:1.8rem;color:#e2e8f0;margin-bottom:8px;font-weight:600}
h2{font-size:1.05rem;color:#a0aec0;margin:24px 0 10px;font-weight:500}
p{margin-bottom:10px}
.section{background:#1a1d29;border:1px solid #2d3148;border-radius:10px;padding:20px;margin-bottom:16px}
code{background:#0f1117;border:1px solid #2d3148;border-radius:4px;padding:2px 6px}
pre{background:#0f1117;border:1px solid #2d3148;border-radius:6px;padding:14px;overflow-x:auto;font-size:.84rem;color:#68d391;margin-top:8px}
a{color:#f6ad55}
a:hover{color:#fbd38d}
ul{margin:8px 0 0 18px}
.links{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:8px;margin-top:10px}
.links a{display:block;background:#0f1117;border:1px solid #2d3148;border-radius:6px;padding:10px 14px;
  color:#90cdf4;text-decoration:none;font-size:.85rem;transition:border-color .2s}
.links a:hover{border-color:#63b3ed}
.links a .path{color:#68d391;font-family:monospace;font-size:.8rem}
</style>
</head>
<body>
<h1>Augur MCP Setup</h1>
<p>Augur already ships a working local stdio MCP wrapper. Use it when you want the existing paid HTTP API surfaced as MCP tools inside Claude Desktop, Codex-compatible clients, or other MCP tooling.</p>

<div class="section">
<h2>What this gives you</h2>
<ul>
  <li>Local stdio MCP server</li>
  <li>x402 payment stays client-side on your machine</li>
  <li>No API key or signup for Augur itself</li>
  <li>Two tools out of the box: <code>analyze_base_contract_risk</code> and <code>describe_augur_service</code></li>
</ul>
</div>

<div class="section">
<h2>Install</h2>
<pre>git clone https://github.com/JleviEderer/risk-api
cd risk-api/examples/javascript/augur-mcp
npm install</pre>
<p>Set your wallet key in <code>.env</code> using the example file in that folder, then smoke test it:</p>
<pre>npm run smoke
npm run smoke -- --paid</pre>
</div>

<div class="section">
<h2>Wire it into an MCP client</h2>
<p>Point your MCP client at the local stdio server entrypoint:</p>
<pre>{
  "command": "node",
  "args": [
    "C:/path/to/risk-api/examples/javascript/augur-mcp/index.mjs"
  ],
  "env": {
    "CLIENT_PRIVATE_KEY": "0xYOUR_PRIVATE_KEY"
  }
}</pre>
<p>Use the same stdio command in Claude Desktop, Codex-compatible clients, or other MCP tooling that supports local servers.</p>
</div>

<div class="section">
<h2>Read the wrapper docs</h2>
<div class="links">
  <a href="https://github.com/JleviEderer/risk-api/tree/master/examples/javascript/augur-mcp">GitHub MCP Example<div class="path">examples/javascript/augur-mcp</div></a>
  <a href="__BASE_URL__/how-payment-works">How Payment Works<div class="path">/how-payment-works</div></a>
  <a href="__BASE_URL__/openapi.json">OpenAPI Spec<div class="path">/openapi.json</div></a>
  <a href="__BASE_URL__/.well-known/x402">x402 Discovery<div class="path">/.well-known/x402</div></a>
</div>
</div>
</body>
</html>"""

PAYMENT_GUIDE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>How Augur Payment Works</title>
<meta name="description" content="How to pay for Augur via x402: request, receive 402, sign payment, retry with PAYMENT-SIGNATURE, receive JSON.">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  background:#0f1117;color:#e0e0e0;padding:24px;max-width:820px;margin:0 auto;line-height:1.65}
h1{font-size:1.8rem;color:#e2e8f0;margin-bottom:8px;font-weight:600}
h2{font-size:1.05rem;color:#a0aec0;margin:24px 0 10px;font-weight:500}
p{margin-bottom:10px}
.section{background:#1a1d29;border:1px solid #2d3148;border-radius:10px;padding:20px;margin-bottom:16px}
.step{margin-bottom:14px}
.step strong{color:#90cdf4}
code{background:#0f1117;border:1px solid #2d3148;border-radius:4px;padding:2px 6px}
pre{background:#0f1117;border:1px solid #2d3148;border-radius:6px;padding:14px;overflow-x:auto;font-size:.84rem;color:#68d391;margin-top:8px}
a{color:#90cdf4}
ul{margin:8px 0 0 18px}
</style>
</head>
<body>
<h1>How Augur Payment Works</h1>
<p>Augur uses x402 for per-call payment. The flow is HTTP-native: request the resource, receive payment requirements, sign the payment, retry the same request, receive JSON.</p>

<div class="section">
<h2>The 4-step flow</h2>
<div class="step"><strong>1. Request analysis</strong><br>Call <code>GET __BASE_URL__/analyze?address=0x4200000000000000000000000000000000000006</code>.</div>
<div class="step"><strong>2. Receive a 402</strong><br>Augur returns <code>402 Payment Required</code> with a base64-encoded <code>Payment-Required</code> header describing the exact USDC payment on Base.</div>
<div class="step"><strong>3. Sign and attach payment</strong><br>Your x402 client signs the payment authorization from your wallet and retries the same request with a <code>PAYMENT-SIGNATURE</code> header.</div>
<div class="step"><strong>4. Receive JSON</strong><br>Augur verifies the payment with the facilitator, settles it, and returns the contract score, level, findings, and proxy details if present.</div>
</div>

<div class="section">
<h2>What you do not need</h2>
<ul>
  <li>No API key</li>
  <li>No signup</li>
  <li>No subscription</li>
</ul>
</div>

<div class="section">
<h2>What can fail before payment</h2>
<p>If the address is missing, malformed, or has no bytecode on Base mainnet, Augur returns <code>422</code> before the x402 paywall. That prevents paying for EOAs or undeployed contracts.</p>
</div>

<div class="section">
<h2>Quick examples</h2>
<pre># First request
GET __BASE_URL__/analyze?address=0x4200000000000000000000000000000000000006

# Retry after signing payment
GET __BASE_URL__/analyze?address=0x4200000000000000000000000000000000000006
PAYMENT-SIGNATURE: &lt;x402-payment-proof&gt;</pre>
<p>Integration references:</p>
<ul>
  <li><a href="__BASE_URL__/.well-known/x402">Live x402 discovery document</a></li>
  <li><a href="__BASE_URL__/openapi.json">OpenAPI spec</a></li>
  <li><a href="https://github.com/JleviEderer/risk-api">GitHub repository</a> for Python and JavaScript example code</li>
 </ul>
</div>
</body>
</html>"""


INTENT_PAGES: dict[str, dict[str, object]] = {
    "/honeypot-detection-api": {
        "title": "Base Honeypot Detection API",
        "meta_description": (
            "Base mainnet honeypot detection API for agents. Screen contract bytecode "
            "for transfer restrictions, fee traps, proxy risk, and related signals."
        ),
        "eyebrow": "Buyer Intent",
        "summary": (
            "Use Augur when an agent needs a fast Base token screen before buying, "
            "routing, or surfacing a token to a user. Honeypot patterns are checked "
            "alongside the rest of Augur's bytecode risk model."
        ),
        "problem_points": [
            "Catch transfer restriction patterns before a trading agent routes funds.",
            "Avoid treating a token as clean just because a swap quote succeeds.",
            "Pair honeypot checks with proxy, fee manipulation, and deployer signals.",
        ],
        "check_points": [
            "Honeypot bytecode patterns that can trap exits or restrict transfers.",
            "Fee manipulation and hidden mint signals that often travel with scam tokens.",
            "Proxy and delegatecall behavior that can hide mutable token logic.",
            "Deployer reputation context from Basescan-backed history checks.",
        ],
    },
    "/proxy-risk-api": {
        "title": "Base Proxy Risk API",
        "meta_description": (
            "Base mainnet proxy risk API for agents. Detect proxy contracts, inspect "
            "implementation bytecode, and score upgrade-related risk."
        ),
        "eyebrow": "Buyer Intent",
        "summary": (
            "Use Augur when your workflow needs to know whether a Base contract is a "
            "proxy, whether upgradeable logic exists behind it, and what the "
            "implementation bytecode looks like."
        ),
        "problem_points": [
            "Identify upgradeable contracts before an agent assumes logic is immutable.",
            "Inspect implementation risk without building custom proxy resolution logic.",
            "Surface proxy-specific findings in the same JSON response as the top-level score.",
        ],
        "check_points": [
            "EIP-1967, EIP-1822, and related proxy storage slot patterns.",
            "Delegatecall and other upgrade-surface indicators in the proxy.",
            "Implementation address resolution and implementation-level findings when present.",
            "Composite scoring that reuses the same engine across proxy and implementation paths.",
        ],
    },
    "/deployer-reputation-api": {
        "title": "Base Deployer Reputation API",
        "meta_description": (
            "Base mainnet deployer reputation API for agents. Add deployer-history "
            "context to contract screening before interacting or listing."
        ),
        "eyebrow": "Buyer Intent",
        "summary": (
            "Use Augur when contract triage needs more than raw bytecode. The deployer "
            "reputation detector adds Basescan-backed context so an agent can weigh "
            "who deployed a contract, not just what the bytecode contains."
        ),
        "problem_points": [
            "Flag contracts tied to deployers with suspicious or low-trust history.",
            "Add deployer context to listing, routing, and monitoring workflows.",
            "Keep reputation in the same response shape as the rest of Augur's findings.",
        ],
        "check_points": [
            "Deployer reputation signals gathered through the existing Basescan-backed path.",
            "Bytecode findings that combine with reputation instead of replacing it.",
            "A single 0-100 score plus category scores for downstream agent policies.",
            "The same paid /analyze endpoint used by the landing page, OpenAPI, and MCP wrapper.",
        ],
    },
}

PUBLIC_REQUEST_STAGE_BY_PATH: dict[str, str] = {
    "/": "landing_view",
    "/mcp": "mcp_guide_view",
    "/how-payment-works": "how_payment_view",
    "/honeypot-detection-api": "intent_honeypot_view",
    "/proxy-risk-api": "intent_proxy_view",
    "/deployer-reputation-api": "intent_deployer_view",
    "/openapi.json": "openapi_fetch",
    "/llms.txt": "llms_txt_fetch",
    "/llms-full.txt": "llms_full_fetch",
    "/.well-known/x402": "x402_doc_fetch",
    "/.well-known/agent-card.json": "agent_card_fetch",
    "/agent-metadata.json": "agent_metadata_fetch",
    "/robots.txt": "robots_fetch",
    "/sitemap.xml": "sitemap_fetch",
}

MACHINE_DOC_STAGES = {
    "openapi_fetch",
    "llms_txt_fetch",
    "llms_full_fetch",
    "x402_doc_fetch",
    "agent_card_fetch",
    "agent_metadata_fetch",
    "robots_fetch",
    "sitemap_fetch",
}

INTENT_PAGE_STAGES = {
    "intent_honeypot_view",
    "intent_proxy_view",
    "intent_deployer_view",
}


def _public_request_stage(path: str) -> str:
    stage = PUBLIC_REQUEST_STAGE_BY_PATH.get(path)
    if stage:
        return stage
    if path in REPORT_PAGES:
        return "proof_report_view"
    return ""


def _should_log_request(path: str, method: str) -> bool:
    if path == "/analyze":
        return True
    return method == "GET" and bool(_public_request_stage(path))


def _render_intent_page(base_url: str, path: str) -> str:
    page = INTENT_PAGES[path]
    title = str(page["title"])
    meta_description = str(page["meta_description"])
    summary = str(page["summary"])
    eyebrow = str(page["eyebrow"])
    problem_points = "\n".join(
        f"<li>{item}</li>" for item in page["problem_points"]
    )
    check_points = "\n".join(
        f"<li>{item}</li>" for item in page["check_points"]
    )
    related_links = "\n".join(
        (
            f'<a href="{base_url}{other_path}">{other_page["title"]}'
            f'<div class="path">{other_path}</div></a>'
        )
        for other_path, other_page in INTENT_PAGES.items()
        if other_path != path
    )
    json_ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "description": meta_description,
        "url": f"{base_url}{path}",
        "isPartOf": {
            "@type": "WebSite",
            "name": "Augur",
            "url": base_url,
        },
        "about": [
            "Base mainnet smart contract risk scoring",
            "x402-paid API",
            title,
        ],
    })
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} | Augur</title>
<meta name="description" content="{meta_description}">
<meta name="robots" content="index, follow">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{meta_description}">
<meta property="og:type" content="article">
<meta property="og:url" content="{base_url}{path}">
<meta property="og:image" content="{base_url}/avatar.png">
<script type="application/ld+json">{json_ld}</script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  background:#0f1117;color:#e0e0e0;padding:24px;max-width:900px;margin:0 auto;line-height:1.65}}
.topnav{{display:flex;gap:10px;justify-content:flex-end;flex-wrap:wrap;margin-bottom:18px}}
.topnav a{{display:inline-block;background:#1a1d29;border:1px solid #2d3148;border-radius:999px;
  padding:6px 12px;color:#90cdf4;text-decoration:none;font-size:.82rem;transition:border-color .2s}}
.topnav a:hover{{border-color:#63b3ed}}
.eyebrow{{display:inline-block;background:#1a365d;color:#63b3ed;padding:4px 12px;border-radius:6px;font-size:.85rem;margin-bottom:16px}}
h1{{font-size:1.9rem;color:#e2e8f0;margin-bottom:8px;font-weight:600}}
h2{{font-size:1.08rem;color:#a0aec0;margin:24px 0 10px;font-weight:500}}
p{{margin-bottom:10px}}
.section{{background:#1a1d29;border:1px solid #2d3148;border-radius:10px;padding:20px;margin-bottom:16px}}
code{{background:#0f1117;border:1px solid #2d3148;border-radius:4px;padding:2px 6px}}
pre{{background:#0f1117;border:1px solid #2d3148;border-radius:6px;padding:14px;overflow-x:auto;font-size:.84rem;color:#68d391;margin-top:8px}}
ul{{margin:8px 0 0 18px}}
.links{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:8px;margin-top:10px}}
.links a{{display:block;background:#0f1117;border:1px solid #2d3148;border-radius:6px;padding:10px 14px;
  color:#90cdf4;text-decoration:none;font-size:.85rem;transition:border-color .2s}}
.links a:hover{{border-color:#63b3ed}}
.links a .path{{color:#68d391;font-family:monospace;font-size:.8rem}}
a{{color:#90cdf4}}
</style>
</head>
<body>
<nav class="topnav">
  <a href="{base_url}/">Augur Home</a>
  <a href="{base_url}/how-payment-works">How Payment Works</a>
  <a href="{base_url}/openapi.json">OpenAPI</a>
</nav>
<span class="eyebrow">{eyebrow}</span>
<h1>{title}</h1>
<p>{summary}</p>
<p style="color:#718096;font-size:.88rem">Augur scores Base mainnet contract bytecode for agents. A <code>safe</code> result means no major bytecode-level risk signals were detected in this scan, not a full audit or guarantee.</p>

<div class="section">
<h2>Why teams look for this API</h2>
<ul>
{problem_points}
</ul>
</div>

<div class="section">
<h2>What Augur checks on the same request</h2>
<ul>
{check_points}
</ul>
</div>

<div class="section">
<h2>Call the canonical endpoint</h2>
<p>All buyer-intent pages map back to the same paid API: <code>GET {base_url}/analyze?address=0x4200000000000000000000000000000000000006</code></p>
<pre>curl -s "{base_url}/analyze?address=0x4200000000000000000000000000000000000006" \\
  -H "PAYMENT-SIGNATURE: &lt;x402-payment-proof&gt;" | jq</pre>
<p>x402 payment is per-call, using USDC on Base. For the 402 flow details, see <a href="{base_url}/how-payment-works">How Augur payment works</a>.</p>
</div>

<div class="section">
<h2>Integration links</h2>
<div class="links">
  <a href="{base_url}/openapi.json">OpenAPI Spec<div class="path">/openapi.json</div></a>
  <a href="{base_url}/llms.txt">LLM Documentation<div class="path">/llms.txt</div></a>
  <a href="{base_url}/.well-known/x402">x402 Discovery<div class="path">/.well-known/x402</div></a>
  <a href="{base_url}/agent-metadata.json">Agent Metadata<div class="path">/agent-metadata.json</div></a>
</div>
</div>

<div class="section">
<h2>Related intent pages</h2>
<div class="links">
{related_links}
</div>
</div>
</body>
</html>"""


LLMS_TXT = """\
# Augur

> Base mainnet smart contract bytecode risk scoring API for agents and the developers \
building them. Returns a 0-100 risk score with findings. Pay $0.10/call via x402 in USDC on Base.

## What It Does

Augur fetches on-chain bytecode for a Base mainnet smart contract (EIP-155:8453) \
and runs 8 deterministic detectors to produce a composite risk score from 0 (safe) to 100 (critical).
A `safe` result means no major bytecode-level risk signals were detected in this scan, not that the contract is audited or guaranteed safe.

## How to Call

```
GET __BASE_URL__/analyze?address=0x4200000000000000000000000000000000000006
```

Payment: Include a `PAYMENT-SIGNATURE` header with an x402 payment proof ($0.10 USDC on Base). \
Any x402-compatible HTTP client handles this automatically.

## Example Response

```json
{
  "address": "0x4200000000000000000000000000000000000006",
  "score": 0,
  "level": "safe",
  "bytecode_size": 4632,
  "findings": [],
  "category_scores": {}
}
```

## Risk Levels

- **safe** (0-15): No major bytecode-level risk signals detected in this scan; not a guarantee
- **low** (16-35): Limited bytecode-level concerns detected; review context
- **medium** (36-55): Notable risks, review before interacting
- **high** (56-75): Significant risks detected
- **critical** (76-100): Severe risks, avoid interaction

## Links

- [MCP Setup](__BASE_URL__/mcp)
- [OpenAPI Spec](__BASE_URL__/openapi.json)
- [A2A Agent Card](__BASE_URL__/.well-known/agent-card.json)
- [AI Plugin Manifest](__BASE_URL__/.well-known/ai-plugin.json)
- [x402 Discovery](__BASE_URL__/.well-known/x402)
- [API Catalog](__BASE_URL__/.well-known/api-catalog)
- [Full Documentation](__BASE_URL__/llms-full.txt)
"""

LLMS_FULL_TXT = """\
# Augur - Full Documentation

> Base mainnet smart contract bytecode risk scoring API for agents and the developers \
building them. Returns a 0-100 score with findings. Pay $0.10/call via x402 in USDC on Base.

## Overview

Augur is an agent-to-agent API that scores smart contract risk on Base (EIP-155:8453). \
It uses deterministic bytecode pattern matching (no LLM) for fast, reliable results. \
It is a fast bytecode screen, not a full security audit or guarantee. \
Payment is via the x402 HTTP payment protocol - no API key, no signup, no subscription.

## Endpoint

```
GET __BASE_URL__/analyze?address={base_contract_address}
POST __BASE_URL__/analyze  (body: {"address": "{base_contract_address}"})
```

**Payment:** $0.10 USDC on Base via x402. Send a request, receive 402 with payment \
details, sign USDC authorization, retry with `PAYMENT-SIGNATURE` header.

## Request Parameters

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| address   | string | Yes      | Base mainnet contract address, 0x-prefixed, 40 hex chars |

## Example: Safe Contract

```json
{
  "address": "0x4200000000000000000000000000000000000006",
  "score": 0,
  "level": "safe",
  "bytecode_size": 4632,
  "findings": [],
  "category_scores": {}
}
```

## Example: High-Risk Proxy Contract

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
      "description": "Contract uses the EIP-1967 transparent proxy pattern.",
      "points": 20
    },
    {
      "detector": "delegatecall",
      "severity": "medium",
      "title": "Delegatecall Usage",
      "description": "Contract uses DELEGATECALL to execute code from another contract.",
      "points": 15
    }
  ],
  "category_scores": {
    "proxy": 20,
    "delegatecall": 15,
    "impl_delegatecall": 15,
    "impl_hidden_mint": 10
  },
  "implementation": {
    "address": "0x2cE6409Bc2Ff3E36834E44e15bbE83e4aD02d779",
    "bytecode_size": 24576,
    "findings": [
      {
        "detector": "impl_delegatecall",
        "severity": "medium",
        "title": "Implementation Uses Delegatecall",
        "points": 15
      },
      {
        "detector": "impl_hidden_mint",
        "severity": "medium",
        "title": "Implementation Has Hidden Mint",
        "points": 10
      }
    ],
    "category_scores": {
      "impl_delegatecall": 15,
      "impl_hidden_mint": 10
    }
  }
}
```

## Response Schema

| Field            | Type    | Description |
|------------------|---------|-------------|
| address          | string  | The analyzed contract address |
| score            | integer | Composite risk score, 0-100 |
| level            | string  | Risk bucket: safe, low, medium, high, critical (`safe` is not a guarantee) |
| bytecode_size    | integer | Contract bytecode size in bytes |
| findings         | array   | List of risk findings from detectors |
| category_scores  | object  | Risk points by detector category |
| implementation   | object  | Proxy implementation analysis (only for proxy contracts) |

### Finding Object

| Field       | Type    | Description |
|-------------|---------|-------------|
| detector    | string  | Detector name (e.g. proxy, reentrancy, selfdestruct) |
| severity    | string  | info, low, medium, high, or critical |
| title       | string  | Human-readable finding title |
| description | string  | Detailed explanation |
| points      | integer | Risk points contributed to composite score |

## Risk Levels

| Level    | Score Range | Meaning |
|----------|-------------|---------|
| safe     | 0-15        | No major bytecode-level risk signals detected in this scan; not a guarantee |
| low      | 16-35       | Limited bytecode-level concerns detected; review context |
| medium   | 36-55       | Notable risks, review before interacting |
| high     | 56-75       | Significant risks detected |
| critical | 76-100      | Severe risks, avoid interaction |

## Detectors

1. **Proxy Detection** - identifies upgradeable proxy behavior and can include nested implementation analysis.
2. **Reentrancy** - surfaces bytecode patterns associated with reentrant control flow risk.
3. **Selfdestruct** - flags contract destruction capability when present.
4. **Honeypot** - looks for transfer restriction patterns that can trap exits.
5. **Hidden Mint** - highlights mint-related capability that may matter for token trust decisions.
6. **Fee Manipulation** - surfaces fee and transfer-tax related bytecode signals.
7. **Delegatecall** - flags external code execution surfaces that may affect mutability or trust.
8. **Deployer Reputation** - adds deployer-history context when Basescan-backed data is available.

## Error Responses

**422 - Invalid request:**
```json
{"error": "Missing 'address' query parameter"}
{"error": "Invalid Ethereum address: 0x1234"}
{"error": "No contract bytecode found at Base address: 0x4200000000000000000000000000000000000006"}
```

**402 - Payment required:** Returned with x402 payment instructions. \
Use an x402-compatible client to handle payment automatically.

**502 - RPC error:** Upstream Base RPC node error. Retry after a moment.

## Integration

Use any x402-compatible HTTP client. The flow is:

1. `GET /analyze?address=<addr>` → receives 402 with payment details
2. The client handles the x402 payment flow
3. The client retries with `PAYMENT-SIGNATURE`
4. Augur returns JSON risk analysis

## Links

- [MCP Setup](__BASE_URL__/mcp)
- [OpenAPI Spec](__BASE_URL__/openapi.json)
- [A2A Agent Card](__BASE_URL__/.well-known/agent-card.json)
- [AI Plugin Manifest](__BASE_URL__/.well-known/ai-plugin.json)
- [x402 Discovery](__BASE_URL__/.well-known/x402)
- [API Catalog (RFC 9727)](__BASE_URL__/.well-known/api-catalog)
- [Agent Metadata](__BASE_URL__/agent-metadata.json)
- [ERC-8004 Registry](https://8004scan.io/agents/base/19074)
- [Summary](__BASE_URL__/llms.txt)
"""


class FlaskHTTPAdapter:
    """Adapts Flask request to x402 HTTPAdapter protocol."""

    def get_header(self, name: str) -> str | None:
        return request.headers.get(name)

    def get_method(self) -> str:
        return request.method

    def get_path(self) -> str:
        return request.path

    def get_accept_header(self) -> str:
        return request.headers.get("Accept", "")

    def get_query_param(self, name: str) -> str | list[str] | None:
        return request.args.get(name)

    def get_query_params(self) -> dict[str, str | list[str]] | None:
        return dict(request.args)

    def get_url(self) -> str:
        public_url = current_app.config.get("PUBLIC_URL")
        if public_url:
            return f"{public_url}{request.full_path.rstrip('?')}"
        return request.url

    def get_user_agent(self) -> str:
        return request.headers.get("User-Agent", "")

    def get_body(self) -> Any:
        return request.get_json(silent=True)


def _setup_x402_middleware(app: Flask, config: Config) -> bool:
    """Set up x402 payment middleware. Returns True if successful."""
    try:
        from x402 import x402ResourceServerSync
        from x402.http import (
            FacilitatorConfig,
            HTTPFacilitatorClientSync,
            HTTPRequestContext,
            PaymentOption,
            RouteConfig,
            x402HTTPResourceServerSync,
        )
        from x402.mechanisms.evm.exact import ExactEvmServerScheme
    except ImportError:
        logger.warning("x402 SDK not available — payment middleware disabled")
        return False

    auth_provider = None
    if config.cdp_api_key_id and config.cdp_api_key_secret:
        try:
            from risk_api.cdp_auth import create_cdp_auth_headers

            from x402.http import CreateHeadersAuthProvider

            auth_provider = CreateHeadersAuthProvider(
                lambda: create_cdp_auth_headers(
                    config.cdp_api_key_id,
                    config.cdp_api_key_secret,
                    config.facilitator_url,
                )
            )
            logger.info("CDP auth provider configured for facilitator")
        except ImportError:
            logger.warning(
                "PyJWT/cryptography not available — CDP auth disabled, "
                "facilitator may reject requests"
            )

    fac_config = FacilitatorConfig(
        url=config.facilitator_url, auth_provider=auth_provider
    )
    facilitator = HTTPFacilitatorClientSync(fac_config)
    resource_server = x402ResourceServerSync(facilitator)
    resource_server.register(config.network, ExactEvmServerScheme())  # type: ignore[arg-type]  # x402 SDK parameter name mismatch

    # Register Bazaar discovery extension so 402 responses include input schema
    try:
        from x402.extensions.bazaar.resource_service import (
            OutputConfig,
            declare_discovery_extension,
        )
        from x402.extensions.bazaar.server import bazaar_resource_server_extension

        resource_server.register_extension(bazaar_resource_server_extension)

        address_schema = {
            "properties": {
                "address": {
                    "type": "string",
                    "pattern": "^0x[0-9a-fA-F]{40}$",
                    "description": BASE_ADDRESS_DESCRIPTION,
                },
            },
            "required": ["address"],
        }
        example_input = {"address": SAFE_EXAMPLE_ADDRESS}

        example_output = {
            "address": SAFE_EXAMPLE_ADDRESS,
            "score": 0,
            "level": "safe",
            "bytecode_size": 4632,
            "findings": [],
            "category_scores": {},
        }

        get_bazaar = declare_discovery_extension(
            input=example_input,
            input_schema=address_schema,
            output=OutputConfig(example=example_output),
        )
        post_bazaar = declare_discovery_extension(
            input=example_input,
            input_schema={
                "type": "object",
                **address_schema,
            },
            body_type="json",
            output=OutputConfig(example=example_output),
        )
    except ImportError:
        logger.warning("Bazaar extension not available — 402 responses will lack input schema")
        get_bazaar = None
        post_bazaar = None

    payment_option = PaymentOption(
        scheme="exact",
        pay_to=config.wallet_address,
        price=config.price,
        network=config.network,
    )
    routes = {
        "GET /analyze": RouteConfig(
            accepts=payment_option,
            description=(
                "Base smart contract security analysis - bytecode risk scoring "
                "with 8 detectors (delegatecall, hidden mint, fee-on-transfer, "
                "selfdestruct, proxy, deployer reputation). Returns a 0-100 "
                'risk score with proxy resolution. "safe" is not a guarantee.'
            ),
            extensions=get_bazaar,
        ),
        "POST /analyze": RouteConfig(
            accepts=payment_option,
            description=(
                "Base smart contract security analysis - bytecode risk scoring "
                "with 8 detectors (delegatecall, hidden mint, fee-on-transfer, "
                "selfdestruct, proxy, deployer reputation). Returns a 0-100 "
                'risk score with proxy resolution. "safe" is not a guarantee.'
            ),
            extensions=post_bazaar,
        ),
    }

    http_server = x402HTTPResourceServerSync(resource_server, routes)

    try:
        http_server.initialize()
    except Exception:
        logger.warning(
            "x402 middleware initialization failed (facilitator unreachable?) "
            "— payment middleware disabled",
            exc_info=True,
        )
        return False

    @app.before_request
    def x402_payment_gate():
        if request.path not in PROTECTED_ROUTES:
            return None

        # HEAD should be gated same as GET for payment purposes;
        # x402 SDK only registers GET/POST routes.
        method = "GET" if request.method == "HEAD" else request.method

        adapter = FlaskHTTPAdapter()
        context = HTTPRequestContext(
            adapter=adapter,
            path=request.path,
            method=method,
        )
        result = http_server.process_http_request(context)

        if result.type == "no-payment-required":
            return None
        elif result.type == "payment-verified":
            # Store payment info for potential settlement after response
            request.environ["x402_payload"] = result.payment_payload
            request.environ["x402_requirements"] = result.payment_requirements
            return None
        else:
            # payment-error: return 402 with payment requirements
            request.environ["funnel_stage"] = "unpaid_402"
            resp = result.response
            if resp is None:
                return Response("Payment Required", status=402)
            body = resp.body
            if not isinstance(body, str):
                body = json.dumps(body)
            return Response(
                body,
                status=resp.status,
                headers=resp.headers,
            )

    @app.after_request
    def x402_settle(response: Response) -> Response:
        if response.status_code == 200 and request.path in PROTECTED_ROUTES:
            payload = request.environ.get("x402_payload")
            requirements = request.environ.get("x402_requirements")
            if payload and requirements:
                try:
                    http_server.process_settlement(payload, requirements)
                except Exception:
                    logger.exception("x402 settlement failed")
        return response

    logger.info("x402 payment middleware enabled for %s", PROTECTED_ROUTES)
    return True


def _configure_request_log_file(app: Flask) -> None:
    """Attach a file handler to the request logger if REQUEST_LOG_PATH is set."""
    import os

    log_path = os.environ.get("REQUEST_LOG_PATH", "")
    if not log_path:
        return

    app.config["REQUEST_LOG_PATH"] = log_path
    os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)

    for handler in list(request_logger.handlers):
        if getattr(handler, "_risk_api_request_log", False):
            request_logger.removeHandler(handler)
            handler.close()

    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler._risk_api_request_log = True  # type: ignore[attr-defined]
    handler.setFormatter(logging.Formatter("%(message)s"))
    request_logger.addHandler(handler)
    request_logger.setLevel(logging.INFO)
    request_logger.propagate = False
    logger.info("Request logging enabled: %s", log_path)


def _configure_analytics_store(app: Flask) -> None:
    """Initialize the durable analytics backend when configured."""
    import os

    db_path = os.environ.get("ANALYTICS_DB_PATH", "")
    if not db_path:
        return

    init_sqlite_store(db_path)
    app.config["ANALYTICS_DB_PATH"] = db_path
    logger.info("Durable analytics enabled: %s", db_path)


def _setup_request_logging(app: Flask) -> None:
    """Log public page views plus /analyze funnel events as structured JSON."""

    @app.before_request
    def _start_timer() -> None:
        request.environ["request_id"] = (
            request.headers.get("X-Request-ID") or uuid4().hex
        )
        if _should_log_request(request.path, request.method):
            request.environ["_req_start"] = time.monotonic()

    @app.after_request
    def _log_request(response: Response) -> Response:
        request_id = request.environ.get("request_id")
        if isinstance(request_id, str) and request_id:
            response.headers["X-Request-ID"] = request_id

        if request.environ.get("skip_request_log"):
            return response
        if not _should_log_request(request.path, request.method):
            return response

        start = request.environ.get("_req_start")
        duration_ms = (
            round((time.monotonic() - start) * 1000) if start else None
        )

        entry: dict[str, object] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "path": request.path,
            "status": response.status_code,
            "paid": request.environ.get("x402_payload") is not None,
            "duration_ms": duration_ms,
            "user_agent": request.headers.get("User-Agent", ""),
            "method": request.method,
            "host": request.host,
            "referer": request.headers.get("Referer", ""),
            "request_id": request_id or "",
        }
        funnel_stage = request.environ.get("funnel_stage") or _public_request_stage(
            request.path
        )
        if isinstance(funnel_stage, str) and funnel_stage:
            entry["funnel_stage"] = funnel_stage

        if request.path == "/analyze":
            entry["address"] = _extract_requested_address()
            error_type = request.environ.get("analyze_error_type")
            if isinstance(error_type, str) and error_type:
                entry["error_type"] = error_type

        if request.path == "/analyze" and response.status_code == 200:
            try:
                data = response.get_json(silent=True)
                if data and isinstance(data, dict):
                    entry["score"] = data.get("score")
                    entry["level"] = data.get("level")
            except Exception:
                pass

        request_logger.info(json.dumps(entry, separators=(",", ":")))

        db_path = app.config.get("ANALYTICS_DB_PATH", "")
        if isinstance(db_path, str) and db_path:
            try:
                append_sqlite_entry(db_path, entry)
            except Exception:
                logger.exception("failed to persist analytics entry")
        return response


def create_app(
    config: Config | None = None,
    *,
    enable_x402: bool = True,
) -> Flask:
    """Flask application factory.

    Pass a Config object for testing; defaults to loading from environment.
    Set enable_x402=False to skip payment middleware (useful for testing).
    """
    if config is None:
        config = load_config()

    app = Flask(__name__)
    app.config["RISK_API_CONFIG"] = config
    if config.erc8004_agent_id is not None:
        app.config["ERC8004_AGENT_ID"] = config.erc8004_agent_id
    if config.public_url:
        app.config["PUBLIC_URL"] = config.public_url

    @app.before_request
    def enforce_canonical_host():
        public_url = app.config.get("PUBLIC_URL", "")
        if not public_url or app.config.get("TESTING"):
            return None
        if request.path == "/health":
            return None

        redirect_target = _canonical_redirect_target(public_url)
        if redirect_target is None:
            return None

        request.environ["skip_request_log"] = True
        return redirect(redirect_target, code=308)

    _configure_request_log_file(app)
    _configure_analytics_store(app)
    _setup_request_logging(app)

    @app.before_request
    def validate_analyze_params():
        """Reject malformed /analyze requests before the x402 paywall."""
        if request.path != "/analyze":
            return None

        address = _extract_requested_address()

        if not address:
            request.environ["funnel_stage"] = "invalid_address"
            request.environ["analyze_error_type"] = "missing_address"
            return jsonify({"error": "Missing 'address' query parameter"}), 422

        if not ADDRESS_RE.match(address):
            request.environ["funnel_stage"] = "invalid_address"
            request.environ["analyze_error_type"] = "invalid_address"
            return (
                jsonify({"error": f"Invalid Ethereum address: {address}"}),
                422,
            )

        # Store validated address for the route handler
        request.environ["validated_address"] = address
        if request.method == "HEAD":
            return None

        try:
            bytecode_hex = get_code(address, config.base_rpc_url)
        except RPCError as e:
            request.environ["funnel_stage"] = "rpc_error"
            request.environ["analyze_error_type"] = "rpc_error"
            return jsonify({"error": f"RPC error: {e}"}), 502

        if _bytecode_size(bytecode_hex) == 0:
            request.environ["funnel_stage"] = "no_bytecode"
            request.environ["analyze_error_type"] = "no_bytecode"
            return jsonify({"error": _no_bytecode_error(address)}), 422

        return None

    if enable_x402:
        _setup_x402_middleware(app, config)

    @app.route("/.well-known/x402-verification.json")
    def x402_verification():
        return jsonify({"x402": "dccd5db92bc9"})

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.route("/")
    def landing():
        request.environ["funnel_stage"] = "landing_view"
        base_url = app.config.get("PUBLIC_URL") or request.url_root.rstrip("/")
        json_ld = json.dumps({
            "@context": "https://schema.org",
            "@type": "WebAPI",
            "name": "Augur",
            "description": (
                "Base mainnet smart contract bytecode risk scoring API for agents. "
                "Runs deterministic detectors and returns a 0-100 score with findings."
            ),
            "url": base_url,
            "provider": {
                "@type": "Organization",
                "name": "risk-api",
            },
            "offers": {
                "@type": "Offer",
                "price": "0.10",
                "priceCurrency": "USD",
                "url": f"{base_url}/analyze",
                "description": "Per-call pricing via x402 protocol in USDC on Base",
            },
            "documentation": f"{base_url}/openapi.json",
        })
        faq_json_ld = json.dumps({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": "What does Augur do?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": (
                            "Augur is a Base mainnet smart contract bytecode risk scoring API "
                            "for agents and the developers building them. It fetches on-chain "
                            "bytecode for a contract on Base and runs "
                            "8 detectors (proxy, reentrancy, selfdestruct, honeypot, hidden mint, "
                            "fee manipulation, delegatecall, deployer reputation) to produce a "
                            "composite 0-100 risk score with detailed findings."
                        ),
                    },
                },
                {
                    "@type": "Question",
                    "name": "How much does it cost?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": (
                            "$0.10 per call, paid in USDC on Base via the x402 protocol. "
                            "No subscription, no API key, no signup required."
                        ),
                    },
                },
                {
                    "@type": "Question",
                    "name": "How do AI agents pay for the API?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": (
                            "Via the x402 protocol: send GET /analyze?address=<contract>, "
                            "receive a 402 response with payment details, sign a USDC "
                            "authorization on Base, and retry the request with the "
                            "PAYMENT-SIGNATURE header. The entire flow is automated by "
                            "x402-compatible HTTP clients."
                        ),
                    },
                },
                {
                    "@type": "Question",
                    "name": "What risk patterns does Augur detect?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": (
                            "8 detectors: proxy contracts (EIP-1967/1822/OZ), reentrancy "
                            "vulnerabilities, selfdestruct capability, honeypot patterns, "
                            "hidden mint functions, fee manipulation, delegatecall usage, "
                            "and deployer wallet reputation via Basescan."
                        ),
                    },
                },
                {
                    "@type": "Question",
                    "name": "What chains are supported?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": "Base (EIP-155:8453). Payment is also in USDC on Base.",
                    },
                },
                {
                    "@type": "Question",
                    "name": "Does a safe score mean the contract is guaranteed safe?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": (
                            'No. "safe" means Augur did not detect major bytecode-level risk '
                            "signals in this scan. It is not a full security audit or guarantee."
                        ),
                    },
                },
                {
                    "@type": "Question",
                    "name": "Do I need an API key?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": (
                            "No. x402 payment is the only authentication. Any agent or "
                            "client with a USDC wallet on Base can call the API immediately."
                        ),
                    },
                },
            ],
        })
        html = LANDING_HTML.replace("__BASE_URL__", base_url).replace(
            "__JSON_LD__", json_ld
        ).replace("__FAQ_JSON_LD__", faq_json_ld)
        return Response(html, content_type="text/html")

    @app.route("/robots.txt")
    def robots_txt():
        base_url = app.config.get("PUBLIC_URL") or request.url_root.rstrip("/")
        body = (
            "User-agent: *\n"
            "Allow: /\n"
            "Allow: /openapi.json\n"
            "Allow: /.well-known/\n"
            "Allow: /agent-metadata.json\n"
            "Allow: /llms.txt\n"
            "Allow: /llms-full.txt\n"
            "Disallow: /stats\n"
            "Disallow: /dashboard\n"
            "\n"
            f"Sitemap: {base_url}/sitemap.xml\n"
        )
        return Response(body, content_type="text/plain")

    @app.route("/sitemap.xml")
    def sitemap_xml():
        base_url = app.config.get("PUBLIC_URL") or request.url_root.rstrip("/")
        paths = [
            "/",
            "/mcp",
            "/how-payment-works",
            *INTENT_PAGES.keys(),
            *REPORT_PAGES.keys(),
            "/openapi.json",
            "/agent-metadata.json",
            "/.well-known/ai-plugin.json",
            "/.well-known/agent-card.json",
            "/.well-known/x402",
            "/.well-known/api-catalog",
            "/llms.txt",
            "/llms-full.txt",
        ]
        urls = "\n".join(
            f"  <url><loc>{base_url}{p}</loc></url>" for p in paths
        )
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{urls}\n"
            "</urlset>\n"
        )
        return Response(xml, content_type="application/xml")

    @app.route("/how-payment-works")
    def how_payment_works():
        request.environ["funnel_stage"] = "how_payment_view"
        base_url = app.config.get("PUBLIC_URL") or request.url_root.rstrip("/")
        html = PAYMENT_GUIDE_HTML.replace("__BASE_URL__", base_url)
        return Response(html, content_type="text/html")

    @app.route("/mcp")
    def mcp_guide():
        request.environ["funnel_stage"] = "mcp_guide_view"
        base_url = app.config.get("PUBLIC_URL") or request.url_root.rstrip("/")
        html = MCP_GUIDE_HTML.replace("__BASE_URL__", base_url)
        return Response(html, content_type="text/html")

    @app.route("/reports/<path:slug>")
    def proof_report(slug: str):
        report_path = f"/reports/{slug}"
        if report_path not in REPORT_PAGES:
            return jsonify({"error": "report not found"}), 404
        request.environ["funnel_stage"] = _public_request_stage(report_path)
        base_url = app.config.get("PUBLIC_URL") or request.url_root.rstrip("/")
        return Response(
            render_report_page(base_url, report_path),
            content_type="text/html",
        )

    @app.route("/honeypot-detection-api")
    @app.route("/proxy-risk-api")
    @app.route("/deployer-reputation-api")
    def buyer_intent_page():
        request.environ["funnel_stage"] = (
            PUBLIC_REQUEST_STAGE_BY_PATH.get(request.path, "intent_page_view")
        )
        base_url = app.config.get("PUBLIC_URL") or request.url_root.rstrip("/")
        return Response(
            _render_intent_page(base_url, request.path),
            content_type="text/html",
        )

    @app.route("/dashboard")
    def dashboard():
        return Response(DASHBOARD_HTML, content_type="text/html")

    @app.route("/stats")
    def stats():
        """Basic analytics from the configured request-event store."""
        analytics_db_path = app.config.get("ANALYTICS_DB_PATH", "")
        log_path = app.config.get("REQUEST_LOG_PATH", "")
        if analytics_db_path:
            return jsonify(
                build_stats_payload(
                    iter_sqlite_entries(str(analytics_db_path)),
                    intent_page_stages=INTENT_PAGE_STAGES,
                    machine_doc_stages=MACHINE_DOC_STAGES,
                    storage_backend="sqlite",
                    storage_path=str(analytics_db_path),
                    storage_durable=True,
                )
            )
        if not log_path:
            return jsonify({"error": "logging not configured"}), 501

        import os
        if not os.path.exists(log_path):
            payload = empty_stats_payload()
            payload["storage_backend"] = "jsonl"
            payload["storage_path"] = str(log_path)
            payload["storage_durable"] = False
            return jsonify(payload)

        return jsonify(
            build_stats_payload(
                iter_jsonl_entries(str(log_path)),
                intent_page_stages=INTENT_PAGE_STAGES,
                machine_doc_stages=MACHINE_DOC_STAGES,
                storage_backend="jsonl",
                storage_path=str(log_path),
                storage_durable=False,
            )
        )

    @app.route("/avatar.png")
    def avatar():
        if _AVATAR_BYTES is None:
            return Response("Avatar not found", status=404)
        return Response(_AVATAR_BYTES, content_type="image/png")

    @app.route("/openapi.json")
    def openapi_spec():
        spec = dict(OPENAPI_SPEC)
        base_url = app.config.get("PUBLIC_URL") or request.url_root.rstrip("/")
        spec["servers"] = [{"url": base_url}]
        return jsonify(spec)

    @app.route("/.well-known/ai-plugin.json")
    def ai_plugin():
        base_url = app.config.get("PUBLIC_URL") or request.url_root.rstrip("/")
        return jsonify({
            "schema_version": "v1",
            "name_for_human": "Augur",
            "name_for_model": "augur",
            "description_for_human": (
                "Base mainnet smart contract bytecode risk scoring via x402. "
                "Analyzes bytecode for proxy, reentrancy, selfdestruct, "
                "honeypot, hidden mint, fee manipulation, delegatecall, and "
                "deployer reputation patterns. Returns a 0-100 risk score with findings."
            ),
            "description_for_model": (
                "Analyze Base mainnet smart contract bytecode. "
                "Send a Base contract address to /analyze and receive a 0-100 "
                'risk score with detailed findings from 8 detectors. "safe" is '
                "not a guarantee or audit result. Requires x402 payment of $0.10 USDC on Base."
            ),
            "auth": {"type": "none"},
            "api": {
                "type": "openapi",
                "url": f"{base_url}/openapi.json",
            },
        })

    @app.route("/.well-known/agent.json")
    @app.route("/.well-known/agent-card.json")
    def a2a_agent_card():
        """A2A (Agent-to-Agent) protocol agent card for discovery."""
        base_url = app.config.get("PUBLIC_URL") or request.url_root.rstrip("/")
        return jsonify({
            "name": "Augur",
            "description": (
                "Base mainnet smart contract bytecode risk scoring API for agents. "
                "Analyzes bytecode patterns and returns a 0-100 risk score with findings. "
                "Pay $0.10/call via x402 in USDC on Base."
            ),
            "provider": {"organization": "risk-api"},
            "version": "1.0.0",
            "url": base_url,
            "interfaces": [
                {
                    "type": "http",
                    "baseUrl": base_url,
                }
            ],
            "capabilities": {
                "streaming": False,
                "pushNotifications": False,
                "extendedAgentCard": False,
            },
            "skills": [
                {
                    "id": "analyze-contract",
                    "name": "Risk Classification (OASF 1304)",
                    "description": (
                        "Fetch on-chain bytecode for a Base mainnet contract address "
                        "and run 8 detectors to produce a 0-100 risk score."
                    ),
                    "tags": ["oasf:security_privacy"],
                },
            ],
            "security": [],
            "securitySchemes": {},
            "defaultInputModes": ["application/json"],
            "defaultOutputModes": ["application/json"],
        })

    @app.route("/llms.txt")
    def llms_txt():
        base_url = app.config.get("PUBLIC_URL") or request.url_root.rstrip("/")
        body = LLMS_TXT.replace("__BASE_URL__", base_url)
        return Response(body, content_type="text/plain; charset=utf-8")

    @app.route("/llms-full.txt")
    def llms_full_txt():
        base_url = app.config.get("PUBLIC_URL") or request.url_root.rstrip("/")
        body = LLMS_FULL_TXT.replace("__BASE_URL__", base_url)
        return Response(body, content_type="text/plain; charset=utf-8")

    @app.route("/.well-known/x402")
    def wellknown_x402():
        """x402 discovery document for x402scan and compatible crawlers."""
        base_url = app.config.get("PUBLIC_URL") or request.url_root.rstrip("/")
        return jsonify({
            "version": 1,
            "resources": [
                f"{base_url}/analyze",
            ],
            "instructions": (
                "# Augur - Base Smart Contract Security Analysis\n\n"
                "Bytecode-level risk scoring for Base mainnet smart contracts. "
                "8 detectors: delegatecall, hidden mint, fee-on-transfer, "
                "selfdestruct, reentrancy patterns, honeypot, proxy detection, "
                "deployer reputation (Basescan). Returns a 0-100 composite "
                "risk score with per-category breakdown.\n\n"
                "## Usage\n\n"
                "GET /analyze?address={base_contract_address}\n"
                "POST /analyze with JSON body: {\"address\": \"0x...\"}\n\n"
                "## Output\n\n"
                "- `score`: 0-100 (safe=0-15, low=16-35, medium=36-55, "
                "high=56-75, critical=76-100)\n"
                '- `safe`: no major bytecode-level risk signals detected in this scan, not a guarantee\n'
                "- `findings`: array of detector results with severity and points\n"
                "- `category_scores`: per-category breakdown\n"
                "- `implementation`: proxy target analysis (when proxy detected)\n\n"
                "## Pricing\n\n"
                "$0.10/call via x402 (USDC on Base). No API key needed.\n\n"
                f"Agent Card: {base_url}/.well-known/agent-card.json\n"
                f"OpenAPI: {base_url}/openapi.json"
            ),
        })

    @app.route("/.well-known/api-catalog")
    def api_catalog():
        """RFC 9727 API Catalog for machine discovery of API descriptions."""
        base_url = app.config.get("PUBLIC_URL") or request.url_root.rstrip("/")
        catalog = {
            "linkset": [{
                "anchor": f"{base_url}/.well-known/api-catalog",
                "service-desc": [
                    {"href": f"{base_url}/openapi.json", "type": "application/json"},
                ],
                "service-doc": [
                    {"href": f"{base_url}/", "type": "text/html"},
                ],
            }],
        }
        return Response(
            json.dumps(catalog),
            content_type=(
                'application/linkset+json;'
                ' profile="https://www.rfc-editor.org/info/rfc9727"'
            ),
        )

    @app.route("/agent-metadata.json")
    def agent_metadata():
        """ERC-8004 agent registration metadata."""
        base_url = app.config.get("PUBLIC_URL") or request.url_root.rstrip("/")
        wallet_addr = config.wallet_address
        metadata: dict[str, object] = {
            "type": "https://eips.ethereum.org/EIPS/eip-8004#registration-v1",
            "name": "Augur",
            "description": (
                "Base mainnet smart contract bytecode risk scoring API for agents. "
                "Analyzes bytecode patterns (proxy detection, reentrancy, "
                "selfdestruct, honeypot, hidden mint, fee manipulation, "
                "delegatecall, deployer reputation) and returns a composite 0-100 "
                'risk score with findings. "safe" is not a guarantee or audit. '
                "Pay $0.10/call via x402 in USDC on Base. "
                "Endpoint: GET /analyze?address={base_contract_address}"
            ),
            "services": [
                {
                    "name": "web",
                    "endpoint": base_url.rstrip("/") + "/",
                },
                {
                    "name": "A2A",
                    "endpoint": f"{base_url}/.well-known/agent-card.json",
                    "version": "0.3.0",
                },
                {
                    "name": "OASF",
                    "endpoint": "https://github.com/agntcy/oasf/",
                    "version": "0.8.0",
                    "skills": ["security_privacy"],
                    "domains": ["technology"],
                },
                {
                    "name": "agentWallet",
                    "endpoint": f"eip155:8453:{wallet_addr}",
                },
            ],
            "x402Support": True,
            "active": True,
            "supportedTrust": ["reputation"],
            "image": f"{base_url}/avatar.png",
            "updatedAt": int(time.time()),
            "pricing": {
                "amount": "0.10",
                "currency": "USDC",
                "network": "eip155:8453",
            },
            "openapi_url": f"{base_url}/openapi.json",
            "capabilities": [
                "contract risk scoring",
                "proxy detection",
                "bytecode analysis",
                "honeypot detection",
                "reentrancy detection",
                "security assessment",
            ],
        }

        agent_id = app.config.get("ERC8004_AGENT_ID")
        if agent_id is not None:
            metadata["registrations"] = [
                {
                    "agentId": agent_id,
                    "agentRegistry": (
                        "eip155:8453:"
                        "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
                    ),
                }
            ]

        return jsonify(metadata)

    @app.route("/analyze", methods=["GET", "POST"])
    def analyze():
        # Address already validated by validate_analyze_params before_request hook
        address: str = request.environ["validated_address"]

        try:
            result = analyze_contract(
                address, config.base_rpc_url, config.basescan_api_key
            )
        except NoBytecodeError as e:
            request.environ["funnel_stage"] = "no_bytecode"
            request.environ["analyze_error_type"] = "no_bytecode"
            return jsonify({"error": str(e)}), 422
        except RPCError as e:
            request.environ["funnel_stage"] = "rpc_error"
            request.environ["analyze_error_type"] = "rpc_error"
            return jsonify({"error": f"RPC error: {e}"}), 502

        if request.environ.get("x402_payload") is not None:
            request.environ["funnel_stage"] = "paid_request"
        else:
            request.environ["funnel_stage"] = "analyze_success"

        response_data: dict[str, object] = {
            "address": result.address,
            "score": result.score,
            "level": result.level.value,
            "bytecode_size": result.bytecode_size,
            "findings": [
                {
                    "detector": f.detector,
                    "severity": f.severity.value,
                    "title": f.title,
                    "description": f.description,
                    "points": f.points,
                }
                for f in result.findings
            ],
            "category_scores": result.category_scores,
        }

        if result.implementation is not None:
            impl = result.implementation
            response_data["implementation"] = {
                "address": impl.address,
                "bytecode_size": impl.bytecode_size,
                "findings": [
                    {
                        "detector": f.detector,
                        "severity": f.severity.value,
                        "title": f.title,
                        "description": f.description,
                        "points": f.points,
                    }
                    for f in impl.findings
                ],
                "category_scores": impl.category_scores,
            }

        return jsonify(response_data)

    return app
