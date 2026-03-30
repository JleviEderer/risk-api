from risk_api.analysis.patterns import Finding, Severity
from risk_api.analysis.policy import (
    PolicyAction,
    PolicyReasonCode,
    ProxyResolutionStatus,
    derive_policy,
)
from risk_api.analysis.scoring import RiskLevel


def test_safe_score_recommends_allow():
    result = derive_policy(
        score=0,
        level=RiskLevel.SAFE,
        findings=[],
        category_scores={},
    )

    assert result.action == PolicyAction.ALLOW
    assert result.reason_codes == []


def test_low_score_with_honeypot_blocks():
    result = derive_policy(
        score=25,
        level=RiskLevel.LOW,
        findings=[
            Finding("honeypot", Severity.HIGH, "t", "d", 25),
        ],
        category_scores={"honeypot": 25},
    )

    assert result.action == PolicyAction.BLOCK
    assert PolicyReasonCode.HONEYPOT_SIGNAL.value in result.reason_codes


def test_hidden_mint_signal_recommends_manual_review_even_when_score_is_low():
    result = derive_policy(
        score=25,
        level=RiskLevel.LOW,
        findings=[
            Finding("hidden_mint", Severity.CRITICAL, "t", "d", 25),
        ],
        category_scores={"hidden_mint": 25},
    )

    assert result.action == PolicyAction.MANUAL_REVIEW
    assert PolicyReasonCode.HIDDEN_MINT_SIGNAL.value in result.reason_codes


def test_selfdestruct_signal_recommends_manual_review_even_when_score_is_low():
    result = derive_policy(
        score=30,
        level=RiskLevel.LOW,
        findings=[
            Finding("selfdestruct", Severity.CRITICAL, "t", "d", 30),
        ],
        category_scores={"selfdestruct": 30},
    )

    assert result.action == PolicyAction.MANUAL_REVIEW
    assert PolicyReasonCode.SELFDESTRUCT_SIGNAL.value in result.reason_codes


def test_fee_manipulation_signal_warns_even_when_score_is_safe():
    result = derive_policy(
        score=15,
        level=RiskLevel.SAFE,
        findings=[
            Finding("fee_manipulation", Severity.HIGH, "t", "d", 15),
        ],
        category_scores={"fee_manipulation": 15},
    )

    assert result.action == PolicyAction.WARN
    assert PolicyReasonCode.FEE_MANIPULATION_SIGNAL.value in result.reason_codes


def test_medium_score_recommends_manual_review():
    result = derive_policy(
        score=40,
        level=RiskLevel.MEDIUM,
        findings=[
            Finding("proxy", Severity.INFO, "Proxy contract detected", "d", 10),
            Finding("delegatecall", Severity.INFO, "t", "d", 10),
        ],
        category_scores={"proxy": 10, "delegatecall": 10, "impl_selfdestruct": 20},
        proxy_resolution_status=ProxyResolutionStatus.RESOLVED,
    )

    assert result.action == PolicyAction.MANUAL_REVIEW
    assert "elevated_risk_score" in result.reason_codes


def test_unresolved_proxy_recommends_manual_review_even_when_low():
    result = derive_policy(
        score=20,
        level=RiskLevel.LOW,
        findings=[
            Finding(
                "proxy",
                Severity.HIGH,
                "Proxy implementation could not be resolved",
                "d",
                20,
            ),
        ],
        category_scores={"proxy": 20},
        proxy_resolution_status=ProxyResolutionStatus.UNRESOLVED,
    )

    assert result.action == PolicyAction.MANUAL_REVIEW
    assert PolicyReasonCode.PROXY_LOGIC_UNRESOLVED.value in result.reason_codes


def test_proxy_no_code_recommends_manual_review_even_when_low():
    result = derive_policy(
        score=20,
        level=RiskLevel.LOW,
        findings=[
            Finding(
                "proxy",
                Severity.HIGH,
                "Proxy implementation has no bytecode",
                "d",
                20,
            ),
        ],
        category_scores={"proxy": 20},
        proxy_resolution_status=ProxyResolutionStatus.NO_CODE,
    )

    assert result.action == PolicyAction.MANUAL_REVIEW
    assert PolicyReasonCode.PROXY_LOGIC_UNRESOLVED.value in result.reason_codes
    assert PolicyReasonCode.PROXY_LOGIC_NO_CODE.value in result.reason_codes


def test_nested_proxy_recommends_manual_review_even_when_implementation_present():
    result = derive_policy(
        score=20,
        level=RiskLevel.LOW,
        findings=[
            Finding("proxy", Severity.INFO, "Proxy contract detected", "d", 10),
            Finding("impl_proxy", Severity.HIGH, "Implementation is itself a proxy", "d", 20),
        ],
        category_scores={"proxy": 10, "impl_proxy": 20},
        proxy_resolution_status=ProxyResolutionStatus.NESTED_PROXY,
    )

    assert result.action == PolicyAction.MANUAL_REVIEW
    assert PolicyReasonCode.PROXY_LOGIC_UNRESOLVED.value in result.reason_codes
    assert PolicyReasonCode.PROXY_LOGIC_NESTED_PROXY.value in result.reason_codes


def test_raw_delegatecall_recommends_manual_review_even_when_score_is_safe():
    result = derive_policy(
        score=15,
        level=RiskLevel.SAFE,
        findings=[
            Finding(
                "delegatecall",
                Severity.HIGH,
                "Raw DELEGATECALL without proxy pattern",
                "d",
                15,
            ),
        ],
        category_scores={"delegatecall": 15},
    )

    assert result.action == PolicyAction.MANUAL_REVIEW
    assert PolicyReasonCode.RAW_DELEGATECALL_SURFACE.value in result.reason_codes


def test_high_score_recommends_block():
    result = derive_policy(
        score=80,
        level=RiskLevel.CRITICAL,
        findings=[
            Finding("hidden_mint", Severity.CRITICAL, "t", "d", 25),
        ],
        category_scores={"hidden_mint": 25, "honeypot": 25, "proxy": 10, "impl_hidden_mint": 20},
        proxy_resolution_status=ProxyResolutionStatus.RESOLVED,
    )

    assert result.action == PolicyAction.BLOCK
    assert "high_risk_score" in result.reason_codes
    assert "hidden_mint_signal" in result.reason_codes
