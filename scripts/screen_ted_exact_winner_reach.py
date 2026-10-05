#!/usr/bin/env python3
"""Screen TED procurement winner data against an already-consumed cohort.

Research-only. This script does not emit Signalpost production claims.

Precision rules:
- only TED's winner-identifier field can establish a target hit;
- organisation numbers must exact-match a supplied 9-digit target;
- notice-level website/email values are associated with a target only when the
  notice exposes exactly one Norwegian-looking 9-digit winner identifier and it
  is the target. Multi-winner notices still count as award/activity hits, but
  their contact metadata is deliberately not attributed to a specific winner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

TED_SEARCH_URL = "https://api.ted.europa.eu/v3/notices/search"
ORG_RE = re.compile(r"(?<!\d)(\d{9})(?!\d)")
FIELDS = [
    "publication-number",
    "notice-title",
    "publication-date",
    "winner-identifier",
    "winner-name",
    "winner-internet-address",
    "winner-email",
    "winner-decision-date",
]


def normalize_org(value: Any) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(digits) != 9:
        raise ValueError(f"invalid Norwegian organisation number: {value!r}")
    return digits


def company_org(row: dict[str, Any]) -> str:
    for key in ("organisation_number", "organization_number", "orgnr", "org_number"):
        if row.get(key) is not None:
            return normalize_org(row[key])
    raise ValueError(f"company row has no organisation number: {row!r}")


def read_companies(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError("company JSONL rows must be objects")
        org = company_org(row)
        if org in seen:
            raise ValueError(f"duplicate target organisation number: {org}")
        seen.add(org)
        rows.append(row)
    if not rows:
        raise ValueError("empty company cohort")
    return rows


def exact_orgs(value: Any) -> set[str]:
    out: set[str] = set()
    for scalar in iter_scalars(value):
        out.update(ORG_RE.findall(scalar))
    return out


def iter_scalars(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for child in value.values():
            yield from iter_scalars(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_scalars(child)
    elif value is not None:
        yield str(value)


def build_winner_query(orgs: Iterable[str]) -> str:
    normalized = [normalize_org(org) for org in orgs]
    if not normalized:
        raise ValueError("TED query requires at least one organisation number")
    return f"winner-identifier IN ({' '.join(normalized)})"


def _extract_notice_list(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    for key in ("notices", "results", "items", "content"):
        value = payload.get(key)
        if isinstance(value, list) and all(isinstance(x, dict) for x in value):
            return value
    # Tolerant fallback for minor response-shape changes.
    for value in payload.values():
        if isinstance(value, list) and value and all(isinstance(x, dict) for x in value):
            if any("winner-identifier" in json.dumps(x, ensure_ascii=False) for x in value[:3]):
                return value
    return []


def field_value(notice: dict[str, Any], field: str) -> Any:
    if field in notice:
        return notice[field]
    fields = notice.get("fields")
    if isinstance(fields, dict) and field in fields:
        return fields[field]
    return None


def field_strings(notice: dict[str, Any], field: str) -> list[str]:
    value = field_value(notice, field)
    return [s.strip() for s in iter_scalars(value) if s.strip()]


def parse_date(value: str) -> date | None:
    candidate = value.strip()
    if not candidate:
        return None
    for parser in (
        lambda s: datetime.fromisoformat(s.replace("Z", "+00:00")).date(),
        lambda s: datetime.strptime(s[:10], "%Y-%m-%d").date(),
        lambda s: datetime.strptime(s[:8], "%Y%m%d").date(),
    ):
        try:
            return parser(candidate)
        except (TypeError, ValueError):
            pass
    return None


def analyse_notice(notice: dict[str, Any], targets: set[str], recent_since: date) -> dict[str, Any]:
    winner_id_values = field_strings(notice, "winner-identifier")
    winner_orgs = exact_orgs(winner_id_values)
    target_orgs = sorted(winner_orgs & targets)

    dates: list[date] = []
    raw_dates: list[str] = []
    for field in ("winner-decision-date", "publication-date"):
        for raw in field_strings(notice, field):
            raw_dates.append(raw)
            parsed = parse_date(raw)
            if parsed:
                dates.append(parsed)
    recent = any(d >= recent_since for d in dates)

    unambiguous_single_winner = len(winner_orgs) == 1 and len(target_orgs) == 1
    websites = field_strings(notice, "winner-internet-address") if unambiguous_single_winner else []
    emails = field_strings(notice, "winner-email") if unambiguous_single_winner else []

    return {
        "target_orgs": target_orgs,
        "winner_orgs": sorted(winner_orgs),
        "recent": recent,
        "dates": raw_dates,
        "publication_numbers": field_strings(notice, "publication-number"),
        "titles": field_strings(notice, "notice-title"),
        "winner_names": field_strings(notice, "winner-name"),
        "websites": websites,
        "emails": emails,
        "unambiguous_single_winner": unambiguous_single_winner,
    }


def _post_search(query: str, page: int, limit: int, timeout: float) -> tuple[bytes, dict[str, Any]]:
    request_body = {
        "query": query,
        "fields": FIELDS,
        "page": page,
        "limit": limit,
        "checkQuerySyntax": True,
        "paginationMode": "PAGE_NUMBER",
    }
    encoded = json.dumps(request_body, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        TED_SEARCH_URL,
        data=encoded,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Signalpost-research-source-screen/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read()
        raise RuntimeError(f"TED HTTP {exc.code}: {body[:2000].decode('utf-8', errors='replace')}") from exc
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise RuntimeError("TED response was not a JSON object")
    return body, payload


def _total_hits(payload: dict[str, Any]) -> int | None:
    for key in ("totalNoticeCount", "total", "totalCount", "count"):
        value = payload.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return None


def chunks(values: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--companies", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--chunk-size", type=int, default=25)
    parser.add_argument("--page-size", type=int, default=250)
    parser.add_argument("--max-requests", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--recent-since", default="2021-10-05")
    args = parser.parse_args()

    if not (1 <= args.chunk_size <= 100):
        raise SystemExit("--chunk-size must be in 1..100")
    if not (1 <= args.page_size <= 250):
        raise SystemExit("--page-size must be in 1..250")
    if args.max_requests < 1:
        raise SystemExit("--max-requests must be positive")

    recent_since = date.fromisoformat(args.recent_since)
    companies = read_companies(args.companies)
    target_rows = {company_org(row): row for row in companies}
    target_orgs = sorted(target_rows)
    targets = set(target_orgs)

    output = args.output_dir
    raw_dir = output / "raw"
    output.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    per_company: dict[str, dict[str, Any]] = {
        org: {
            "organisation_number": org,
            "name": target_rows[org].get("name"),
            "award_notices": 0,
            "recent_award_notices": 0,
            "website_candidates": [],
            "email_candidates": [],
            "publication_numbers": [],
            "ambiguous_multiwinner_notices": 0,
        }
        for org in target_orgs
    }

    request_count = 0
    raw_hashes: list[str] = []
    queries: list[str] = []
    notices_seen = 0
    truncated = False

    for chunk_index, org_chunk in enumerate(chunks(target_orgs, args.chunk_size), start=1):
        query = build_winner_query(org_chunk)
        queries.append(query)
        page = 1
        while True:
            if request_count >= args.max_requests:
                truncated = True
                break
            body, payload = _post_search(query, page, args.page_size, args.timeout)
            request_count += 1
            raw_path = raw_dir / f"chunk-{chunk_index:02d}-page-{page:02d}.json"
            raw_path.write_bytes(body)
            raw_hashes.append(hashlib.sha256(body).hexdigest())

            notices = _extract_notice_list(payload)
            notices_seen += len(notices)
            for notice in notices:
                analysis = analyse_notice(notice, targets, recent_since)
                for org in analysis["target_orgs"]:
                    row = per_company[org]
                    row["award_notices"] += 1
                    if analysis["recent"]:
                        row["recent_award_notices"] += 1
                    if analysis["unambiguous_single_winner"]:
                        row["website_candidates"].extend(analysis["websites"])
                        row["email_candidates"].extend(analysis["emails"])
                    elif len(analysis["winner_orgs"]) > 1:
                        row["ambiguous_multiwinner_notices"] += 1
                    row["publication_numbers"].extend(analysis["publication_numbers"])

            total = _total_hits(payload)
            if len(notices) < args.page_size:
                break
            if total is not None and page * args.page_size >= total:
                break
            page += 1
        if truncated:
            break

    for row in per_company.values():
        for key in ("website_candidates", "email_candidates", "publication_numbers"):
            row[key] = sorted(set(row[key]))

    rows = list(per_company.values())
    hits = [r for r in rows if r["award_notices"]]
    recent_hits = [r for r in rows if r["recent_award_notices"]]
    website_hits = [r for r in rows if r["website_candidates"]]
    email_hits = [r for r in rows if r["email_candidates"]]

    rows_path = output / "rows.jsonl"
    with rows_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    report = {
        "source": "TED Search API v3",
        "screen_type": "consumed_exact_winner_identifier",
        "companies": len(rows),
        "requests": request_count,
        "max_requests": args.max_requests,
        "chunk_size": args.chunk_size,
        "notices_seen": notices_seen,
        "companies_with_award": len(hits),
        "companies_with_recent_award": len(recent_hits),
        "companies_with_unambiguous_website_candidate": len(website_hits),
        "companies_with_unambiguous_email_candidate": len(email_hits),
        "recent_since": recent_since.isoformat(),
        "truncated": truncated,
        "queries": queries,
        "raw_response_sha256": raw_hashes,
        "production_publication_enabled": False,
        "notes": [
            "Only winner-identifier establishes a company hit.",
            "Website/email candidates are retained only for notices with exactly one 9-digit winner identifier.",
            "This screen does not publish claims or verify candidate websites.",
        ],
    }
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
