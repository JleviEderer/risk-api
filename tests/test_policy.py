from risk_api.analysis.patterns import Finding, Severity
from risk_api.analysis.policy import PolicyAction, derive_policy
from risk_api.analysis.scoring import RiskLevel


def test_safe_score_recommends_allow():
    result = derive_policy(
        score=0,
        level=RiskLevel.SAFE,
        findings=[],
        category_scores={},
        implementation_present=False,
    )

    assert result.action == PolicyAction.ALLOW
    assert result.reason_codes == []


def test_low_score_recommends_warn():
    result = derive_policy(
        score=25,
        level=RiskLevel.LOW,
        findings=[
            Finding("honeypot", Severity.HIGH, "t", "d", 25),
        ],
        category_scores={"honeypot": 25},
        implementation_present=False,
    )

    assert result.action == PolicyAction.WARN
    assert "honeypot_signal" in result.reason_codes


def test_medium_score_recommends_manual_review():
    result = derive_policy(
        score=40,
        level=RiskLevel.MEDIUM,
        findings=[
            Finding("proxy", Severity.INFO, "Proxy contract detected", "d", 10),
            Finding("delegatecall", Severity.INFO, "t", "d", 10),
        ],
        category_scores={"proxy": 10, "delegatecall": 10, "impl_hidden_mint": 20},
        implementation_present=True,
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
        implementation_present=False,
    )

    assert result.action == PolicyAction.MANUAL_REVIEW
    assert "proxy_logic_unresolved" in result.reason_codes


def test_high_score_recommends_block():
    result = derive_policy(
        score=80,
        level=RiskLevel.CRITICAL,
        findings=[
            Finding("hidden_mint", Severity.CRITICAL, "t", "d", 25),
        ],
        category_scores={"hidden_mint": 25, "honeypot": 25, "proxy": 10, "impl_hidden_mint": 20},
        implementation_present=True,
    )

    assert result.action == PolicyAction.BLOCK
    assert "high_risk_score" in result.reason_codes
    assert "hidden_mint_signal" in result.reason_codes
