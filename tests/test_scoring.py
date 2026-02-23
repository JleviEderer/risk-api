from risk_api.analysis.disassembler import disassemble
from risk_api.analysis.patterns import Finding, Severity, run_all_detectors
from risk_api.analysis.scoring import RiskLevel, compute_score


def test_clean_contract_is_safe():
    # Simple bytecode, no risky patterns, >200 bytes
    bytecode = "6080604052" + "00" * 200  # padded to >200 bytes
    instructions = disassemble(bytecode)
    findings = run_all_detectors(instructions)
    result = compute_score(findings, instructions, bytecode)
    assert result.score == 0
    assert result.level == RiskLevel.SAFE


def test_selfdestruct_scores_30():
    bytecode = "ff" + "00" * 200  # SELFDESTRUCT + padding
    instructions = disassemble(bytecode)
    findings = run_all_detectors(instructions)
    result = compute_score(findings, instructions, bytecode)
    assert result.category_scores.get("selfdestruct") == 30
    assert result.level == RiskLevel.LOW  # 30 points → 16-35 range


def test_tiny_bytecode_penalty():
    # 10 bytes of no-op — should get tiny_bytecode penalty
    bytecode = "00" * 10
    instructions = disassemble(bytecode)
    findings = run_all_detectors(instructions)
    result = compute_score(findings, instructions, bytecode)
    assert result.category_scores.get("tiny_bytecode") == 10


def test_tiny_bytecode_not_for_proxy():
    # Tiny proxy should NOT get tiny_bytecode penalty
    eip1967 = "360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
    bytecode = "7f" + eip1967 + "f4"  # PUSH32 + DELEGATECALL — proxy, <200 bytes
    instructions = disassemble(bytecode)
    findings = run_all_detectors(instructions)
    result = compute_score(findings, instructions, bytecode)
    assert "tiny_bytecode" not in result.category_scores


def test_category_cap_prevents_overflow():
    # Multiple selfdestruct findings should still cap at 30
    findings = [
        Finding("selfdestruct", Severity.CRITICAL, "test", "test", 30),
        Finding("selfdestruct", Severity.CRITICAL, "test2", "test2", 30),
    ]
    bytecode = "00" * 200
    instructions = disassemble(bytecode)
    result = compute_score(findings, instructions, bytecode)
    assert result.category_scores["selfdestruct"] == 30


def test_score_capped_at_100():
    # Stack up enough findings to exceed 100
    findings = [
        Finding("selfdestruct", Severity.CRITICAL, "t", "t", 30),
        Finding("hidden_mint", Severity.CRITICAL, "t", "t", 25),
        Finding("honeypot", Severity.HIGH, "t", "t", 25),
        Finding("fee_manipulation", Severity.HIGH, "t", "t", 15),
        Finding("delegatecall", Severity.HIGH, "t", "t", 15),
    ]
    bytecode = "00" * 10  # also gets tiny_bytecode
    instructions = disassemble(bytecode)
    result = compute_score(findings, instructions, bytecode)
    assert result.score == 100
    assert result.level == RiskLevel.CRITICAL


def test_risk_level_boundaries():
    from risk_api.analysis.scoring import _score_to_level

    assert _score_to_level(0) == RiskLevel.SAFE
    assert _score_to_level(15) == RiskLevel.SAFE
    assert _score_to_level(16) == RiskLevel.LOW
    assert _score_to_level(35) == RiskLevel.LOW
    assert _score_to_level(36) == RiskLevel.MEDIUM
    assert _score_to_level(55) == RiskLevel.MEDIUM
    assert _score_to_level(56) == RiskLevel.HIGH
    assert _score_to_level(75) == RiskLevel.HIGH
    assert _score_to_level(76) == RiskLevel.CRITICAL
    assert _score_to_level(100) == RiskLevel.CRITICAL


def test_suspicious_selectors_scored():
    # PUSH4 renounceOwnership() = 0x715018a6
    bytecode = "63715018a6" + "00" * 200
    instructions = disassemble(bytecode)
    findings = run_all_detectors(instructions)
    result = compute_score(findings, instructions, bytecode)
    assert result.category_scores.get("suspicious_selector", 0) == 5


def test_deployer_reputation_category_cap():
    # Multiple deployer_reputation findings should cap at 10
    findings = [
        Finding("deployer_reputation", Severity.INFO, "young", "desc", 5),
        Finding("deployer_reputation", Severity.INFO, "low tx", "desc", 5),
        Finding("deployer_reputation", Severity.INFO, "extra", "desc", 5),
    ]
    bytecode = "00" * 200
    instructions = disassemble(bytecode)
    result = compute_score(findings, instructions, bytecode)
    assert result.category_scores["deployer_reputation"] == 10
