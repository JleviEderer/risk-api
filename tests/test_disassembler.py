from risk_api.analysis.disassembler import Instruction, disassemble


def test_simple_sequence():
    # PUSH1 0x80 PUSH1 0x40 MSTORE
    bytecode = "6080604052"
    instructions = disassemble(bytecode)
    assert len(instructions) == 3
    assert instructions[0] == Instruction(0, 0x60, "PUSH1", b"\x80")
    assert instructions[1] == Instruction(2, 0x60, "PUSH1", b"\x40")
    assert instructions[2] == Instruction(4, 0x52, "MSTORE", b"")


def test_0x_prefix():
    instructions = disassemble("0x6080604052")
    assert len(instructions) == 3
    assert instructions[0].name == "PUSH1"


def test_push32():
    # PUSH32 + 32 bytes of 0xff
    bytecode = "7f" + "ff" * 32
    instructions = disassemble(bytecode)
    assert len(instructions) == 1
    assert instructions[0].name == "PUSH32"
    assert instructions[0].operand == b"\xff" * 32
    assert instructions[0].opcode == 0x7F


def test_unknown_opcode():
    # 0x0C is not a defined opcode
    instructions = disassemble("0c")
    assert len(instructions) == 1
    assert instructions[0].name == "UNKNOWN_0C"
    assert instructions[0].operand == b""


def test_empty_input():
    assert disassemble("") == []
    assert disassemble("0x") == []


def test_truncated_push():
    # PUSH2 but only 1 byte of operand available
    bytecode = "61ff"
    instructions = disassemble(bytecode)
    assert len(instructions) == 1
    assert instructions[0].name == "PUSH2"
    assert instructions[0].operand == b"\xff"  # truncated: only 1 of 2 bytes


def test_offsets_are_correct():
    # PUSH1 0x01 (2 bytes) + PUSH2 0x0002 (3 bytes) + STOP (1 byte)
    bytecode = "600161000200"
    instructions = disassemble(bytecode)
    assert instructions[0].offset == 0  # PUSH1
    assert instructions[1].offset == 2  # PUSH2
    assert instructions[2].offset == 5  # STOP
