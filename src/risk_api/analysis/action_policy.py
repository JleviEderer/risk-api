"""Action-aware policy recommendations layered on top of contract screening."""

from __future__ import annotations

from collections.abc import Collection
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


class ApproveSpenderTrust(str, Enum):
    UNCHECKED = "unchecked"
    ALLOWLISTED = "allowlisted"
    NOT_ALLOWLISTED = "not_allowlisted"


def derive_action_evaluation(
    base_policy: PolicyResult,
    action_context: ActionContext,
    *,
    approve_spender_allowlist: Collection[str] | None = None,
) -> ActionEvaluation:
    """Derive a narrow action-specific policy from the contract-level policy."""
    if action_context.action != AnalyzeAction.APPROVE:
        raise ValueError(f"Unsupported action context: {action_context.action}")

    spender_trust = classify_approve_spender_trust(
        action_context.spender,
        approve_spender_allowlist,
    )
    action_decision = _approve_decision(
        base_policy.action,
        spender_trust=spender_trust,
    )
    action_policy = PolicyResult(
        action=action_decision,
        summary=_approve_summary(
            action_decision,
            base_action=base_policy.action,
            spender_trust=spender_trust,
        ),
        reason_codes=_merge_reason_codes(base_policy.reason_codes, spender_trust),
    )
    return ActionEvaluation(
        decision=action_decision,
        recommended_policy=action_policy,
    )


def classify_approve_spender_trust(
    spender: str,
    approve_spender_allowlist: Collection[str] | None,
) -> ApproveSpenderTrust:
    if approve_spender_allowlist is None:
        return ApproveSpenderTrust.UNCHECKED

    normalized_allowlist = {address.lower() for address in approve_spender_allowlist}
    if spender.lower() in normalized_allowlist:
        return ApproveSpenderTrust.ALLOWLISTED
    return ApproveSpenderTrust.NOT_ALLOWLISTED


def _approve_decision(
    base_action: PolicyAction,
    *,
    spender_trust: ApproveSpenderTrust,
) -> PolicyAction:
    if base_action in {PolicyAction.MANUAL_REVIEW, PolicyAction.BLOCK}:
        return base_action

    if spender_trust == ApproveSpenderTrust.ALLOWLISTED:
        return base_action

    if spender_trust == ApproveSpenderTrust.NOT_ALLOWLISTED:
        return PolicyAction.MANUAL_REVIEW

    if base_action == PolicyAction.ALLOW:
        return PolicyAction.WARN
    if base_action == PolicyAction.WARN:
        return PolicyAction.MANUAL_REVIEW
    return base_action


def _approve_summary(
    action: PolicyAction,
    *,
    base_action: PolicyAction,
    spender_trust: ApproveSpenderTrust,
) -> str:
    if action == PolicyAction.BLOCK:
        return (
            "Do not approve this spender automatically. The base contract "
            "screening already recommends blocking interaction."
        )

    if spender_trust == ApproveSpenderTrust.NOT_ALLOWLISTED:
        return (
            "Escalate before approving this spender. It is not on the configured "
            "spender allowlist, so this approval should not proceed automatically."
        )

    if action == PolicyAction.MANUAL_REVIEW:
        return (
            "Escalate before approving this spender. Approvals grant durable "
            "spending authority and the base contract screening already needs a "
            "human review step."
        )

    if action == PolicyAction.WARN:
        if spender_trust == ApproveSpenderTrust.ALLOWLISTED:
            return (
                "Allow with caution only if this workflow explicitly expects the "
                "approval. The spender is on your allowlist, but the base contract "
                "still has residual risk signals."
            )
        return (
            "Allow with caution only if this workflow explicitly expects the "
            "approval. Keep the spender on an allowlist and the approval scope narrow."
        )

    if spender_trust == ApproveSpenderTrust.ALLOWLISTED:
        return (
            "Allow only if this workflow explicitly expects the approval and this "
            "spender is still on your configured allowlist. Keep the approval "
            "scope narrow."
        )

    if base_action == PolicyAction.ALLOW:
        return (
            "Allow by default for first-pass automation only if this workflow "
            "explicitly expects the approval and the approval scope is narrow."
        )

    return (
        "Allow only if this workflow explicitly expects the approval and this "
        "matches your broader strategy and trust model."
    )


def _merge_reason_codes(
    reason_codes: list[str],
    spender_trust: ApproveSpenderTrust,
) -> list[str]:
    merged = list(reason_codes)
    extra_codes = [PolicyReasonCode.ACTION_APPROVE_REQUESTED.value]

    if spender_trust == ApproveSpenderTrust.ALLOWLISTED:
        extra_codes.append(
            PolicyReasonCode.ACTION_APPROVE_SPENDER_ALLOWLISTED.value
        )
    elif spender_trust == ApproveSpenderTrust.NOT_ALLOWLISTED:
        extra_codes.append(
            PolicyReasonCode.ACTION_APPROVE_SPENDER_NOT_ALLOWLISTED.value
        )

    for extra_code in extra_codes:
        if extra_code not in merged:
            merged.append(extra_code)
    return merged
