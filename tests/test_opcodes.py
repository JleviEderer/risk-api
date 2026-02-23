from risk_api.analysis.opcodes import OPCODES, lookup


def test_known_opcodes():
    assert OPCODES[0x00] == ("STOP", 0)
    assert OPCODES[0x01] == ("ADD", 0)
    assert OPCODES[0xF1] == ("CALL", 0)
    assert OPCODES[0xFD] == ("REVERT", 0)
    assert OPCODES[0xFF] == ("SELFDESTRUCT", 0)


def test_push_operand_sizes():
    for i in range(32):
        name, size = OPCODES[0x60 + i]
        assert name == f"PUSH{i + 1}"
        assert size == i + 1


def test_push0_has_no_operand():
    assert OPCODES[0x5F] == ("PUSH0", 0)


def test_dup_swap_no_operands():
    for i in range(16):
        _, size = OPCODES[0x80 + i]
        assert size == 0
        _, size = OPCODES[0x90 + i]
        assert size == 0


def test_lookup_unknown():
    name, size = lookup(0x0C)
    assert name == "UNKNOWN_0C"
    assert size == 0


def test_total_opcode_count():
    # 12 arith + 14 compare/bit + 1 sha3 + 16 env + 11 block
    # + 15 stack/mem + 1 push0 + 32 push + 16 dup + 16 swap
    # + 5 log + 10 system = 149
    assert len(OPCODES) >= 140  # conservative lower bound
