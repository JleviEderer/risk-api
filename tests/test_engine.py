import pytest
import responses

from risk_api.analysis.engine import (
    ImplementationResult,
    analyze_contract,
    clear_analysis_cache,
    resolve_implementation,
)
from risk_api.analysis.patterns import EIP_1822_SLOT, EIP_1967_IMPL_SLOT
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


@pytest.fixture(autouse=True)
def _clear_caches():
    clear_cache()
    clear_analysis_cache()
    yield
    clear_cache()
    clear_analysis_cache()


# --- Existing tests (updated for storage slot mocks) ---


@responses.activate
def test_analyze_clean_contract():
    bytecode = "0x" + "6080604052" + "00" * 200
    responses.post(RPC_URL, json=_rpc_response(bytecode))
    result = analyze_contract("0x" + "ab" * 20, RPC_URL)
    assert result.score == 0
    assert result.level == RiskLevel.SAFE
    assert result.findings == []
    assert result.bytecode_size > 200
    assert result.implementation is None


@responses.activate
def test_analyze_contract_with_selfdestruct():
    bytecode = "0x" + "ff" + "00" * 200
    responses.post(RPC_URL, json=_rpc_response(bytecode))
    result = analyze_contract("0x" + "cd" * 20, RPC_URL)
    assert result.score >= 30
    assert any(f.detector == "selfdestruct" for f in result.findings)


@responses.activate
def test_analyze_eoa():
    responses.post(RPC_URL, json=_rpc_response("0x"))
    result = analyze_contract("0x" + "11" * 20, RPC_URL)
    assert result.bytecode_size == 0
    assert result.score == 0
    assert result.level == RiskLevel.SAFE


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
    assert result.score == 20  # proxy(10) + delegatecall(10)


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
    # Impl proxy findings are filtered out (no double-counting)
    assert not any(f.detector == "impl_proxy" for f in result.findings)
    # But impl delegatecall is still reported
    assert any(f.detector == "impl_delegatecall" for f in result.findings)


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
    assert result.score == 20  # proxy(10) + delegatecall(10)


# --- Analysis cache tests ---


@responses.activate
def test_cache_returns_same_result():
    """Second call returns cached result without extra RPC calls."""
    bytecode = "0x" + "6080604052" + "00" * 200
    # Only register ONE RPC response — second call must use cache
    responses.post(RPC_URL, json=_rpc_response(bytecode))

    addr = "0x" + "d4" * 20
    result1 = analyze_contract(addr, RPC_URL)
    result2 = analyze_contract(addr, RPC_URL)

    assert result1 is result2
    assert len(responses.calls) == 1  # Only 1 RPC call, not 2


@responses.activate
def test_cache_is_case_insensitive():
    """Cache key normalizes address to lowercase."""
    bytecode = "0x" + "6080604052" + "00" * 200
    responses.post(RPC_URL, json=_rpc_response(bytecode))

    addr_lower = "0x" + "ab" * 20
    addr_upper = "0x" + "AB" * 20
    result1 = analyze_contract(addr_lower, RPC_URL)
    result2 = analyze_contract(addr_upper, RPC_URL)

    assert result1 is result2
    assert len(responses.calls) == 1


def test_clear_analysis_cache_works():
    """clear_analysis_cache() empties the cache."""
    from risk_api.analysis.engine import _analysis_cache

    _analysis_cache[("test", "url", "")] = (None, 0)  # type: ignore[assignment]
    assert len(_analysis_cache) == 1
    clear_analysis_cache()
    assert len(_analysis_cache) == 0
