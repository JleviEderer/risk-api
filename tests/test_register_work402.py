"""Tests for scripts/register_work402.py"""

from __future__ import annotations

import json

import responses

from scripts.register_work402 import (
    AGENT_PROFILE,
    API_BASE,
    WALLET_ADDRESS,
    cmd_onboard,
    cmd_show,
)


class TestAgentProfile:
    """Verify the agent profile payload is well-formed."""

    def test_has_required_fields(self) -> None:
        required = ["name", "bio", "role", "wallet_address"]
        for field in required:
            assert field in AGENT_PROFILE, f"Missing required field: {field}"

    def test_role_is_seller(self) -> None:
        assert AGENT_PROFILE["role"] == "seller"

    def test_wallet_address_matches(self) -> None:
        assert AGENT_PROFILE["wallet_address"] == WALLET_ADDRESS

    def test_bio_mentions_risk_scoring(self) -> None:
        assert "risk scoring" in AGENT_PROFILE["bio"].lower()

    def test_bio_mentions_x402(self) -> None:
        assert "x402" in AGENT_PROFILE["bio"]

    def test_bio_mentions_price(self) -> None:
        assert "$0.10" in AGENT_PROFILE["bio"]


class TestOnboard:
    """Test the onboarding API flow with mocked HTTP."""

    @responses.activate
    def test_onboard_success(self) -> None:
        responses.add(
            responses.POST,
            f"{API_BASE}/agents/onboard",
            json={
                "success": True,
                "message": "Agent onboarded successfully",
                "data": {
                    "did": "did:erc8004:19074",
                    "wallet_address": WALLET_ADDRESS,
                    "used_existing_wallet": True,
                },
            },
            status=200,
        )

        cmd_onboard()

        assert len(responses.calls) == 1
        raw_body = responses.calls[0].request.body
        assert raw_body is not None
        body = json.loads(raw_body)
        assert body["name"] == AGENT_PROFILE["name"]
        assert body["role"] == "seller"
        assert body["wallet_address"] == WALLET_ADDRESS

    @responses.activate
    def test_onboard_already_registered(self) -> None:
        """409 should not crash — agent may already be registered."""
        responses.add(
            responses.POST,
            f"{API_BASE}/agents/onboard",
            json={"error": "Agent already registered"},
            status=409,
        )

        # Should not raise SystemExit on 409
        cmd_onboard()

    @responses.activate
    def test_onboard_server_error(self) -> None:
        responses.add(
            responses.POST,
            f"{API_BASE}/agents/onboard",
            json={"error": "internal error"},
            status=500,
        )

        try:
            cmd_onboard()
            assert False, "Should have exited"
        except SystemExit as e:
            assert e.code == 1


class TestShow:
    """Test agents listing."""

    @responses.activate
    def test_show_agents(self) -> None:
        responses.add(
            responses.GET,
            f"{API_BASE}/agents",
            json={
                "agents": [
                    {
                        "name": "Smart Contract Risk Scorer",
                        "did": "did:erc8004:19074",
                        "skills": ["risk-scoring", "security"],
                        "reputation_score": 0,
                        "task_catalog": [
                            {"name": "Risk Score", "price_amount": 0.10}
                        ],
                    }
                ],
                "meta": {"total": 1, "page": 1},
            },
            status=200,
        )

        cmd_show()
        assert len(responses.calls) == 1

    @responses.activate
    def test_show_empty(self) -> None:
        responses.add(
            responses.GET,
            f"{API_BASE}/agents",
            json={"agents": []},
            status=200,
        )

        cmd_show()  # Should not crash

    @responses.activate
    def test_show_error(self) -> None:
        responses.add(
            responses.GET,
            f"{API_BASE}/agents",
            json={"error": "server error"},
            status=500,
        )

        try:
            cmd_show()
            assert False, "Should have exited"
        except SystemExit as e:
            assert e.code == 1
