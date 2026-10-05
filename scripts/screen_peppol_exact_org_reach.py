#!/usr/bin/env python3
"""Screen the Peppol Directory BusinessCard export for exact Norwegian org numbers.

Research-only source qualification. No Signalpost production claims are emitted.

The official Peppol Directory CSV exporter has stable columns including:
Participant ID, Names (per-row), Websites, Contact email, Registration date.
Norwegian organisations are accepted only when the participant identifier uses
ISO 6523 scheme 0192 and contains one exact 9-digit value.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import re
import urllib.parse
from pathlib import Path
from typing import Any, Iterable

PARTICIPANT_RE = re.compile(
    r"^(?:iso6523-actorid-upis::)?0192:(\d{9})$",
    re.IGNORECASE,
)
EXPECTED_COLUMNS = {
    "Participant ID",
    "Names (per-row)",
    "Country code",
    "Websites",
    "Contact email",
    "Registration date",
}


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


def participant_org(value: str) -> str | None:
    decoded = urllib.parse.unquote(str(value or "").strip())
    match = PARTICIPANT_RE.fullmatch(decoded)
    return match.group(1) if match else None


def split_multivalue(value: str | None) -> list[str]:
    if value is None:
        return []
    return sorted({part.strip() for part in str(value).splitlines() if part.strip()})


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def iter_business_rows(path: Path) -> Iterable[dict[str, str]]:
    with gzip.open(path, mode="rt", encoding="iso-8859-1", newline="") as handle:
        reader = csv.DictReader(handle)
        actual = set(reader.fieldnames or [])
        missing = EXPECTED_COLUMNS - actual
        if missing:
            raise ValueError(f"Peppol CSV missing expected columns: {sorted(missing)}")
        for row in reader:
            yield {str(k): str(v or "") for k, v in row.items()}


def scan(path: Path, cohorts: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    all_targets: set[str] = set()
    for companies in cohorts.values():
        all_targets.update(companies)

    matches: dict[str, dict[str, Any]] = {
        org: {
            "organisation_number": org,
            "rows": 0,
            "participant_ids": set(),
            "names": set(),
            "websites": set(),
            "emails": set(),
            "registration_dates": set(),
            "country_codes": set(),
        }
        for org in all_targets
    }

    source_rows = 0
    norwegian_0192_rows = 0
    malformed_0192_rows = 0
    target_rows = 0
    for row in iter_business_rows(path):
        source_rows += 1
        pid_raw = row.get("Participant ID", "")
        decoded = urllib.parse.unquote(pid_raw.strip())
        if "0192:" not in decoded.lower():
            continue
        org = participant_org(pid_raw)
        if org is None:
            malformed_0192_rows += 1
            continue
        norwegian_0192_rows += 1
        if org not in all_targets:
            continue
        target_rows += 1
        hit = matches[org]
        hit["rows"] += 1
        hit["participant_ids"].add(decoded)
        hit["names"].update(split_multivalue(row.get("Names (per-row)")))
        hit["websites"].update(split_multivalue(row.get("Websites")))
        hit["emails"].update(split_multivalue(row.get("Contact email")))
        hit["registration_dates"].update(split_multivalue(row.get("Registration date")))
        hit["country_codes"].update(split_multivalue(row.get("Country code")))

    serial: dict[str, dict[str, Any]] = {}
    for org, row in matches.items():
        serial[org] = {
            **row,
            "participant_ids": sorted(row["participant_ids"]),
            "names": sorted(row["names"]),
            "websites": sorted(row["websites"]),
            "emails": sorted(row["emails"]),
            "registration_dates": sorted(row["registration_dates"]),
            "country_codes": sorted(row["country_codes"]),
        }

    cohort_reports: dict[str, Any] = {}
    for cohort_name, companies in cohorts.items():
        rows = [serial[org] for org in companies]
        participant_hits = [r for r in rows if r["rows"] > 0]
        website_hits = [r for r in rows if r["websites"]]
        email_hits = [r for r in rows if r["emails"]]
        cohort_reports[cohort_name] = {
            "companies": len(rows),
            "participant_hits": len(participant_hits),
            "participant_reach": round(len(participant_hits) / len(rows), 6),
            "website_candidate_companies": len(website_hits),
            "website_candidate_reach": round(len(website_hits) / len(rows), 6),
            "email_candidate_companies": len(email_hits),
            "email_candidate_reach": round(len(email_hits) / len(rows), 6),
        }

    return {
        "source_rows": source_rows,
        "norwegian_0192_rows": norwegian_0192_rows,
        "malformed_0192_rows": malformed_0192_rows,
        "target_rows": target_rows,
        "matches": serial,
        "cohorts": cohort_reports,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--export-gz", required=True, type=Path)
    parser.add_argument("--companies-100", required=True, type=Path)
    parser.add_argument("--companies-1000", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    cohorts = {
        "consumed_100": read_companies(args.companies_100),
        "consumed_1000": read_companies(args.companies_1000),
    }
    if not set(cohorts["consumed_100"]).issubset(cohorts["consumed_1000"]):
        raise SystemExit("consumed 100 must be a subset of consumed 1000")

    result = scan(args.export_gz, cohorts)
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)

    matches_path = output / "matched-companies.jsonl"
    with matches_path.open("w", encoding="utf-8") as handle:
        for org in sorted(result["matches"]):
            row = result["matches"][org]
            if row["rows"]:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    report = {
        "source": "Peppol Directory BusinessCard CSV export",
        "screen_type": "exact_no_org_participant_0192",
        "export_bytes": args.export_gz.stat().st_size,
        "export_sha256": sha256_file(args.export_gz),
        "source_rows": result["source_rows"],
        "norwegian_0192_rows": result["norwegian_0192_rows"],
        "malformed_0192_rows": result["malformed_0192_rows"],
        "target_rows": result["target_rows"],
        "cohorts": result["cohorts"],
        "external_requests": 1,
        "production_publication_enabled": False,
        "reuse_rights_status": "UNRESOLVED_FOR_DIRECTORY_DATA",
        "notes": [
            "Only participant scheme 0192 with one exact 9-digit value establishes a target match.",
            "Website and email values are source candidates only, not Signalpost publication proof.",
            "No production promotion is allowed until directory-data reuse rights are explicitly cleared.",
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
