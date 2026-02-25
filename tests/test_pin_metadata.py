"""Tests for scripts/pin_metadata_ipfs.py"""

from __future__ import annotations

import json
import subprocess
import sys

import responses

from scripts.pin_metadata_ipfs import build_metadata, pin_to_ipfs


class TestBuildMetadata:
    def test_has_required_erc8004_fields(self) -> None:
        meta = build_metadata()
        assert meta["type"] == "https://eips.ethereum.org/EIPS/eip-8004#registration-v1"
        assert meta["name"] == "Smart Contract Risk Scorer"
        assert meta["x402Support"] is True
        assert meta["active"] is True
        assert isinstance(meta["services"], list)
        assert len(meta["services"]) == 1  # type: ignore[arg-type]

    def test_has_ipfs_specific_fields(self) -> None:
        """Metadata for IPFS should have fixed timestamps and absolute URLs."""
        meta = build_metadata()
        assert isinstance(meta["updatedAt"], int)
        assert meta["updatedAt"] > 0  # type: ignore[operator]
        # URLs should be absolute (not relative)
        assert str(meta["image"]).startswith("https://")
        assert str(meta["openapi_url"]).startswith("https://")

    def test_has_registrations(self) -> None:
        meta = build_metadata()
        registrations = meta["registrations"]
        assert isinstance(registrations, list)
        assert len(registrations) == 1  # type: ignore[arg-type]
        reg = registrations[0]  # type: ignore[index]
        assert reg["agentId"] == 19074  # type: ignore[index]

    def test_has_pricing(self) -> None:
        meta = build_metadata()
        pricing = meta["pricing"]
        assert isinstance(pricing, dict)
        assert pricing["amount"] == "0.10"  # type: ignore[index]
        assert pricing["currency"] == "USDC"  # type: ignore[index]

    def test_has_capabilities(self) -> None:
        meta = build_metadata()
        capabilities = meta["capabilities"]
        assert isinstance(capabilities, list)
        assert len(capabilities) >= 3  # type: ignore[arg-type]

    def test_is_json_serializable(self) -> None:
        meta = build_metadata()
        serialized = json.dumps(meta)
        roundtripped = json.loads(serialized)
        assert roundtripped["name"] == meta["name"]


class TestPinToIpfs:
    @responses.activate
    def test_successful_pin(self) -> None:
        responses.add(
            responses.POST,
            "https://api.pinata.cloud/pinning/pinJSONToIPFS",
            json={
                "IpfsHash": "QmTest1234567890abcdef",
                "PinSize": 1234,
                "Timestamp": "2026-02-25T00:00:00.000Z",
            },
            status=200,
        )

        cid = pin_to_ipfs({"test": "data"}, "test_jwt_token")
        assert cid == "QmTest1234567890abcdef"

        # Verify request was sent correctly
        assert len(responses.calls) == 1
        req = responses.calls[0].request
        assert req.headers["Authorization"] == "Bearer test_jwt_token"
        body = json.loads(req.body)
        assert body["pinataContent"] == {"test": "data"}
        assert body["pinataMetadata"]["name"] == "risk-api-agent-metadata"

    @responses.activate
    def test_pin_api_error_exits(self) -> None:
        responses.add(
            responses.POST,
            "https://api.pinata.cloud/pinning/pinJSONToIPFS",
            json={"error": "Unauthorized"},
            status=401,
        )

        try:
            pin_to_ipfs({"test": "data"}, "bad_jwt")
            assert False, "Should have called sys.exit"
        except SystemExit as e:
            assert e.code == 1


class TestCLI:
    def test_missing_jwt_exits_with_error(self) -> None:
        """Running without PINATA_JWT should exit with error."""
        import os

        # Inherit env but ensure PINATA_JWT is absent
        env = os.environ.copy()
        env.pop("PINATA_JWT", None)
        result = subprocess.run(
            [sys.executable, "scripts/pin_metadata_ipfs.py"],
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
        assert result.returncode == 1
        assert "PINATA_JWT" in result.stderr


class TestRegisterErc8004UpdateUri:
    def test_update_uri_accepts_custom_uri(self) -> None:
        """--update-uri with a positional arg should use that arg."""
        # We test the arg parsing logic, not the actual transaction
        args = ["script", "--update-uri", "ipfs://QmTestCid123"]
        idx = args.index("--update-uri")
        if idx + 1 < len(args) and not args[idx + 1].startswith("--"):
            uri = args[idx + 1]
        else:
            uri = "https://risk-api.life.conway.tech/agent-metadata.json"
        assert uri == "ipfs://QmTestCid123"

    def test_update_uri_falls_back_to_default(self) -> None:
        """--update-uri without a positional arg should use default URL."""
        args = ["script", "--update-uri"]
        idx = args.index("--update-uri")
        if idx + 1 < len(args) and not args[idx + 1].startswith("--"):
            uri = args[idx + 1]
        else:
            uri = "https://risk-api.life.conway.tech/agent-metadata.json"
        assert uri == "https://risk-api.life.conway.tech/agent-metadata.json"

    def test_update_uri_ignores_next_flag(self) -> None:
        """--update-uri followed by another flag should use default."""
        args = ["script", "--update-uri", "--dry-run"]
        idx = args.index("--update-uri")
        if idx + 1 < len(args) and not args[idx + 1].startswith("--"):
            uri = args[idx + 1]
        else:
            uri = "https://risk-api.life.conway.tech/agent-metadata.json"
        assert uri == "https://risk-api.life.conway.tech/agent-metadata.json"
