"""Autoresearch benchmark harness for Augur detector and API-contract checks."""

from __future__ import annotations

import argparse
from contextlib import nullcontext
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, cast

from risk_api.analysis.disassembler import disassemble
from risk_api.analysis.patterns import Finding, Severity, run_all_detectors
from risk_api.analysis.policy import ProxyResolutionStatus, derive_policy
from risk_api.analysis.scoring import RiskLevel, compute_score
from risk_api.api_contract import (
    analysis_result_from_snapshot,
    normalize_analysis_snapshot,
)
from risk_api.app import (
    PROXY_ANALYSIS_EXAMPLE,
    PROXY_ANALYSIS_EXAMPLE_JSON,
    SAFE_ANALYSIS_EXAMPLE,
    SAFE_ANALYSIS_EXAMPLE_JSON,
    create_app,
)
from risk_api.config import Config
from risk_api.proof_reports import REPORT_PAGES


GENERIC_TAGS = {
    "policy",
    "serializer",
    "docs",
    "openapi",
    "proof-report",
    "machine-doc",
    "smoke",
}


@dataclass(frozen=True, slots=True)
class CheckResult:
    case_id: str
    name: str
    kind: str
    source: str
    tags: tuple[str, ...]
    blind_spot: str | None
    passed: bool
    mismatches: tuple[str, ...]


def default_case_paths(repo_root: Path) -> list[Path]:
    """Return the default tracked and local case files."""
    paths = [repo_root / "auto" / "corpus" / "public_cases.json"]
    for pattern in ("auto/corpus/*.local.json", "auto/candidates/*.local.json"):
        paths.extend(sorted(repo_root.glob(pattern)))
    return [path for path in paths if path.exists()]


def run_bench(
    case_paths: Iterable[Path],
    *,
    include_app_contract_checks: bool = True,
) -> dict[str, Any]:
    """Evaluate the configured cases and return a summary payload."""
    results: list[CheckResult] = []
    for case in _load_cases(case_paths):
        results.append(_evaluate_case(case))

    if include_app_contract_checks:
        results.extend(_app_contract_checks())

    failures = [result for result in results if not result.passed]
    blind_spots = sorted({
        result.blind_spot
        for result in failures
        if result.blind_spot
    })

    summary = {
        "total_checks": len(results),
        "passed_checks": len(results) - len(failures),
        "failed_checks": len(failures),
        "new_reproducible_failures_found": sum(
            1 for result in failures if result.source == "candidate"
        ),
        "distinct_blind_spots_found": len(blind_spots),
        "blind_spots": blind_spots,
        "holdout_disagreements": sum(
            1 for result in failures if result.source == "holdout"
        ),
        "policy_regressions": sum(
            1 for result in failures if "policy" in result.tags
        ),
        "serializer_doc_drifts": sum(
            1
            for result in failures
            if {"serializer", "docs", "openapi", "proof-report", "machine-doc"}
            & set(result.tags)
        ),
        "failures": [
            {
                "id": result.case_id,
                "name": result.name,
                "kind": result.kind,
                "source": result.source,
                "tags": list(result.tags),
                "blind_spot": result.blind_spot,
                "mismatches": list(result.mismatches),
            }
            for result in failures
        ],
    }
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run Augur autoresearch benchmarks over labeled cases and "
            "public API-contract drift checks."
        )
    )
    parser.add_argument(
        "case_paths",
        nargs="*",
        type=Path,
        help=(
            "Optional case files. Defaults to auto/corpus/public_cases.json plus "
            "any *.local.json files under auto/corpus and auto/candidates."
        ),
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        help="Optional path to write the benchmark summary as JSON.",
    )
    parser.add_argument(
        "--skip-app-contract-checks",
        action="store_true",
        help="Skip built-in OpenAPI, machine-doc, and proof-report drift checks.",
    )
    parser.add_argument(
        "--allow-failures",
        action="store_true",
        help="Return exit code 0 even if checks fail.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[2]
    case_paths = args.case_paths or default_case_paths(repo_root)
    summary = run_bench(
        case_paths,
        include_app_contract_checks=not args.skip_app_contract_checks,
    )

    text = json.dumps(summary, indent=2)
    print(text)

    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text + "\n", encoding="utf-8")

    if summary["failed_checks"] and not args.allow_failures:
        return 1
    return 0


def _load_cases(case_paths: Iterable[Path]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for path in case_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        raw_cases = payload.get("cases", payload) if isinstance(payload, dict) else payload
        if not isinstance(raw_cases, list):
            raise ValueError(f"Case file must contain a list of cases: {path}")
        for raw_case in raw_cases:
            if not isinstance(raw_case, dict):
                raise ValueError(f"Case must be an object: {path}")
            case = dict(raw_case)
            case.setdefault("source", _infer_source_from_path(path))
            case.setdefault("file", str(path))
            cases.append(case)
    return cases


def _infer_source_from_path(path: Path) -> str:
    name = path.name.lower()
    if "holdout" in name:
        return "holdout"
    if "candidate" in str(path).lower():
        return "candidate"
    return "public"


def _evaluate_case(case: Mapping[str, Any]) -> CheckResult:
    kind = str(case["kind"])
    if kind == "bytecode":
        actual = _evaluate_bytecode_case(case)
    elif kind == "policy":
        actual = _evaluate_policy_case(case)
    elif kind == "analysis":
        actual = _evaluate_analysis_case(case)
    elif kind == "serialization":
        actual = _evaluate_serialization_case(case)
    else:
        raise ValueError(f"Unsupported case kind: {kind}")

    mismatches = tuple(_compare_expected(actual, case.get("expected", {})))
    return CheckResult(
        case_id=str(case["id"]),
        name=str(case.get("name", case["id"])),
        kind=kind,
        source=str(case.get("source", "public")),
        tags=tuple(str(tag) for tag in case.get("tags", [])),
        blind_spot=(
            str(case["blind_spot"])
            if case.get("blind_spot") is not None
            else _blind_spot_from_tags(case.get("tags", []))
        ),
        passed=not mismatches,
        mismatches=mismatches,
    )


def _evaluate_bytecode_case(case: Mapping[str, Any]) -> dict[str, Any]:
    bytecode = str(case["bytecode"])
    instructions = disassemble(bytecode)
    findings = run_all_detectors(instructions)
    score_result = compute_score(findings, instructions, bytecode)
    policy = derive_policy(
        score=score_result.score,
        level=score_result.level,
        findings=findings,
        category_scores=score_result.category_scores,
    )
    return {
        "score": score_result.score,
        "level": score_result.level.value,
        "decision": policy.action.value,
        "reason_codes": list(policy.reason_codes),
        "findings": [finding.detector for finding in findings],
        "category_scores": dict(score_result.category_scores),
    }


def _evaluate_policy_case(case: Mapping[str, Any]) -> dict[str, Any]:
    inputs = _require_mapping(case, "input")
    findings = [
        _finding_from_mapping(finding)
        for finding in inputs.get("findings", [])
    ]
    policy = derive_policy(
        score=int(inputs["score"]),
        level=RiskLevel(str(inputs["level"])),
        findings=findings,
        category_scores={
            str(category): int(points)
            for category, points in dict(inputs.get("category_scores", {})).items()
        },
        proxy_resolution_status=ProxyResolutionStatus(
            str(inputs.get("proxy_resolution_status", "not_proxy"))
        ),
    )
    return {
        "decision": policy.action.value,
        "reason_codes": list(policy.reason_codes),
    }


def _evaluate_analysis_case(case: Mapping[str, Any]) -> dict[str, Any]:
    try:
        import responses
    except ImportError as exc:
        raise RuntimeError(
            "analysis cases require the optional dev dependency 'responses'"
        ) from exc

    from unittest.mock import patch

    from risk_api.analysis.engine import analyze_contract, clear_analysis_cache
    from risk_api.analysis.reputation import BLOCKSCOUT_API, clear_reputation_cache
    from risk_api.chain.rpc import clear_cache as clear_rpc_cache

    inputs = _require_mapping(case, "input")
    address = str(inputs["address"])
    rpc_url = str(inputs.get("rpc_url", "https://mainnet.base.org"))
    basescan_api_key = str(inputs.get("basescan_api_key", ""))
    rpc_specs = _require_list(inputs, "rpc")
    explorer_specs = _optional_list(inputs, "explorer")
    mock_now = inputs.get("mock_now")

    clear_rpc_cache()
    clear_analysis_cache()
    clear_reputation_cache()

    try:
        with responses.RequestsMock(assert_all_requests_are_fired=True) as mocked:
            for spec in rpc_specs:
                _register_mock_response(
                    mocked,
                    responses.POST,
                    rpc_url,
                    spec,
                    wrap_as_json_rpc=True,
                )
            for spec in explorer_specs:
                _register_mock_response(
                    mocked,
                    responses.GET,
                    BLOCKSCOUT_API,
                    spec,
                    wrap_as_json_rpc=False,
                )

            time_ctx = (
                patch("risk_api.analysis.reputation.time.time", return_value=int(mock_now))
                if mock_now is not None
                else nullcontext()
            )
            with time_ctx:
                result = analyze_contract(address, rpc_url, basescan_api_key)
    finally:
        clear_rpc_cache()
        clear_analysis_cache()
        clear_reputation_cache()

    return {
        "score": result.score,
        "level": result.level.value,
        "decision": result.decision.value,
        "reason_codes": list(result.recommended_policy.reason_codes),
        "findings": [finding.detector for finding in result.findings],
        "category_scores": dict(result.category_scores),
        "proxy_resolution_status": result.proxy_resolution_status.value,
    }


def _evaluate_serialization_case(case: Mapping[str, Any]) -> dict[str, Any]:
    snapshot = _require_mapping(case, "snapshot")
    wire = normalize_analysis_snapshot(snapshot)
    result = dict(wire)
    result["keys"] = sorted(result.keys())
    if "implementation" in result:
        implementation = result["implementation"]
        if isinstance(implementation, dict):
            result["implementation_keys"] = sorted(implementation.keys())
            result["implementation_category_scores"] = dict(
                implementation.get("category_scores", {})
            )
    return result


def _compare_expected(actual: Mapping[str, Any], expected: Any) -> list[str]:
    if not isinstance(expected, Mapping):
        return [f"Expected contract must be an object, got: {type(expected).__name__}"]

    mismatches: list[str] = []
    for key in ("score", "level", "decision", "proxy_resolution_status"):
        if key in expected and actual.get(key) != expected[key]:
            mismatches.append(
                f"{key}: expected {expected[key]!r}, got {actual.get(key)!r}"
            )

    if "reason_codes" in expected and actual.get("reason_codes") != expected["reason_codes"]:
        mismatches.append(
            f"reason_codes: expected {expected['reason_codes']!r}, got {actual.get('reason_codes')!r}"
        )
    for key, field in (
        ("reason_codes_include", "reason_codes"),
        ("findings_include", "findings"),
    ):
        if key in expected:
            actual_values = set(actual.get(field, []))
            for value in expected[key]:
                if value not in actual_values:
                    mismatches.append(f"{field}: missing expected value {value!r}")
    for key, field in (
        ("reason_codes_exclude", "reason_codes"),
        ("findings_exclude", "findings"),
    ):
        if key in expected:
            actual_values = set(actual.get(field, []))
            for value in expected[key]:
                if value in actual_values:
                    mismatches.append(f"{field}: unexpected value {value!r}")

    if "category_scores_include" in expected:
        actual_scores = dict(actual.get("category_scores", {}))
        for category, points in expected["category_scores_include"].items():
            if actual_scores.get(category) != points:
                mismatches.append(
                    f"category_scores[{category!r}]: expected {points!r}, got {actual_scores.get(category)!r}"
                )

    if "present_keys" in expected:
        actual_keys = set(actual.keys())
        for key in expected["present_keys"]:
            if key not in actual_keys:
                mismatches.append(f"missing key {key!r}")
    if "missing_keys" in expected:
        actual_keys = set(actual.keys())
        for key in expected["missing_keys"]:
            if key in actual_keys:
                mismatches.append(f"unexpected key {key!r}")

    if "implementation_category_scores_include" in expected:
        impl_scores = dict(actual.get("implementation_category_scores", {}))
        for category, points in expected["implementation_category_scores_include"].items():
            if impl_scores.get(category) != points:
                mismatches.append(
                    f"implementation.category_scores[{category!r}]: expected {points!r}, got {impl_scores.get(category)!r}"
                )
    if "implementation_category_scores_exclude" in expected:
        impl_scores = dict(actual.get("implementation_category_scores", {}))
        for category in expected["implementation_category_scores_exclude"]:
            if category in impl_scores:
                mismatches.append(
                    f"implementation.category_scores unexpectedly contains {category!r}"
                )

    return mismatches


def _app_contract_checks() -> list[CheckResult]:
    app = create_app(config=_test_config(), enable_x402=False)
    app.config["TESTING"] = True
    client = app.test_client()

    openapi = client.get("/openapi.json").get_json()
    examples = openapi["paths"]["/analyze"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["examples"]

    checks = [
        _make_contract_check(
            case_id="openapi-safe-example",
            name="OpenAPI safe example matches serializer",
            tags=("serializer", "docs", "openapi"),
            mismatches=_dict_mismatch(
                examples["safe_contract"]["value"], SAFE_ANALYSIS_EXAMPLE
            ),
        ),
        _make_contract_check(
            case_id="openapi-proxy-example",
            name="OpenAPI proxy example matches serializer",
            tags=("serializer", "docs", "openapi"),
            mismatches=_dict_mismatch(
                examples["proxy_contract"]["value"], PROXY_ANALYSIS_EXAMPLE
            ),
        ),
        _make_contract_check(
            case_id="machine-doc-safe-example",
            name="Machine docs embed current safe example",
            tags=("serializer", "docs", "machine-doc"),
            mismatches=_machine_doc_mismatches(client),
        ),
        _make_contract_check(
            case_id="proof-report-wire-shape",
            name="Proof report omits null implementation on non-proxy snapshots",
            tags=("serializer", "docs", "proof-report"),
            mismatches=_proof_report_mismatches(client),
        ),
        _make_contract_check(
            case_id="proof-report-policy-semantics",
            name="Proof report snapshots match current policy semantics",
            tags=("policy", "serializer", "docs", "proof-report"),
            mismatches=_proof_report_policy_mismatches(),
        ),
    ]
    return checks


def _machine_doc_mismatches(client: Any) -> list[str]:
    mismatches: list[str] = []
    llms_text = client.get("/llms.txt").data.decode("utf-8")
    if SAFE_ANALYSIS_EXAMPLE_JSON not in llms_text:
        mismatches.append("llms.txt does not contain the current safe example JSON")

    skill_text = client.get("/skill.md").data.decode("utf-8")
    if SAFE_ANALYSIS_EXAMPLE_JSON not in skill_text:
        mismatches.append("skill.md does not contain the current safe example JSON")

    llms_full_text = client.get("/llms-full.txt").data.decode("utf-8")
    if SAFE_ANALYSIS_EXAMPLE_JSON not in llms_full_text:
        mismatches.append("llms-full.txt does not contain the current safe example JSON")
    if PROXY_ANALYSIS_EXAMPLE_JSON not in llms_full_text:
        mismatches.append("llms-full.txt does not contain the current proxy example JSON")

    return mismatches


def _proof_report_mismatches(client: Any) -> list[str]:
    text = client.get("/reports/base-bluechip-bytecode-snapshot").data.decode("utf-8")
    mismatches: list[str] = []
    if '&quot;implementation&quot;: null' in text:
        mismatches.append("proof report still renders implementation: null")
    if '&quot;implementation&quot;: {' not in text:
        mismatches.append("proof report no longer renders a nested implementation example")
    return mismatches


def _proof_report_policy_mismatches() -> list[str]:
    mismatches: list[str] = []
    for path, report in REPORT_PAGES.items():
        for contract in cast(list[Mapping[str, object]], report.get("contracts", [])):
            contract_name = str(contract.get("name", "<unknown>"))
            snapshot = _require_mapping(contract, "snapshot")
            result = analysis_result_from_snapshot(snapshot)
            expected_policy = derive_policy(
                score=result.score,
                level=result.level,
                findings=result.findings,
                category_scores=result.category_scores,
                proxy_resolution_status=result.proxy_resolution_status,
            )

            if result.decision != expected_policy.action:
                mismatches.append(
                    f"{path} {contract_name}: decision drift "
                    f"embedded={result.decision.value!r} expected={expected_policy.action.value!r}"
                )
            if result.recommended_policy.action != expected_policy.action:
                mismatches.append(
                    f"{path} {contract_name}: recommended_policy.action drift "
                    f"embedded={result.recommended_policy.action.value!r} expected={expected_policy.action.value!r}"
                )
            if result.recommended_policy.summary != expected_policy.summary:
                mismatches.append(
                    f"{path} {contract_name}: recommended_policy.summary drift"
                )
            if result.recommended_policy.reason_codes != expected_policy.reason_codes:
                mismatches.append(
                    f"{path} {contract_name}: recommended_policy.reason_codes drift "
                    f"embedded={result.recommended_policy.reason_codes!r} expected={expected_policy.reason_codes!r}"
                )
    return mismatches


def _make_contract_check(
    *,
    case_id: str,
    name: str,
    tags: tuple[str, ...],
    mismatches: list[str],
) -> CheckResult:
    return CheckResult(
        case_id=case_id,
        name=name,
        kind="app_contract",
        source="app_contract",
        tags=tags,
        blind_spot=None,
        passed=not mismatches,
        mismatches=tuple(mismatches),
    )


def _dict_mismatch(actual: Mapping[str, Any], expected: Mapping[str, Any]) -> list[str]:
    if actual == expected:
        return []
    return [
        "serialized payload mismatch",
        f"expected={json.dumps(expected, sort_keys=True)}",
        f"actual={json.dumps(actual, sort_keys=True)}",
    ]


def _test_config() -> Config:
    return Config(
        wallet_address="0x13580b9C6A9AfBfE4C739e74136C1dA174dB9891",
        base_rpc_url="https://mainnet.base.org",
        facilitator_url="https://x402.org/facilitator",
        network="eip155:8453",
        price="$0.10",
        basescan_api_key="",
        public_url="https://augurrisk.com",
    )


def _finding_from_mapping(raw: Mapping[str, Any]) -> Finding:
    return Finding(
        detector=str(raw["detector"]),
        severity=Severity(str(raw["severity"])),
        title=str(raw["title"]),
        description=str(raw["description"]),
        points=int(raw["points"]),
        offset=(
            int(raw["offset"])
            if raw.get("offset") is not None
            else None
        ),
    )


def _blind_spot_from_tags(tags: Iterable[Any]) -> str | None:
    specific_tags = [
        str(tag)
        for tag in tags
        if str(tag) not in GENERIC_TAGS
    ]
    if not specific_tags:
        return None
    return specific_tags[0]


def _require_mapping(case: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = case.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"Case {case.get('id', '<unknown>')} must include object {key!r}")
    return value


def _require_list(case: Mapping[str, Any], key: str) -> list[Any]:
    value = case.get(key)
    if not isinstance(value, list):
        raise ValueError(f"Case {case.get('id', '<unknown>')} must include array {key!r}")
    return value


def _optional_list(case: Mapping[str, Any], key: str) -> list[Any]:
    value = case.get(key, [])
    if not isinstance(value, list):
        raise ValueError(f"Case {case.get('id', '<unknown>')} field {key!r} must be an array")
    return value


def _register_mock_response(
    mocked: Any,
    method: str,
    url: str,
    raw_spec: Any,
    *,
    wrap_as_json_rpc: bool,
) -> None:
    if not isinstance(raw_spec, Mapping):
        raise ValueError(f"Mock response must be an object, got {type(raw_spec).__name__}")

    status = int(raw_spec.get("status", 200))
    if "connection_error" in raw_spec:
        mocked.add(method, url, body=ConnectionError(str(raw_spec["connection_error"])))
        return

    if "json" in raw_spec:
        payload = raw_spec["json"]
    elif wrap_as_json_rpc and "result" in raw_spec:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": raw_spec["result"],
        }
    elif wrap_as_json_rpc and "error" in raw_spec:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": raw_spec["error"],
        }
    else:
        raise ValueError(
            "Mock response must include one of 'json', 'result', 'error', or "
            "'connection_error'"
        )

    mocked.add(method, url, json=payload, status=status)


if __name__ == "__main__":
    raise SystemExit(main())
