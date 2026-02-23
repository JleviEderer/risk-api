"""7 pattern detectors for EVM bytecode risk analysis.

Each detector takes a list[Instruction] and returns list[Finding].
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from risk_api.analysis.disassembler import Instruction
from risk_api.analysis.selectors import (
    extract_selectors,
    find_malicious_selectors,
    find_suspicious_selectors,
)


class Severity(str, Enum):
    INFO = "info"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class Finding:
    detector: str
    severity: Severity
    title: str
    description: str
    points: int
    offset: int | None = None  # bytecode offset where pattern was found


# EIP-1967 implementation slot:
# keccak256("eip1967.proxy.implementation") - 1
EIP_1967_IMPL_SLOT = bytes.fromhex(
    "360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
)

# EIP-1967 admin slot:
# keccak256("eip1967.proxy.admin") - 1
EIP_1967_ADMIN_SLOT = bytes.fromhex(
    "b53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103"
)

# EIP-1822 (UUPS) logic slot:
# keccak256("PROXIABLE")
EIP_1822_SLOT = bytes.fromhex(
    "c5f16f0fcc639fa48a6947836d9850f504798523bf8c9a3a87d5876cf622bcf7"
)

# OpenZeppelin (pre-EIP-1967) proxy slots:
# keccak256("org.zeppelinos.proxy.implementation")
OZ_IMPL_SLOT = bytes.fromhex(
    "7050c9e0f4ca769c69bd3a8ef740bc37934f8e2c036e5a723fd8ee048ed3f8c3"
)

# keccak256("org.zeppelinos.proxy.admin")
OZ_ADMIN_SLOT = bytes.fromhex(
    "10d6a54a4754c8869d6886b5f5d7fbfa5b4522237ea5c60d11bc4e7a1ff9390b"
)

PROXY_SLOTS = {
    EIP_1967_IMPL_SLOT,
    EIP_1967_ADMIN_SLOT,
    EIP_1822_SLOT,
    OZ_IMPL_SLOT,
    OZ_ADMIN_SLOT,
}


def detect_selfdestruct(instructions: list[Instruction]) -> list[Finding]:
    """Detect SELFDESTRUCT opcode (0xFF). Critical — can destroy contract."""
    findings: list[Finding] = []
    for instr in instructions:
        if instr.opcode == 0xFF:
            findings.append(
                Finding(
                    detector="selfdestruct",
                    severity=Severity.CRITICAL,
                    title="SELFDESTRUCT opcode found",
                    description=(
                        "Contract contains SELFDESTRUCT which allows the owner "
                        "to destroy the contract and drain all funds."
                    ),
                    points=30,
                    offset=instr.offset,
                )
            )
            break  # one finding is enough
    return findings


def detect_delegatecall(instructions: list[Instruction]) -> list[Finding]:
    """Detect DELEGATECALL (0xF4). Downgrade severity if proxy context detected."""
    findings: list[Finding] = []
    has_delegatecall = False
    is_proxy = _has_proxy_slots(instructions)

    for instr in instructions:
        if instr.opcode == 0xF4 and not has_delegatecall:
            has_delegatecall = True
            if is_proxy:
                findings.append(
                    Finding(
                        detector="delegatecall",
                        severity=Severity.INFO,
                        title="DELEGATECALL in proxy pattern",
                        description=(
                            "Contract uses DELEGATECALL with standard proxy storage "
                            "slots (EIP-1967/1822). This is expected proxy behavior."
                        ),
                        points=10,
                        offset=instr.offset,
                    )
                )
            else:
                findings.append(
                    Finding(
                        detector="delegatecall",
                        severity=Severity.HIGH,
                        title="Raw DELEGATECALL without proxy pattern",
                        description=(
                            "Contract uses DELEGATECALL without recognized proxy "
                            "storage slots. This could allow arbitrary code execution."
                        ),
                        points=15,
                        offset=instr.offset,
                    )
                )
    return findings


def detect_reentrancy_risk(instructions: list[Instruction]) -> list[Finding]:
    """Detect CALL followed by SSTORE — potential reentrancy vulnerability."""
    findings: list[Finding] = []
    for i, instr in enumerate(instructions):
        if instr.opcode == 0xF1:  # CALL
            # Look ahead for SSTORE within next 20 instructions
            for j in range(i + 1, min(i + 21, len(instructions))):
                if instructions[j].opcode == 0x55:  # SSTORE
                    findings.append(
                        Finding(
                            detector="reentrancy",
                            severity=Severity.MEDIUM,
                            title="Potential reentrancy: CALL before SSTORE",
                            description=(
                                "External CALL at offset {} is followed by SSTORE "
                                "at offset {}. State changes after external calls "
                                "can enable reentrancy attacks."
                            ).format(instr.offset, instructions[j].offset),
                            points=10,
                            offset=instr.offset,
                        )
                    )
                    return findings  # one finding is enough
    return findings


def detect_proxy_patterns(instructions: list[Instruction]) -> list[Finding]:
    """Detect EIP-1967/1822 proxy storage slots in PUSH32 instructions."""
    findings: list[Finding] = []
    if _has_proxy_slots(instructions):
        findings.append(
            Finding(
                detector="proxy",
                severity=Severity.INFO,
                title="Proxy contract detected",
                description=(
                    "Contract uses standard proxy storage slots (EIP-1967 or "
                    "EIP-1822). The implementation contract should also be analyzed."
                ),
                points=10,
            )
        )
    return findings


def detect_honeypot_patterns(instructions: list[Instruction]) -> list[Finding]:
    """Detect conditional REVERT patterns that could trap tokens.

    Looks for: comparison (EQ/LT/GT) → JUMPI → REVERT pattern near
    transfer-related selectors, which suggests conditional blocking.
    """
    findings: list[Finding] = []
    selectors = extract_selectors(instructions)

    # Check if transfer-related selectors exist (keys from ERC20_SELECTORS)
    transfer_sels = {bytes.fromhex("a9059cbb"), bytes.fromhex("23b872dd")}
    has_transfer = bool(selectors & transfer_sels)
    if not has_transfer:
        return findings

    # Look for conditional revert patterns
    comparison_ops = {0x10, 0x11, 0x12, 0x13, 0x14}  # LT, GT, SLT, SGT, EQ
    for i, instr in enumerate(instructions):
        if instr.opcode in comparison_ops and i + 2 < len(instructions):
            # Check if comparison leads to JUMPI → ... → REVERT
            if instructions[i + 1].opcode == 0x57:  # JUMPI
                # Look for REVERT in the fallthrough path (next few instructions)
                for j in range(i + 2, min(i + 6, len(instructions))):
                    if instructions[j].opcode == 0xFD:  # REVERT
                        findings.append(
                            Finding(
                                detector="honeypot",
                                severity=Severity.HIGH,
                                title="Potential honeypot: conditional REVERT in transfer path",
                                description=(
                                    "Contract has transfer functions with conditional "
                                    "REVERT patterns that could selectively block "
                                    "token transfers for certain addresses."
                                ),
                                points=25,
                                offset=instr.offset,
                            )
                        )
                        return findings
    return findings


def detect_hidden_mint(instructions: list[Instruction]) -> list[Finding]:
    """Detect presence of mint-related malicious selectors."""
    findings: list[Finding] = []
    selectors = extract_selectors(instructions)
    malicious = find_malicious_selectors(selectors)

    mint_selectors = {
        k: v for k, v in malicious.items() if "mint" in v.lower()
    }

    if mint_selectors:
        sigs = ", ".join(mint_selectors.values())
        findings.append(
            Finding(
                detector="hidden_mint",
                severity=Severity.CRITICAL,
                title="Hidden mint capability detected",
                description=(
                    f"Contract contains mint function selectors ({sigs}) "
                    "that could allow unlimited token minting."
                ),
                points=25,
            )
        )
    return findings


def detect_fee_manipulation(instructions: list[Instruction]) -> list[Finding]:
    """Detect fee/tax manipulation selectors."""
    findings: list[Finding] = []
    selectors = extract_selectors(instructions)
    malicious = find_malicious_selectors(selectors)

    fee_selectors = {
        k: v
        for k, v in malicious.items()
        if any(term in v.lower() for term in ("fee", "tax", "maxtx", "maxwallet"))
    }

    if fee_selectors:
        sigs = ", ".join(fee_selectors.values())
        findings.append(
            Finding(
                detector="fee_manipulation",
                severity=Severity.HIGH,
                title="Fee/limit manipulation functions detected",
                description=(
                    f"Contract contains functions ({sigs}) that allow the owner "
                    "to change fees, taxes, or transaction limits."
                ),
                points=15,
            )
        )
    return findings


def run_all_detectors(instructions: list[Instruction]) -> list[Finding]:
    """Run all 7 pattern detectors and return combined findings."""
    findings: list[Finding] = []
    for detector in [
        detect_selfdestruct,
        detect_delegatecall,
        detect_reentrancy_risk,
        detect_proxy_patterns,
        detect_honeypot_patterns,
        detect_hidden_mint,
        detect_fee_manipulation,
    ]:
        findings.extend(detector(instructions))
    return findings


def _has_proxy_slots(instructions: list[Instruction]) -> bool:
    """Check if any PUSH32 operand matches known proxy storage slots."""
    for instr in instructions:
        if instr.name == "PUSH32" and instr.operand in PROXY_SLOTS:
            return True
    return False
