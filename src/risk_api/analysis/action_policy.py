"""Action-aware policy recommendations layered on top of contract screening."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from risk_api.analysis.policy import PolicyAction, PolicyReasonCode, PolicyResult


class AnalyzeAction(str, Enum):
    APPROVE = "approve"


@dataclass(frozen=True, slots=True)
class ActionContext:
    action: AnalyzeAction
    spender: str
    chain: str = "base"


@dataclass(frozen=True, slots=True)
class ActionEvaluation:
    decision: PolicyAction
    recommended_policy: PolicyResult


def derive_action_evaluation(
    base_policy: PolicyResult,
    action_context: ActionContext,
) -> ActionEvaluation:
    """Derive a narrow action-specific policy from the contract-level policy."""
    if action_context.action != AnalyzeAction.APPROVE:
        raise ValueError(f"Unsupported action context: {action_context.action}")

    action_decision = _approve_decision(base_policy.action)
    action_policy = PolicyResult(
        action=action_decision,
        summary=_approve_summary(action_decision),
        reason_codes=_merge_reason_codes(
            base_policy.reason_codes,
            PolicyReasonCode.ACTION_APPROVE_REQUESTED.value,
        ),
    )
    return ActionEvaluation(
        decision=action_decision,
        recommended_policy=action_policy,
    )


def _approve_decision(base_action: PolicyAction) -> PolicyAction:
    if base_action == PolicyAction.ALLOW:
        return PolicyAction.WARN
    if base_action == PolicyAction.WARN:
        return PolicyAction.MANUAL_REVIEW
    return base_action


def _approve_summary(action: PolicyAction) -> str:
    if action == PolicyAction.BLOCK:
        return (
            "Do not approve this spender automatically. The base contract "
            "screening already recommends blocking interaction."
        )
    if action == PolicyAction.MANUAL_REVIEW:
        return (
            "Escalate before approving this spender. Approvals grant durable "
            "spending authority and should not proceed automatically here."
        )
    return (
        "Allow with caution only if this workflow explicitly expects the "
        "approval. Keep the spender on an allowlist and the approval scope narrow."
    )


def _merge_reason_codes(reason_codes: list[str], extra_code: str) -> list[str]:
    if extra_code in reason_codes:
        return list(reason_codes)
    return [*reason_codes, extra_code]
