from risk_api.analysis.disassembler import Instruction, disassemble
from risk_api.analysis.patterns import (
    Severity,
    detect_delegatecall,
    detect_fee_manipulation,
    detect_hidden_mint,
    detect_honeypot_patterns,
    detect_proxy_patterns,
    detect_reentrancy_risk,
    detect_selfdestruct,
    run_all_detectors,
)


def test_detect_selfdestruct():
    # SELFDESTRUCT = 0xFF
    instructions = disassemble("00ff")  # STOP, SELFDESTRUCT
    findings = detect_selfdestruct(instructions)
    assert len(findings) == 1
    assert findings[0].severity == Severity.CRITICAL
    assert findings[0].points == 30
    assert findings[0].detector == "selfdestruct"


def test_detect_selfdestruct_absent():
    instructions = disassemble("6080604052")  # PUSH1 PUSH1 MSTORE
    assert detect_selfdestruct(instructions) == []


def test_detect_delegatecall_raw():
    # DELEGATECALL = 0xF4, without proxy slots → HIGH
    instructions = disassemble("f4")
    findings = detect_delegatecall(instructions)
    assert len(findings) == 1
    assert findings[0].severity == Severity.HIGH
    assert findings[0].points == 15


def test_detect_delegatecall_with_proxy():
    # PUSH32 <EIP-1967 impl slot> + DELEGATECALL → INFO
    eip1967 = "360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
    bytecode = "7f" + eip1967 + "f4"  # PUSH32 + DELEGATECALL
    instructions = disassemble(bytecode)
    findings = detect_delegatecall(instructions)
    assert len(findings) == 1
    assert findings[0].severity == Severity.INFO
    assert findings[0].points == 10


def test_detect_reentrancy_risk():
    # CALL (0xF1) followed by SSTORE (0x55)
    bytecode = "f155"  # CALL then SSTORE
    instructions = disassemble(bytecode)
    findings = detect_reentrancy_risk(instructions)
    assert len(findings) == 1
    assert findings[0].severity == Severity.MEDIUM
    assert findings[0].points == 10


def test_detect_reentrancy_no_sstore():
    # CALL without SSTORE after
    instructions = disassemble("f100")  # CALL then STOP
    assert detect_reentrancy_risk(instructions) == []


def test_detect_proxy_patterns():
    # EIP-1967 implementation slot in PUSH32
    eip1967 = "360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
    bytecode = "7f" + eip1967
    instructions = disassemble(bytecode)
    findings = detect_proxy_patterns(instructions)
    assert len(findings) == 1
    assert findings[0].severity == Severity.INFO
    assert findings[0].detector == "proxy"


def test_detect_proxy_patterns_absent():
    instructions = disassemble("6080604052")
    assert detect_proxy_patterns(instructions) == []


def test_detect_honeypot_patterns():
    # Build minimal: PUSH4 transfer selector + EQ → JUMPI → REVERT
    bytecode = (
        "63a9059cbb"  # PUSH4 transfer(address,uint256)
        "14"          # EQ
        "57"          # JUMPI
        "fd"          # REVERT (fallthrough)
    )
    instructions = disassemble(bytecode)
    findings = detect_honeypot_patterns(instructions)
    assert len(findings) == 1
    assert findings[0].severity == Severity.HIGH
    assert findings[0].points == 25


def test_detect_honeypot_no_transfer():
    # No transfer selector → no honeypot finding
    bytecode = "1457fd"  # EQ JUMPI REVERT but no transfer selector
    instructions = disassemble(bytecode)
    assert detect_honeypot_patterns(instructions) == []


def test_detect_hidden_mint():
    # PUSH4 mint(address,uint256) selector
    bytecode = "6340c10f19"  # PUSH4 0x40c10f19
    instructions = disassemble(bytecode)
    findings = detect_hidden_mint(instructions)
    assert len(findings) == 1
    assert findings[0].severity == Severity.CRITICAL
    assert findings[0].points == 25


def test_detect_hidden_mint_absent():
    # Standard ERC20 selector, no mint
    bytecode = "63a9059cbb"  # PUSH4 transfer
    instructions = disassemble(bytecode)
    assert detect_hidden_mint(instructions) == []


def test_detect_fee_manipulation():
    # PUSH4 setFee(uint256) selector
    bytecode = "6369fe0e2d"  # PUSH4 0x69fe0e2d
    instructions = disassemble(bytecode)
    findings = detect_fee_manipulation(instructions)
    assert len(findings) == 1
    assert findings[0].severity == Severity.HIGH
    assert findings[0].points == 15


def test_detect_fee_manipulation_absent():
    instructions = disassemble("6080604052")
    assert detect_fee_manipulation(instructions) == []


def test_run_all_detectors_combines():
    # SELFDESTRUCT + DELEGATECALL (no proxy) → should get both findings
    bytecode = "f4ff"  # DELEGATECALL then SELFDESTRUCT
    instructions = disassemble(bytecode)
    findings = run_all_detectors(instructions)
    detectors = {f.detector for f in findings}
    assert "selfdestruct" in detectors
    assert "delegatecall" in detectors


def test_run_all_detectors_clean():
    # Simple PUSH1 PUSH1 MSTORE — should produce no findings
    instructions = disassemble("6080604052")
    findings = run_all_detectors(instructions)
    assert findings == []
