import json
from pathlib import Path

from risk_api import auto_loop


def test_render_loop_summary_groups_failures():
    summary = {
        "total_checks": 4,
        "passed_checks": 1,
        "failed_checks": 3,
        "distinct_blind_spots_found": 1,
        "holdout_disagreements": 1,
        "policy_regressions": 2,
        "serializer_doc_drifts": 1,
        "failures": [
            {
                "id": "candidate-regression-a",
                "kind": "bytecode",
                "source": "candidate",
                "blind_spot": "raw_delegatecall_allow_regression",
            },
            {
                "id": "candidate-regression-b",
                "kind": "policy",
                "source": "candidate",
                "blind_spot": "raw_delegatecall_allow_regression",
            },
            {
                "id": "proof-report-policy-semantics",
                "kind": "app_contract",
                "source": "app_contract",
                "blind_spot": None,
            },
        ],
    }

    text = auto_loop.render_loop_summary(
        summary,
        case_paths=[Path("auto/corpus/public_cases.json"), Path("auto/corpus/holdout.local.json")],
        json_out=Path("auto/runs/latest.json"),
    )

    assert "Autoresearch loop: FAIL (1/4 checks passed)" in text
    assert "Case files: 2" in text
    assert "raw_delegatecall_allow_regression: 2 failure(s)" in text
    assert "proof-report-policy-semantics: 1 failure(s)" in text
    assert "JSON report: auto/runs/latest.json" in text


def test_main_writes_json_and_returns_zero(monkeypatch, tmp_path, capsys):
    summary = {
        "total_checks": 2,
        "passed_checks": 2,
        "failed_checks": 0,
        "distinct_blind_spots_found": 0,
        "holdout_disagreements": 0,
        "policy_regressions": 0,
        "serializer_doc_drifts": 0,
        "failures": [],
    }

    monkeypatch.setattr(auto_loop, "default_case_paths", lambda repo_root: [Path("public.json")])
    monkeypatch.setattr(auto_loop, "run_bench", lambda case_paths, include_app_contract_checks: summary)

    json_out = tmp_path / "latest.json"
    exit_code = auto_loop.main(["--json-out", str(json_out)])

    assert exit_code == 0
    assert json.loads(json_out.read_text(encoding="utf-8")) == summary
    assert "Autoresearch loop: PASS (2/2 checks passed)" in capsys.readouterr().out


def test_main_returns_nonzero_on_failures_unless_allowed(
    monkeypatch, tmp_path, capsys,
):
    summary = {
        "total_checks": 1,
        "passed_checks": 0,
        "failed_checks": 1,
        "distinct_blind_spots_found": 1,
        "holdout_disagreements": 0,
        "policy_regressions": 1,
        "serializer_doc_drifts": 0,
        "failures": [
            {
                "id": "candidate-regression",
                "kind": "bytecode",
                "source": "candidate",
                "blind_spot": "raw_delegatecall_allow_regression",
            }
        ],
    }

    monkeypatch.setattr(auto_loop, "default_case_paths", lambda repo_root: [Path("public.json")])
    monkeypatch.setattr(auto_loop, "run_bench", lambda case_paths, include_app_contract_checks: summary)

    json_out = tmp_path / "latest.json"
    assert auto_loop.main(["--json-out", str(json_out)]) == 1
    assert auto_loop.main(["--json-out", str(json_out), "--allow-failures"]) == 0
    assert "Failure groups:" in capsys.readouterr().out
