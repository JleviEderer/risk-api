"""Tests for environment configuration loading."""

import os

import pytest

from risk_api.config import Config, ConfigError, load_config


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Ensure required env var is set and optional ones are cleared."""
    monkeypatch.setenv("WALLET_ADDRESS", "0x" + "ab" * 20)
    monkeypatch.delenv("ERC8004_AGENT_ID", raising=False)
    monkeypatch.delenv("BASESCAN_API_KEY", raising=False)


def test_load_config_defaults(monkeypatch):
    config = load_config()
    assert config.erc8004_agent_id is None
    assert config.basescan_api_key == ""


def test_load_config_with_agent_id(monkeypatch):
    monkeypatch.setenv("ERC8004_AGENT_ID", "19074")
    config = load_config()
    assert config.erc8004_agent_id == 19074


def test_load_config_with_basescan_key(monkeypatch):
    monkeypatch.setenv("BASESCAN_API_KEY", "my-secret-key")
    config = load_config()
    assert config.basescan_api_key == "my-secret-key"


def test_load_config_empty_agent_id(monkeypatch):
    monkeypatch.setenv("ERC8004_AGENT_ID", "")
    config = load_config()
    assert config.erc8004_agent_id is None


def test_load_config_missing_wallet(monkeypatch):
    monkeypatch.delenv("WALLET_ADDRESS")
    with pytest.raises(ConfigError):
        load_config()
