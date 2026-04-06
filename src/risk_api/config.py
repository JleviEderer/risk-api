"""Environment configuration loading."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

CDP_KEY_FILE = Path.home() / ".config" / "risk-api" / "cdp_api_key.json"
ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


class ConfigError(Exception):
    """Raised when required configuration is missing."""


@dataclass(frozen=True, slots=True)
class Config:
    wallet_address: str
    base_rpc_url: str
    facilitator_url: str
    network: str
    price: str
    erc8004_agent_id: int | None = None
    basescan_api_key: str = ""
    public_url: str = ""
    cdp_api_key_id: str = ""
    cdp_api_key_secret: str = ""
    approve_spender_allowlist: tuple[str, ...] = ()


def _parse_address_allowlist(env_var: str) -> tuple[str, ...]:
    raw_value = os.environ.get(env_var, "")
    if not raw_value.strip():
        return ()

    addresses: list[str] = []
    seen: set[str] = set()
    for raw_part in raw_value.split(","):
        address = raw_part.strip()
        if not address:
            continue
        if not ADDRESS_RE.match(address):
            raise ConfigError(
                f"{env_var} contains invalid Ethereum address: {address}"
            )

        normalized = address.lower()
        if normalized not in seen:
            seen.add(normalized)
            addresses.append(normalized)

    return tuple(addresses)


def load_config() -> Config:
    """Load configuration from environment variables.

    Raises ConfigError if WALLET_ADDRESS is not set.
    """
    load_dotenv()

    wallet = os.environ.get("WALLET_ADDRESS", "")
    if not wallet:
        raise ConfigError("WALLET_ADDRESS environment variable is required")

    raw_agent_id = os.environ.get("ERC8004_AGENT_ID", "")
    erc8004_agent_id: int | None = int(raw_agent_id) if raw_agent_id else None

    # CDP API key: env vars take precedence, fall back to key file
    cdp_key_id = os.environ.get("CDP_API_KEY_ID", "")
    cdp_key_secret = os.environ.get("CDP_API_KEY_SECRET", "")
    if not cdp_key_id and CDP_KEY_FILE.is_file():
        try:
            data = json.loads(CDP_KEY_FILE.read_text())
            cdp_key_id = data.get("id", "")
            cdp_key_secret = data.get("privateKey", "")
        except (json.JSONDecodeError, OSError):
            pass  # Logged downstream when CDP auth fails

    return Config(
        wallet_address=wallet,
        base_rpc_url=os.environ.get("BASE_RPC_URL", "https://mainnet.base.org"),
        facilitator_url=os.environ.get(
            "FACILITATOR_URL",
            "https://v2.facilitator.mogami.tech",
        ),
        network=os.environ.get("NETWORK", "eip155:8453"),
        price=os.environ.get("PRICE", "$0.10"),
        erc8004_agent_id=erc8004_agent_id,
        basescan_api_key=os.environ.get(
            "BLOCKSCOUT_API_KEY",
            os.environ.get(
                "ETHERSCAN_API_KEY",
                os.environ.get("BASESCAN_API_KEY", ""),
            ),
        ),
        public_url=os.environ.get("PUBLIC_URL", ""),
        cdp_api_key_id=cdp_key_id,
        cdp_api_key_secret=cdp_key_secret,
        approve_spender_allowlist=_parse_address_allowlist(
            "APPROVE_SPENDER_ALLOWLIST"
        ),
    )
