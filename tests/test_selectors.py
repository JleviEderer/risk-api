from risk_api.analysis.disassembler import Instruction, disassemble
from risk_api.analysis.selectors import (
    ERC20_SELECTORS,
    MALICIOUS_SELECTORS,
    SUSPICIOUS_SELECTORS,
    extract_selectors,
    find_malicious_selectors,
    find_suspicious_selectors,
)


def test_extract_push4_selectors():
    # Build bytecode with PUSH4 <selector> EQ PUSH2 <dest> JUMPI pattern
    # transfer(address,uint256) = 0xa9059cbb
    # balanceOf(address) = 0x70a08231
    bytecode = (
        "63a9059cbb"  # PUSH4 0xa9059cbb
        "14"  # EQ
        "6100"  # PUSH2 (placeholder)
        "57"  # JUMPI
        "6370a08231"  # PUSH4 0x70a08231
        "14"  # EQ
    )
    instructions = disassemble(bytecode)
    selectors = extract_selectors(instructions)
    assert bytes.fromhex("a9059cbb") in selectors
    assert bytes.fromhex("70a08231") in selectors
    assert len(selectors) == 2


def test_find_malicious_selectors():
    selectors = {
        bytes.fromhex("40c10f19"),  # mint(address,uint256) — malicious
        bytes.fromhex("a9059cbb"),  # transfer — standard ERC20
    }
    malicious = find_malicious_selectors(selectors)
    assert len(malicious) == 1
    assert bytes.fromhex("40c10f19") in malicious
    assert "mint" in malicious[bytes.fromhex("40c10f19")]


def test_find_suspicious_selectors():
    selectors = {
        bytes.fromhex("715018a6"),  # renounceOwnership
        bytes.fromhex("18160ddd"),  # totalSupply — standard
    }
    suspicious = find_suspicious_selectors(selectors)
    assert len(suspicious) == 1
    assert bytes.fromhex("715018a6") in suspicious


def test_no_false_positives_on_clean_erc20():
    # Pure ERC20 selectors should not match malicious or suspicious
    selectors = set(ERC20_SELECTORS.keys())
    assert len(find_malicious_selectors(selectors)) == 0
    assert len(find_suspicious_selectors(selectors)) == 0


def test_empty_instructions():
    selectors = extract_selectors([])
    assert selectors == set()


def test_non_push4_instructions_ignored():
    # PUSH1, PUSH2, PUSH32 should not be extracted as selectors
    instructions = [
        Instruction(0, 0x60, "PUSH1", b"\xff"),
        Instruction(2, 0x61, "PUSH2", b"\xff\xff"),
        Instruction(5, 0x7F, "PUSH32", b"\xff" * 32),
    ]
    assert extract_selectors(instructions) == set()
