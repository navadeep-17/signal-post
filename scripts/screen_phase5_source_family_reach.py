#!/usr/bin/env python3
"""Consumed-only exact-organisation-number reach screen for Phase 5 source selection.

This script is deliberately NOT a production connector. It measures whether an already
rights-reviewed deterministic source contains exact organisation-number occurrences for a
frozen, already-consumed Signalpost cohort. It never emits publication-ready claims.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Iterable

ORG_RE = re.compile(r"(?<!\d)(?:NO\s*)?(\d{3})[\s.\-]?(\d{3})[\s.\-]?(\d{3})(?!\d)", re.I)


def normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def valid_org_number(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    if len(digits) != 9:
        return False
    nums = [int(ch) for ch in digits]
    weighted = sum(n * w for n, w in zip(nums[:8], (3, 2, 7, 6, 5, 4, 3, 2), strict=True))
    remainder = 11 - (weighted % 11)
    check = 0 if remainder == 11 else remainder
    return check != 10 and check == nums[8]


def extract_org_numbers(value: object) -> set[str]:
    text = "" if value is None else str(value)
    found: set[str] = set()
    for match in ORG_RE.finditer(text):
        candidate = "".join(match.groups())
        if valid_org_number(candidate):
            found.add(candidate)
    return found


def load_targets(path: Path) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            if not raw.strip():
                continue
            row = json.loads(raw)
            org = re.sub(r"\D", "", str(row["organisation_number"]))
            if len(org) != 9:
                raise ValueError(f"invalid cohort organisation number: {org!r}")
            rows[org] = row
    if not rows:
        raise ValueError("cohort is empty")
    return rows


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sniff_dialect(path: Path) -> csv.Dialect:
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        sample = handle.read(65536)
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        return csv.excel


def candidate_org_columns(headers: Iterable[str], source: str) -> list[str]:
    selected: list[str] = []
    for header in headers:
        norm = normalize_header(header)
        has_org_marker = any(
            marker in norm
            for marker in (
                "organisasjonsnummer",
                "organisasjonsnr",
                "orgnr",
                "org nr",
                "organisation number",
                "organization number",
                "organisation identifier",
                "organization identifier",
                "national id",
                "national identifier",
            )
        )
        if has_org_marker:
            selected.append(header)
            continue
        # eForms/Doffin exports sometimes expose role-scoped identifiers without the
        # Norwegian label. Keep these as research nominations only.
        if source == "doffin" and "identifier" in norm and any(
            role in norm for role in ("buyer", "winner", "supplier", "tenderer", "organisation", "organization")
        ):
            selected.append(header)
    return selected


def role_for_header(header: str) -> str:
    norm = normalize_header(header)
    if any(word in norm for word in ("winner", "supplier", "tenderer", "leverand")):
        return "supplier_or_winner"
    if any(word in norm for word in ("buyer", "contracting", "oppdragsgiver")):
        return "buyer_or_contracting_authority"
    if any(word in norm for word in ("recipient", "mottaker", "stoettemottaker", "stottemottaker")):
        return "recipient"
    return "unspecified_exact_org_field"


def screen_csv(path: Path, source: str, targets: dict[str, dict]) -> dict:
    dialect = sniff_dialect(path)
    matched_companies: set[str] = set()
    matched_rows = 0
    row_count = 0
    field_role_counts: Counter[str] = Counter()
    match_role_counts: Counter[str] = Counter()
    sample_matches: list[dict] = []

    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle, dialect=dialect)
        headers = [header for header in (reader.fieldnames or []) if header]
        org_columns = candidate_org_columns(headers, source)
        if not org_columns:
            return {
                "source": source,
                "path": str(path),
                "sha256": sha256_file(path),
                "status": "no_exact_org_columns_detected",
                "headers": headers,
                "companies_in_cohort": len(targets),
                "matched_companies": 0,
                "company_reach": 0.0,
                "publication_enabled": False,
                "candidate_only": True,
            }

        for column in org_columns:
            field_role_counts[role_for_header(column)] += 1

        for row in reader:
            row_count += 1
            row_orgs: set[str] = set()
            row_roles: set[str] = set()
            for column in org_columns:
                values = extract_org_numbers(row.get(column))
                if values:
                    row_orgs.update(values)
                    row_roles.add(role_for_header(column))
            hits = row_orgs.intersection(targets)
            if not hits:
                continue
            matched_rows += 1
            matched_companies.update(hits)
            for role in row_roles:
                match_role_counts[role] += 1
            if len(sample_matches) < 20:
                sample_matches.append(
                    {
                        "organisation_numbers": sorted(hits),
                        "roles": sorted(row_roles),
                        "nonempty_fields": {
                            key: value
                            for key, value in row.items()
                            if value not in (None, "") and key in org_columns
                        },
                    }
                )

    return {
        "source": source,
        "path": str(path),
        "sha256": sha256_file(path),
        "status": "screened",
        "companies_in_cohort": len(targets),
        "rows_scanned": row_count,
        "matched_rows": matched_rows,
        "matched_companies": len(matched_companies),
        "company_reach": round(len(matched_companies) / len(targets), 6),
        "matched_organisation_numbers": sorted(matched_companies),
        "detected_org_columns": org_columns,
        "detected_column_roles": dict(field_role_counts),
        "matched_row_roles": dict(match_role_counts),
        "sample_matches": sample_matches,
        "publication_enabled": False,
        "candidate_only": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cohort", type=Path, required=True)
    parser.add_argument("--stotte-csv", type=Path)
    parser.add_argument("--doffin-csv", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    targets = load_targets(args.cohort)
    reports: list[dict] = []
    if args.stotte_csv and args.stotte_csv.exists():
        reports.append(screen_csv(args.stotte_csv, "stotteregisteret", targets))
    else:
        reports.append(
            {
                "source": "stotteregisteret",
                "status": "source_file_unavailable",
                "companies_in_cohort": len(targets),
                "matched_companies": 0,
                "company_reach": 0.0,
                "publication_enabled": False,
                "candidate_only": True,
            }
        )

    doffin_files = [path for path in args.doffin_csv if path.exists()]
    if doffin_files:
        doffin_reports = [screen_csv(path, "doffin", targets) for path in doffin_files]
        matched = set()
        for report in doffin_reports:
            matched.update(report.get("matched_organisation_numbers", []))
        reports.append(
            {
                "source": "doffin",
                "status": "screened",
                "companies_in_cohort": len(targets),
                "matched_companies": len(matched),
                "company_reach": round(len(matched) / len(targets), 6),
                "matched_organisation_numbers": sorted(matched),
                "files": doffin_reports,
                "publication_enabled": False,
                "candidate_only": True,
            }
        )
    else:
        reports.append(
            {
                "source": "doffin",
                "status": "source_file_unavailable",
                "companies_in_cohort": len(targets),
                "matched_companies": 0,
                "company_reach": 0.0,
                "publication_enabled": False,
                "candidate_only": True,
            }
        )

    result = {
        "purpose": "phase5_consumed_only_source_family_selection",
        "cohort": str(args.cohort),
        "cohort_sha256": sha256_file(args.cohort),
        "companies": len(targets),
        "fresh_cohort_consumed": False,
        "production_publication_enabled": False,
        "sources": reports,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
