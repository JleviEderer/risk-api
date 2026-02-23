import pytest
import responses

from risk_api.analysis.engine import analyze_contract
from risk_api.analysis.scoring import RiskLevel
from risk_api.chain.rpc import RPCError, clear_cache


RPC_URL = "https://mainnet.base.org"


@pytest.fixture(autouse=True)
def _clear_rpc_cache():
    clear_cache()
    yield
    clear_cache()


@responses.activate
def test_analyze_clean_contract():
    # >200 bytes of harmless bytecode
    bytecode = "0x" + "6080604052" + "00" * 200
    responses.post(
        RPC_URL,
        json={"jsonrpc": "2.0", "id": 1, "result": bytecode},
    )
    result = analyze_contract("0x" + "ab" * 20, RPC_URL)
    assert result.score == 0
    assert result.level == RiskLevel.SAFE
    assert result.findings == []
    assert result.bytecode_size > 200


@responses.activate
def test_analyze_contract_with_selfdestruct():
    bytecode = "0x" + "ff" + "00" * 200
    responses.post(
        RPC_URL,
        json={"jsonrpc": "2.0", "id": 1, "result": bytecode},
    )
    result = analyze_contract("0x" + "cd" * 20, RPC_URL)
    assert result.score >= 30
    assert any(f.detector == "selfdestruct" for f in result.findings)


@responses.activate
def test_analyze_eoa():
    responses.post(
        RPC_URL,
        json={"jsonrpc": "2.0", "id": 1, "result": "0x"},
    )
    result = analyze_contract("0x" + "11" * 20, RPC_URL)
    assert result.bytecode_size == 0
    assert result.score == 0
    assert result.level == RiskLevel.SAFE


@responses.activate
def test_analyze_proxy_contract():
    # EIP-1967 proxy: PUSH32 <impl slot> + DELEGATECALL
    eip1967 = "360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
    bytecode = "0x7f" + eip1967 + "f4" + "00" * 200
    responses.post(
        RPC_URL,
        json={"jsonrpc": "2.0", "id": 1, "result": bytecode},
    )
    result = analyze_contract("0x" + "22" * 20, RPC_URL)
    assert any(f.detector == "proxy" for f in result.findings)
    assert any(f.detector == "delegatecall" for f in result.findings)
    # Proxy delegatecall should be INFO, not HIGH
    dc_finding = next(f for f in result.findings if f.detector == "delegatecall")
    assert dc_finding.severity.value == "info"


@responses.activate
def test_analyze_rpc_failure():
    responses.post(RPC_URL, body=ConnectionError("network down"))
    with pytest.raises(RPCError):
        analyze_contract("0x" + "33" * 20, RPC_URL)
