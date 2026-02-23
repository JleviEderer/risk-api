"""Analysis engine: orchestrates fetch → disassemble → detect → score."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from risk_api.analysis.disassembler import disassemble
from risk_api.analysis.patterns import (
    EIP_1822_SLOT,
    EIP_1967_IMPL_SLOT,
    Finding,
    OZ_IMPL_SLOT,
    run_all_detectors,
)
from risk_api.analysis.reputation import detect_deployer_reputation
from risk_api.analysis.scoring import (
    CATEGORY_CAPS,
    RiskLevel,
    ScoreResult,
    compute_score,
    score_to_level,
)
from risk_api.chain.rpc import RPCError, get_code, get_storage_at

logger = logging.getLogger(__name__)

# Ordered by popularity: EIP-1967 first (vast majority), then EIP-1822, then OZ
_IMPL_SLOTS: list[tuple[str, bytes]] = [
    ("EIP-1967", EIP_1967_IMPL_SLOT),
    ("EIP-1822", EIP_1822_SLOT),
    ("OpenZeppelin", OZ_IMPL_SLOT),
]

_ZERO_WORD = "0" * 64


@dataclass(frozen=True, slots=True)
class ImplementationResult:
    address: str
    bytecode_size: int
    findings: list[Finding]
    category_scores: dict[str, int]


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    address: str
    score: int
    level: RiskLevel
    findings: list[Finding]
    category_scores: dict[str, int]
    bytecode_size: int
    implementation: ImplementationResult | None = None


def resolve_implementation(address: str, rpc_url: str) -> str | None:
    """Try each known proxy storage slot and return the implementation address.

    Returns checksummed-ish hex address (0x-prefixed, 40 chars) or None.
    Graceful: returns None on any RPC failure.
    """
    for slot_name, slot_bytes in _IMPL_SLOTS:
        slot_hex = "0x" + slot_bytes.hex()
        try:
            raw = get_storage_at(address, slot_hex, rpc_url)
        except RPCError:
            logger.debug("Failed to read %s slot for %s", slot_name, address)
            continue

        # Strip 0x prefix and check for zero
        value = raw[2:] if raw.startswith("0x") else raw
        if not value or value == _ZERO_WORD or all(c == "0" for c in value):
            continue

        # Address is right-aligned in the 32-byte word (last 20 bytes = last 40 hex chars)
        addr_hex = value[-40:]
        if all(c == "0" for c in addr_hex):
            continue

        impl_address = "0x" + addr_hex
        logger.debug(
            "Resolved %s implementation for %s: %s",
            slot_name,
            address,
            impl_address,
        )
        return impl_address

    return None


def _analyze_implementation(
    impl_address: str, rpc_url: str
) -> ImplementationResult | None:
    """Fetch and analyze the implementation contract behind a proxy.

    Returns None if bytecode fetch fails. Filters out proxy findings
    to avoid double-counting with the proxy contract itself.
    """
    try:
        bytecode_hex = get_code(impl_address, rpc_url)
    except RPCError:
        logger.debug("Failed to fetch implementation bytecode for %s", impl_address)
        return None

    hex_body = bytecode_hex[2:] if bytecode_hex.startswith("0x") else bytecode_hex
    bytecode_size = len(hex_body) // 2

    if bytecode_size == 0:
        return None

    instructions = disassemble(bytecode_hex)
    findings = run_all_detectors(instructions)

    # Filter out proxy findings — the proxy itself already reported that
    findings = [f for f in findings if f.detector != "proxy"]

    # Prefix detector names with impl_ for clarity in combined output
    prefixed_findings = [
        Finding(
            detector=f"impl_{f.detector}",
            severity=f.severity,
            title=f.title,
            description=f.description,
            points=f.points,
            offset=f.offset,
        )
        for f in findings
    ]

    # Score the implementation findings using standard category caps
    category_points: dict[str, int] = {}
    for finding in findings:
        cat = finding.detector
        current = category_points.get(cat, 0)
        cap = CATEGORY_CAPS.get(cat, 100)
        category_points[cat] = min(cap, current + finding.points)

    return ImplementationResult(
        address=impl_address,
        bytecode_size=bytecode_size,
        findings=prefixed_findings,
        category_scores=category_points,
    )


def analyze_contract(
    address: str, rpc_url: str, basescan_api_key: str = ""
) -> AnalysisResult:
    """Full analysis pipeline: fetch bytecode → disassemble → detect → score.

    For proxy contracts, also resolves and analyzes the implementation (max 1 hop).
    Raises RPCError if bytecode fetch fails.
    """
    bytecode_hex = get_code(address, rpc_url)

    # Strip 0x prefix for size calculation
    hex_body = bytecode_hex[2:] if bytecode_hex.startswith("0x") else bytecode_hex
    bytecode_size = len(hex_body) // 2

    instructions = disassemble(bytecode_hex)
    findings = run_all_detectors(instructions)
    findings.extend(detect_deployer_reputation(address, basescan_api_key))
    score_result: ScoreResult = compute_score(findings, instructions, bytecode_hex)

    # Check if this is a proxy and resolve implementation
    impl_result: ImplementationResult | None = None
    is_proxy = any(f.detector == "proxy" for f in findings)

    if is_proxy:
        impl_address = resolve_implementation(address, rpc_url)
        if impl_address is not None:
            impl_result = _analyze_implementation(impl_address, rpc_url)

    # Combine scores if implementation was analyzed
    final_score = score_result.score
    final_category_scores = dict(score_result.category_scores)

    if impl_result is not None:
        # Add implementation category scores to the proxy's scores
        impl_total = sum(impl_result.category_scores.values())
        final_score = min(100, score_result.score + impl_total)
        for cat, points in impl_result.category_scores.items():
            prefixed = f"impl_{cat}"
            final_category_scores[prefixed] = points

    final_level = score_to_level(final_score)

    return AnalysisResult(
        address=address,
        score=final_score,
        level=final_level,
        findings=findings + (impl_result.findings if impl_result else []),
        category_scores=final_category_scores,
        bytecode_size=bytecode_size,
        implementation=impl_result,
    )
