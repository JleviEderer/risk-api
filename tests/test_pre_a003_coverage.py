"""Pre-A-003 regression coverage for decision-primary response design."""

from __future__ import annotations

from unittest.mock import patch

from risk_api.api_contract import analysis_result_from_snapshot
from risk_api.analysis.patterns import Finding, Severity
from risk_api.analysis.policy import PolicyAction, PolicyReasonCode, derive_policy
from risk_api.analysis.scoring import RiskLevel


def test_synthetic_critical_block_case_covers_primary_decision_branch() -> None:
    policy = derive_policy(
        score=85,
        level=RiskLevel.CRITICAL,
        findings=[
            Finding(
                "honeypot",
                Severity.HIGH,
                "Blacklist-style transfer restriction detected",
                "Synthetic pre-A-003 block coverage.",
                25,
            ),
            Finding(
                "selfdestruct",
                Severity.CRITICAL,
                "SELFDESTRUCT opcode found",
                "Synthetic pre-A-003 block coverage.",
                30,
            ),
        ],
        category_scores={
            "honeypot": 25,
            "selfdestruct": 30,
            "hidden_mint": 30,
        },
    )

    assert policy.action == PolicyAction.BLOCK
    assert PolicyReasonCode.HIGH_RISK_SCORE.value in policy.reason_codes
    assert PolicyReasonCode.HONEYPOT_SIGNAL.value in policy.reason_codes
    assert PolicyReasonCode.SELFDESTRUCT_SIGNAL.value in policy.reason_codes


def test_weth_approve_keeps_contract_allow_but_action_warn(client) -> None:
    weth_address = "0x4200000000000000000000000000000000000006"
    spender = "0x1111111111111111111111111111111111111111"
    clean_weth_result = analysis_result_from_snapshot(
        {
            "address": weth_address,
            "score": 0,
            "level": "safe",
            "decision": "allow",
            "recommended_policy": {
                "action": "allow",
                "summary": "Allow by default.",
                "reason_codes": [],
            },
            "bytecode_size": 2041,
            "findings": [],
            "category_scores": {},
        }
    )

    with patch("risk_api.app.get_code", return_value="0x60006000"), patch(
        "risk_api.app.analyze_contract",
        return_value=clean_weth_result,
    ):
        resp = client.get(
            f"/analyze?address={weth_address}"
            f"&action=approve&spender={spender}&chain=base"
        )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["address"] == weth_address
    assert data["score"] == 0
    assert data["level"] == "safe"
    assert data["decision"] == "allow"
    assert data["recommended_policy"]["action"] == "allow"
    assert data["recommended_policy"]["reason_codes"] == []
    assert data["action_context"] == {
        "action": "approve",
        "spender": spender,
        "chain": "base",
    }
    assert data["action_evaluation"]["decision"] == "warn"
    assert data["action_evaluation"]["recommended_policy"]["action"] == "warn"
    assert data["action_evaluation"]["recommended_policy"]["reason_codes"] == [
        PolicyReasonCode.ACTION_APPROVE_REQUESTED.value
    ]
