"""Flask application with x402 payment middleware."""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from flask import Flask, Response, current_app, jsonify, redirect, request

from risk_api.analysis.engine import analyze_contract
from risk_api.chain.rpc import RPCError, get_code
from risk_api.config import Config, load_config

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
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  background:#0f1117;color:#e0e0e0;padding:24px;max-width:1200px;margin:0 auto}
h1{font-size:1.4rem;color:#a0aec0;margin-bottom:20px;font-weight:500}
h1 span{color:#63b3ed}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-bottom:28px}
.card{background:#1a1d29;border:1px solid #2d3148;border-radius:10px;padding:20px}
.card .label{font-size:.75rem;color:#718096;text-transform:uppercase;letter-spacing:.05em}
.card .value{font-size:2rem;font-weight:700;margin-top:4px}
.card .value.blue{color:#63b3ed}
.card .value.green{color:#68d391}
.card .value.orange{color:#f6ad55}
.section{background:#1a1d29;border:1px solid #2d3148;border-radius:10px;padding:20px;margin-bottom:20px}
.section h2{font-size:.9rem;color:#a0aec0;margin-bottom:14px;font-weight:500}
#chart-container{position:relative;height:260px}
#chart-fallback{display:none;color:#718096;padding:40px;text-align:center}
table{width:100%;border-collapse:collapse;font-size:.85rem}
th{text-align:left;color:#718096;font-weight:500;padding:8px 10px;border-bottom:1px solid #2d3148}
td{padding:8px 10px;border-bottom:1px solid #1e2235}
.addr{font-family:monospace;font-size:.8rem;color:#90cdf4}
.badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:.7rem;font-weight:600;text-transform:uppercase}
.badge.safe{background:#22543d;color:#68d391}
.badge.low{background:#2a4365;color:#63b3ed}
.badge.medium{background:#744210;color:#f6ad55}
.badge.high{background:#742a2a;color:#fc8181}
.badge.critical{background:#63171b;color:#feb2b2}
.badge.paid{background:#2a4365;color:#63b3ed}
.badge.unpaid{background:#2d3748;color:#718096}
.ts{color:#718096;font-size:.75rem}
.status{text-align:center}
.status-bar{font-size:.7rem;color:#4a5568;margin-top:16px;text-align:right}
</style>
</head>
<body>
<h1><span>risk-api</span> dashboard</h1>
<div class="cards">
  <div class="card"><div class="label">Tracked Events</div><div class="value blue" id="total">-</div></div>
  <div class="card"><div class="label">Paid Requests</div><div class="value green" id="paid">-</div></div>
  <div class="card"><div class="label">Avg Response Time</div><div class="value orange" id="avgdur">-</div></div>
</div>
<div class="section">
  <h2>Requests per hour</h2>
  <div id="chart-container"><canvas id="chart"></canvas></div>
  <div id="chart-fallback">Chart unavailable (Chart.js CDN unreachable)</div>
</div>
<div class="section">
  <h2>Recent events</h2>
  <table>
    <thead><tr><th>Time</th><th>Stage</th><th>Address</th><th>Status</th><th>Score</th><th>Level</th><th>Paid</th><th>Duration</th></tr></thead>
    <tbody id="recent"></tbody>
  </table>
</div>
<div class="status-bar">Auto-refreshes every 30s &middot; <span id="updated"></span></div>

<script>
var chartInstance=null,chartLoaded=false;
function loadChart(){
  return new Promise(function(resolve){
    if(window.Chart){chartLoaded=true;resolve();return}
    var s=document.createElement('script');
    s.src='https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js';
    s.onload=function(){chartLoaded=true;resolve()};
    s.onerror=function(){
      document.getElementById('chart-container').querySelector('canvas').style.display='none';
      document.getElementById('chart-fallback').style.display='block';
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
function truncAddr(a){
  if(!a||a.length<12)return a||'';
  return a.slice(0,6)+'\\u2026'+a.slice(-4);
}
function stageLabel(stage){
  var labels={
    landing_view:'landing',
    unpaid_402:'402 attempt',
    invalid_address:'invalid',
    no_bytecode:'no bytecode',
    paid_request:'paid',
    analyze_success:'success',
    rpc_error:'rpc error'
  };
  return labels[stage]||stage||'';
}
function refresh(){
  fetch('/stats').then(function(r){return r.json()}).then(function(d){
    document.getElementById('total').textContent=d.total_requests;
    document.getElementById('paid').textContent=d.paid_requests;
    document.getElementById('avgdur').textContent=d.avg_duration_ms?d.avg_duration_ms+'ms':'-';
    document.getElementById('updated').textContent='Updated '+new Date().toLocaleTimeString();

    if(chartLoaded&&window.Chart&&d.hourly){
      var labels=d.hourly.map(function(h){return h.hour.slice(11,16)});
      var paidData=d.hourly.map(function(h){return h.paid});
      var unpaidData=d.hourly.map(function(h){return h.count-h.paid});
      if(chartInstance){chartInstance.destroy()}
      var ctx=document.getElementById('chart').getContext('2d');
      chartInstance=new Chart(ctx,{type:'bar',data:{labels:labels,datasets:[
        {label:'Paid',data:paidData,backgroundColor:'#68d391',borderRadius:3},
        {label:'Unpaid',data:unpaidData,backgroundColor:'#4a5568',borderRadius:3}
      ]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#a0aec0'}}},
        scales:{x:{stacked:true,ticks:{color:'#718096'},grid:{color:'#1e2235'}},
                y:{stacked:true,beginAtZero:true,ticks:{color:'#718096',stepSize:1},grid:{color:'#1e2235'}}}}});
    }

    var tbody=document.getElementById('recent');
    tbody.innerHTML='';
    var rows=(d.recent||[]).slice().reverse();
    rows.forEach(function(e){
      var tr=document.createElement('tr');
      var lvl=e.level||'';
      var stage=stageLabel(e.funnel_stage);
      var paidBadge=e.paid?'<span class="badge paid">paid</span>':'<span class="badge unpaid">free</span>';
      tr.innerHTML='<td class="ts">'+relTime(e.ts)+'</td>'
        +'<td>'+(stage?'<span class="badge unpaid">'+stage+'</span>':'')+'</td>'
        +'<td class="addr">'+(e.address?truncAddr(e.address):'')</td>'
        +'<td class="status">'+e.status+'</td>'
        +'<td>'+(e.score!=null?e.score:'')+'</td>'
        +'<td>'+(lvl?'<span class="badge '+lvl+'">'+lvl+'</span>':'')+'</td>'
        +'<td>'+paidBadge+'</td>'
        +'<td>'+(e.duration_ms!=null?e.duration_ms+'ms':'')+'</td>';
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
<h2>Discovery &amp; Integration</h2>
<div class="links">
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

1. **Proxy Detection** - EIP-1967, EIP-1822, and OpenZeppelin proxy slots. \
Proxy contracts auto-resolve implementation (max 1 hop).
2. **Reentrancy** - CALL before state update patterns that enable reentrancy attacks.
3. **Selfdestruct** - Contract contains SELFDESTRUCT opcode, allowing destruction.
4. **Honeypot** - Transfer restriction patterns that prevent token selling.
5. **Hidden Mint** - Unauthorized token creation functions not visible in the ABI.
6. **Fee Manipulation** - Dynamic fee extraction patterns that can drain value.
7. **Delegatecall** - External code execution that can change contract state.
8. **Deployer Reputation** - Basescan deployer wallet history analysis.

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
2. Client signs USDC `transferWithAuthorization` on Base
3. Client retries with `PAYMENT-SIGNATURE: <proof>` header
4. Receives 200 with risk analysis JSON

## Links

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

    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    request_logger.addHandler(handler)
    request_logger.setLevel(logging.INFO)
    logger.info("Request logging enabled: %s", log_path)


def _setup_request_logging(app: Flask) -> None:
    """Log landing views plus /analyze funnel events as structured JSON."""

    @app.before_request
    def _start_timer() -> None:
        if request.path in {"/", "/analyze"}:
            request.environ["_req_start"] = time.monotonic()

    @app.after_request
    def _log_request(response: Response) -> Response:
        if request.environ.get("skip_request_log"):
            return response
        if request.path not in {"/", "/analyze"}:
            return response
        if request.path == "/" and request.method != "GET":
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
        }
        funnel_stage = request.environ.get("funnel_stage")
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

    _setup_request_logging(app)
    _configure_request_log_file(app)

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
            "/how-payment-works",
            *INTENT_PAGES.keys(),
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
        base_url = app.config.get("PUBLIC_URL") or request.url_root.rstrip("/")
        html = PAYMENT_GUIDE_HTML.replace("__BASE_URL__", base_url)
        return Response(html, content_type="text/html")

    @app.route("/honeypot-detection-api")
    @app.route("/proxy-risk-api")
    @app.route("/deployer-reputation-api")
    def buyer_intent_page():
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
        """Basic analytics from the request log."""
        log_path = app.config.get("REQUEST_LOG_PATH", "")
        if not log_path:
            return jsonify({"error": "logging not configured"}), 501

        import os
        if not os.path.exists(log_path):
            return jsonify({
                "total_requests": 0,
                "paid_requests": 0,
                "funnel": {
                    "landing_views": 0,
                    "valid_unpaid_402_attempts": 0,
                    "invalid_address_requests": 0,
                    "no_bytecode_requests": 0,
                    "paid_requests": 0,
                },
                "avg_duration_ms": 0,
                "hourly": [],
                "recent": [],
            })

        total = 0
        paid = 0
        duration_sum = 0.0
        duration_count = 0
        hourly_buckets: dict[str, dict[str, int]] = {}
        recent: list[dict[str, object]] = []
        funnel = {
            "landing_views": 0,
            "valid_unpaid_402_attempts": 0,
            "invalid_address_requests": 0,
            "no_bytecode_requests": 0,
            "paid_requests": 0,
        }
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                total += 1
                if entry.get("paid"):
                    paid += 1

                stage = entry.get("funnel_stage", "")
                if not isinstance(stage, str) or not stage:
                    if entry.get("path") == "/":
                        stage = "landing_view"
                    elif entry.get("paid") and entry.get("status") == 200:
                        stage = "paid_request"
                    elif entry.get("status") == 402:
                        stage = "unpaid_402"
                    elif entry.get("status") == 422:
                        stage = "invalid_address"
                    else:
                        stage = ""

                dur = entry.get("duration_ms")
                if isinstance(dur, (int, float)):
                    duration_sum += dur
                    duration_count += 1

                ts = entry.get("ts", "")
                if len(ts) >= 13:
                    hour_key = ts[:13] + ":00:00Z"
                    bucket = hourly_buckets.get(hour_key)
                    if bucket is None:
                        bucket = {
                            "count": 0,
                            "paid": 0,
                            "dur_sum": 0,
                            "dur_n": 0,
                            "landing_views": 0,
                            "valid_unpaid_402_attempts": 0,
                            "invalid_address_requests": 0,
                            "no_bytecode_requests": 0,
                            "paid_requests": 0,
                        }
                        hourly_buckets[hour_key] = bucket
                    bucket["count"] += 1
                    if entry.get("paid"):
                        bucket["paid"] += 1
                    if isinstance(dur, (int, float)):
                        bucket["dur_sum"] += int(dur)
                        bucket["dur_n"] += 1

                    if stage == "landing_view":
                        bucket["landing_views"] += 1
                    elif stage == "unpaid_402":
                        bucket["valid_unpaid_402_attempts"] += 1
                    elif stage == "invalid_address":
                        bucket["invalid_address_requests"] += 1
                    elif stage == "no_bytecode":
                        bucket["no_bytecode_requests"] += 1
                    elif stage == "paid_request":
                        bucket["paid_requests"] += 1

                if stage == "landing_view":
                    funnel["landing_views"] += 1
                elif stage == "unpaid_402":
                    funnel["valid_unpaid_402_attempts"] += 1
                elif stage == "invalid_address":
                    funnel["invalid_address_requests"] += 1
                elif stage == "no_bytecode":
                    funnel["no_bytecode_requests"] += 1
                elif stage == "paid_request":
                    funnel["paid_requests"] += 1

                recent.append(entry)

        hourly = [
            {
                "hour": h,
                "count": b["count"],
                "paid": b["paid"],
                "landing_views": b["landing_views"],
                "valid_unpaid_402_attempts": b["valid_unpaid_402_attempts"],
                "invalid_address_requests": b["invalid_address_requests"],
                "no_bytecode_requests": b["no_bytecode_requests"],
                "paid_requests": b["paid_requests"],
                "avg_duration_ms": (
                    round(b["dur_sum"] / b["dur_n"]) if b["dur_n"] else 0
                ),
            }
            for h, b in sorted(hourly_buckets.items())
        ]

        return jsonify({
            "total_requests": total,
            "paid_requests": paid,
            "funnel": funnel,
            "avg_duration_ms": (
                round(duration_sum / duration_count) if duration_count else 0
            ),
            "hourly": hourly,
            "recent": recent[-20:],
        })

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
