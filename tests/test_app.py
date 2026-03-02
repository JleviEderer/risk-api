import json

import pytest
import responses

from risk_api.analysis.engine import clear_analysis_cache
from risk_api.chain.rpc import clear_cache


RPC_URL = "https://mainnet.base.org"


def setup_function():
    clear_cache()
    clear_analysis_cache()


def teardown_function():
    clear_cache()
    clear_analysis_cache()


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_x402_verification_endpoint(client):
    resp = client.get("/.well-known/x402-verification.json")
    assert resp.status_code == 200
    assert resp.get_json() == {"x402": "64cb3a6a29bb"}


def test_x402_verification_not_behind_paywall(client_with_x402):
    resp = client_with_x402.get("/.well-known/x402-verification.json")
    assert resp.status_code == 200
    assert resp.get_json()["x402"] == "64cb3a6a29bb"


def test_missing_address(client):
    resp = client.get("/analyze")
    assert resp.status_code == 422
    data = resp.get_json()
    assert "Missing" in data["error"]


def test_invalid_address_too_short(client):
    resp = client.get("/analyze?address=0x1234")
    assert resp.status_code == 422
    data = resp.get_json()
    assert "Invalid" in data["error"]


def test_invalid_address_no_prefix(client):
    resp = client.get(f"/analyze?address={'ab' * 20}")
    assert resp.status_code == 422


def test_invalid_address_bad_chars(client):
    resp = client.get(f"/analyze?address=0x{'zz' * 20}")
    assert resp.status_code == 422


@responses.activate
def test_analyze_success(client):
    bytecode = "0x" + "6080604052" + "00" * 200
    responses.post(
        RPC_URL,
        json={"jsonrpc": "2.0", "id": 1, "result": bytecode},
    )
    addr = "0x" + "ab" * 20
    resp = client.get(f"/analyze?address={addr}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["address"] == addr
    assert data["score"] == 0
    assert data["level"] == "safe"
    assert isinstance(data["findings"], list)
    assert isinstance(data["category_scores"], dict)


@responses.activate
def test_analyze_rpc_error(client):
    responses.post(
        RPC_URL,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32000, "message": "server busy"},
        },
    )
    addr = "0x" + "cd" * 20
    resp = client.get(f"/analyze?address={addr}")
    assert resp.status_code == 502
    data = resp.get_json()
    assert "RPC error" in data["error"]


@responses.activate
def test_analyze_with_findings(client):
    # Bytecode with SELFDESTRUCT
    bytecode = "0x" + "ff" + "00" * 200
    responses.post(
        RPC_URL,
        json={"jsonrpc": "2.0", "id": 1, "result": bytecode},
    )
    addr = "0x" + "ef" * 20
    resp = client.get(f"/analyze?address={addr}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["score"] >= 30
    assert len(data["findings"]) > 0
    assert data["findings"][0]["detector"] == "selfdestruct"


def test_x402_returns_402_without_payment(client_with_x402):
    """With x402 middleware enabled, /analyze should return 402 without payment."""
    addr = "0x" + "ab" * 20
    resp = client_with_x402.get(f"/analyze?address={addr}")
    assert resp.status_code == 402


def test_x402_402_response_has_bazaar_extension(client_with_x402):
    """402 response Payment-Required header should include bazaar discovery extension."""
    import base64

    addr = "0x" + "ab" * 20
    resp = client_with_x402.get(f"/analyze?address={addr}")
    assert resp.status_code == 402

    # Payment-Required header is base64-encoded JSON
    pr_header = resp.headers.get("Payment-Required")
    assert pr_header is not None, "Missing Payment-Required header"
    pr_data = json.loads(base64.b64decode(pr_header))

    # Must have extensions.bazaar with input schema
    assert "extensions" in pr_data, f"No extensions in 402 response: {list(pr_data.keys())}"
    bazaar = pr_data["extensions"].get("bazaar")
    assert bazaar is not None, "No bazaar extension in 402 response"

    # Check info.input has query params example
    info = bazaar.get("info", {})
    input_data = info.get("input", {})
    assert input_data.get("type") == "http"
    assert "queryParams" in input_data or "query_params" in input_data

    # Check schema has address property
    schema = bazaar.get("schema", {})
    input_schema = schema.get("properties", {}).get("input", {})
    query_schema = input_schema.get("properties", {}).get("queryParams", {})
    assert "address" in query_schema.get("properties", {}), "Missing address in schema"


def test_x402_402_post_has_bazaar_body_extension(client_with_x402):
    """POST 402 response should include bazaar body discovery extension."""
    import base64

    addr = "0x" + "ab" * 20
    resp = client_with_x402.post("/analyze", json={"address": addr})
    assert resp.status_code == 402

    pr_header = resp.headers.get("Payment-Required")
    assert pr_header is not None
    pr_data = json.loads(base64.b64decode(pr_header))

    bazaar = pr_data.get("extensions", {}).get("bazaar")
    assert bazaar is not None, "No bazaar extension in POST 402 response"

    info = bazaar.get("info", {})
    input_data = info.get("input", {})
    assert input_data.get("type") == "http"
    assert input_data.get("bodyType") == "json"

    # Check schema has body with address property
    schema = bazaar.get("schema", {})
    input_schema = schema.get("properties", {}).get("input", {})
    body_schema = input_schema.get("properties", {}).get("body", {})
    assert "address" in body_schema.get("properties", {}), "Missing address in body schema"


def test_x402_health_not_gated(client_with_x402):
    """/health should NOT be behind the payment gate."""
    resp = client_with_x402.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_agent_metadata_endpoint(client):
    resp = client.get("/agent-metadata.json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["type"] == "https://eips.ethereum.org/EIPS/eip-8004#registration-v1"
    assert data["name"] == "Augur"
    assert data["x402Support"] is True
    assert data["active"] is True
    assert len(data["services"]) == 4
    service_names = [s["name"] for s in data["services"]]
    assert service_names == ["web", "A2A", "OASF", "agentWallet"]
    assert "registrations" not in data
    # New discovery fields
    assert "/avatar.png" in data["image"]
    assert isinstance(data["updatedAt"], int)
    assert data["updatedAt"] > 0
    assert data["pricing"] == {
        "amount": "0.10",
        "currency": "USDC",
        "network": "eip155:8453",
    }
    assert "/openapi.json" in data["openapi_url"]
    assert isinstance(data["capabilities"], list)
    assert "contract risk scoring" in data["capabilities"]
    assert "proxy detection" in data["capabilities"]


def test_agent_metadata_uses_public_url(app):
    app.config["PUBLIC_URL"] = "https://risk-api.life.conway.tech"
    with app.test_client() as c:
        resp = c.get("/agent-metadata.json")
        data = resp.get_json()
        assert data["services"][0]["endpoint"] == "https://risk-api.life.conway.tech/"


def test_agent_metadata_falls_back_to_request_url(client):
    resp = client.get("/agent-metadata.json")
    data = resp.get_json()
    endpoint = data["services"][0]["endpoint"]
    assert "localhost" in endpoint or "127.0.0.1" in endpoint


def test_agent_metadata_with_agent_id(app):
    app.config["ERC8004_AGENT_ID"] = 12345
    with app.test_client() as c:
        resp = c.get("/agent-metadata.json")
        data = resp.get_json()
        assert "registrations" in data
        assert data["registrations"][0]["agentId"] == 12345


def test_agent_metadata_not_behind_paywall(client_with_x402):
    resp = client_with_x402.get("/agent-metadata.json")
    assert resp.status_code == 200
    assert resp.get_json()["x402Support"] is True


@responses.activate
def test_analyze_proxy_response_includes_implementation(client):
    """API response includes implementation object for proxy contracts."""
    eip1967 = "360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
    proxy_bytecode = "0x7f" + eip1967 + "f4" + "00" * 200

    impl_addr_hex = "ab" * 20
    impl_addr_padded = "0x" + "0" * 24 + impl_addr_hex
    impl_bytecode = "0x" + "ff" + "00" * 200  # SELFDESTRUCT

    # get_code for proxy
    responses.post(RPC_URL, json={"jsonrpc": "2.0", "id": 1, "result": proxy_bytecode})
    # storage slot returns impl address
    responses.post(RPC_URL, json={"jsonrpc": "2.0", "id": 1, "result": impl_addr_padded})
    # get_code for implementation
    responses.post(RPC_URL, json={"jsonrpc": "2.0", "id": 1, "result": impl_bytecode})

    addr = "0x" + "ee" * 20
    resp = client.get(f"/analyze?address={addr}")
    assert resp.status_code == 200
    data = resp.get_json()

    assert "implementation" in data
    impl = data["implementation"]
    assert impl["address"] == "0x" + impl_addr_hex
    assert impl["bytecode_size"] > 0
    assert isinstance(impl["findings"], list)
    assert isinstance(impl["category_scores"], dict)


@responses.activate
def test_analyze_non_proxy_no_implementation_key(client):
    """Non-proxy contracts should NOT have implementation key."""
    bytecode = "0x" + "6080604052" + "00" * 200
    responses.post(RPC_URL, json={"jsonrpc": "2.0", "id": 1, "result": bytecode})

    addr = "0x" + "dd" * 20
    resp = client.get(f"/analyze?address={addr}")
    assert resp.status_code == 200
    data = resp.get_json()

    assert "implementation" not in data


@responses.activate
def test_analyze_post_with_json_body(client):
    """POST /analyze with address in JSON body should work."""
    bytecode = "0x" + "6080604052" + "00" * 200
    responses.post(
        RPC_URL,
        json={"jsonrpc": "2.0", "id": 1, "result": bytecode},
    )
    addr = "0x" + "ab" * 20
    resp = client.post("/analyze", json={"address": addr})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["address"] == addr
    assert data["score"] == 0


@responses.activate
def test_analyze_post_with_query_param(client):
    """POST /analyze with address in query param should also work."""
    bytecode = "0x" + "6080604052" + "00" * 200
    responses.post(
        RPC_URL,
        json={"jsonrpc": "2.0", "id": 1, "result": bytecode},
    )
    addr = "0x" + "ab" * 20
    resp = client.post(f"/analyze?address={addr}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["address"] == addr


def test_analyze_post_missing_address(client):
    """POST /analyze with no address should return 422."""
    resp = client.post("/analyze", json={})
    assert resp.status_code == 422


def test_x402_post_returns_402_without_payment(client_with_x402):
    """POST /analyze should also be behind x402 paywall."""
    addr = "0x" + "ab" * 20
    resp = client_with_x402.post("/analyze", json={"address": addr})
    assert resp.status_code == 402


def test_dashboard_returns_html(client):
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert resp.content_type.startswith("text/html")
    assert b"risk-api" in resp.data
    assert b"<canvas" in resp.data


def test_dashboard_not_behind_paywall(client_with_x402):
    resp = client_with_x402.get("/dashboard")
    assert resp.status_code == 200
    assert resp.content_type.startswith("text/html")


def test_avatar_returns_png(client):
    resp = client.get("/avatar.png")
    assert resp.status_code == 200
    assert resp.content_type == "image/png"
    # PNG magic bytes
    assert resp.data[:4] == b"\x89PNG"


def test_avatar_not_behind_paywall(client_with_x402):
    resp = client_with_x402.get("/avatar.png")
    assert resp.status_code == 200
    assert resp.content_type == "image/png"


def test_openapi_returns_valid_json(client):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["openapi"] == "3.0.3"
    assert data["info"]["title"] == "Augur"
    assert "/analyze" in data["paths"]
    assert "servers" in data
    assert "get" in data["paths"]["/analyze"]
    assert "post" in data["paths"]["/analyze"]
    # x-payment-info (Bazaar standard for x402scan)
    for method in ("get", "post"):
        op = data["paths"]["/analyze"][method]
        pi = op["x-payment-info"]
        assert pi["protocols"] == ["x402"]
        assert pi["pricingMode"] == "fixed"
        assert pi["price"] == "0.10"
        assert pi["currency"] == "USDC"
        assert pi["network"] == "eip155:8453"
        assert pi["payTo"].startswith("0x")
        assert op["security"] == [{"x402": []}]
    # securitySchemes
    scheme = data["components"]["securitySchemes"]["x402"]
    assert scheme["type"] == "apiKey"
    assert scheme["in"] == "header"
    assert scheme["name"] == "PAYMENT-SIGNATURE"


def test_openapi_uses_public_url(app):
    app.config["PUBLIC_URL"] = "https://risk-api.life.conway.tech"
    with app.test_client() as c:
        resp = c.get("/openapi.json")
        data = resp.get_json()
        assert data["servers"][0]["url"] == "https://risk-api.life.conway.tech"


def test_openapi_not_behind_paywall(client_with_x402):
    resp = client_with_x402.get("/openapi.json")
    assert resp.status_code == 200
    assert "openapi" in resp.get_json()


def test_ai_plugin_json_endpoint(client):
    resp = client.get("/.well-known/ai-plugin.json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["schema_version"] == "v1"
    assert data["name_for_model"] == "augur"
    assert data["auth"] == {"type": "none"}
    assert data["api"]["type"] == "openapi"
    assert "/openapi.json" in data["api"]["url"]


def test_ai_plugin_uses_public_url(app):
    app.config["PUBLIC_URL"] = "https://risk-api.life.conway.tech"
    with app.test_client() as c:
        resp = c.get("/.well-known/ai-plugin.json")
        data = resp.get_json()
        assert data["api"]["url"] == "https://risk-api.life.conway.tech/openapi.json"


def test_ai_plugin_not_behind_paywall(client_with_x402):
    resp = client_with_x402.get("/.well-known/ai-plugin.json")
    assert resp.status_code == 200
    assert resp.get_json()["schema_version"] == "v1"


def test_a2a_agent_card_endpoint(client):
    resp = client.get("/.well-known/agent.json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["name"] == "Augur"
    assert data["version"] == "1.0.0"
    assert data["capabilities"]["streaming"] is False
    assert len(data["skills"]) == 1
    assert data["skills"][0]["id"] == "analyze-contract"
    assert data["skills"][0]["name"] == "Risk Classification (OASF 1304)"
    assert "oasf:risk_classification" in data["skills"][0]["tags"]
    assert "oasf:vulnerability_analysis" in data["skills"][0]["tags"]
    assert data["interfaces"][0]["type"] == "http"
    assert data["security"] == []
    assert data["defaultInputModes"] == ["application/json"]


def test_a2a_agent_card_json_endpoint(client):
    """/.well-known/agent-card.json serves same A2A card (8004scan canonical path)."""
    resp = client.get("/.well-known/agent-card.json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["name"] == "Augur"
    assert data["version"] == "1.0.0"
    assert data["skills"][0]["id"] == "analyze-contract"
    assert data["skills"][0]["tags"] == ["oasf:risk_classification", "oasf:vulnerability_analysis", "oasf:threat_detection"]


def test_a2a_agent_card_uses_public_url(app):
    app.config["PUBLIC_URL"] = "https://risk-api.life.conway.tech"
    with app.test_client() as c:
        resp = c.get("/.well-known/agent.json")
        data = resp.get_json()
        assert data["url"] == "https://risk-api.life.conway.tech"
        assert data["interfaces"][0]["baseUrl"] == "https://risk-api.life.conway.tech"


def test_a2a_agent_card_json_uses_public_url(app):
    """agent-card.json path also respects PUBLIC_URL."""
    app.config["PUBLIC_URL"] = "https://risk-api.life.conway.tech"
    with app.test_client() as c:
        resp = c.get("/.well-known/agent-card.json")
        data = resp.get_json()
        assert data["url"] == "https://risk-api.life.conway.tech"


def test_a2a_agent_card_not_behind_paywall(client_with_x402):
    resp = client_with_x402.get("/.well-known/agent.json")
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "Augur"


def test_a2a_agent_card_json_not_behind_paywall(client_with_x402):
    """agent-card.json should also be exempt from x402 paywall."""
    resp = client_with_x402.get("/.well-known/agent-card.json")
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "Augur"


def test_agent_metadata_has_a2a_service(client):
    resp = client.get("/agent-metadata.json")
    data = resp.get_json()
    a2a = next(s for s in data["services"] if s["name"] == "A2A")
    assert "/.well-known/agent-card.json" in a2a["endpoint"]
    assert a2a["version"] == "0.3.0"


def test_agent_metadata_has_oasf_service(client):
    resp = client.get("/agent-metadata.json")
    data = resp.get_json()
    oasf = next(s for s in data["services"] if s["name"] == "OASF")
    assert oasf["endpoint"] == "https://github.com/agntcy/oasf/"
    assert oasf["version"] == "0.8.0"
    assert oasf["skills"] == ["risk_classification", "vulnerability_analysis", "threat_detection"]
    assert oasf["domains"] == ["technology/blockchain"]


def test_agent_metadata_has_agent_wallet_service(client):
    resp = client.get("/agent-metadata.json")
    data = resp.get_json()
    wallet = next(s for s in data["services"] if s["name"] == "agentWallet")
    assert wallet["endpoint"].startswith("eip155:8453:0x")


def test_wellknown_x402_returns_discovery_doc(client):
    """/.well-known/x402 returns valid x402 discovery document."""
    resp = client.get("/.well-known/x402")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["version"] == 1
    assert isinstance(data["resources"], list)
    assert len(data["resources"]) == 1
    assert data["resources"][0].endswith("/analyze")
    assert isinstance(data["instructions"], str)
    assert "risk score" in data["instructions"].lower()


def test_wellknown_x402_not_behind_paywall(client_with_x402):
    """/.well-known/x402 should NOT be behind x402 payment gate."""
    resp = client_with_x402.get("/.well-known/x402")
    assert resp.status_code == 200
    assert resp.get_json()["version"] == 1


def test_wellknown_x402_uses_public_url(app):
    """/.well-known/x402 resources should use PUBLIC_URL when set."""
    app.config["PUBLIC_URL"] = "https://risk-api.life.conway.tech"
    with app.test_client() as c:
        resp = c.get("/.well-known/x402")
        data = resp.get_json()
        assert data["resources"][0] == "https://risk-api.life.conway.tech/analyze"
        assert "risk-api.life.conway.tech" in data["instructions"]


# --- Landing page tests ---


def test_landing_returns_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.content_type.startswith("text/html")
    assert b"Augur" in resp.data


def test_landing_has_schema_org_json_ld(client):
    resp = client.get("/")
    assert b"application/ld+json" in resp.data
    assert b'"@type": "WebAPI"' in resp.data
    assert b'"priceCurrency": "USD"' in resp.data


def test_landing_has_meta_tags(client):
    resp = client.get("/")
    assert b'<meta name="description"' in resp.data
    assert b'<meta name="robots" content="index, follow"' in resp.data
    assert b'og:title' in resp.data
    assert b'og:image' in resp.data


def test_landing_links_discovery_endpoints(client):
    resp = client.get("/")
    assert b"/openapi.json" in resp.data
    assert b"/.well-known/agent-card.json" in resp.data
    assert b"/.well-known/x402" in resp.data
    assert b"/.well-known/ai-plugin.json" in resp.data
    assert b"/.well-known/api-catalog" in resp.data
    assert b"/agent-metadata.json" in resp.data


def test_landing_uses_public_url(app):
    app.config["PUBLIC_URL"] = "https://risk-api.life.conway.tech"
    with app.test_client() as c:
        resp = c.get("/")
        assert b"https://risk-api.life.conway.tech/openapi.json" in resp.data
        assert b"https://risk-api.life.conway.tech/avatar.png" in resp.data


def test_landing_not_behind_paywall(client_with_x402):
    resp = client_with_x402.get("/")
    assert resp.status_code == 200
    assert resp.content_type.startswith("text/html")


# --- robots.txt tests ---


def test_robots_txt_returns_text(client):
    resp = client.get("/robots.txt")
    assert resp.status_code == 200
    assert resp.content_type.startswith("text/plain")
    text = resp.data.decode()
    assert "User-agent: *" in text
    assert "Allow: /" in text
    assert "Disallow: /dashboard" in text


def test_robots_txt_includes_sitemap(client):
    resp = client.get("/robots.txt")
    text = resp.data.decode()
    assert "Sitemap:" in text
    assert "/sitemap.xml" in text


def test_robots_txt_uses_public_url(app):
    app.config["PUBLIC_URL"] = "https://risk-api.life.conway.tech"
    with app.test_client() as c:
        resp = c.get("/robots.txt")
        text = resp.data.decode()
        assert "https://risk-api.life.conway.tech/sitemap.xml" in text


def test_robots_txt_not_behind_paywall(client_with_x402):
    resp = client_with_x402.get("/robots.txt")
    assert resp.status_code == 200
    assert resp.content_type.startswith("text/plain")


# --- sitemap.xml tests ---


def test_sitemap_returns_xml(client):
    resp = client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert resp.content_type.startswith("application/xml")
    text = resp.data.decode()
    assert '<?xml version="1.0"' in text
    assert "<urlset" in text


def test_sitemap_lists_public_endpoints(client):
    resp = client.get("/sitemap.xml")
    text = resp.data.decode()
    assert "/openapi.json" in text
    assert "/agent-metadata.json" in text
    assert "/.well-known/agent-card.json" in text
    assert "/.well-known/api-catalog" in text
    # Should NOT include private/gated endpoints
    assert "/stats" not in text
    assert "/dashboard" not in text
    assert "/analyze" not in text


def test_sitemap_uses_public_url(app):
    app.config["PUBLIC_URL"] = "https://risk-api.life.conway.tech"
    with app.test_client() as c:
        resp = c.get("/sitemap.xml")
        text = resp.data.decode()
        assert "https://risk-api.life.conway.tech/" in text


def test_sitemap_not_behind_paywall(client_with_x402):
    resp = client_with_x402.get("/sitemap.xml")
    assert resp.status_code == 200
    assert resp.content_type.startswith("application/xml")


# --- api-catalog tests ---


def test_api_catalog_returns_linkset_json(client):
    resp = client.get("/.well-known/api-catalog")
    assert resp.status_code == 200
    assert "application/linkset+json" in resp.content_type
    assert "rfc9727" in resp.content_type
    data = resp.get_json()
    assert "linkset" in data


def test_api_catalog_points_to_openapi(client):
    resp = client.get("/.well-known/api-catalog")
    data = resp.get_json()
    linkset = data["linkset"][0]
    assert linkset["service-desc"][0]["href"].endswith("/openapi.json")
    assert linkset["service-desc"][0]["type"] == "application/json"


def test_api_catalog_points_to_landing(client):
    resp = client.get("/.well-known/api-catalog")
    data = resp.get_json()
    linkset = data["linkset"][0]
    assert linkset["service-doc"][0]["href"].endswith("/")
    assert linkset["service-doc"][0]["type"] == "text/html"


def test_api_catalog_uses_public_url(app):
    app.config["PUBLIC_URL"] = "https://risk-api.life.conway.tech"
    with app.test_client() as c:
        resp = c.get("/.well-known/api-catalog")
        data = resp.get_json()
        linkset = data["linkset"][0]
        assert linkset["anchor"] == "https://risk-api.life.conway.tech/.well-known/api-catalog"
        assert linkset["service-desc"][0]["href"] == "https://risk-api.life.conway.tech/openapi.json"


def test_api_catalog_not_behind_paywall(client_with_x402):
    resp = client_with_x402.get("/.well-known/api-catalog")
    assert resp.status_code == 200
    assert "linkset" in resp.get_json()
