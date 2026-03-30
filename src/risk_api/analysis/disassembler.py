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


def strip_solidity_metadata(bytecode_hex: str) -> str:
    """Strip the standard Solidity CBOR metadata trailer when present."""
    hex_str = bytecode_hex.strip()
    if hex_str.startswith(("0x", "0X")):
        hex_str = hex_str[2:]

    if not hex_str:
        return ""

    raw = bytes.fromhex(hex_str)
    stripped = _strip_solidity_metadata_bytes(raw)
    return stripped.hex()


def disassemble(bytecode_hex: str) -> list[Instruction]:
    """Disassemble EVM bytecode hex string into instructions.

    Handles 0x prefix, PUSH operand extraction, unknown opcodes,
    truncated PUSH operands at end of bytecode, and strips the
    standard Solidity metadata trailer before decoding.
    """
    hex_str = strip_solidity_metadata(bytecode_hex)

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


def _strip_solidity_metadata_bytes(raw: bytes) -> bytes:
    if len(raw) < 4:
        return raw

    metadata_len = int.from_bytes(raw[-2:], "big")
    trailer_len = metadata_len + 2
    if trailer_len >= len(raw):
        return raw

    metadata = raw[-trailer_len:-2]
    if not metadata:
        return raw

    # Solidity appends CBOR-encoded metadata that typically starts with a
    # small map and contains keys such as "ipfs", "bzzr", or "solc".
    if metadata[0] >> 5 != 5:
        return raw
    if b"ipfs" not in metadata and b"bzzr" not in metadata and b"solc" not in metadata:
        return raw

    return raw[:-trailer_len]
