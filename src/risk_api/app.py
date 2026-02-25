"""Flask application with x402 payment middleware."""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from flask import Flask, Response, jsonify, request

from risk_api.analysis.engine import analyze_contract
from risk_api.chain.rpc import RPCError
from risk_api.config import Config, load_config

logger = logging.getLogger(__name__)
request_logger = logging.getLogger("risk_api.requests")

# Ethereum address pattern: 0x followed by 40 hex chars
ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")

# Routes that require x402 payment
PROTECTED_ROUTES = {"/analyze"}

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
        "title": "Smart Contract Risk Scorer",
        "version": "1.0.0",
        "description": (
            "EVM smart contract risk scoring API on Base. "
            "Analyzes bytecode patterns (proxy detection, reentrancy, "
            "selfdestruct, honeypot, hidden mint, fee manipulation, "
            "delegatecall) and returns a composite 0-100 risk score. "
            "Pay $0.10/call via x402 in USDC on Base."
        ),
        "contact": {
            "url": "https://github.com/JleviEderer/risk-api",
        },
    },
    "paths": {
        "/analyze": {
            "get": {
                "operationId": "analyzeContract",
                "summary": "Analyze a smart contract for risk",
                "description": (
                    "Fetches on-chain bytecode for the given contract address "
                    "and runs 8 detectors (proxy, reentrancy, selfdestruct, "
                    "honeypot, hidden mint, fee manipulation, delegatecall, "
                    "deployer reputation). Returns a composite 0-100 risk score."
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
                        "description": "EVM contract address (0x-prefixed, 40 hex chars)",
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Risk analysis result",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/AnalysisResult"},
                            }
                        },
                    },
                    "402": {
                        "description": "Payment required — send x402 payment and retry",
                    },
                    "422": {
                        "description": "Invalid or missing contract address",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "error": {"type": "string"},
                                    },
                                },
                            }
                        },
                    },
                },
                "x-x402-price": "$0.10",
                "x-x402-network": "eip155:8453",
                "x-x402-pay-to": "0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891",
            },
            "post": {
                "operationId": "analyzeContractPost",
                "summary": "Analyze a smart contract for risk (POST)",
                "description": "Same as GET but accepts address in JSON body.",
                "parameters": [
                    {
                        "name": "address",
                        "in": "query",
                        "required": False,
                        "schema": {
                            "type": "string",
                            "pattern": "^0x[0-9a-fA-F]{40}$",
                        },
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
                            }
                        },
                    },
                    "402": {
                        "description": "Payment required — send x402 payment and retry",
                    },
                    "422": {
                        "description": "Invalid or missing contract address",
                    },
                },
                "x-x402-price": "$0.10",
                "x-x402-network": "eip155:8453",
                "x-x402-pay-to": "0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891",
            },
        },
    },
    "components": {
        "schemas": {
            "Finding": {
                "type": "object",
                "properties": {
                    "detector": {"type": "string"},
                    "severity": {
                        "type": "string",
                        "enum": ["info", "low", "medium", "high", "critical"],
                    },
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "points": {"type": "integer"},
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
                    "address": {"type": "string"},
                    "score": {"type": "integer", "minimum": 0, "maximum": 100},
                    "level": {
                        "type": "string",
                        "enum": ["safe", "low", "medium", "high", "critical"],
                    },
                    "bytecode_size": {"type": "integer"},
                    "findings": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/Finding"},
                    },
                    "category_scores": {
                        "type": "object",
                        "additionalProperties": {"type": "number"},
                    },
                    "implementation": {
                        "$ref": "#/components/schemas/ImplementationResult",
                    },
                },
                "required": [
                    "address", "score", "level", "bytecode_size",
                    "findings", "category_scores",
                ],
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
  <div class="card"><div class="label">Total Requests</div><div class="value blue" id="total">-</div></div>
  <div class="card"><div class="label">Paid Requests</div><div class="value green" id="paid">-</div></div>
  <div class="card"><div class="label">Avg Response Time</div><div class="value orange" id="avgdur">-</div></div>
</div>
<div class="section">
  <h2>Requests per hour</h2>
  <div id="chart-container"><canvas id="chart"></canvas></div>
  <div id="chart-fallback">Chart unavailable (Chart.js CDN unreachable)</div>
</div>
<div class="section">
  <h2>Recent requests</h2>
  <table>
    <thead><tr><th>Time</th><th>Address</th><th>Status</th><th>Score</th><th>Level</th><th>Paid</th><th>Duration</th></tr></thead>
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
      var paidBadge=e.paid?'<span class="badge paid">paid</span>':'<span class="badge unpaid">free</span>';
      tr.innerHTML='<td class="ts">'+relTime(e.ts)+'</td>'
        +'<td class="addr">'+truncAddr(e.address)+'</td>'
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

    fac_config = FacilitatorConfig(url=config.facilitator_url)
    facilitator = HTTPFacilitatorClientSync(fac_config)
    resource_server = x402ResourceServerSync(facilitator)
    resource_server.register(config.network, ExactEvmServerScheme())  # type: ignore[arg-type]  # x402 SDK parameter name mismatch

    payment_option = PaymentOption(
        scheme="exact",
        pay_to=config.wallet_address,
        price=config.price,
        network=config.network,
    )
    routes = {
        "GET /analyze": RouteConfig(
            accepts=payment_option,
            description="Smart contract risk scoring",
        ),
        "POST /analyze": RouteConfig(
            accepts=payment_option,
            description="Smart contract risk scoring",
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

        adapter = FlaskHTTPAdapter()
        context = HTTPRequestContext(
            adapter=adapter,
            path=request.path,
            method=request.method,
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
    """Log every /analyze request as structured JSON for analytics."""

    @app.before_request
    def _start_timer() -> None:
        if request.path == "/analyze":
            request.environ["_req_start"] = time.monotonic()

    @app.after_request
    def _log_analyze(response: Response) -> Response:
        if request.path != "/analyze":
            return response

        start = request.environ.get("_req_start")
        duration_ms = (
            round((time.monotonic() - start) * 1000) if start else None
        )

        address = request.args.get("address", "")
        if not address and request.is_json:
            body = request.get_json(silent=True)
            if body and isinstance(body, dict):
                address = str(body.get("address", ""))

        entry: dict[str, object] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "address": address,
            "status": response.status_code,
            "paid": request.environ.get("x402_payload") is not None,
            "duration_ms": duration_ms,
            "user_agent": request.headers.get("User-Agent", ""),
            "method": request.method,
        }

        if response.status_code == 200:
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

    _setup_request_logging(app)
    _configure_request_log_file(app)

    if enable_x402:
        _setup_x402_middleware(app, config)

    @app.route("/.well-known/x402-verification.json")
    def x402_verification():
        return jsonify({"x402": "64cb3a6a29bb"})

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

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

                dur = entry.get("duration_ms")
                if isinstance(dur, (int, float)):
                    duration_sum += dur
                    duration_count += 1

                ts = entry.get("ts", "")
                if len(ts) >= 13:
                    hour_key = ts[:13] + ":00:00Z"
                    bucket = hourly_buckets.get(hour_key)
                    if bucket is None:
                        bucket = {"count": 0, "paid": 0, "dur_sum": 0, "dur_n": 0}
                        hourly_buckets[hour_key] = bucket
                    bucket["count"] += 1
                    if entry.get("paid"):
                        bucket["paid"] += 1
                    if isinstance(dur, (int, float)):
                        bucket["dur_sum"] += int(dur)
                        bucket["dur_n"] += 1

                recent.append(entry)

        hourly = [
            {
                "hour": h,
                "count": b["count"],
                "paid": b["paid"],
                "avg_duration_ms": (
                    round(b["dur_sum"] / b["dur_n"]) if b["dur_n"] else 0
                ),
            }
            for h, b in sorted(hourly_buckets.items())
        ]

        return jsonify({
            "total_requests": total,
            "paid_requests": paid,
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
            "name_for_human": "Smart Contract Risk Scorer",
            "name_for_model": "smart_contract_risk_scorer",
            "description_for_human": (
                "EVM smart contract risk scoring on Base via x402. "
                "Analyzes bytecode for proxy, reentrancy, selfdestruct, "
                "honeypot, hidden mint, fee manipulation, and delegatecall "
                "patterns. Returns a 0-100 risk score."
            ),
            "description_for_model": (
                "Analyzes EVM smart contract bytecode on Base mainnet. "
                "Send a contract address to /analyze and receive a 0-100 "
                "risk score with detailed findings from 8 detectors. "
                "Requires x402 payment of $0.10 USDC on Base."
            ),
            "auth": {"type": "none"},
            "api": {
                "type": "openapi",
                "url": f"{base_url}/openapi.json",
            },
        })

    @app.route("/agent-metadata.json")
    def agent_metadata():
        """ERC-8004 agent registration metadata."""
        base_url = app.config.get("PUBLIC_URL") or request.url_root.rstrip("/")
        metadata: dict[str, object] = {
            "type": "https://eips.ethereum.org/EIPS/eip-8004#registration-v1",
            "name": "Smart Contract Risk Scorer",
            "description": (
                "EVM smart contract risk scoring API on Base. "
                "Analyzes bytecode patterns (proxy detection, reentrancy, "
                "selfdestruct, honeypot, hidden mint, fee manipulation, "
                "delegatecall) and returns a composite 0-100 risk score. "
                "Pay $0.10/call via x402 in USDC on Base. "
                "Endpoint: GET /analyze?address={contract_address}"
            ),
            "services": [
                {
                    "name": "web",
                    "endpoint": base_url.rstrip("/") + "/",
                }
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
        address = request.args.get("address", "").strip()
        if not address and request.is_json:
            body = request.get_json(silent=True)
            if body and isinstance(body, dict):
                address = str(body.get("address", "")).strip()

        if not address:
            return jsonify({"error": "Missing 'address' query parameter"}), 422

        if not ADDRESS_RE.match(address):
            return (
                jsonify({"error": f"Invalid Ethereum address: {address}"}),
                422,
            )

        try:
            result = analyze_contract(
                address, config.base_rpc_url, config.basescan_api_key
            )
        except RPCError as e:
            return jsonify({"error": f"RPC error: {e}"}), 502

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
