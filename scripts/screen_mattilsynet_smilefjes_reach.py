#!/usr/bin/env python3
"""Research-only Mattilsynet Smilefjes exact-org reach screen.

The Smilefjes source describes inspections of establishments. Signalpost counts a
target company only when the source orgnummer exactly equals the target legal
organisation number. Even then, inspection facts remain scoped to the source's
specific tilsynsobjektid; no parent/subunit/group inheritance is permitted.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

ORG_RE = re.compile(r"^\d{9}$")


def normalize_org(value: Any) -> str | None:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits if ORG_RE.fullmatch(digits) else None


def parse_source_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not re.fullmatch(r"\d{8}", text):
        return None
    try:
        return date(int(text[4:8]), int(text[2:4]), int(text[0:2]))
    except ValueError:
        return None


def load_targets(path: Path) -> set[str]:
    targets: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        org = normalize_org(row.get("organisation_number"))
        if org is None:
            raise ValueError(f"target row has invalid organisation number: {row!r}")
        if org in targets:
            raise ValueError(f"duplicate target organisation number {org}")
        targets.add(org)
    if not targets:
        raise ValueError("empty target cohort")
    return targets


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_source(path: Path) -> tuple[list[dict[str, str]], dict[str, Any]]:
    rows: list[dict[str, str]] = []
    malformed_org_rows = 0
    malformed_date_rows = 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        required = {
            "tilsynsobjektid",
            "orgnummer",
            "navn",
            "tilsynid",
            "status",
            "dato",
            "total_karakter",
            "tilsynsbesoektype",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Smilefjes source missing required fields: {sorted(missing)}")

        for raw in reader:
            row = {str(key): str(value or "").strip() for key, value in raw.items()}
            org = normalize_org(row.get("orgnummer"))
            if org is None:
                malformed_org_rows += 1
                continue
            row["orgnummer"] = org
            parsed = parse_source_date(row.get("dato"))
            if parsed is None:
                malformed_date_rows += 1
                row["_parsed_date"] = ""
            else:
                row["_parsed_date"] = parsed.isoformat()
            rows.append(row)

    return rows, {
        "source_rows": len(rows),
        "malformed_org_rows_excluded": malformed_org_rows,
        "malformed_date_rows": malformed_date_rows,
    }


def _event(row: dict[str, str]) -> dict[str, Any]:
    return {
        "inspection_id": row.get("tilsynid") or None,
        "establishment_id": row.get("tilsynsobjektid") or None,
        "establishment_name": row.get("navn") or None,
        "inspection_date": row.get("_parsed_date") or None,
        "source_date_raw": row.get("dato") or None,
        "source_status_code": row.get("status") or None,
        "overall_grade_code": row.get("total_karakter") or None,
        "visit_type_code": row.get("tilsynsbesoektype") or None,
        "address": {
            "line1": row.get("adrlinje1") or None,
            "line2": row.get("adrlinje2") or None,
            "postal_code": row.get("postnr") or None,
            "postal_place": row.get("poststed") or None,
        },
    }


def screen(
    rows: list[dict[str, str]],
    targets: set[str],
    *,
    today: date,
    max_events_per_company: int = 3,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    by_org: dict[str, list[dict[str, str]]] = defaultdict(list)
    all_orgs: set[str] = set()
    all_establishments: set[str] = set()

    for row in rows:
        org = normalize_org(row.get("orgnummer"))
        if org is None:
            continue
        all_orgs.add(org)
        establishment = str(row.get("tilsynsobjektid") or "").strip()
        if establishment:
            all_establishments.add(establishment)
        if org in targets:
            by_org[org].append(row)

    cutoff_365 = today - timedelta(days=365)
    cutoff_730 = today - timedelta(days=730)
    matched: list[dict[str, Any]] = []
    recent_365 = 0
    recent_730 = 0
    dated_hits = 0
    grade_codes = Counter()

    for org in sorted(by_org):
        company_rows = by_org[org]
        dated_rows = [row for row in company_rows if row.get("_parsed_date")]
        dated_rows.sort(key=lambda row: (row["_parsed_date"], row.get("tilsynid", "")), reverse=True)
        latest_date = date.fromisoformat(dated_rows[0]["_parsed_date"]) if dated_rows else None
        if latest_date is not None:
            dated_hits += 1
            if latest_date >= cutoff_365:
                recent_365 += 1
            if latest_date >= cutoff_730:
                recent_730 += 1

        for row in company_rows:
            grade = str(row.get("total_karakter") or "").strip()
            if grade:
                grade_codes[grade] += 1

        establishments = sorted({
            str(row.get("tilsynsobjektid") or "").strip()
            for row in company_rows
            if str(row.get("tilsynsobjektid") or "").strip()
        })
        names = sorted({
            str(row.get("navn") or "").strip()
            for row in company_rows
            if str(row.get("navn") or "").strip()
        })

        matched.append(
            {
                "organisation_number": org,
                "exact_identity_basis": "Smilefjes.orgnummer == target legal organisation_number",
                "scope": "establishment_inspection_only",
                "inspection_rows": len(company_rows),
                "establishment_ids": establishments,
                "establishment_names": names,
                "latest_inspection_date": latest_date.isoformat() if latest_date else None,
                "recent_within_365_days": bool(latest_date and latest_date >= cutoff_365),
                "recent_within_730_days": bool(latest_date and latest_date >= cutoff_730),
                "latest_inspections": [_event(row) for row in dated_rows[:max_events_per_company]],
            }
        )

    report = {
        "source": "Mattilsynet Smilefjestilsyn complete CSV",
        "screen_type": "bulk_exact_org_establishment_inspection",
        "production_publication_enabled": False,
        "api_access_status": "OPEN_FREE_NO_REGISTRATION",
        "reuse_rights_status": "CC_BY_4_0",
        "reuse_attribution_required": True,
        "source_rows": len(rows),
        "unique_org_numbers_in_source": len(all_orgs),
        "unique_establishments_in_source": len(all_establishments),
        "target_companies": len(targets),
        "exact_target_company_hits": len(matched),
        "exact_target_reach": len(matched) / len(targets) if targets else 0.0,
        "companies_with_parseable_inspection_date": dated_hits,
        "companies_with_latest_inspection_within_365_days": recent_365,
        "companies_with_latest_inspection_within_730_days": recent_730,
        "observed_grade_code_counts_for_matched_rows": dict(sorted(grade_codes.items())),
        "external_requests": 1,
        "notes": [
            "Only exact equality between Smilefjes orgnummer and the target 9-digit legal organisation number counts.",
            "No parent, subunit, group, franchise, address or name-based inheritance is allowed.",
            "Every retained event remains scoped to its exact tilsynsobjektid establishment.",
            "Status and grade codes are preserved as source codes in this research screen; no adverse semantic interpretation is inferred here.",
            "The official Data.norge distribution is licensed CC BY 4.0 and requires source attribution.",
            "This consumed-only screen publishes no production claims and touches no fresh evaluator cohort.",
        ],
    }
    return report, matched


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-csv", required=True, type=Path)
    parser.add_argument("--companies", required=True, type=Path)
    parser.add_argument("--today", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    today = date.fromisoformat(args.today)
    rows, source_meta = load_source(args.source_csv)
    targets = load_targets(args.companies)
    report, matched = screen(rows, targets, today=today)
    report.update(source_meta)
    report["source_bytes"] = args.source_csv.stat().st_size
    report["source_sha256"] = sha256_file(args.source_csv)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "matched-companies.jsonl").write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
            for row in matched
        ),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
