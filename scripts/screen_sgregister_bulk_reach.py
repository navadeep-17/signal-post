#!/usr/bin/env python3
"""Screen DiBK SGregister v2 bulk data for exact-org Signalpost reach.

Research-only. The SGregister v2 bulk endpoint returns every centrally approved
enterprise in one response. Exact 9-digit organization number is the only join
key. Website/email/phone values are candidates only; no production claims are
emitted from this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

ORG_RE = re.compile(r"^\d{9}$")


def normalize_org(value: Any) -> str | None:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits if ORG_RE.fullmatch(digits) else None


def company_org(row: dict[str, Any]) -> str:
    for key in ("organisation_number", "organization_number", "orgnr", "org_number"):
        org = normalize_org(row.get(key))
        if org:
            return org
    raise ValueError(f"company row has no exact 9-digit organisation number: {row!r}")


def read_companies(path: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError("company JSONL rows must be objects")
        org = company_org(row)
        if org in result:
            raise ValueError(f"duplicate company orgnr {org}")
        result[org] = row
    if not result:
        raise ValueError("empty company cohort")
    return result


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_source(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("enterprises"), list):
        raise ValueError("expected SGregister v2 object with enterprises array")

    records: dict[str, dict[str, Any]] = {}
    malformed_org_rows = 0
    duplicate_org_rows = 0
    source_rows = 0

    for item in payload["enterprises"]:
        if not isinstance(item, dict):
            continue
        source_rows += 1
        org = normalize_org(item.get("organizational_number"))
        if org is None:
            malformed_org_rows += 1
            continue

        status = item.get("status") if isinstance(item.get("status"), dict) else {}
        areas = item.get("valid_approval_areas")
        if not isinstance(areas, list):
            areas = []
        area_rows = []
        for area in areas:
            if not isinstance(area, dict):
                continue
            area_rows.append(
                {
                    "function": clean_text(area.get("function")),
                    "subject_area": clean_text(area.get("subject_area")),
                    "grade": clean_text(area.get("grade")),
                }
            )

        row = {
            "organisation_number": org,
            "name": clean_text(item.get("name")),
            "website": clean_text(item.get("www")),
            "email": clean_text(item.get("email")),
            "phone": clean_text(item.get("phone")),
            "approved": status.get("approved") is True,
            "approval_period_to": clean_text(status.get("approval_period_to")),
            "approval_certificate": clean_text(status.get("approval_certificate")),
            "approval_areas": area_rows,
        }
        if org in records:
            duplicate_org_rows += 1
            old = records[org]
            # SGregister should be unique by orgnr. Keep the first identity row,
            # but merge non-empty contact/area data for audit robustness.
            for key in ("website", "email", "phone", "approval_period_to", "approval_certificate"):
                if not old.get(key) and row.get(key):
                    old[key] = row[key]
            old["approved"] = bool(old.get("approved") or row.get("approved"))
            old["approval_areas"] = old.get("approval_areas", []) + row.get("approval_areas", [])
        else:
            records[org] = row

    return {
        "source_rows": source_rows,
        "unique_orgs": len(records),
        "malformed_org_rows": malformed_org_rows,
        "duplicate_org_rows": duplicate_org_rows,
        "records": records,
    }


def _date_on_or_after(value: str | None, today: date) -> bool:
    if not value:
        return False
    try:
        return date.fromisoformat(value) >= today
    except ValueError:
        return False


def cohort_metrics(
    companies: dict[str, dict[str, Any]],
    records: dict[str, dict[str, Any]],
    *,
    today: date,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    hit_orgs = sorted(set(companies) & set(records))
    hits = {org: records[org] for org in hit_orgs}
    rows = list(hits.values())

    blank_input_website_with_candidate = 0
    for org, row in hits.items():
        input_website = clean_text(companies[org].get("website"))
        if not input_website and row.get("website"):
            blank_input_website_with_candidate += 1

    metrics = {
        "companies": len(companies),
        "exact_company_hits": len(rows),
        "reach": round(len(rows) / len(companies), 6),
        "approved_true_companies": sum(row["approved"] for row in rows),
        "approval_current_through_today_companies": sum(
            _date_on_or_after(row.get("approval_period_to"), today) for row in rows
        ),
        "website_candidate_companies": sum(bool(row.get("website")) for row in rows),
        "email_candidate_companies": sum(bool(row.get("email")) for row in rows),
        "phone_candidate_companies": sum(bool(row.get("phone")) for row in rows),
        "website_and_email_candidate_companies": sum(
            bool(row.get("website")) and bool(row.get("email")) for row in rows
        ),
        "blank_input_website_gains_candidate": blank_input_website_with_candidate,
        "companies_with_approval_areas": sum(bool(row.get("approval_areas")) for row in rows),
    }
    return metrics, hits


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-json", required=True, type=Path)
    parser.add_argument("--companies-100", required=True, type=Path)
    parser.add_argument("--companies-1000", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--today", default=date.today().isoformat())
    args = parser.parse_args()

    today = date.fromisoformat(args.today)
    companies_100 = read_companies(args.companies_100)
    companies_1000 = read_companies(args.companies_1000)
    if not set(companies_100).issubset(companies_1000):
        raise SystemExit("consumed 100 must be a subset of consumed 1000")

    source = parse_source(args.source_json)
    metrics_100, _ = cohort_metrics(companies_100, source["records"], today=today)
    metrics_1000, hits_1000 = cohort_metrics(companies_1000, source["records"], today=today)

    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    with (output / "matched-companies-1000.jsonl").open("w", encoding="utf-8") as handle:
        for org in sorted(hits_1000):
            handle.write(json.dumps(hits_1000[org], ensure_ascii=False, sort_keys=True) + "\n")

    report = {
        "source": "DiBK SGregister API v2 bulk enterprises",
        "screen_type": "bulk_exact_org_central_approval",
        "source_bytes": args.source_json.stat().st_size,
        "source_sha256": sha256_file(args.source_json),
        "source_rows": source["source_rows"],
        "unique_orgs": source["unique_orgs"],
        "malformed_org_rows": source["malformed_org_rows"],
        "duplicate_org_rows": source["duplicate_org_rows"],
        "cohorts": {
            "consumed_100": metrics_100,
            "consumed_1000": metrics_1000,
        },
        "external_requests": 1,
        "api_access_status": "OPEN_FREE_NO_REGISTRATION",
        "reuse_rights_status": "UNRESOLVED_FOR_PERSISTENT_REUSE",
        "production_publication_enabled": False,
        "notes": [
            "Exact 9-digit organizational_number is the only company join key.",
            "SGregister documentation says the API is open/free but encourages direct or regular lookup rather than permanent storage.",
            "No explicit reuse license was established for production persistence during this research screen.",
            "Website/email/phone values are candidates only until Signalpost verification/publication policy is decided.",
            "No production code or fresh evaluator cohort is touched.",
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
