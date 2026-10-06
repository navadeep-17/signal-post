#!/usr/bin/env python3
"""Research-only exact-org eInnsyn recent public-record reach screen.

A target hit is counted only when:
1. the query is the exact quoted 9-digit organisation number,
2. eInnsyn returns a Journalpost inside the requested recent window, and
3. the returned public title (offentligTittel) itself contains that exact
   9-digit organisation number.

No result titles, entity IDs, company names, or matched org lists are persisted.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ORG_RE = re.compile(r"^\d{9}$")
API = "https://api.einnsyn.no/search"


def norm_org(value: Any) -> str | None:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits if ORG_RE.fullmatch(digits) else None


def load_targets(path: Path, *, limit: int | None = None) -> list[str]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        org = norm_org(row.get("organisation_number"))
        if not org:
            raise ValueError(f"invalid organisation number: {row!r}")
        rows.append(org)
    if len(rows) != len(set(rows)):
        raise ValueError("duplicate target organisation numbers")
    return rows[:limit] if limit is not None else rows


def title_has_exact_org(item: dict[str, Any], org: str) -> bool:
    title = str(item.get("offentligTittel") or "")
    return bool(re.search(rf"(?<!\d){re.escape(org)}(?!\d)", title))


def public_date(item: dict[str, Any]) -> str | None:
    for field in ("publisertDato", "journaldato", "dokumentetsDato"):
        value = str(item.get(field) or "").strip()
        if value:
            return value
    return None


def fetch_one(org: str, cutoff: str, *, timeout: float = 30.0) -> tuple[int, dict[str, Any], int]:
    params = {
        "query": f'"{org}"',
        "entity": "Journalpost",
        "limit": "1",
        "sortBy": "publisertDato",
        "sortOrder": "desc",
        "publisertDatoFrom": cutoff,
    }
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "Signalpost-research-source-screen/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            status = resp.status
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        status = exc.code
    try:
        data = json.loads(raw.decode("utf-8-sig")) if raw else {}
    except Exception:
        data = {}
    return status, data if isinstance(data, dict) else {}, len(raw)


def screen(
    targets: list[str],
    *,
    today: dt.date,
    lookback_days: int,
    delay_seconds: float,
) -> dict[str, Any]:
    cutoff = (today - dt.timedelta(days=lookback_days)).isoformat()

    requests = 0
    bytes_total = 0
    http_counts: dict[str, int] = {}
    exact_recent_hits = 0
    query_hits_without_title_org = 0
    empty_results = 0
    errors = 0
    result_has_date = 0

    for index, org in enumerate(targets):
        if index and delay_seconds > 0:
            time.sleep(delay_seconds)
        status, data, nbytes = fetch_one(org, cutoff)
        requests += 1
        bytes_total += nbytes
        http_counts[str(status)] = http_counts.get(str(status), 0) + 1

        if status != 200:
            errors += 1
            continue

        items = data.get("items")
        if not isinstance(items, list) or not items:
            empty_results += 1
            continue

        item = items[0] if isinstance(items[0], dict) else {}
        if public_date(item):
            result_has_date += 1
        if title_has_exact_org(item, org):
            exact_recent_hits += 1
        else:
            query_hits_without_title_org += 1

    n = len(targets)
    return {
        "screen_type": "einnsyn_recent_exact_org_public_title_reach",
        "companies": n,
        "lookback_days": lookback_days,
        "cutoff": cutoff,
        "exact_recent_public_record_companies": exact_recent_hits,
        "exact_recent_public_record_reach": round(exact_recent_hits / n, 6) if n else 0.0,
        "query_hits_without_exact_org_in_public_title": query_hits_without_title_org,
        "empty_results": empty_results,
        "results_with_public_date": result_has_date,
        "http_status_counts": dict(sorted(http_counts.items())),
        "request_errors": errors,
        "external_requests": requests,
        "response_bytes": bytes_total,
        "exact_hits_per_request": round(exact_recent_hits / requests, 6) if requests else 0.0,
        "publication_enabled": False,
        "reuse_rights_status": "UNRESOLVED_FOR_PRODUCTION_REUSE",
        "privacy_boundary": {
            "raw_titles_retained": False,
            "matched_org_lists_retained": False,
            "entity_ids_retained": False,
            "aggregate_counts_only": True,
        },
        "identity_rule": (
            "Exact quoted 9-digit query plus exact same 9-digit value in returned "
            "offentligTittel; name-only matches are never counted."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--companies", type=Path, required=True)
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--lookback-days", type=int, default=365)
    ap.add_argument("--delay-seconds", type=float, default=0.5)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()

    targets = load_targets(args.companies, limit=args.limit)
    if len(targets) != args.limit:
        raise SystemExit(f"expected {args.limit} companies, got {len(targets)}")

    report = screen(
        targets,
        today=dt.date(2026, 10, 6),
        lookback_days=args.lookback_days,
        delay_seconds=args.delay_seconds,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
