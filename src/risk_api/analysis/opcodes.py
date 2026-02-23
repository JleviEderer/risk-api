"""Complete EVM opcode table: int → (name, operand_size_in_bytes)."""

from __future__ import annotations

# (name, operand_size) — operand_size is only non-zero for PUSH1..PUSH32
OPCODES: dict[int, tuple[str, int]] = {
    # Stop & arithmetic
    0x00: ("STOP", 0),
    0x01: ("ADD", 0),
    0x02: ("MUL", 0),
    0x03: ("SUB", 0),
    0x04: ("DIV", 0),
    0x05: ("SDIV", 0),
    0x06: ("MOD", 0),
    0x07: ("SMOD", 0),
    0x08: ("ADDMOD", 0),
    0x09: ("MULMOD", 0),
    0x0A: ("EXP", 0),
    0x0B: ("SIGNEXTEND", 0),
    # Comparison & bitwise
    0x10: ("LT", 0),
    0x11: ("GT", 0),
    0x12: ("SLT", 0),
    0x13: ("SGT", 0),
    0x14: ("EQ", 0),
    0x15: ("ISZERO", 0),
    0x16: ("AND", 0),
    0x17: ("OR", 0),
    0x18: ("XOR", 0),
    0x19: ("NOT", 0),
    0x1A: ("BYTE", 0),
    0x1B: ("SHL", 0),
    0x1C: ("SHR", 0),
    0x1D: ("SAR", 0),
    # SHA3
    0x20: ("SHA3", 0),
    # Environmental
    0x30: ("ADDRESS", 0),
    0x31: ("BALANCE", 0),
    0x32: ("ORIGIN", 0),
    0x33: ("CALLER", 0),
    0x34: ("CALLVALUE", 0),
    0x35: ("CALLDATALOAD", 0),
    0x36: ("CALLDATASIZE", 0),
    0x37: ("CALLDATACOPY", 0),
    0x38: ("CODESIZE", 0),
    0x39: ("CODECOPY", 0),
    0x3A: ("GASPRICE", 0),
    0x3B: ("EXTCODESIZE", 0),
    0x3C: ("EXTCODECOPY", 0),
    0x3D: ("RETURNDATASIZE", 0),
    0x3E: ("RETURNDATACOPY", 0),
    0x3F: ("EXTCODEHASH", 0),
    # Block
    0x40: ("BLOCKHASH", 0),
    0x41: ("COINBASE", 0),
    0x42: ("TIMESTAMP", 0),
    0x43: ("NUMBER", 0),
    0x44: ("PREVRANDAO", 0),
    0x45: ("GASLIMIT", 0),
    0x46: ("CHAINID", 0),
    0x47: ("SELFBALANCE", 0),
    0x48: ("BASEFEE", 0),
    0x49: ("BLOBHASH", 0),
    0x4A: ("BLOBBASEFEE", 0),
    # Stack / memory / storage
    0x50: ("POP", 0),
    0x51: ("MLOAD", 0),
    0x52: ("MSTORE", 0),
    0x53: ("MSTORE8", 0),
    0x54: ("SLOAD", 0),
    0x55: ("SSTORE", 0),
    0x56: ("JUMP", 0),
    0x57: ("JUMPI", 0),
    0x58: ("PC", 0),
    0x59: ("MSIZE", 0),
    0x5A: ("GAS", 0),
    0x5B: ("JUMPDEST", 0),
    0x5C: ("TLOAD", 0),
    0x5D: ("TSTORE", 0),
    0x5E: ("MCOPY", 0),
    # PUSH0
    0x5F: ("PUSH0", 0),
    # PUSH1 through PUSH32
    **{0x60 + i: (f"PUSH{i + 1}", i + 1) for i in range(32)},
    # DUP1 through DUP16
    **{0x80 + i: (f"DUP{i + 1}", 0) for i in range(16)},
    # SWAP1 through SWAP16
    **{0x90 + i: (f"SWAP{i + 1}", 0) for i in range(16)},
    # LOG0 through LOG4
    0xA0: ("LOG0", 0),
    0xA1: ("LOG1", 0),
    0xA2: ("LOG2", 0),
    0xA3: ("LOG3", 0),
    0xA4: ("LOG4", 0),
    # System
    0xF0: ("CREATE", 0),
    0xF1: ("CALL", 0),
    0xF2: ("CALLCODE", 0),
    0xF3: ("RETURN", 0),
    0xF4: ("DELEGATECALL", 0),
    0xF5: ("CREATE2", 0),
    0xFA: ("STATICCALL", 0),
    0xFD: ("REVERT", 0),
    0xFE: ("INVALID", 0),
    0xFF: ("SELFDESTRUCT", 0),
}


def lookup(opcode: int) -> tuple[str, int]:
    """Return (name, operand_size) for an opcode, or ("UNKNOWN_XX", 0)."""
    if opcode in OPCODES:
        return OPCODES[opcode]
    return (f"UNKNOWN_{opcode:02X}", 0)
