#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ENDPOINT = "https://data.brreg.no/enhetsregisteret/api/oppdateringer/enheter"
ACCEPT = "application/vnd.brreg.enhetsregisteret.oppdatering.enhet.v1+json"
USER_AGENT = "signalpost-brreg-change-screen/1.0 (+https://github.com/navadeep-17/signal-post)"
MAX_RESPONSE_BYTES = 25_000_000


def _org(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("organisation_number")
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(digits) != 9:
        raise ValueError(f"Invalid Norwegian organisation number: {value!r}")
    return digits


def _read_companies(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"Expected object row in {path}")
        org = _org(row)
        if org in seen:
            raise ValueError(f"Duplicate organisation number: {org}")
        seen.add(org)
        rows.append(row)
    if not rows:
        raise ValueError("Company cohort is empty")
    return rows


def _parse_datetime(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def build_url(organisation_numbers: list[str], *, size: int = 10_000) -> str:
    orgs = [_org(value) for value in organisation_numbers]
    if len(orgs) != len(set(orgs)):
        raise ValueError("organisation_numbers contains duplicates")
    if not orgs:
        raise ValueError("organisation_numbers cannot be empty")
    if size < 1 or size > 10_000:
        raise ValueError("size must be between 1 and 10000")
    query = urllib.parse.urlencode(
        {
            "organisasjonsnummer": ",".join(orgs),
            "includeChanges": "true",
            "size": str(size),
            "sort": "id,DESC",
        }
    )
    return ENDPOINT + "?" + query


def extract_events(payload: dict[str, Any]) -> list[dict[str, Any]]:
    embedded = payload.get("_embedded") if isinstance(payload, dict) else None
    rows = (embedded or {}).get("oppdaterteEnheter") if isinstance(embedded, dict) else None
    if rows is None:
        return []
    if not isinstance(rows, list):
        raise ValueError("Expected _embedded.oppdaterteEnheter to be a list")
    return [row for row in rows if isinstance(row, dict)]


def analyse_payload(
    payload: dict[str, Any],
    companies: list[dict[str, Any]],
    *,
    as_of: datetime,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    targets = {_org(row): row for row in companies}
    events = extract_events(payload)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unexpected_orgs: set[str] = set()
    for event in events:
        org = _org(event.get("organisasjonsnummer"))
        if org not in targets:
            unexpected_orgs.add(org)
            continue
        grouped[org].append(event)

    rows: list[dict[str, Any]] = []
    global_paths: Counter[str] = Counter()
    global_types: Counter[str] = Counter()
    for org, company in targets.items():
        company_events = grouped.get(org, [])
        parsed: list[tuple[datetime | None, dict[str, Any]]] = [
            (_parse_datetime(event.get("dato")), event) for event in company_events
        ]
        parsed.sort(key=lambda item: item[0] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

        recent_365 = 0
        recent_730 = 0
        paths: Counter[str] = Counter()
        types: Counter[str] = Counter()
        for timestamp, event in parsed:
            if timestamp is not None:
                age_days = (as_of - timestamp).total_seconds() / 86400
                if 0 <= age_days <= 365:
                    recent_365 += 1
                if 0 <= age_days <= 730:
                    recent_730 += 1
            event_type = str(event.get("endringstype") or "unknown")
            types[event_type] += 1
            global_types[event_type] += 1
            changes = event.get("endringer") or []
            if isinstance(changes, list):
                for change in changes:
                    if not isinstance(change, dict):
                        continue
                    path = str(change.get("path") or "").strip() or "(unknown)"
                    paths[path] += 1
                    global_paths[path] += 1

        latest_timestamp = parsed[0][0] if parsed else None
        latest_event = parsed[0][1] if parsed else None
        rows.append(
            {
                "organisation_number": org,
                "name": company.get("name"),
                "events": len(company_events),
                "has_history": bool(company_events),
                "events_last_365_days": recent_365,
                "events_last_730_days": recent_730,
                "latest_update_at": latest_timestamp.isoformat().replace("+00:00", "Z") if latest_timestamp else None,
                "latest_update_type": (latest_event or {}).get("endringstype") if latest_event else None,
                "change_paths": dict(paths.most_common()),
                "event_types": dict(types.most_common()),
            }
        )

    page = payload.get("page") if isinstance(payload, dict) else {}
    total_elements = (page or {}).get("totalElements") if isinstance(page, dict) else None
    report = {
        "source": "brreg_enhetsregister_change_feed",
        "endpoint": ENDPOINT,
        "companies": len(rows),
        "events_returned": len(events),
        "reported_total_elements": total_elements,
        "companies_with_history": sum(row["has_history"] for row in rows),
        "companies_with_update_last_365_days": sum(row["events_last_365_days"] > 0 for row in rows),
        "companies_with_update_last_730_days": sum(row["events_last_730_days"] > 0 for row in rows),
        "history_reach_rate": round(sum(row["has_history"] for row in rows) / len(rows), 6),
        "recent_365_reach_rate": round(sum(row["events_last_365_days"] > 0 for row in rows) / len(rows), 6),
        "recent_730_reach_rate": round(sum(row["events_last_730_days"] > 0 for row in rows) / len(rows), 6),
        "unexpected_organisation_numbers": sorted(unexpected_orgs),
        "top_change_paths": dict(global_paths.most_common(30)),
        "event_types": dict(global_types.most_common()),
        "as_of": as_of.isoformat().replace("+00:00", "Z"),
        "production_connector_implemented": False,
        "claim_boundary": (
            "Screen-only exact-org BRREG registry update events. A registry update is not treated as "
            "company news; source-specific projection must label it as an official registry change."
        ),
    }
    return rows, report


def fetch_payload(url: str, *, timeout: float) -> tuple[bytes, str]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": ACCEPT, "Accept-Encoding": "identity"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        final_url = response.geturl()
    if len(raw) > MAX_RESPONSE_BYTES:
        raise RuntimeError(f"BRREG change-feed response exceeds {MAX_RESPONSE_BYTES} bytes")
    return raw, final_url


def main() -> None:
    parser = argparse.ArgumentParser(description="Screen exact-org reach of BRREG entity change history.")
    parser.add_argument("--companies", required=True)
    parser.add_argument("--rows-output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--raw-output", required=True)
    parser.add_argument("--as-of", default="2026-10-01T00:00:00Z")
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    companies_path = Path(args.companies)
    companies = _read_companies(companies_path)
    as_of = _parse_datetime(args.as_of)
    if as_of is None:
        raise SystemExit("--as-of must be an ISO-8601 datetime")

    url = build_url([_org(row) for row in companies])
    raw, final_url = fetch_payload(url, timeout=args.timeout)
    payload = json.loads(raw.decode("utf-8"))
    rows, report = analyse_payload(payload, companies, as_of=as_of)
    report.update(
        {
            "request_count": 1,
            "request_url": final_url,
            "response_bytes": len(raw),
            "response_sha256": hashlib.sha256(raw).hexdigest(),
            "cohort_sha256": hashlib.sha256(companies_path.read_bytes()).hexdigest(),
        }
    )

    raw_path = Path(args.raw_output)
    rows_path = Path(args.rows_output)
    report_path = Path(args.report)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    rows_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(raw)
    with rows_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
