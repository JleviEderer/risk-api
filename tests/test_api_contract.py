"""Tests for the public /analyze response serializer contract."""

from __future__ import annotations

from risk_api.api_contract import analysis_result_from_snapshot, serialize_analysis_result
from risk_api.analysis.action_policy import (
    ActionContext,
    ActionEvaluation,
    AnalyzeAction,
)
from risk_api.analysis.policy import PolicyAction, PolicyResult


def _result(decision: str = "allow"):
    level = "medium" if decision == "manual_review" else "safe"
    score = 50 if decision == "manual_review" else 0
    return analysis_result_from_snapshot(
        {
            "address": "0x" + "ab" * 20,
            "score": score,
            "level": level,
            "decision": decision,
            "recommended_policy": {
                "action": decision,
                "summary": f"{decision} summary",
                "reason_codes": [f"{decision}_reason"],
            },
            "bytecode_size": 4,
            "findings": [],
            "category_scores": {},
        }
    )


def _approve_context() -> ActionContext:
    return ActionContext(
        action=AnalyzeAction.APPROVE,
        spender="0x" + "12" * 20,
        chain="base",
    )


def _action_evaluation(
    decision: PolicyAction,
    *,
    policy_action: PolicyAction | None = None,
    reason_codes: list[str] | None = None,
) -> ActionEvaluation:
    policy_action = policy_action or decision
    return ActionEvaluation(
        decision=decision,
        recommended_policy=PolicyResult(
            action=policy_action,
            summary=f"{decision.value} action summary",
            reason_codes=reason_codes or ["action_approve_requested"],
        ),
    )


def test_serialize_no_action_emits_contract_decision() -> None:
    data = serialize_analysis_result(_result("allow"))

    assert data["decision"] == "allow"
    assert data["contract_decision"] == "allow"
    assert data["recommended_policy"]["action"] == "allow"  # type: ignore[index]


def test_serialize_action_raises_allow_to_warn() -> None:
    data = serialize_analysis_result(
        _result("allow"),
        action_context=_approve_context(),
        action_evaluation=_action_evaluation(PolicyAction.WARN),
    )

    assert data["decision"] == "warn"
    assert data["contract_decision"] == "allow"
    assert data["recommended_policy"]["action"] == "warn"  # type: ignore[index]
    assert data["recommended_policy"]["reason_codes"] == [  # type: ignore[index]
        "action_approve_requested"
    ]
    assert data["action_evaluation"]["decision"] == "warn"  # type: ignore[index]


def test_serialize_manual_review_contract_passthrough() -> None:
    data = serialize_analysis_result(
        _result("manual_review"),
        action_context=_approve_context(),
        action_evaluation=_action_evaluation(PolicyAction.MANUAL_REVIEW),
    )

    assert data["decision"] == "manual_review"
    assert data["contract_decision"] == "manual_review"
    assert data["recommended_policy"]["action"] == "manual_review"  # type: ignore[index]


def test_serialize_defensive_weaker_action_does_not_lower_top_level() -> None:
    data = serialize_analysis_result(
        _result("manual_review"),
        action_context=_approve_context(),
        action_evaluation=_action_evaluation(PolicyAction.ALLOW),
    )

    assert data["decision"] == "manual_review"
    assert data["contract_decision"] == "manual_review"
    assert data["recommended_policy"]["action"] == "manual_review"  # type: ignore[index]
    assert data["recommended_policy"]["summary"] == "manual_review summary"  # type: ignore[index]
    assert data["action_evaluation"]["decision"] == "allow"  # type: ignore[index]


def test_serialize_rebuilds_top_policy_for_inconsistent_action_evaluation() -> None:
    data = serialize_analysis_result(
        _result("allow"),
        action_context=_approve_context(),
        action_evaluation=_action_evaluation(
            PolicyAction.WARN,
            policy_action=PolicyAction.ALLOW,
        ),
    )

    assert data["decision"] == "warn"
    assert data["recommended_policy"]["action"] == "warn"  # type: ignore[index]
    assert data["recommended_policy"]["summary"] == "warn action summary"  # type: ignore[index]
    assert data["action_evaluation"]["decision"] == "warn"  # type: ignore[index]
    assert (  # nested object remains verbatim for backwards compatibility
        data["action_evaluation"]["recommended_policy"]["action"] == "allow"  # type: ignore[index]
    )
