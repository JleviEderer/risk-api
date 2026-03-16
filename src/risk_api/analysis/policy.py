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


@dataclass(frozen=True, slots=True)
class PolicyResult:
    action: PolicyAction
    summary: str
    reason_codes: list[str]


def _has_category(category_scores: dict[str, int], category: str) -> bool:
    return category in category_scores or f"impl_{category}" in category_scores


def _has_proxy_resolution_gap(
    findings: list[Finding], implementation_present: bool,
) -> bool:
    if implementation_present:
        return False

    unresolved_titles = {
        "Proxy implementation could not be resolved",
        "Proxy implementation could not be analyzed",
        "Implementation is itself a proxy",
    }
    return any(
        finding.detector == "proxy" and finding.title in unresolved_titles
        for finding in findings
    )


def _reason_codes(
    score: int,
    category_scores: dict[str, int],
    findings: list[Finding],
    implementation_present: bool,
) -> list[str]:
    checks = [
        (
            "proxy_logic_unresolved",
            _has_proxy_resolution_gap(findings, implementation_present),
        ),
        ("high_risk_score", score >= 56),
        ("elevated_risk_score", 36 <= score <= 55),
        ("upgradeable_proxy", _has_category(category_scores, "proxy")),
        ("hidden_mint_signal", _has_category(category_scores, "hidden_mint")),
        ("honeypot_signal", _has_category(category_scores, "honeypot")),
        ("selfdestruct_signal", _has_category(category_scores, "selfdestruct")),
        ("delegatecall_surface", _has_category(category_scores, "delegatecall")),
        ("fee_manipulation_signal", _has_category(category_scores, "fee_manipulation")),
        ("reentrancy_signal", _has_category(category_scores, "reentrancy")),
        (
            "deployer_reputation_signal",
            _has_category(category_scores, "deployer_reputation"),
        ),
        (
            "suspicious_selector_signal",
            _has_category(category_scores, "suspicious_selector"),
        ),
        ("tiny_bytecode_signal", _has_category(category_scores, "tiny_bytecode")),
    ]
    return [code for code, enabled in checks if enabled]


def derive_policy(
    score: int,
    level: RiskLevel,
    findings: list[Finding],
    category_scores: dict[str, int],
    implementation_present: bool,
) -> PolicyResult:
    reason_codes = _reason_codes(
        score=score,
        category_scores=category_scores,
        findings=findings,
        implementation_present=implementation_present,
    )

    if level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
        return PolicyResult(
            action=PolicyAction.BLOCK,
            summary=(
                "Block automatic interaction by default. Only proceed with an "
                "explicit override after deeper review."
            ),
            reason_codes=reason_codes,
        )

    if level == RiskLevel.MEDIUM or "proxy_logic_unresolved" in reason_codes:
        return PolicyResult(
            action=PolicyAction.MANUAL_REVIEW,
            summary=(
                "Escalate before interaction. Use a human review step or a "
                "heavier tool before the workflow proceeds."
            ),
            reason_codes=reason_codes,
        )

    if level == RiskLevel.LOW:
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
