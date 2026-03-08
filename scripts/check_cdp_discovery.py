#!/usr/bin/env python3
"""Check whether Augur appears in Coinbase's public x402 discovery feed.

Usage:
    python scripts/check_cdp_discovery.py
    python scripts/check_cdp_discovery.py --resource https://augurrisk.com/analyze
    python scripts/check_cdp_discovery.py --needle augurrisk --needle /analyze
    python scripts/check_cdp_discovery.py --limit 100 --max-pages 5
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


DEFAULT_FEED_URL = "https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources"
DEFAULT_RESOURCE = "https://augurrisk.com/analyze"
DEFAULT_NEEDLES = ["augur", "augurrisk", "risk-api", "augurrisk.com"]
DEFAULT_LIMIT = 100
DEFAULT_MAX_PAGES = 200
TIMEOUT_SECONDS = 20


def fetch_page(
    feed_url: str,
    limit: int,
    offset: int,
    max_retries: int,
    retry_delay_seconds: float,
) -> dict:
    query = urllib.parse.urlencode({"limit": limit, "offset": offset})
    url = f"{feed_url}?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": "risk-api/check_cdp_discovery"})

    for attempt in range(max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == max_retries:
                raise
            time.sleep(retry_delay_seconds * (attempt + 1))

    raise RuntimeError("unreachable")


def classify_item(item: dict, resource: str, needles: list[str]) -> str | None:
    resource_value = str(item.get("resource", ""))
    if resource_value.lower() == resource.lower():
        return "exact_resource"

    haystack = json.dumps(item, sort_keys=True).lower()
    if any(needle.lower() in haystack for needle in needles):
        return "keyword_match"

    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Check Coinbase x402 public discovery feed")
    parser.add_argument(
        "--feed-url",
        default=DEFAULT_FEED_URL,
        help=f"Discovery feed base URL (default: {DEFAULT_FEED_URL})",
    )
    parser.add_argument(
        "--resource",
        default=DEFAULT_RESOURCE,
        help=f"Primary resource URL to search for (default: {DEFAULT_RESOURCE})",
    )
    parser.add_argument(
        "--needle",
        action="append",
        default=[],
        help="Additional case-insensitive search string (repeatable)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Items per page (default: {DEFAULT_LIMIT})",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=DEFAULT_MAX_PAGES,
        help=f"Maximum pages to scan before stopping (default: {DEFAULT_MAX_PAGES})",
    )
    parser.add_argument(
        "--page-delay",
        type=float,
        default=0.25,
        help="Delay between page requests in seconds (default: 0.25)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=4,
        help="Retries per page on HTTP 429 (default: 4)",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=5.0,
        help="Base retry delay in seconds after HTTP 429 (default: 5.0)",
    )
    args = parser.parse_args()

    needles = DEFAULT_NEEDLES + args.needle
    offset = 0
    pages_scanned = 0
    items_scanned = 0
    exact_matches: list[dict] = []
    keyword_matches: list[dict] = []
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    try:
        while pages_scanned < args.max_pages:
            payload = fetch_page(
                args.feed_url,
                args.limit,
                offset,
                args.max_retries,
                args.retry_delay,
            )
            items = payload.get("items", [])
            pages_scanned += 1
            items_scanned += len(items)

            for item in items:
                match_type = classify_item(item, args.resource, needles)
                if match_type == "exact_resource":
                    exact_matches.append(item)
                elif match_type == "keyword_match":
                    keyword_matches.append(item)

            if len(items) < args.limit:
                break
            offset += args.limit
            if args.page_delay > 0:
                time.sleep(args.page_delay)
    except urllib.error.HTTPError as exc:
        print(f"[{ts}] FAIL: HTTP {exc.code} from discovery feed", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"[{ts}] FAIL: connection error: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"[{ts}] FAIL: unexpected error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"[{ts}] scanned_pages={pages_scanned} scanned_items={items_scanned}")
    print(f"feed_url={args.feed_url}")
    print(f"resource={args.resource}")
    print(f"needles={', '.join(needles)}")

    if exact_matches:
        print(f"status=FOUND exact_matches={len(exact_matches)} keyword_matches={len(keyword_matches)}")
        for idx, match in enumerate(exact_matches, start=1):
            resource = match.get("resource", "")
            print(f"match[{idx}].resource={resource}")
            print(json.dumps(match, indent=2, sort_keys=True))
        sys.exit(0)

    print(f"status=NOT_FOUND keyword_matches={len(keyword_matches)}")
    for idx, match in enumerate(keyword_matches, start=1):
        resource = match.get("resource", "")
        print(f"related_match[{idx}].resource={resource}")
    sys.exit(2)


if __name__ == "__main__":
    main()
