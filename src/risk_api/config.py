"""Environment configuration loading."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

CDP_KEY_FILE = Path.home() / ".config" / "risk-api" / "cdp_api_key.json"


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
        basescan_api_key=os.environ.get("BASESCAN_API_KEY", ""),
        public_url=os.environ.get("PUBLIC_URL", ""),
        cdp_api_key_id=cdp_key_id,
        cdp_api_key_secret=cdp_key_secret,
    )
