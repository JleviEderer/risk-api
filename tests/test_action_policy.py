from risk_api.analysis.action_policy import (
    ActionContext,
    AnalyzeAction,
    derive_action_evaluation,
)
from risk_api.analysis.policy import PolicyAction, PolicyReasonCode, PolicyResult


def test_approve_escalates_allow_to_warn():
    evaluation = derive_action_evaluation(
        PolicyResult(
            action=PolicyAction.ALLOW,
            summary="Allow by default.",
            reason_codes=[],
        ),
        ActionContext(
            action=AnalyzeAction.APPROVE,
            spender="0x" + "ab" * 20,
        ),
    )

    assert evaluation.decision == PolicyAction.WARN
    assert evaluation.recommended_policy.action == PolicyAction.WARN
    assert evaluation.recommended_policy.reason_codes == [
        PolicyReasonCode.ACTION_APPROVE_REQUESTED.value
    ]


def test_approve_escalates_warn_to_manual_review():
    evaluation = derive_action_evaluation(
        PolicyResult(
            action=PolicyAction.WARN,
            summary="Allow with caution.",
            reason_codes=[PolicyReasonCode.FEE_MANIPULATION_SIGNAL.value],
        ),
        ActionContext(
            action=AnalyzeAction.APPROVE,
            spender="0x" + "cd" * 20,
        ),
    )

    assert evaluation.decision == PolicyAction.MANUAL_REVIEW
    assert evaluation.recommended_policy.action == PolicyAction.MANUAL_REVIEW
    assert evaluation.recommended_policy.reason_codes == [
        PolicyReasonCode.FEE_MANIPULATION_SIGNAL.value,
        PolicyReasonCode.ACTION_APPROVE_REQUESTED.value,
    ]


def test_approve_preserves_block():
    evaluation = derive_action_evaluation(
        PolicyResult(
            action=PolicyAction.BLOCK,
            summary="Block automatic interaction.",
            reason_codes=[PolicyReasonCode.HONEYPOT_SIGNAL.value],
        ),
        ActionContext(
            action=AnalyzeAction.APPROVE,
            spender="0x" + "ef" * 20,
        ),
    )

    assert evaluation.decision == PolicyAction.BLOCK
    assert evaluation.recommended_policy.action == PolicyAction.BLOCK
    assert evaluation.recommended_policy.reason_codes == [
        PolicyReasonCode.HONEYPOT_SIGNAL.value,
        PolicyReasonCode.ACTION_APPROVE_REQUESTED.value,
    ]


def test_approve_allowlisted_spender_can_preserve_allow():
    spender = "0x" + "11" * 20
    evaluation = derive_action_evaluation(
        PolicyResult(
            action=PolicyAction.ALLOW,
            summary="Allow by default.",
            reason_codes=[],
        ),
        ActionContext(
            action=AnalyzeAction.APPROVE,
            spender=spender,
        ),
        approve_spender_allowlist=(spender.upper(),),
    )

    assert evaluation.decision == PolicyAction.ALLOW
    assert evaluation.recommended_policy.action == PolicyAction.ALLOW
    assert evaluation.recommended_policy.reason_codes == [
        PolicyReasonCode.ACTION_APPROVE_REQUESTED.value,
        PolicyReasonCode.ACTION_APPROVE_SPENDER_ALLOWLISTED.value,
    ]


def test_approve_non_allowlisted_spender_escalates_to_manual_review():
    evaluation = derive_action_evaluation(
        PolicyResult(
            action=PolicyAction.ALLOW,
            summary="Allow by default.",
            reason_codes=[],
        ),
        ActionContext(
            action=AnalyzeAction.APPROVE,
            spender="0x" + "22" * 20,
        ),
        approve_spender_allowlist=("0x" + "33" * 20,),
    )

    assert evaluation.decision == PolicyAction.MANUAL_REVIEW
    assert evaluation.recommended_policy.action == PolicyAction.MANUAL_REVIEW
    assert evaluation.recommended_policy.reason_codes == [
        PolicyReasonCode.ACTION_APPROVE_REQUESTED.value,
        PolicyReasonCode.ACTION_APPROVE_SPENDER_NOT_ALLOWLISTED.value,
    ]
