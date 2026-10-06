#!/usr/bin/env python3
"""Aggregate exact-org Peppol Directory coverage for Norwegian companies.

Research-only source qualification. No Signalpost production claims are emitted.

Privacy/data-minimisation boundary:
- exact Norwegian participant scheme 0192 is the only identity join;
- contact fields are never read into the result model;
- raw names and raw website URLs are not persisted;
- the retained report contains only aggregate coverage counts;
- the source export is deleted by the workflow after screening.

This is deliberately a source-selection screen, not a production connector.
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
    "Websites",
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


def has_value(value: str | None) -> bool:
    if value is None:
        return False
    return any(part.strip() for part in str(value).splitlines())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def iter_business_rows(path: Path) -> Iterable[dict[str, str]]:
    with gzip.open(path, mode="rt", encoding="iso-8859-1", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        actual = set(reader.fieldnames or [])
        missing = EXPECTED_COLUMNS - actual
        if missing:
            raise ValueError(f"Peppol CSV missing expected columns: {sorted(missing)}")
        for row in reader:
            # Deliberately expose only fields needed for aggregate source selection.
            yield {
                "Participant ID": str(row.get("Participant ID") or ""),
                "Websites": str(row.get("Websites") or ""),
            }


def scan(path: Path, cohorts: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    all_targets: set[str] = set()
    for companies in cohorts.values():
        all_targets.update(companies)

    participant_hits: set[str] = set()
    website_hits: set[str] = set()

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
        participant_hits.add(org)
        if has_value(row.get("Websites")):
            website_hits.add(org)

    cohort_reports: dict[str, Any] = {}
    for cohort_name, companies in cohorts.items():
        orgs = set(companies)
        p = orgs & participant_hits
        w = orgs & website_hits
        cohort_reports[cohort_name] = {
            "companies": len(orgs),
            "participant_hits": len(p),
            "participant_reach": round(len(p) / len(orgs), 6),
            "website_candidate_companies": len(w),
            "website_candidate_reach": round(len(w) / len(orgs), 6),
        }

    return {
        "source_rows": source_rows,
        "norwegian_0192_rows": norwegian_0192_rows,
        "malformed_0192_rows": malformed_0192_rows,
        "target_rows": target_rows,
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

    report = {
        "source": "Peppol Directory BusinessCard CSV export",
        "screen_type": "aggregate_exact_no_org_participant_0192",
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
        "privacy_boundary": {
            "contact_fields_retained": False,
            "raw_names_retained": False,
            "raw_websites_retained": False,
            "matched_org_lists_retained": False,
            "aggregate_counts_only": True,
        },
        "notes": [
            "Only participant scheme 0192 with one exact 9-digit value establishes a target match.",
            "Website presence is counted only as an aggregate candidate signal; raw URLs are not retained.",
            "Contact email/name/phone fields are not collected by this screen.",
            "No production promotion is allowed until directory-data reuse rights are explicitly cleared.",
            "Any later website candidate must independently pass Signalpost exact-company website verification.",
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
