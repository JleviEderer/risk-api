import pytest
import responses

from risk_api.chain.rpc import RPCError, clear_cache, get_code, get_storage_at


@pytest.fixture(autouse=True)
def _clear_rpc_cache():
    """Clear LRU cache before each test."""
    clear_cache()
    yield
    clear_cache()


@responses.activate
def test_get_code_success():
    rpc_url = "https://mainnet.base.org"
    responses.post(
        rpc_url,
        json={"jsonrpc": "2.0", "id": 1, "result": "0x6080604052"},
    )
    result = get_code("0x1234567890abcdef1234567890abcdef12345678", rpc_url)
    assert result == "0x6080604052"


@responses.activate
def test_get_code_eoa_returns_0x():
    rpc_url = "https://mainnet.base.org"
    responses.post(
        rpc_url,
        json={"jsonrpc": "2.0", "id": 1, "result": "0x"},
    )
    result = get_code("0x0000000000000000000000000000000000000001", rpc_url)
    assert result == "0x"


@responses.activate
def test_get_code_rpc_error():
    rpc_url = "https://mainnet.base.org"
    responses.post(
        rpc_url,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32600, "message": "Invalid request"},
        },
    )
    with pytest.raises(RPCError, match="Invalid request"):
        get_code("0x1234567890abcdef1234567890abcdef12345678", rpc_url)


@responses.activate
def test_get_code_network_error():
    rpc_url = "https://mainnet.base.org"
    responses.post(rpc_url, body=ConnectionError("timeout"))
    with pytest.raises(RPCError, match="RPC request failed"):
        get_code("0x1234567890abcdef1234567890abcdef12345678", rpc_url)


@responses.activate
def test_get_code_null_result():
    rpc_url = "https://mainnet.base.org"
    responses.post(
        rpc_url,
        json={"jsonrpc": "2.0", "id": 1, "result": None},
    )
    with pytest.raises(RPCError, match="null result"):
        get_code("0x1234567890abcdef1234567890abcdef12345678", rpc_url)


@responses.activate
def test_get_code_caching():
    rpc_url = "https://mainnet.base.org"
    responses.post(
        rpc_url,
        json={"jsonrpc": "2.0", "id": 1, "result": "0x6080"},
    )
    addr = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    result1 = get_code(addr, rpc_url)
    result2 = get_code(addr, rpc_url)
    assert result1 == result2
    assert len(responses.calls) == 1  # only one HTTP call due to cache


# --- get_storage_at tests ---


@responses.activate
def test_get_storage_at_success():
    rpc_url = "https://mainnet.base.org"
    # Return an address padded to 32 bytes
    impl_addr = "000000000000000000000000" + "ab" * 20
    responses.post(
        rpc_url,
        json={"jsonrpc": "2.0", "id": 1, "result": "0x" + impl_addr},
    )
    result = get_storage_at(
        "0x" + "11" * 20,
        "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc",
        rpc_url,
    )
    assert result == "0x" + impl_addr


@responses.activate
def test_get_storage_at_empty_slot():
    rpc_url = "https://mainnet.base.org"
    responses.post(
        rpc_url,
        json={"jsonrpc": "2.0", "id": 1, "result": "0x" + "0" * 64},
    )
    result = get_storage_at(
        "0x" + "22" * 20,
        "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc",
        rpc_url,
    )
    assert result == "0x" + "0" * 64


@responses.activate
def test_get_storage_at_rpc_error():
    rpc_url = "https://mainnet.base.org"
    responses.post(
        rpc_url,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32000, "message": "execution error"},
        },
    )
    with pytest.raises(RPCError, match="execution error"):
        get_storage_at("0x" + "33" * 20, "0x" + "aa" * 32, rpc_url)


@responses.activate
def test_get_storage_at_network_error():
    rpc_url = "https://mainnet.base.org"
    responses.post(rpc_url, body=ConnectionError("timeout"))
    with pytest.raises(RPCError, match="RPC request failed"):
        get_storage_at("0x" + "44" * 20, "0x" + "bb" * 32, rpc_url)


@responses.activate
def test_get_storage_at_caching():
    rpc_url = "https://mainnet.base.org"
    responses.post(
        rpc_url,
        json={"jsonrpc": "2.0", "id": 1, "result": "0x" + "0" * 64},
    )
    addr = "0x" + "55" * 20
    slot = "0x" + "cc" * 32
    result1 = get_storage_at(addr, slot, rpc_url)
    result2 = get_storage_at(addr, slot, rpc_url)
    assert result1 == result2
    assert len(responses.calls) == 1
