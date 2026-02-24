#!/usr/bin/env python3
"""External health check for risk-api.

Run periodically (cron, Task Scheduler, or external monitor) to detect
when the API is down. Exits with code 1 on failure for easy integration
with monitoring tools.

Usage:
    python scripts/health_check.py
    python scripts/health_check.py --webhook https://hooks.slack.com/...
    python scripts/health_check.py --url https://custom-host/health

Environment:
    HEALTH_CHECK_URL     - Override the default health endpoint
    HEALTH_CHECK_WEBHOOK - Webhook URL for failure notifications
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import requests


DEFAULT_URL = "https://risk-api.life.conway.tech/health"
TIMEOUT_SECONDS = 15


def check_health(url: str) -> tuple[bool, str]:
    """Ping the health endpoint. Returns (ok, detail)."""
    try:
        resp = requests.get(url, timeout=TIMEOUT_SECONDS)
        if resp.status_code != 200:
            return False, f"status={resp.status_code} body={resp.text[:200]}"
        data = resp.json()
        if data.get("status") != "ok":
            return False, f"unexpected body: {data}"
        return True, f"ok ({resp.elapsed.total_seconds():.2f}s)"
    except requests.Timeout:
        return False, f"timeout after {TIMEOUT_SECONDS}s"
    except requests.ConnectionError as e:
        return False, f"connection error: {e}"
    except Exception as e:
        return False, f"unexpected error: {e}"


def notify_webhook(webhook_url: str, message: str) -> None:
    """Send failure alert to a webhook (Slack/Discord compatible)."""
    try:
        requests.post(
            webhook_url,
            json={"text": message, "content": message},
            timeout=10,
        )
    except Exception as e:
        print(f"[WARN] webhook notification failed: {e}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="risk-api health check")
    parser.add_argument(
        "--url",
        default=os.environ.get("HEALTH_CHECK_URL", DEFAULT_URL),
        help=f"Health endpoint URL (default: {DEFAULT_URL})",
    )
    parser.add_argument(
        "--webhook",
        default=os.environ.get("HEALTH_CHECK_WEBHOOK", ""),
        help="Webhook URL for failure alerts (Slack/Discord)",
    )
    args = parser.parse_args()

    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    ok, detail = check_health(args.url)

    if ok:
        print(f"[{ts}] OK: {detail}")
        sys.exit(0)
    else:
        msg = f"[{ts}] FAIL: risk-api health check failed — {detail}"
        print(msg, file=sys.stderr)
        if args.webhook:
            notify_webhook(args.webhook, msg)
        sys.exit(1)


if __name__ == "__main__":
    main()
