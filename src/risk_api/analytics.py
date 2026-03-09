"""Request analytics helpers and storage backends."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from collections import Counter
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

FUNNEL_KEYS = (
    "landing_views",
    "how_payment_views",
    "intent_page_views",
    "intent_honeypot_views",
    "intent_proxy_views",
    "intent_deployer_views",
    "machine_doc_fetches",
    "valid_unpaid_402_attempts",
    "invalid_address_requests",
    "no_bytecode_requests",
    "paid_requests",
)


def empty_stats_payload() -> dict[str, Any]:
    """Return an empty stats response matching the dashboard contract."""
    return {
        "total_requests": 0,
        "paid_requests": 0,
        "storage_backend": "none",
        "storage_path": "",
        "storage_durable": False,
        "funnel": {key: 0 for key in FUNNEL_KEYS},
        "stage_counts": {},
        "top_paths": [],
        "top_hosts": [],
        "top_referers": [],
        "avg_duration_ms": 0,
        "hourly": [],
        "recent": [],
    }


def _normalize_stage(entry: dict[str, Any]) -> str:
    stage = entry.get("funnel_stage", "")
    if isinstance(stage, str) and stage:
        return stage
    if entry.get("path") == "/":
        return "landing_view"
    if entry.get("paid") and entry.get("status") == 200:
        return "paid_request"
    if entry.get("status") == 402:
        return "unpaid_402"
    if entry.get("status") == 422:
        return "invalid_address"
    return ""


def _top_items(counter: Counter[str], key_name: str) -> list[dict[str, Any]]:
    return [{key_name: item, "count": count} for item, count in counter.most_common(10)]


def build_stats_payload(
    entries: Iterable[dict[str, Any]],
    *,
    intent_page_stages: set[str],
    machine_doc_stages: set[str],
    storage_backend: str = "unknown",
    storage_path: str = "",
    storage_durable: bool = False,
) -> dict[str, Any]:
    """Aggregate analytics entries into the dashboard/stats response."""
    total = 0
    paid = 0
    duration_sum = 0.0
    duration_count = 0
    hourly_buckets: dict[str, dict[str, int]] = {}
    recent: list[dict[str, Any]] = []
    stage_counts: Counter[str] = Counter()
    path_counts: Counter[str] = Counter()
    host_counts: Counter[str] = Counter()
    referer_counts: Counter[str] = Counter()
    funnel = {key: 0 for key in FUNNEL_KEYS}

    for entry in entries:
        total += 1
        if entry.get("paid"):
            paid += 1

        stage = _normalize_stage(entry)

        dur = entry.get("duration_ms")
        if isinstance(dur, (int, float)):
            duration_sum += dur
            duration_count += 1

        ts = entry.get("ts", "")
        if isinstance(ts, str) and len(ts) >= 13:
            hour_key = ts[:13] + ":00:00Z"
            bucket = hourly_buckets.get(hour_key)
            if bucket is None:
                bucket = {
                    "count": 0,
                    "paid": 0,
                    "dur_sum": 0,
                    "dur_n": 0,
                    "landing_views": 0,
                    "how_payment_views": 0,
                    "intent_page_views": 0,
                    "intent_honeypot_views": 0,
                    "intent_proxy_views": 0,
                    "intent_deployer_views": 0,
                    "machine_doc_fetches": 0,
                    "valid_unpaid_402_attempts": 0,
                    "invalid_address_requests": 0,
                    "no_bytecode_requests": 0,
                    "paid_requests": 0,
                }
                hourly_buckets[hour_key] = bucket
            bucket["count"] += 1
            if entry.get("paid"):
                bucket["paid"] += 1
            if isinstance(dur, (int, float)):
                bucket["dur_sum"] += int(dur)
                bucket["dur_n"] += 1

            if stage == "landing_view":
                bucket["landing_views"] += 1
            elif stage == "how_payment_view":
                bucket["how_payment_views"] += 1
            elif stage in intent_page_stages:
                bucket["intent_page_views"] += 1
                if stage == "intent_honeypot_view":
                    bucket["intent_honeypot_views"] += 1
                elif stage == "intent_proxy_view":
                    bucket["intent_proxy_views"] += 1
                elif stage == "intent_deployer_view":
                    bucket["intent_deployer_views"] += 1
            elif stage in machine_doc_stages:
                bucket["machine_doc_fetches"] += 1
            elif stage == "unpaid_402":
                bucket["valid_unpaid_402_attempts"] += 1
            elif stage == "invalid_address":
                bucket["invalid_address_requests"] += 1
            elif stage == "no_bytecode":
                bucket["no_bytecode_requests"] += 1
            elif stage == "paid_request":
                bucket["paid_requests"] += 1

        if stage == "landing_view":
            funnel["landing_views"] += 1
        elif stage == "how_payment_view":
            funnel["how_payment_views"] += 1
        elif stage in intent_page_stages:
            funnel["intent_page_views"] += 1
            if stage == "intent_honeypot_view":
                funnel["intent_honeypot_views"] += 1
            elif stage == "intent_proxy_view":
                funnel["intent_proxy_views"] += 1
            elif stage == "intent_deployer_view":
                funnel["intent_deployer_views"] += 1
        elif stage in machine_doc_stages:
            funnel["machine_doc_fetches"] += 1
        elif stage == "unpaid_402":
            funnel["valid_unpaid_402_attempts"] += 1
        elif stage == "invalid_address":
            funnel["invalid_address_requests"] += 1
        elif stage == "no_bytecode":
            funnel["no_bytecode_requests"] += 1
        elif stage == "paid_request":
            funnel["paid_requests"] += 1

        if stage:
            stage_counts[stage] += 1

        path = entry.get("path")
        if isinstance(path, str) and path:
            path_counts[path] += 1

        host = entry.get("host")
        if isinstance(host, str) and host:
            host_counts[host] += 1

        referer = entry.get("referer")
        if isinstance(referer, str) and referer:
            referer_counts[referer] += 1

        recent.append(entry)

    hourly = [
        {
            "hour": hour,
            "count": bucket["count"],
            "paid": bucket["paid"],
            "landing_views": bucket["landing_views"],
            "how_payment_views": bucket["how_payment_views"],
            "intent_page_views": bucket["intent_page_views"],
            "intent_honeypot_views": bucket["intent_honeypot_views"],
            "intent_proxy_views": bucket["intent_proxy_views"],
            "intent_deployer_views": bucket["intent_deployer_views"],
            "machine_doc_fetches": bucket["machine_doc_fetches"],
            "valid_unpaid_402_attempts": bucket["valid_unpaid_402_attempts"],
            "invalid_address_requests": bucket["invalid_address_requests"],
            "no_bytecode_requests": bucket["no_bytecode_requests"],
            "paid_requests": bucket["paid_requests"],
            "avg_duration_ms": (
                round(bucket["dur_sum"] / bucket["dur_n"]) if bucket["dur_n"] else 0
            ),
        }
        for hour, bucket in sorted(hourly_buckets.items())
    ]

    return {
        "total_requests": total,
        "paid_requests": paid,
        "storage_backend": storage_backend,
        "storage_path": storage_path,
        "storage_durable": storage_durable,
        "funnel": funnel,
        "stage_counts": dict(stage_counts),
        "top_paths": _top_items(path_counts, "path"),
        "top_hosts": _top_items(host_counts, "host"),
        "top_referers": _top_items(referer_counts, "referer"),
        "avg_duration_ms": round(duration_sum / duration_count) if duration_count else 0,
        "hourly": hourly,
        "recent": recent[-20:],
    }


def iter_jsonl_entries(log_path: str) -> Iterator[dict[str, Any]]:
    """Yield analytics entries from the legacy JSONL request log."""
    if not log_path or not os.path.exists(log_path):
        return

    with open(log_path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(entry, dict):
                yield entry


def _connect_sqlite(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def _entry_fingerprint(entry: dict[str, Any]) -> str:
    payload = json.dumps(entry, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _ensure_sqlite_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS request_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            path TEXT NOT NULL,
            status INTEGER NOT NULL,
            paid INTEGER NOT NULL,
            duration_ms INTEGER,
            user_agent TEXT NOT NULL,
            method TEXT NOT NULL,
            host TEXT NOT NULL,
            referer TEXT NOT NULL,
            request_id TEXT NOT NULL,
            funnel_stage TEXT NOT NULL,
            address TEXT,
            error_type TEXT,
            score INTEGER,
            level TEXT,
            raw_json TEXT NOT NULL,
            fingerprint TEXT
        )
        """
    )
    columns = {
        str(row[1])
        for row in conn.execute("PRAGMA table_info(request_events)")
    }
    if "fingerprint" not in columns:
        conn.execute("ALTER TABLE request_events ADD COLUMN fingerprint TEXT")

    rows = conn.execute(
        "SELECT id, raw_json FROM request_events WHERE fingerprint IS NULL OR fingerprint = ''"
    ).fetchall()
    for row_id, raw_json in rows:
        try:
            parsed = json.loads(raw_json)
        except json.JSONDecodeError:
            fingerprint = hashlib.sha256(raw_json.encode("utf-8")).hexdigest()
        else:
            if isinstance(parsed, dict):
                fingerprint = _entry_fingerprint(parsed)
            else:
                fingerprint = hashlib.sha256(raw_json.encode("utf-8")).hexdigest()
        conn.execute(
            "UPDATE request_events SET fingerprint = ? WHERE id = ?",
            (fingerprint, row_id),
        )

    conn.execute(
        """
        DELETE FROM request_events
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM request_events
            GROUP BY fingerprint
        )
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_request_events_fingerprint
        ON request_events(fingerprint)
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_request_events_ts ON request_events(ts)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_request_events_path ON request_events(path)"
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_request_events_funnel_stage
        ON request_events(funnel_stage)
        """
    )


def init_sqlite_store(db_path: str) -> None:
    """Create the durable analytics store if it does not exist yet."""
    if not db_path:
        return

    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with _connect_sqlite(db_path) as conn:
        _ensure_sqlite_schema(conn)


def append_sqlite_entry(db_path: str, entry: dict[str, Any]) -> bool:
    """Persist an analytics entry into SQLite."""
    if not db_path:
        return False

    payload = json.dumps(entry, separators=(",", ":"))
    fingerprint = _entry_fingerprint(entry)
    with _connect_sqlite(db_path) as conn:
        _ensure_sqlite_schema(conn)
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO request_events (
                ts, path, status, paid, duration_ms, user_agent, method, host,
                referer, request_id, funnel_stage, address, error_type, score,
                level, raw_json, fingerprint
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(entry.get("ts", "")),
                str(entry.get("path", "")),
                int(entry.get("status", 0)),
                1 if entry.get("paid") else 0,
                entry.get("duration_ms"),
                str(entry.get("user_agent", "")),
                str(entry.get("method", "")),
                str(entry.get("host", "")),
                str(entry.get("referer", "")),
                str(entry.get("request_id", "")),
                str(entry.get("funnel_stage", "")),
                str(entry.get("address", "")) or None,
                str(entry.get("error_type", "")) or None,
                entry.get("score"),
                str(entry.get("level", "")) or None,
                payload,
                fingerprint,
            ),
        )
        return cursor.rowcount == 1


def iter_sqlite_entries(db_path: str) -> Iterator[dict[str, Any]]:
    """Yield analytics entries from the durable SQLite store."""
    if not db_path or not os.path.exists(db_path):
        return

    with _connect_sqlite(db_path) as conn:
        cursor = conn.execute(
            "SELECT raw_json FROM request_events ORDER BY id ASC"
        )
        for (raw_json,) in cursor:
            try:
                entry = json.loads(raw_json)
            except json.JSONDecodeError:
                continue
            if isinstance(entry, dict):
                yield entry
