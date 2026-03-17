"""Thin CLI loop around the Augur autoresearch benchmark harness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from risk_api.auto_bench import default_case_paths, run_bench


def default_json_out(repo_root: Path) -> Path:
    """Return the default persisted summary path for loop runs."""
    return repo_root / "auto" / "runs" / "latest.json"


def render_loop_summary(
    summary: Mapping[str, Any], *, case_paths: Iterable[Path], json_out: Path,
) -> str:
    """Render a compact human-readable loop summary."""
    resolved_case_paths = list(case_paths)
    total_checks = int(summary.get("total_checks", 0))
    failed_checks = int(summary.get("failed_checks", 0))
    passed_checks = int(summary.get("passed_checks", total_checks - failed_checks))
    status = "PASS" if failed_checks == 0 else "FAIL"

    lines = [
        f"Autoresearch loop: {status} ({passed_checks}/{total_checks} checks passed)",
        f"Case files: {len(resolved_case_paths)}",
        (
            "Blind spots: "
            f"{int(summary.get('distinct_blind_spots_found', 0))} | "
            "Holdout disagreements: "
            f"{int(summary.get('holdout_disagreements', 0))}"
        ),
        (
            "Policy regressions: "
            f"{int(summary.get('policy_regressions', 0))} | "
            "Serializer/doc drifts: "
            f"{int(summary.get('serializer_doc_drifts', 0))}"
        ),
        f"JSON report: {json_out.as_posix()}",
    ]

    failures = summary.get("failures", [])
    if not isinstance(failures, list) or not failures:
        lines.append(
            "Next action: add candidate cases or holdouts before changing implementation."
        )
        return "\n".join(lines)

    lines.append("Failure groups:")
    for label, grouped_failures in _group_failures(failures):
        failure_ids = [
            str(failure.get("id", "<unknown>"))
            for failure in grouped_failures
        ]
        preview = ", ".join(failure_ids[:3])
        if len(failure_ids) > 3:
            preview = f"{preview}, +{len(failure_ids) - 3} more"
        kinds = sorted({
            f"{failure.get('kind', '<unknown>')}/{failure.get('source', '<unknown>')}"
            for failure in grouped_failures
        })
        lines.append(
            f"- {label}: {len(grouped_failures)} failure(s) [{preview}] ({', '.join(kinds)})"
        )

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the Augur autoresearch loop, persist auto/runs/latest.json, "
            "and print a compact failure summary."
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
        help="Optional path to write the benchmark summary JSON.",
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
    case_paths = list(args.case_paths or default_case_paths(repo_root))
    summary = run_bench(
        case_paths,
        include_app_contract_checks=not args.skip_app_contract_checks,
    )

    json_out = args.json_out or default_json_out(repo_root)
    json_text = json.dumps(summary, indent=2)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json_text + "\n", encoding="utf-8")

    print(render_loop_summary(summary, case_paths=case_paths, json_out=json_out))

    if summary.get("failed_checks", 0) and not args.allow_failures:
        return 1
    return 0


def _group_failures(
    failures: Iterable[Mapping[str, Any]],
) -> list[tuple[str, list[Mapping[str, Any]]]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for failure in failures:
        label = str(
            failure.get("blind_spot")
            or failure.get("id")
            or failure.get("kind")
            or "ungrouped"
        )
        grouped.setdefault(label, []).append(failure)
    return sorted(grouped.items(), key=lambda item: item[0])


if __name__ == "__main__":
    raise SystemExit(main())
