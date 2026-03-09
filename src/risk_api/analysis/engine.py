"""Analysis engine: orchestrates fetch -> disassemble -> detect -> score."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from risk_api.analysis.disassembler import disassemble
from risk_api.analysis.patterns import (
    EIP_1822_SLOT,
    EIP_1967_IMPL_SLOT,
    Finding,
    OZ_IMPL_SLOT,
    Severity,
    run_all_detectors,
)
from risk_api.analysis.reputation import detect_deployer_reputation
from risk_api.analysis.scoring import RiskLevel, ScoreResult, compute_score, score_to_level
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


class NoBytecodeError(ValueError):
    """Raised when the target address has no deployed contract bytecode."""

    def __init__(self, address: str):
        super().__init__(f"No contract bytecode found at Base address: {address}")
        self.address = address


# TTL cache for analysis results: (address, rpc_url, basescan_key) -> (result, timestamp)
_analysis_cache: dict[tuple[str, str, str], tuple[AnalysisResult, float]] = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes
_CACHE_MAX_SIZE = 128


def _cache_get(
    address: str, rpc_url: str, basescan_api_key: str
) -> AnalysisResult | None:
    """Return cached result if present and not expired."""
    key = (address.lower(), rpc_url, basescan_api_key)
    entry = _analysis_cache.get(key)
    if entry is None:
        return None
    result, ts = entry
    if time.monotonic() - ts > _CACHE_TTL_SECONDS:
        del _analysis_cache[key]
        return None
    return result


def _cache_put(
    address: str, rpc_url: str, basescan_api_key: str, result: AnalysisResult
) -> None:
    """Store result in cache, evicting oldest if at capacity."""
    if len(_analysis_cache) >= _CACHE_MAX_SIZE:
        oldest_key = next(iter(_analysis_cache))
        del _analysis_cache[oldest_key]
    key = (address.lower(), rpc_url, basescan_api_key)
    _analysis_cache[key] = (result, time.monotonic())


def clear_analysis_cache() -> None:
    """Clear the analysis result cache (useful for testing)."""
    _analysis_cache.clear()


def resolve_implementation(address: str, rpc_url: str) -> str | None:
    """Try each known proxy storage slot and return the implementation address."""
    for slot_name, slot_bytes in _IMPL_SLOTS:
        slot_hex = "0x" + slot_bytes.hex()
        try:
            raw = get_storage_at(address, slot_hex, rpc_url)
        except RPCError:
            logger.debug("Failed to read %s slot for %s", slot_name, address)
            continue

        value = raw[2:] if raw.startswith("0x") else raw
        if not value or value == _ZERO_WORD or all(c == "0" for c in value):
            continue

        # Address is right-aligned in the 32-byte word.
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
    """Fetch and analyze the implementation contract behind a proxy."""
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
    is_nested_proxy = any(f.detector == "proxy" for f in findings)

    # Replace the raw proxy flag with an explicit "stopped after one hop" signal.
    findings = [f for f in findings if f.detector != "proxy"]
    if is_nested_proxy:
        findings.append(
            Finding(
                detector="proxy",
                severity=Severity.HIGH,
                title="Implementation is itself a proxy",
                description=(
                    "Resolved implementation appears to be another proxy. "
                    "Augur stops after one hop, so the terminal logic was not analyzed."
                ),
                points=20,
            )
        )

    score_result = compute_score(findings, instructions, bytecode_hex)
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

    return ImplementationResult(
        address=impl_address,
        bytecode_size=bytecode_size,
        findings=prefixed_findings,
        category_scores=score_result.category_scores,
    )


def _unresolved_proxy_finding(title: str, description: str) -> Finding:
    return Finding(
        detector="proxy",
        severity=Severity.HIGH,
        title=title,
        description=description,
        points=20,
    )


def analyze_contract(
    address: str, rpc_url: str, basescan_api_key: str = ""
) -> AnalysisResult:
    """Full analysis pipeline: fetch bytecode -> disassemble -> detect -> score."""
    cached = _cache_get(address, rpc_url, basescan_api_key)
    if cached is not None:
        return cached

    bytecode_hex = get_code(address, rpc_url)
    hex_body = bytecode_hex[2:] if bytecode_hex.startswith("0x") else bytecode_hex
    bytecode_size = len(hex_body) // 2
    if bytecode_size == 0:
        raise NoBytecodeError(address)

    instructions = disassemble(bytecode_hex)
    findings = run_all_detectors(instructions)
    findings.extend(detect_deployer_reputation(address, basescan_api_key))

    impl_result: ImplementationResult | None = None
    is_proxy = any(f.detector == "proxy" for f in findings)
    if is_proxy:
        impl_address = resolve_implementation(address, rpc_url)
        if impl_address is None:
            findings.append(
                _unresolved_proxy_finding(
                    "Proxy implementation could not be resolved",
                    (
                        "Contract appears to be a proxy, but Augur could not resolve "
                        "the implementation address from known storage slots. "
                        "The executable logic was not analyzed."
                    ),
                )
            )
        else:
            impl_result = _analyze_implementation(impl_address, rpc_url)
            if impl_result is None:
                findings.append(
                    _unresolved_proxy_finding(
                        "Proxy implementation could not be analyzed",
                        (
                            "Contract appears to be a proxy, but Augur could not fetch "
                            "bytecode for the resolved implementation address. "
                            "The executable logic was not analyzed."
                        ),
                    )
                )

    score_result: ScoreResult = compute_score(findings, instructions, bytecode_hex)
    final_score = score_result.score
    final_category_scores = dict(score_result.category_scores)

    if impl_result is not None:
        impl_total = sum(impl_result.category_scores.values())
        final_score = min(100, score_result.score + impl_total)
        for cat, points in impl_result.category_scores.items():
            final_category_scores[f"impl_{cat}"] = points

    final_level = score_to_level(final_score)
    result = AnalysisResult(
        address=address,
        score=final_score,
        level=final_level,
        findings=findings + (impl_result.findings if impl_result else []),
        category_scores=final_category_scores,
        bytecode_size=bytecode_size,
        implementation=impl_result,
    )
    _cache_put(address, rpc_url, basescan_api_key, result)
    return result
