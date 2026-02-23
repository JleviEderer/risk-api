"""Analysis engine: orchestrates fetch → disassemble → detect → score."""

from __future__ import annotations

from dataclasses import dataclass

from risk_api.analysis.disassembler import disassemble
from risk_api.analysis.patterns import Finding, run_all_detectors
from risk_api.analysis.scoring import RiskLevel, ScoreResult, compute_score
from risk_api.chain.rpc import get_code


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    address: str
    score: int
    level: RiskLevel
    findings: list[Finding]
    category_scores: dict[str, int]
    bytecode_size: int


def analyze_contract(address: str, rpc_url: str) -> AnalysisResult:
    """Full analysis pipeline: fetch bytecode → disassemble → detect → score.

    Raises RPCError if bytecode fetch fails.
    """
    bytecode_hex = get_code(address, rpc_url)

    # Strip 0x prefix for size calculation
    hex_body = bytecode_hex[2:] if bytecode_hex.startswith("0x") else bytecode_hex
    bytecode_size = len(hex_body) // 2

    instructions = disassemble(bytecode_hex)
    findings = run_all_detectors(instructions)
    score_result: ScoreResult = compute_score(findings, instructions, bytecode_hex)

    return AnalysisResult(
        address=address,
        score=score_result.score,
        level=score_result.level,
        findings=findings,
        category_scores=score_result.category_scores,
        bytecode_size=bytecode_size,
    )
