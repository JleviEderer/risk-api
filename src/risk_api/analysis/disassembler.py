"""EVM bytecode disassembler: hex string → list of Instruction."""

from __future__ import annotations

from dataclasses import dataclass

from risk_api.analysis.opcodes import lookup


@dataclass(frozen=True, slots=True)
class Instruction:
    offset: int
    opcode: int
    name: str
    operand: bytes  # empty for non-PUSH instructions


def disassemble(bytecode_hex: str) -> list[Instruction]:
    """Disassemble EVM bytecode hex string into instructions.

    Handles 0x prefix, PUSH operand extraction, unknown opcodes,
    and truncated PUSH operands at end of bytecode.
    """
    hex_str = bytecode_hex.strip()
    if hex_str.startswith(("0x", "0X")):
        hex_str = hex_str[2:]

    if not hex_str:
        return []

    raw = bytes.fromhex(hex_str)
    instructions: list[Instruction] = []
    i = 0

    while i < len(raw):
        opcode = raw[i]
        name, operand_size = lookup(opcode)

        if operand_size > 0:
            # PUSH instruction — grab operand bytes (may be truncated)
            available = min(operand_size, len(raw) - i - 1)
            operand = raw[i + 1 : i + 1 + available]
            instructions.append(Instruction(i, opcode, name, operand))
            i += 1 + operand_size  # advance past opcode + full operand size
        else:
            instructions.append(Instruction(i, opcode, name, b""))
            i += 1

    return instructions
