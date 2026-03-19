import pytest
import responses

from risk_api.analysis.engine import (
    ImplementationResult,
    NoBytecodeError,
    analyze_contract,
    clear_analysis_cache,
    resolve_implementation,
)
from risk_api.analysis.patterns import EIP_1822_SLOT, EIP_1967_IMPL_SLOT
from risk_api.analysis.policy import PolicyAction, PolicyReasonCode, ProxyResolutionStatus
from risk_api.analysis.reputation import BLOCKSCOUT_API, clear_reputation_cache
from risk_api.analysis.scoring import RiskLevel
from risk_api.chain.rpc import RPCError, clear_cache


RPC_URL = "https://mainnet.base.org"

# EIP-1967 implementation slot hex (for PUSH32 in bytecode)
EIP1967_HEX = "360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"

# A fake implementation address
IMPL_ADDR = "aa" * 20
IMPL_ADDR_PADDED = "0x" + "0" * 24 + IMPL_ADDR


def _rpc_response(result: str) -> dict[str, object]:
    return {"jsonrpc": "2.0", "id": 1, "result": result}


def _proxy_bytecode() -> str:
    """Minimal proxy bytecode: PUSH32 <EIP-1967 slot> + DELEGATECALL + padding."""
    return "0x7f" + EIP1967_HEX + "f4" + "00" * 200


def _clean_impl_bytecode() -> str:
    """Clean implementation bytecode: >200 bytes, no risky patterns."""
    return "0x" + "6080604052" + "00" * 200


def _risky_impl_bytecode() -> str:
    """Implementation with SELFDESTRUCT."""
    return "0x" + "ff" + "00" * 200


def _suspicious_impl_bytecode() -> str:
    """Implementation with a suspicious selector and no other findings."""
    return "0x63a22cb465" + "00" * 200


def _tiny_impl_bytecode() -> str:
    """Tiny non-proxy implementation bytecode."""
    return "0x6000"


@pytest.fixture(autouse=True)
def _clear_caches():
    clear_cache()
    clear_analysis_cache()
    clear_reputation_cache()
    yield
    clear_cache()
    clear_analysis_cache()
    clear_reputation_cache()


# --- Existing tests (updated for storage slot mocks) ---


@responses.activate
def test_analyze_clean_contract():
    bytecode = "0x" + "6080604052" + "00" * 200
    responses.post(RPC_URL, json=_rpc_response(bytecode))
    result = analyze_contract("0x" + "ab" * 20, RPC_URL)
    assert result.score == 0
    assert result.level == RiskLevel.SAFE
    assert result.decision == PolicyAction.ALLOW
    assert result.recommended_policy.reason_codes == []
    assert result.findings == []
    assert result.bytecode_size > 200
    assert result.implementation is None


@responses.activate
def test_analyze_contract_with_selfdestruct():
    bytecode = "0x" + "ff" + "00" * 200
    responses.post(RPC_URL, json=_rpc_response(bytecode))
    result = analyze_contract("0x" + "cd" * 20, RPC_URL)
    assert result.score >= 30
    assert result.decision == PolicyAction.MANUAL_REVIEW
    assert PolicyReasonCode.SELFDESTRUCT_SIGNAL.value in result.recommended_policy.reason_codes
    assert any(f.detector == "selfdestruct" for f in result.findings)


@responses.activate
def test_analyze_raw_delegatecall_requires_manual_review_even_when_score_is_safe():
    bytecode = "0x" + "f4" + "00" * 200
    responses.post(RPC_URL, json=_rpc_response(bytecode))

    result = analyze_contract("0x" + "de" * 20, RPC_URL)

    assert result.score == 15
    assert result.level == RiskLevel.SAFE
    assert result.decision == PolicyAction.MANUAL_REVIEW
    assert PolicyReasonCode.RAW_DELEGATECALL_SURFACE.value in result.recommended_policy.reason_codes


@responses.activate
def test_analyze_hidden_mint_blocks_even_when_level_is_low():
    bytecode = "0x63a0712d68" + "00" * 200
    responses.post(RPC_URL, json=_rpc_response(bytecode))

    result = analyze_contract("0x" + "ba" * 20, RPC_URL)

    assert result.score == 25
    assert result.level == RiskLevel.LOW
    assert result.decision == PolicyAction.BLOCK
    assert PolicyReasonCode.HIDDEN_MINT_SIGNAL.value in result.recommended_policy.reason_codes


@responses.activate
def test_analyze_honeypot_blacklist_blocks_even_when_level_is_low():
    bytecode = "0x63a9059cbb6344337ea1" + "00" * 200
    responses.post(RPC_URL, json=_rpc_response(bytecode))

    result = analyze_contract("0x" + "ac" * 20, RPC_URL)

    assert result.score == 25
    assert result.level == RiskLevel.LOW
    assert result.decision == PolicyAction.BLOCK
    assert PolicyReasonCode.HONEYPOT_SIGNAL.value in result.recommended_policy.reason_codes


@responses.activate
def test_analyze_fee_manipulation_warns_even_when_score_is_safe():
    bytecode = "0x6369fe0e2d" + "00" * 200
    responses.post(RPC_URL, json=_rpc_response(bytecode))

    result = analyze_contract("0x" + "f1" * 20, RPC_URL)

    assert result.score == 15
    assert result.level == RiskLevel.SAFE
    assert result.decision == PolicyAction.WARN
    assert PolicyReasonCode.FEE_MANIPULATION_SIGNAL.value in result.recommended_policy.reason_codes


@responses.activate
def test_analyze_limit_alias_warns_without_suspicious_double_count():
    bytecode = (
        "0x63f34eb0b8"
        "635c85974f"
        "6374010ece"
        "63e99c9d09"
        "63f1d5f517"
        "6327a14fc2"
        "63d8b60040"
        "638bf55409"
        + "00" * 200
    )
    responses.post(RPC_URL, json=_rpc_response(bytecode))

    result = analyze_contract("0x" + "f4" * 20, RPC_URL)

    assert result.score == 15
    assert result.level == RiskLevel.SAFE
    assert result.decision == PolicyAction.WARN
    assert result.category_scores["fee_manipulation"] == 15
    assert "suspicious_selector" not in result.category_scores
    assert PolicyReasonCode.FEE_MANIPULATION_SIGNAL.value in result.recommended_policy.reason_codes


@responses.activate
def test_analyze_pause_selector_warns_even_when_score_is_safe():
    bytecode = "0x638456cb59" + "00" * 200
    responses.post(RPC_URL, json=_rpc_response(bytecode))

    result = analyze_contract("0x" + "f2" * 20, RPC_URL)

    assert result.score == 5
    assert result.level == RiskLevel.SAFE
    assert result.decision == PolicyAction.WARN
    assert PolicyReasonCode.SUSPICIOUS_SELECTOR_SIGNAL.value in result.recommended_policy.reason_codes


@responses.activate
def test_analyze_blacklist_selector_without_transfer_warns():
    bytecode = "0x6344337ea1" + "00" * 200
    responses.post(RPC_URL, json=_rpc_response(bytecode))

    result = analyze_contract("0x" + "f3" * 20, RPC_URL)

    assert result.score == 5
    assert result.level == RiskLevel.SAFE
    assert result.decision == PolicyAction.WARN
    assert result.findings == []
    assert PolicyReasonCode.SUSPICIOUS_SELECTOR_SIGNAL.value in result.recommended_policy.reason_codes


@responses.activate
def test_analyze_eoa():
    responses.post(RPC_URL, json=_rpc_response("0x"))
    with pytest.raises(NoBytecodeError, match="No contract bytecode found"):
        analyze_contract("0x" + "11" * 20, RPC_URL)


@responses.activate
def test_analyze_proxy_contract():
    """Proxy detected, but storage slots return zero — no impl resolution."""
    proxy_addr = "0x" + "22" * 20
    # First call: get_code for proxy
    responses.post(RPC_URL, json=_rpc_response(_proxy_bytecode()))
    # Storage slot reads all return zero (no implementation found)
    zero_slot = "0x" + "0" * 64
    responses.post(RPC_URL, json=_rpc_response(zero_slot))
    responses.post(RPC_URL, json=_rpc_response(zero_slot))
    responses.post(RPC_URL, json=_rpc_response(zero_slot))

    result = analyze_contract(proxy_addr, RPC_URL)
    assert any(f.detector == "proxy" for f in result.findings)
    assert any(f.detector == "delegatecall" for f in result.findings)
    dc_finding = next(f for f in result.findings if f.detector == "delegatecall")
    assert dc_finding.severity.value == "info"
    assert result.implementation is None
    assert result.score == 40
    assert result.level == RiskLevel.MEDIUM
    assert result.decision == PolicyAction.MANUAL_REVIEW
    assert result.proxy_resolution_status == ProxyResolutionStatus.UNRESOLVED
    assert PolicyReasonCode.PROXY_LOGIC_UNRESOLVED.value in result.recommended_policy.reason_codes
    assert any(
        f.title == "Proxy implementation could not be resolved"
        for f in result.findings
    )


@responses.activate
def test_analyze_rpc_failure():
    responses.post(RPC_URL, body=ConnectionError("network down"))
    with pytest.raises(RPCError):
        analyze_contract("0x" + "33" * 20, RPC_URL)


# --- resolve_implementation tests ---


@responses.activate
def test_resolve_implementation_eip1967():
    """EIP-1967 slot returns valid address."""
    addr = "0x" + "aa" * 20
    responses.post(RPC_URL, json=_rpc_response(IMPL_ADDR_PADDED))

    result = resolve_implementation(addr, RPC_URL)
    assert result == "0x" + IMPL_ADDR


@responses.activate
def test_resolve_implementation_fallthrough_to_eip1822():
    """EIP-1967 empty, EIP-1822 returns valid address."""
    addr = "0x" + "bb" * 20
    zero = "0x" + "0" * 64
    # EIP-1967 returns zero
    responses.post(RPC_URL, json=_rpc_response(zero))
    # EIP-1822 returns valid address
    responses.post(RPC_URL, json=_rpc_response(IMPL_ADDR_PADDED))

    result = resolve_implementation(addr, RPC_URL)
    assert result == "0x" + IMPL_ADDR


@responses.activate
def test_resolve_implementation_all_empty():
    """All slots return zero — no implementation found."""
    addr = "0x" + "cc" * 20
    zero = "0x" + "0" * 64
    responses.post(RPC_URL, json=_rpc_response(zero))
    responses.post(RPC_URL, json=_rpc_response(zero))
    responses.post(RPC_URL, json=_rpc_response(zero))

    result = resolve_implementation(addr, RPC_URL)
    assert result is None


@responses.activate
def test_resolve_implementation_rpc_failure_graceful():
    """RPC failure on all slots returns None gracefully."""
    addr = "0x" + "dd" * 20
    responses.post(RPC_URL, body=ConnectionError("timeout"))
    responses.post(RPC_URL, body=ConnectionError("timeout"))
    responses.post(RPC_URL, body=ConnectionError("timeout"))

    result = resolve_implementation(addr, RPC_URL)
    assert result is None


# --- Full proxy + implementation analysis tests ---


@responses.activate
def test_analyze_proxy_resolves_implementation():
    """Proxy with risky implementation — score includes impl findings."""
    proxy_addr = "0x" + "ee" * 20
    # get_code for proxy
    responses.post(RPC_URL, json=_rpc_response(_proxy_bytecode()))
    # EIP-1967 storage slot returns impl address
    responses.post(RPC_URL, json=_rpc_response(IMPL_ADDR_PADDED))
    # get_code for implementation (SELFDESTRUCT)
    responses.post(RPC_URL, json=_rpc_response(_risky_impl_bytecode()))

    result = analyze_contract(proxy_addr, RPC_URL)

    assert result.implementation is not None
    assert result.implementation.address == "0x" + IMPL_ADDR
    # Proxy base score is 20 (proxy=10 + delegatecall=10)
    # Implementation adds selfdestruct=30
    assert result.score >= 50
    assert "impl_selfdestruct" in result.category_scores
    assert result.decision == PolicyAction.MANUAL_REVIEW
    assert result.proxy_resolution_status == ProxyResolutionStatus.RESOLVED
    assert any(f.detector == "impl_selfdestruct" for f in result.findings)


@responses.activate
def test_analyze_proxy_clean_implementation():
    """Proxy with clean implementation — low score."""
    proxy_addr = "0x" + "ff" * 20
    # get_code for proxy
    responses.post(RPC_URL, json=_rpc_response(_proxy_bytecode()))
    # EIP-1967 storage slot returns impl address
    responses.post(RPC_URL, json=_rpc_response(IMPL_ADDR_PADDED))
    # get_code for implementation (clean)
    responses.post(RPC_URL, json=_rpc_response(_clean_impl_bytecode()))

    result = analyze_contract(proxy_addr, RPC_URL)

    assert result.implementation is not None
    assert result.implementation.findings == []
    # Score is just proxy + delegatecall = 20
    assert result.score == 20
    assert result.level == RiskLevel.LOW
    assert result.decision == PolicyAction.WARN


@responses.activate
def test_analyze_proxy_impl_includes_suspicious_selector_score():
    """Implementation scoring reuses top-level heuristics like suspicious selectors."""
    proxy_addr = "0x" + "12" * 20
    responses.post(RPC_URL, json=_rpc_response(_proxy_bytecode()))
    responses.post(RPC_URL, json=_rpc_response(IMPL_ADDR_PADDED))
    responses.post(RPC_URL, json=_rpc_response(_suspicious_impl_bytecode()))

    result = analyze_contract(proxy_addr, RPC_URL)

    assert result.implementation is not None
    assert result.implementation.category_scores["suspicious_selector"] == 5
    assert result.category_scores["impl_suspicious_selector"] == 5
    assert result.score == 25
    assert result.level == RiskLevel.LOW
    assert result.decision == PolicyAction.WARN


@responses.activate
def test_analyze_proxy_impl_includes_tiny_bytecode_score():
    """Implementation scoring reuses top-level heuristics like tiny bytecode."""
    proxy_addr = "0x" + "13" * 20
    responses.post(RPC_URL, json=_rpc_response(_proxy_bytecode()))
    responses.post(RPC_URL, json=_rpc_response(IMPL_ADDR_PADDED))
    responses.post(RPC_URL, json=_rpc_response(_tiny_impl_bytecode()))

    result = analyze_contract(proxy_addr, RPC_URL)

    assert result.implementation is not None
    assert result.implementation.category_scores["tiny_bytecode"] == 10
    assert result.category_scores["impl_tiny_bytecode"] == 10
    assert result.score == 30
    assert result.level == RiskLevel.LOW
    assert result.decision == PolicyAction.WARN


@responses.activate
def test_analyze_proxy_storage_rpc_failure():
    """Storage read fails — gracefully returns proxy-only findings."""
    proxy_addr = "0x" + "a1" * 20
    # get_code for proxy
    responses.post(RPC_URL, json=_rpc_response(_proxy_bytecode()))
    # All storage reads fail
    responses.post(RPC_URL, body=ConnectionError("timeout"))
    responses.post(RPC_URL, body=ConnectionError("timeout"))
    responses.post(RPC_URL, body=ConnectionError("timeout"))

    result = analyze_contract(proxy_addr, RPC_URL)

    assert result.implementation is None
    assert any(f.detector == "proxy" for f in result.findings)
    assert result.score == 40
    assert result.level == RiskLevel.MEDIUM
    assert result.proxy_resolution_status == ProxyResolutionStatus.UNRESOLVED
    assert any(
        f.title == "Proxy implementation could not be resolved"
        for f in result.findings
    )


@responses.activate
def test_analyze_proxy_implementation_is_also_proxy():
    """Implementation is itself a proxy — no recursion, just 1 hop."""
    proxy_addr = "0x" + "b2" * 20
    # get_code for proxy
    responses.post(RPC_URL, json=_rpc_response(_proxy_bytecode()))
    # EIP-1967 storage slot returns impl address
    responses.post(RPC_URL, json=_rpc_response(IMPL_ADDR_PADDED))
    # get_code for implementation — also a proxy
    responses.post(RPC_URL, json=_rpc_response(_proxy_bytecode()))

    result = analyze_contract(proxy_addr, RPC_URL)

    assert result.implementation is not None
    assert any(f.detector == "impl_proxy" for f in result.findings)
    assert any(f.detector == "impl_delegatecall" for f in result.findings)
    assert result.score == 50
    assert result.level == RiskLevel.MEDIUM
    assert result.proxy_resolution_status == ProxyResolutionStatus.NESTED_PROXY
    assert PolicyReasonCode.PROXY_LOGIC_UNRESOLVED.value in result.recommended_policy.reason_codes
    assert PolicyReasonCode.PROXY_LOGIC_NESTED_PROXY.value in result.recommended_policy.reason_codes


@responses.activate
def test_analyze_proxy_impl_bytecode_fetch_fails():
    """Implementation address resolved but bytecode fetch fails — graceful."""
    proxy_addr = "0x" + "c3" * 20
    # get_code for proxy
    responses.post(RPC_URL, json=_rpc_response(_proxy_bytecode()))
    # EIP-1967 storage slot returns impl address
    responses.post(RPC_URL, json=_rpc_response(IMPL_ADDR_PADDED))
    # get_code for implementation fails
    responses.post(RPC_URL, body=ConnectionError("timeout"))

    result = analyze_contract(proxy_addr, RPC_URL)

    assert result.implementation is None
    assert result.score == 40
    assert result.level == RiskLevel.MEDIUM
    assert result.proxy_resolution_status == ProxyResolutionStatus.FETCH_FAILED
    assert PolicyReasonCode.PROXY_LOGIC_FETCH_FAILED.value in result.recommended_policy.reason_codes
    assert any(
        f.title == "Proxy implementation could not be analyzed"
        for f in result.findings
    )


@responses.activate
def test_analyze_proxy_impl_address_has_no_code():
    """Implementation address resolved but eth_getCode returns 0x."""
    proxy_addr = "0x" + "c4" * 20
    responses.post(RPC_URL, json=_rpc_response(_proxy_bytecode()))
    responses.post(RPC_URL, json=_rpc_response(IMPL_ADDR_PADDED))
    responses.post(RPC_URL, json=_rpc_response("0x"))

    result = analyze_contract(proxy_addr, RPC_URL)

    assert result.implementation is None
    assert result.score == 40
    assert result.level == RiskLevel.MEDIUM
    assert result.proxy_resolution_status == ProxyResolutionStatus.NO_CODE
    assert PolicyReasonCode.PROXY_LOGIC_NO_CODE.value in result.recommended_policy.reason_codes
    assert any(
        f.title == "Proxy implementation has no bytecode"
        for f in result.findings
    )


# --- Analysis cache tests ---


@responses.activate
def test_cache_returns_same_result():
    """Second call returns cached result without extra RPC calls."""
    bytecode = "0x" + "6080604052" + "00" * 200
    # Only register ONE RPC response and ONE explorer response - second call must use cache.
    responses.post(RPC_URL, json=_rpc_response(bytecode))
    responses.get(
        BLOCKSCOUT_API,
        json={"status": "0", "message": "No data found", "result": []},
    )

    addr = "0x" + "d4" * 20
    result1 = analyze_contract(addr, RPC_URL)
    result2 = analyze_contract(addr, RPC_URL)

    assert result1 is result2
    assert len(responses.calls) == 2  # 1 RPC call + 1 explorer call, not repeated


@responses.activate
def test_cache_is_case_insensitive():
    """Cache key normalizes address to lowercase."""
    bytecode = "0x" + "6080604052" + "00" * 200
    responses.post(RPC_URL, json=_rpc_response(bytecode))
    responses.get(
        BLOCKSCOUT_API,
        json={"status": "0", "message": "No data found", "result": []},
    )

    addr_lower = "0x" + "ab" * 20
    addr_upper = "0x" + "AB" * 20
    result1 = analyze_contract(addr_lower, RPC_URL)
    result2 = analyze_contract(addr_upper, RPC_URL)

    assert result1 is result2
    assert len(responses.calls) == 2


def test_clear_analysis_cache_works():
    """clear_analysis_cache() empties the cache."""
    from risk_api.analysis.engine import _analysis_cache

    _analysis_cache[("test", "url", "")] = (None, 0)  # type: ignore[assignment]
    assert len(_analysis_cache) == 1
    clear_analysis_cache()
    assert len(_analysis_cache) == 0
