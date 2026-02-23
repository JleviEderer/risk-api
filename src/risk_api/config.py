"""Environment configuration loading."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigError(Exception):
    """Raised when required configuration is missing."""


@dataclass(frozen=True, slots=True)
class Config:
    wallet_address: str
    base_rpc_url: str
    facilitator_url: str
    network: str
    price: str


def load_config() -> Config:
    """Load configuration from environment variables.

    Raises ConfigError if WALLET_ADDRESS is not set.
    """
    load_dotenv()

    wallet = os.environ.get("WALLET_ADDRESS", "")
    if not wallet:
        raise ConfigError("WALLET_ADDRESS environment variable is required")

    return Config(
        wallet_address=wallet,
        base_rpc_url=os.environ.get("BASE_RPC_URL", "https://mainnet.base.org"),
        facilitator_url=os.environ.get(
            "FACILITATOR_URL",
            "https://x402.dexter.cash",
        ),
        network=os.environ.get("NETWORK", "eip155:8453"),
        price=os.environ.get("PRICE", "$0.10"),
    )
