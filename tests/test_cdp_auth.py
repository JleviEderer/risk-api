"""Tests for CDP auth provider."""

from __future__ import annotations

import base64
import time

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from risk_api.cdp_auth import (
    _build_jwt,
    _parse_ed25519_key,
    create_cdp_auth_headers,
)


def _make_test_keypair() -> tuple[str, Ed25519PrivateKey]:
    """Generate a test Ed25519 keypair, return (base64_secret, private_key)."""
    private_key = Ed25519PrivateKey.generate()
    seed = private_key.private_bytes_raw()
    pub = private_key.public_key().public_bytes_raw()
    secret = base64.b64encode(seed + pub).decode()
    return secret, private_key


def test_parse_ed25519_key():
    secret, expected_key = _make_test_keypair()
    parsed = _parse_ed25519_key(secret)
    assert parsed.private_bytes_raw() == expected_key.private_bytes_raw()


def test_parse_ed25519_key_wrong_length():
    bad_secret = base64.b64encode(b"too short").decode()
    try:
        _parse_ed25519_key(bad_secret)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Expected 64-byte" in str(e)


def test_build_jwt_structure():
    secret, private_key = _make_test_keypair()
    key_id = "test-key-id"

    token = _build_jwt(
        key_id=key_id,
        private_key=private_key,
        method="GET",
        host="https://api.cdp.coinbase.com",
        path="/platform/v2/x402/supported",
    )

    # Decode without verification to inspect claims
    public_key = private_key.public_key()
    decoded = jwt.decode(token, public_key, algorithms=["EdDSA"])

    assert decoded["sub"] == key_id
    assert decoded["iss"] == "cdp"
    assert "uris" in decoded
    assert len(decoded["uris"]) == 1
    assert decoded["uris"][0].startswith("GET ")
    assert decoded["exp"] - decoded["nbf"] == 120

    # Check header
    header = jwt.get_unverified_header(token)
    assert header["alg"] == "EdDSA"
    assert header["kid"] == key_id
    assert header["typ"] == "JWT"
    assert "nonce" in header


def test_build_jwt_is_valid():
    """JWT should be verifiable with the corresponding public key."""
    secret, private_key = _make_test_keypair()
    token = _build_jwt(
        key_id="k1",
        private_key=private_key,
        method="POST",
        host="https://example.com",
        path="/verify",
    )
    public_key = private_key.public_key()
    decoded = jwt.decode(token, public_key, algorithms=["EdDSA"])
    assert decoded["sub"] == "k1"


def test_create_cdp_auth_headers_all_endpoints():
    secret, _ = _make_test_keypair()
    key_id = "test-uuid"
    url = "https://api.cdp.coinbase.com/platform/v2/x402"

    headers = create_cdp_auth_headers(key_id, secret, url)

    assert "verify" in headers
    assert "settle" in headers
    assert "supported" in headers

    for endpoint in ("verify", "settle", "supported"):
        assert "Authorization" in headers[endpoint]
        assert headers[endpoint]["Authorization"].startswith("Bearer ")


def test_jwt_not_expired():
    secret, private_key = _make_test_keypair()
    token = _build_jwt(
        key_id="k1",
        private_key=private_key,
        method="GET",
        host="https://api.cdp.coinbase.com",
        path="/supported",
    )
    header = jwt.get_unverified_header(token)
    public_key = private_key.public_key()
    decoded = jwt.decode(token, public_key, algorithms=["EdDSA"])
    assert decoded["exp"] > int(time.time())
