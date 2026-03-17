"""Shared API contract serialization helpers."""

from __future__ import annotations

from typing import Any, Mapping

from risk_api.analysis.engine import AnalysisResult, ImplementationResult
from risk_api.analysis.patterns import Finding, Severity
from risk_api.analysis.policy import (
    PolicyAction,
    PolicyResult,
    ProxyResolutionStatus,
    derive_policy,
)
from risk_api.analysis.scoring import RiskLevel


def serialize_analysis_result(result: AnalysisResult) -> dict[str, object]:
    """Serialize an analysis result into the public wire shape."""
    response_data: dict[str, object] = {
        "address": result.address,
        "score": result.score,
        "level": result.level.value,
        "decision": result.decision.value,
        "recommended_policy": {
            "action": result.recommended_policy.action.value,
            "summary": result.recommended_policy.summary,
            "reason_codes": result.recommended_policy.reason_codes,
        },
        "bytecode_size": result.bytecode_size,
        "findings": [_serialize_finding(finding) for finding in result.findings],
        "category_scores": result.category_scores,
    }

    if result.implementation is not None:
        response_data["implementation"] = _serialize_implementation(result.implementation)

    return response_data


def normalize_analysis_snapshot(snapshot: Mapping[str, Any]) -> dict[str, object]:
    """Round-trip a static snapshot through the live serializer."""
    return serialize_analysis_result(analysis_result_from_snapshot(snapshot))


def analysis_result_from_snapshot(snapshot: Mapping[str, Any]) -> AnalysisResult:
    """Build an AnalysisResult from a snapshot-like mapping."""
    implementation = _implementation_from_mapping(snapshot.get("implementation"))
    proxy_resolution_status = _proxy_resolution_status_from_snapshot(
        snapshot,
        implementation_present=implementation is not None,
    )

    findings = [_finding_from_mapping(finding) for finding in snapshot.get("findings", [])]
    category_scores = {
        str(category): int(points)
        for category, points in dict(snapshot.get("category_scores", {})).items()
    }
    level = RiskLevel(str(snapshot["level"]))
    score = int(snapshot["score"])

    recommended_policy_raw = snapshot.get("recommended_policy")
    if isinstance(recommended_policy_raw, Mapping):
        recommended_policy = _policy_from_mapping(recommended_policy_raw)
    else:
        recommended_policy = derive_policy(
            score=score,
            level=level,
            findings=findings,
            category_scores=category_scores,
            proxy_resolution_status=proxy_resolution_status,
        )

    decision_raw = snapshot.get("decision")
    decision = (
        PolicyAction(str(decision_raw))
        if decision_raw is not None
        else recommended_policy.action
    )

    return AnalysisResult(
        address=str(snapshot["address"]),
        score=score,
        level=level,
        decision=decision,
        recommended_policy=recommended_policy,
        findings=findings,
        category_scores=category_scores,
        bytecode_size=int(snapshot["bytecode_size"]),
        implementation=implementation,
        proxy_resolution_status=proxy_resolution_status,
    )


def _serialize_finding(finding: Finding) -> dict[str, object]:
    return {
        "detector": finding.detector,
        "severity": finding.severity.value,
        "title": finding.title,
        "description": finding.description,
        "points": finding.points,
    }


def _serialize_implementation(implementation: ImplementationResult) -> dict[str, object]:
    return {
        "address": implementation.address,
        "bytecode_size": implementation.bytecode_size,
        "findings": [_serialize_finding(finding) for finding in implementation.findings],
        "category_scores": implementation.category_scores,
    }


def _finding_from_mapping(finding: Mapping[str, Any]) -> Finding:
    offset = finding.get("offset")
    return Finding(
        detector=str(finding["detector"]),
        severity=Severity(str(finding["severity"])),
        title=str(finding["title"]),
        description=str(finding["description"]),
        points=int(finding["points"]),
        offset=int(offset) if offset is not None else None,
    )


def _policy_from_mapping(policy: Mapping[str, Any]) -> PolicyResult:
    return PolicyResult(
        action=PolicyAction(str(policy["action"])),
        summary=str(policy["summary"]),
        reason_codes=[str(code) for code in policy.get("reason_codes", [])],
    )


def _implementation_from_mapping(
    implementation: Any,
) -> ImplementationResult | None:
    if not isinstance(implementation, Mapping):
        return None

    return ImplementationResult(
        address=str(implementation["address"]),
        bytecode_size=int(implementation["bytecode_size"]),
        findings=[
            _finding_from_mapping(finding)
            for finding in implementation.get("findings", [])
        ],
        category_scores={
            str(category): int(points)
            for category, points in dict(
                implementation.get("category_scores", {})
            ).items()
        },
    )


def _proxy_resolution_status_from_snapshot(
    snapshot: Mapping[str, Any], *, implementation_present: bool,
) -> ProxyResolutionStatus:
    raw_status = snapshot.get("proxy_resolution_status")
    if raw_status is not None:
        return ProxyResolutionStatus(str(raw_status))
    if implementation_present:
        return ProxyResolutionStatus.RESOLVED
    return ProxyResolutionStatus.NOT_PROXY
