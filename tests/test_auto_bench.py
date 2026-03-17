import json
from pathlib import Path

from risk_api import auto_bench
from risk_api.auto_bench import run_bench


def test_public_auto_bench_passes():
    repo_root = Path(__file__).resolve().parents[1]
    summary = run_bench(
        [repo_root / "auto" / "corpus" / "public_cases.json"],
        include_app_contract_checks=True,
    )

    assert summary["failed_checks"] == 0
    assert summary["serializer_doc_drifts"] == 0
    assert summary["policy_regressions"] == 0


def test_candidate_failure_metrics_count_reproducible_blind_spots(tmp_path):
    candidate_path = tmp_path / "candidate.local.json"
    candidate_path.write_text(
        json.dumps(
            [
                {
                    "id": "candidate-regression",
                    "name": "Candidate regression example",
                    "kind": "bytecode",
                    "source": "candidate",
                    "tags": ["policy", "delegatecall"],
                    "blind_spot": "raw_delegatecall_allow_regression",
                    "bytecode": "0xf4" + ("00" * 200),
                    "expected": {
                        "decision": "allow",
                    },
                }
            ]
        ),
        encoding="utf-8",
    )

    summary = run_bench([candidate_path], include_app_contract_checks=False)

    assert summary["failed_checks"] == 1
    assert summary["new_reproducible_failures_found"] == 1
    assert summary["distinct_blind_spots_found"] == 1
    assert summary["blind_spots"] == ["raw_delegatecall_allow_regression"]


def test_app_contract_checks_fail_on_stale_proof_report_policy(monkeypatch):
    stale_reports = {
        **auto_bench.REPORT_PAGES,
        "/reports/base-bluechip-bytecode-snapshot": {
            **auto_bench.REPORT_PAGES["/reports/base-bluechip-bytecode-snapshot"],
            "contracts": [
                {
                    **auto_bench.REPORT_PAGES["/reports/base-bluechip-bytecode-snapshot"]["contracts"][0],
                    "snapshot": {
                        **auto_bench.REPORT_PAGES["/reports/base-bluechip-bytecode-snapshot"]["contracts"][0]["snapshot"],
                        "decision": "warn",
                        "recommended_policy": {
                            "action": "warn",
                            "summary": (
                                "Allow with caution. Log the findings and keep the "
                                "contract on a watchlist or secondary review path."
                            ),
                            "reason_codes": ["honeypot_signal"],
                        },
                    },
                },
                *auto_bench.REPORT_PAGES["/reports/base-bluechip-bytecode-snapshot"]["contracts"][1:],
            ],
        },
    }
    monkeypatch.setattr(auto_bench, "REPORT_PAGES", stale_reports)

    repo_root = Path(__file__).resolve().parents[1]
    summary = run_bench(
        [repo_root / "auto" / "corpus" / "public_cases.json"],
        include_app_contract_checks=True,
    )

    assert summary["failed_checks"] == 1
    assert summary["policy_regressions"] == 1
    assert summary["serializer_doc_drifts"] == 1
    assert summary["failures"][0]["id"] == "proof-report-policy-semantics"
    assert "decision drift" in summary["failures"][0]["mismatches"][0]
