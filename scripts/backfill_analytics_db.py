"""Backfill legacy JSONL request logs into the SQLite analytics store."""

from __future__ import annotations

import argparse
from pathlib import Path

from risk_api.analytics import append_sqlite_entry, init_sqlite_store, iter_jsonl_entries


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Import request events from a legacy JSONL log into the durable "
            "SQLite analytics store used by /stats."
        )
    )
    parser.add_argument(
        "--from-log",
        required=True,
        help="Path to the source JSONL request log",
    )
    parser.add_argument(
        "--to-db",
        required=True,
        help="Path to the destination SQLite analytics database",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = Path(args.from_log)
    target = Path(args.to_db)

    if not source.is_file():
        raise SystemExit(f"Source log not found: {source}")

    init_sqlite_store(str(target))

    total = 0
    inserted = 0
    for entry in iter_jsonl_entries(str(source)):
        total += 1
        if append_sqlite_entry(str(target), entry):
            inserted += 1

    skipped = total - inserted
    print(f"Backfill complete: total={total} inserted={inserted} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
