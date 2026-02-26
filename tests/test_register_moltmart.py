"""Tests for scripts/register_moltmart.py"""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

import responses

from scripts.register_moltmart import (
    AGENT_DESCRIPTION,
    AGENT_NAME,
    API_BASE,
    SERVICE_LISTING,
    cmd_register,
    cmd_list_service,
    cmd_recover,
    cmd_show,
    cmd_update_service,
)


FAKE_WALLET_DATA = {"privateKey": "0x" + "ab" * 32}
FAKE_ADDRESS = "0xBcd4042DE499D14e55001CcbB24a551F3b954096"


def _mock_wallet(monkeypatch: object, tmp_path: object) -> None:
    """Set up a fake wallet file."""
    # We patch _load_wallet to avoid filesystem dependency
    pass


class TestServiceListing:
    """Verify the service listing payload is well-formed."""

    def test_has_required_fields(self) -> None:
        required = ["name", "description", "endpoint_url", "price_usdc", "category"]
        for field in required:
            assert field in SERVICE_LISTING, f"Missing required field: {field}"

    def test_category_is_valid(self) -> None:
        valid_categories = {"development", "data", "content", "analysis", "automation", "other"}
        assert SERVICE_LISTING["category"] in valid_categories

    def test_price_is_correct(self) -> None:
        assert SERVICE_LISTING["price_usdc"] == 0.10

    def test_endpoint_url_is_live(self) -> None:
        assert SERVICE_LISTING["endpoint_url"] == "https://risk-api.life.conway.tech/analyze"

    def test_has_input_schema(self) -> None:
        schema = SERVICE_LISTING["input_schema"]
        assert schema["type"] == "object"
        assert "address" in schema["properties"]
        assert "address" in schema["required"]

    def test_has_output_schema(self) -> None:
        schema = SERVICE_LISTING["output_schema"]
        assert schema["type"] == "object"
        assert "score" in schema["properties"]
        assert "risk_level" in schema["properties"]
        assert "findings" in schema["properties"]

    def test_has_examples(self) -> None:
        assert "example_request" in SERVICE_LISTING
        assert "example_response" in SERVICE_LISTING
        assert "address" in SERVICE_LISTING["example_request"]
        assert SERVICE_LISTING["example_response"]["score"] == 0
        assert SERVICE_LISTING["example_response"]["risk_level"] == "safe"

    def test_has_usage_instructions(self) -> None:
        instructions = SERVICE_LISTING["usage_instructions"]
        assert "GET" in instructions
        assert "POST" in instructions
        assert "x402" in instructions
        assert "PAYMENT-SIGNATURE" in instructions

    def test_output_schema_score_range(self) -> None:
        score_schema = SERVICE_LISTING["output_schema"]["properties"]["score"]
        assert score_schema["minimum"] == 0
        assert score_schema["maximum"] == 100


class TestAgentMetadata:
    """Verify agent registration metadata."""

    def test_agent_name(self) -> None:
        assert AGENT_NAME == "Smart Contract Risk Scorer"

    def test_agent_description_mentions_x402(self) -> None:
        assert "x402" in AGENT_DESCRIPTION

    def test_agent_description_mentions_price(self) -> None:
        assert "$0.10" in AGENT_DESCRIPTION


class TestRegisterFlow:
    """Test the registration API flow with mocked HTTP."""

    @responses.activate
    def test_register_success(self) -> None:
        # Mock challenge endpoint
        responses.add(
            responses.GET,
            f"{API_BASE}/agents/challenge",
            json={"challenge": "Sign this message to verify ownership"},
            status=200,
        )

        # Mock register endpoint
        responses.add(
            responses.POST,
            f"{API_BASE}/agents/register",
            json={
                "id": "agent-123",
                "api_key": "mk_test_key_abc",
                "name": AGENT_NAME,
                "erc8004": {"id": 19074, "verified": True},
            },
            status=201,
        )

        with patch("scripts.register_moltmart._load_wallet") as mock_wallet:
            account = MagicMock()
            account.address = FAKE_ADDRESS
            mock_wallet.return_value = (account, "0x" + "ab" * 32)

            with patch("scripts.register_moltmart.Account") as mock_account_cls:
                mock_signed = MagicMock()
                mock_signed.signature.hex.return_value = "0x" + "cd" * 65
                mock_account_cls.sign_message.return_value = mock_signed

                api_key = cmd_register()

        assert api_key == "mk_test_key_abc"
        # Verify challenge was fetched
        assert len(responses.calls) == 2
        # Verify register body
        body = responses.calls[1].request.body
        assert body is not None
        register_body = json.loads(body)
        assert register_body["name"] == AGENT_NAME
        assert register_body["erc8004_id"] == 19074
        assert register_body["wallet_address"] == FAKE_ADDRESS

    @responses.activate
    def test_register_challenge_failure(self) -> None:
        responses.add(
            responses.GET,
            f"{API_BASE}/agents/challenge",
            json={"error": "server error"},
            status=500,
        )

        with patch("scripts.register_moltmart._load_wallet") as mock_wallet:
            account = MagicMock()
            account.address = FAKE_ADDRESS
            mock_wallet.return_value = (account, "0x" + "ab" * 32)

            try:
                cmd_register()
                assert False, "Should have exited"
            except SystemExit as e:
                assert e.code == 1


class TestListService:
    """Test service listing API flow."""

    @responses.activate
    def test_list_service_success(self) -> None:
        responses.add(
            responses.POST,
            f"{API_BASE}/services",
            json={
                "id": "svc-456",
                "secret_token": "st_test_token_xyz",
            },
            status=201,
        )

        cmd_list_service("mk_test_key_abc")

        assert len(responses.calls) == 1
        raw_body = responses.calls[0].request.body
        assert raw_body is not None
        body = json.loads(raw_body)
        assert body["name"] == SERVICE_LISTING["name"]
        assert body["price_usdc"] == 0.10
        assert body["category"] == "analysis"
        assert responses.calls[0].request.headers["X-API-Key"] == "mk_test_key_abc"

    @responses.activate
    def test_list_service_failure(self) -> None:
        responses.add(
            responses.POST,
            f"{API_BASE}/services",
            json={"error": "unauthorized"},
            status=401,
        )

        try:
            cmd_list_service("bad_key")
            assert False, "Should have exited"
        except SystemExit as e:
            assert e.code == 1


class TestUpdateService:
    """Test service update API flow."""

    @responses.activate
    def test_update_success(self) -> None:
        responses.add(
            responses.PATCH,
            f"{API_BASE}/services/svc-456",
            json={"id": "svc-456", "name": SERVICE_LISTING["name"]},
            status=200,
        )

        cmd_update_service("mk_test_key_abc", "svc-456")
        assert len(responses.calls) == 1

    @responses.activate
    def test_update_failure(self) -> None:
        responses.add(
            responses.PATCH,
            f"{API_BASE}/services/svc-456",
            json={"error": "not found"},
            status=404,
        )

        try:
            cmd_update_service("mk_test_key_abc", "svc-456")
            assert False, "Should have exited"
        except SystemExit as e:
            assert e.code == 1


class TestShowProfile:
    """Test agent profile fetch."""

    @responses.activate
    def test_show_success(self) -> None:
        responses.add(
            responses.GET,
            f"{API_BASE}/agents/me",
            json={"id": "agent-123", "name": AGENT_NAME, "erc8004_id": 19074},
            status=200,
        )

        cmd_show("mk_test_key_abc")
        assert responses.calls[0].request.headers["X-API-Key"] == "mk_test_key_abc"


class TestRecoverKey:
    """Test API key recovery flow."""

    @responses.activate
    def test_recover_success(self) -> None:
        responses.add(
            responses.GET,
            f"{API_BASE}/agents/challenge",
            json={"challenge": "Sign to recover"},
            status=200,
        )
        responses.add(
            responses.POST,
            f"{API_BASE}/agents/recover-key",
            json={"success": True, "api_key": "mk_recovered_key"},
            status=200,
        )

        with patch("scripts.register_moltmart._load_wallet") as mock_wallet:
            account = MagicMock()
            account.address = FAKE_ADDRESS
            mock_wallet.return_value = (account, "0x" + "ab" * 32)

            with patch("scripts.register_moltmart.Account") as mock_account_cls:
                mock_signed = MagicMock()
                mock_signed.signature.hex.return_value = "0x" + "cd" * 65
                mock_account_cls.sign_message.return_value = mock_signed

                api_key = cmd_recover()

        assert api_key == "mk_recovered_key"
