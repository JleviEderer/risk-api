"""CDP (Coinbase Developer Platform) JWT auth provider for x402 facilitator.

Generates Ed25519-signed JWTs for authenticating with the CDP facilitator at
https://api.cdp.coinbase.com/platform/v2/x402. Follows the same JWT structure
as the official cdp-sdk (coinbase/cdp-sdk) without pulling in the full SDK.

Requires: PyJWT, cryptography
"""

from __future__ import annotations

import base64
import random
import time
from urllib.parse import urlparse

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def _parse_ed25519_key(secret: str) -> Ed25519PrivateKey:
    """Parse base64-encoded Ed25519 private key (64 bytes: 32 seed + 32 pub)."""
    decoded = base64.b64decode(secret)
    if len(decoded) != 64:
        raise ValueError(
            f"Expected 64-byte Ed25519 key (32 seed + 32 pub), got {len(decoded)} bytes"
        )
    return Ed25519PrivateKey.from_private_bytes(decoded[:32])


def _generate_nonce() -> str:
    """Generate a 16-digit random nonce for the JWT header."""
    return "".join(random.choices("0123456789", k=16))


def _build_jwt(
    key_id: str,
    private_key: Ed25519PrivateKey,
    method: str,
    host: str,
    path: str,
) -> str:
    """Build a CDP-compatible JWT for a specific HTTP request.

    Args:
        key_id: CDP API key ID (UUID).
        private_key: Parsed Ed25519 private key.
        method: HTTP method (GET, POST).
        host: Request host without scheme (e.g. api.cdp.coinbase.com).
        path: Request path (e.g. /platform/v2/x402/supported).

    Returns:
        Signed JWT string.
    """
    now = int(time.time())
    parsed = urlparse(f"{host}{path}")
    uri = f"{method} {parsed.netloc}{parsed.path}"

    header = {
        "alg": "EdDSA",
        "kid": key_id,
        "typ": "JWT",
        "nonce": _generate_nonce(),
    }
    claims = {
        "sub": key_id,
        "iss": "cdp",
        "nbf": now,
        "exp": now + 120,
        "uris": [uri],
    }
    return jwt.encode(claims, private_key, algorithm="EdDSA", headers=header)


def create_cdp_auth_headers(
    key_id: str,
    key_secret: str,
    facilitator_url: str,
) -> dict[str, dict[str, str]]:
    """Create a dict of auth headers for each facilitator endpoint.

    Compatible with x402 SDK's CreateHeadersAuthProvider (dict-style config).

    Args:
        key_id: CDP_API_KEY_ID env var.
        key_secret: CDP_API_KEY_SECRET env var.
        facilitator_url: Full facilitator URL (e.g. https://api.cdp.coinbase.com/platform/v2/x402).

    Returns:
        Dict with 'verify', 'settle', 'supported' keys, each containing auth headers.
    """
    private_key = _parse_ed25519_key(key_secret)
    host = facilitator_url.rstrip("/")

    def _headers_for(endpoint: str, method: str = "POST") -> dict[str, str]:
        token = _build_jwt(key_id, private_key, method, host, f"/{endpoint}")
        return {"Authorization": f"Bearer {token}"}

    return {
        "verify": _headers_for("verify"),
        "settle": _headers_for("settle"),
        "supported": _headers_for("supported", method="GET"),
    }
