"""Regression coverage for contracts real callers paid Augur to screen."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from risk_api.analysis import engine
from risk_api.analysis.engine import clear_analysis_cache
from risk_api.analysis.reputation import clear_reputation_cache
from risk_api.chain.rpc import clear_cache as clear_rpc_cache


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "paid_contract_cases.json"
ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
ZERO_STORAGE_WORD = "0x" + ("0" * 64)


def _load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _case_ids() -> list[str]:
    payload = _load_fixture()
    return [str(case["id"]) for case in payload["cases"]]


@pytest.fixture(autouse=True)
def clear_caches() -> Iterator[None]:
    clear_rpc_cache()
    clear_analysis_cache()
    clear_reputation_cache()
    yield
    clear_rpc_cache()
    clear_analysis_cache()
    clear_reputation_cache()


def test_paid_contract_fixture_contains_only_public_contract_context() -> None:
    payload = _load_fixture()
    assert payload["schema_version"] == 1
    assert payload["snapshot_table_count_at_generation"] == 0
    assert "no source IP" in payload["privacy_note"]

    cases = payload["cases"]
    assert {case["source"] for case in cases} == {"real_paid_request_events"}
    assert len(cases) == 8

    addresses = [case["address"] for case in cases]
    assert len(addresses) == len(set(addresses))
    assert all(ADDRESS_RE.match(address) for address in addresses)
    assert all(case["paid_request_count"] >= 1 for case in cases)

    serialized = json.dumps(payload).lower()
    private_markers = (
        "user_agent",
        "referer",
        "payer_wallet",
        "source_ip",
        "tx_hash",
        "facilitator_payload",
    )
    assert not any(marker in serialized for marker in private_markers)


@pytest.mark.parametrize("case_id", _case_ids())
def test_real_paid_contract_bytecode_regressions(
    monkeypatch: pytest.MonkeyPatch,
    case_id: str,
) -> None:
    payload = _load_fixture()
    case = next(item for item in payload["cases"] if item["id"] == case_id)
    bytecodes = {case["address"].lower(): case["bytecode"]}
    implementation = case.get("implementation")
    if isinstance(implementation, dict):
        bytecodes[str(implementation["address"]).lower()] = str(
            implementation["bytecode"]
        )

    def fake_get_code(address: str, rpc_url: str) -> str:
        _ = rpc_url
        return bytecodes[address.lower()]

    monkeypatch.setattr(engine, "get_code", fake_get_code)
    monkeypatch.setattr(
        engine,
        "get_storage_at",
        lambda address, slot, rpc_url: ZERO_STORAGE_WORD,
    )
    # These fixtures intentionally lock bytecode + policy behavior only.
    # Deployer reputation uses live explorer data in production, so keep it out
    # of this paid-contract corpus to avoid API-dependent regression tests.
    monkeypatch.setattr(engine, "detect_deployer_reputation", lambda address, key: [])

    result = engine.analyze_contract(
        str(case["address"]),
        "https://fixture-rpc.invalid",
        "",
    )
    expected = case["expected"]

    assert result.score == expected["score"]
    assert result.level.value == expected["level"]
    assert result.decision.value == expected["decision"]
    assert result.recommended_policy.action.value == expected["decision"]
    assert result.recommended_policy.reason_codes == expected["reason_codes"]
    assert result.category_scores == expected["category_scores"]
    assert result.proxy_resolution_status.value == expected["proxy_resolution_status"]
    assert [finding.detector for finding in result.findings] == expected["findings"]

    if implementation is None:
        assert result.implementation is None
    else:
        assert result.implementation is not None
        assert result.implementation.address.lower() == implementation["address"]
        assert result.implementation.bytecode_size == implementation["bytecode_size"]
        assert result.implementation.category_scores == implementation["category_scores"]
