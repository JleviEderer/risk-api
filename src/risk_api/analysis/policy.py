"""Thin policy recommendations derived from Augur scoring output."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from risk_api.analysis.patterns import Finding
from risk_api.analysis.scoring import RiskLevel


class PolicyAction(str, Enum):
    ALLOW = "allow"
    WARN = "warn"
    MANUAL_REVIEW = "manual_review"
    BLOCK = "block"


class ProxyResolutionStatus(str, Enum):
    NOT_PROXY = "not_proxy"
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    FETCH_FAILED = "fetch_failed"
    NO_CODE = "no_code"
    NESTED_PROXY = "nested_proxy"


class PolicyReasonCode(str, Enum):
    ACTION_APPROVE_REQUESTED = "action_approve_requested"
    ACTION_APPROVE_SPENDER_ALLOWLISTED = "action_approve_spender_allowlisted"
    ACTION_APPROVE_SPENDER_NOT_ALLOWLISTED = "action_approve_spender_not_allowlisted"
    PROXY_LOGIC_UNRESOLVED = "proxy_logic_unresolved"
    PROXY_LOGIC_FETCH_FAILED = "proxy_logic_fetch_failed"
    PROXY_LOGIC_NO_CODE = "proxy_logic_no_code"
    PROXY_LOGIC_NESTED_PROXY = "proxy_logic_nested_proxy"
    HIGH_RISK_SCORE = "high_risk_score"
    ELEVATED_RISK_SCORE = "elevated_risk_score"
    UPGRADEABLE_PROXY = "upgradeable_proxy"
    HIDDEN_MINT_SIGNAL = "hidden_mint_signal"
    HONEYPOT_SIGNAL = "honeypot_signal"
    SELFDESTRUCT_SIGNAL = "selfdestruct_signal"
    DELEGATECALL_SURFACE = "delegatecall_surface"
    RAW_DELEGATECALL_SURFACE = "raw_delegatecall_surface"
    FEE_MANIPULATION_SIGNAL = "fee_manipulation_signal"
    REENTRANCY_SIGNAL = "reentrancy_signal"
    DEPLOYER_REPUTATION_SIGNAL = "deployer_reputation_signal"
    SUSPICIOUS_SELECTOR_SIGNAL = "suspicious_selector_signal"
    TINY_BYTECODE_SIGNAL = "tiny_bytecode_signal"


@dataclass(frozen=True, slots=True)
class PolicyResult:
    action: PolicyAction
    summary: str
    reason_codes: list[str]


_BLOCK_REASON_CODES = {
    PolicyReasonCode.HONEYPOT_SIGNAL.value,
}

_MANUAL_REVIEW_REASON_CODES = {
    PolicyReasonCode.HIDDEN_MINT_SIGNAL.value,
    PolicyReasonCode.PROXY_LOGIC_UNRESOLVED.value,
    PolicyReasonCode.RAW_DELEGATECALL_SURFACE.value,
    PolicyReasonCode.SELFDESTRUCT_SIGNAL.value,
}

_MANAGED_PROXY_ADMIN_SURFACE_REASON_CODES = {
    PolicyReasonCode.HIGH_RISK_SCORE.value,
    PolicyReasonCode.ELEVATED_RISK_SCORE.value,
    PolicyReasonCode.UPGRADEABLE_PROXY.value,
    PolicyReasonCode.HIDDEN_MINT_SIGNAL.value,
    PolicyReasonCode.DELEGATECALL_SURFACE.value,
    PolicyReasonCode.RAW_DELEGATECALL_SURFACE.value,
    PolicyReasonCode.SUSPICIOUS_SELECTOR_SIGNAL.value,
}


def _has_category(category_scores: dict[str, int], category: str) -> bool:
    return category in category_scores or f"impl_{category}" in category_scores


def _has_raw_delegatecall(findings: list[Finding]) -> bool:
    return any(
        finding.detector.endswith("delegatecall")
        and finding.severity.value in {"high", "critical"}
        for finding in findings
    )


def _proxy_resolution_reason_codes(
    proxy_resolution_status: ProxyResolutionStatus,
) -> list[str]:
    if proxy_resolution_status == ProxyResolutionStatus.UNRESOLVED:
        return [
            PolicyReasonCode.PROXY_LOGIC_UNRESOLVED.value,
        ]
    if proxy_resolution_status == ProxyResolutionStatus.FETCH_FAILED:
        return [
            PolicyReasonCode.PROXY_LOGIC_UNRESOLVED.value,
            PolicyReasonCode.PROXY_LOGIC_FETCH_FAILED.value,
        ]
    if proxy_resolution_status == ProxyResolutionStatus.NO_CODE:
        return [
            PolicyReasonCode.PROXY_LOGIC_UNRESOLVED.value,
            PolicyReasonCode.PROXY_LOGIC_NO_CODE.value,
        ]
    if proxy_resolution_status == ProxyResolutionStatus.NESTED_PROXY:
        return [
            PolicyReasonCode.PROXY_LOGIC_UNRESOLVED.value,
            PolicyReasonCode.PROXY_LOGIC_NESTED_PROXY.value,
        ]
    return []


def _reason_codes(
    score: int,
    category_scores: dict[str, int],
    findings: list[Finding],
    proxy_resolution_status: ProxyResolutionStatus,
) -> list[str]:
    reason_codes = _proxy_resolution_reason_codes(proxy_resolution_status)
    checks = [
        (PolicyReasonCode.HIGH_RISK_SCORE.value, score >= 56),
        (PolicyReasonCode.ELEVATED_RISK_SCORE.value, 36 <= score <= 55),
        (PolicyReasonCode.UPGRADEABLE_PROXY.value, _has_category(category_scores, "proxy")),
        (PolicyReasonCode.HIDDEN_MINT_SIGNAL.value, _has_category(category_scores, "hidden_mint")),
        (PolicyReasonCode.HONEYPOT_SIGNAL.value, _has_category(category_scores, "honeypot")),
        (PolicyReasonCode.SELFDESTRUCT_SIGNAL.value, _has_category(category_scores, "selfdestruct")),
        (PolicyReasonCode.DELEGATECALL_SURFACE.value, _has_category(category_scores, "delegatecall")),
        (PolicyReasonCode.RAW_DELEGATECALL_SURFACE.value, _has_raw_delegatecall(findings)),
        (
            PolicyReasonCode.FEE_MANIPULATION_SIGNAL.value,
            _has_category(category_scores, "fee_manipulation"),
        ),
        (PolicyReasonCode.REENTRANCY_SIGNAL.value, _has_category(category_scores, "reentrancy")),
        (
            PolicyReasonCode.DEPLOYER_REPUTATION_SIGNAL.value,
            _has_category(category_scores, "deployer_reputation"),
        ),
        (
            PolicyReasonCode.SUSPICIOUS_SELECTOR_SIGNAL.value,
            _has_category(category_scores, "suspicious_selector"),
        ),
        (
            PolicyReasonCode.TINY_BYTECODE_SIGNAL.value,
            _has_category(category_scores, "tiny_bytecode"),
        ),
    ]
    reason_codes.extend(code for code, enabled in checks if enabled)
    return reason_codes


def _is_managed_proxy_admin_surface(reason_codes: list[str]) -> bool:
    codes = set(reason_codes)
    if PolicyReasonCode.UPGRADEABLE_PROXY.value not in codes:
        return False
    if PolicyReasonCode.HIDDEN_MINT_SIGNAL.value not in codes:
        return False
    return codes.issubset(_MANAGED_PROXY_ADMIN_SURFACE_REASON_CODES)


def derive_policy(
    score: int,
    level: RiskLevel,
    findings: list[Finding],
    category_scores: dict[str, int],
    proxy_resolution_status: ProxyResolutionStatus = ProxyResolutionStatus.NOT_PROXY,
) -> PolicyResult:
    reason_codes = _reason_codes(
        score=score,
        category_scores=category_scores,
        findings=findings,
        proxy_resolution_status=proxy_resolution_status,
    )

    if _is_managed_proxy_admin_surface(reason_codes):
        return PolicyResult(
            action=PolicyAction.MANUAL_REVIEW,
            summary=(
                "Escalate before interaction. This looks like an upgradeable, "
                "admin-controlled asset rather than an obvious trap, so require "
                "an explicit issuer-aware override before the workflow proceeds."
            ),
            reason_codes=reason_codes,
        )

    if level in {RiskLevel.HIGH, RiskLevel.CRITICAL} or any(
        code in _BLOCK_REASON_CODES for code in reason_codes
    ):
        return PolicyResult(
            action=PolicyAction.BLOCK,
            summary=(
                "Block automatic interaction by default. Only proceed with an "
                "explicit override after deeper review."
            ),
            reason_codes=reason_codes,
        )

    if (
        level == RiskLevel.MEDIUM
        or any(code in _MANUAL_REVIEW_REASON_CODES for code in reason_codes)
    ):
        return PolicyResult(
            action=PolicyAction.MANUAL_REVIEW,
            summary=(
                "Escalate before interaction. Use a human review step or a "
                "heavier tool before the workflow proceeds."
            ),
            reason_codes=reason_codes,
        )

    if level == RiskLevel.LOW or reason_codes:
        return PolicyResult(
            action=PolicyAction.WARN,
            summary=(
                "Allow with caution. Log the findings and keep the contract on a "
                "watchlist or secondary review path."
            ),
            reason_codes=reason_codes,
        )

    return PolicyResult(
        action=PolicyAction.ALLOW,
        summary=(
            "Allow by default for first-pass automation. Continue only if this "
            "matches your broader strategy and trust model."
        ),
        reason_codes=reason_codes,
    )
