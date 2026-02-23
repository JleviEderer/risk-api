"""Weighted composite risk scoring: findings → 0-100 score + risk level."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from risk_api.analysis.disassembler import Instruction
from risk_api.analysis.patterns import Finding
from risk_api.analysis.selectors import extract_selectors, find_suspicious_selectors


class RiskLevel(str, Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Per-category point caps
CATEGORY_CAPS: dict[str, int] = {
    "selfdestruct": 30,
    "hidden_mint": 25,
    "honeypot": 25,
    "fee_manipulation": 15,
    "delegatecall": 15,
    "proxy": 10,
    "reentrancy": 10,
    "suspicious_selector": 15,
    "tiny_bytecode": 10,
    "deployer_reputation": 10,
}

SUSPICIOUS_SELECTOR_POINTS = 5


@dataclass(frozen=True, slots=True)
class ScoreResult:
    score: int
    level: RiskLevel
    category_scores: dict[str, int]


def compute_score(
    findings: list[Finding],
    instructions: list[Instruction],
    bytecode_hex: str,
) -> ScoreResult:
    """Compute weighted composite risk score from findings.

    Additional heuristics:
    - Suspicious selectors: +5 each, capped at 15
    - Tiny bytecode (<200 bytes, non-proxy): +10
    """
    category_points: dict[str, int] = {}

    # Accumulate points from findings, capped per category
    for finding in findings:
        cat = finding.detector
        current = category_points.get(cat, 0)
        cap = CATEGORY_CAPS.get(cat, 100)
        category_points[cat] = min(cap, current + finding.points)

    # Suspicious selectors (separate from malicious)
    selectors = extract_selectors(instructions)
    suspicious = find_suspicious_selectors(selectors)
    if suspicious:
        sus_points = min(
            len(suspicious) * SUSPICIOUS_SELECTOR_POINTS,
            CATEGORY_CAPS["suspicious_selector"],
        )
        category_points["suspicious_selector"] = sus_points

    # Tiny bytecode heuristic
    hex_str = bytecode_hex.strip()
    if hex_str.startswith(("0x", "0X")):
        hex_str = hex_str[2:]
    bytecode_len = len(hex_str) // 2
    is_proxy = "proxy" in category_points
    if bytecode_len < 200 and not is_proxy and bytecode_len > 0:
        category_points["tiny_bytecode"] = CATEGORY_CAPS["tiny_bytecode"]

    total = min(100, sum(category_points.values()))
    level = _score_to_level(total)

    return ScoreResult(
        score=total,
        level=level,
        category_scores=category_points,
    )


def _score_to_level(score: int) -> RiskLevel:
    if score <= 15:
        return RiskLevel.SAFE
    if score <= 35:
        return RiskLevel.LOW
    if score <= 55:
        return RiskLevel.MEDIUM
    if score <= 75:
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL
