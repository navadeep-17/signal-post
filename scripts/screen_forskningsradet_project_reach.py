#!/usr/bin/env python3
"""Research-only exact-org screen for Forskningsradet open project/application data.

Only an exact nine-digit organisasjonsnummer match establishes identity.
Project-leader personal data is ignored. Funded-project metrics require
tildelt_belop > 0. No production claims are emitted by this script.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ORG_RE = re.compile(r"^\d{9}$")


def normalize_org(value: Any) -> str | None:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits if ORG_RE.fullmatch(digits) else None


def parse_float(value: Any) -> float | None:
    text = str(value or "").strip().replace(" ", "")
    if not text:
        return None
    try:
        return float(text.replace(",", "."))
    except ValueError:
        return None


def parse_year(value: Any) -> int | None:
    text = str(value or "").strip()
    match = re.search(r"(?<!\d)(19\d{2}|20\d{2}|21\d{2})(?!\d)", text)
    return int(match.group(1)) if match else None


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
    zero_or_blank_org_rows = 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "prosjektnummer", "prosjekttittel", "prosjektfase",
            "prosjektstart", "prosjektslutt", "prosjektansvarlig_navn",
            "organisasjonsnummer", "aktivitet", "fagomraade",
            "sokt_belop", "tildelt_belop",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Forskningsradet source missing required fields: {sorted(missing)}")

        raw_rows = 0
        for raw in reader:
            raw_rows += 1
            row = {str(key): str(value or "").strip() for key, value in raw.items()}
            raw_org = row.get("organisasjonsnummer")
            org = normalize_org(raw_org)
            if org is None:
                digits = "".join(ch for ch in str(raw_org or "") if ch.isdigit())
                if not digits or set(digits) <= {"0"}:
                    zero_or_blank_org_rows += 1
                else:
                    malformed_org_rows += 1
                continue
            row["organisasjonsnummer"] = org
            rows.append(row)

    return rows, {
        "source_raw_rows": raw_rows,
        "source_rows_with_exact_9_digit_org": len(rows),
        "malformed_org_rows_excluded": malformed_org_rows,
        "zero_or_blank_org_rows_excluded": zero_or_blank_org_rows,
    }


def is_funded(row: dict[str, str]) -> bool:
    amount = parse_float(row.get("tildelt_belop"))
    return amount is not None and amount > 0


def is_nonterminal_phase(value: Any) -> bool:
    phase = str(value or "").strip().casefold()
    if not phase:
        return False
    terminal = ("avslutt", "avbrutt", "trukket", "avvist", "lukket", "rejected", "closed", "cancel")
    return not any(fragment in phase for fragment in terminal)


def project_event(row: dict[str, str]) -> dict[str, Any]:
    return {
        "project_number": row.get("prosjektnummer") or None,
        "project_title": row.get("prosjekttittel") or None,
        "project_phase": row.get("prosjektfase") or None,
        "project_start_year": parse_year(row.get("prosjektstart")),
        "project_end_year": parse_year(row.get("prosjektslutt")),
        "responsible_organisation_name": row.get("prosjektansvarlig_navn") or None,
        "project_type": row.get("prosjekttype") or None,
        "application_type": row.get("soknadstype") or None,
        "instrument": row.get("virkemiddel") or None,
        "main_activity": row.get("hovedaktivitet") or None,
        "activity": row.get("aktivitet") or None,
        "research_field": row.get("fagomraade") or None,
        "field": row.get("fag") or None,
        "discipline": row.get("fagdisiplin") or None,
        "amount_applied": parse_float(row.get("sokt_belop")),
        "amount_awarded": parse_float(row.get("tildelt_belop")),
    }


def screen(rows: list[dict[str, str]], targets: set[str], *, current_year: int, max_projects_per_company: int = 5):
    by_org: dict[str, list[dict[str, str]]] = defaultdict(list)
    source_orgs: set[str] = set()
    for row in rows:
        org = normalize_org(row.get("organisasjonsnummer"))
        if org is None:
            continue
        source_orgs.add(org)
        if org in targets:
            by_org[org].append(row)

    funded_hits = 0
    current_window_hits = 0
    current_nonterminal_hits = 0
    recent_start_hits = 0
    phases = Counter()
    matched = []

    for org in sorted(by_org):
        company_rows = by_org[org]
        funded = [row for row in company_rows if is_funded(row)]
        if funded:
            funded_hits += 1

        current_window = [
            row for row in funded
            if (parse_year(row.get("prosjektstart")) or 9999) <= current_year
            and (parse_year(row.get("prosjektslutt")) or -1) >= current_year
        ]
        if current_window:
            current_window_hits += 1

        current_nonterminal = [row for row in current_window if is_nonterminal_phase(row.get("prosjektfase"))]
        if current_nonterminal:
            current_nonterminal_hits += 1

        recent_start = [
            row for row in funded
            if (year := parse_year(row.get("prosjektstart"))) is not None
            and year >= current_year - 2
        ]
        if recent_start:
            recent_start_hits += 1

        for row in company_rows:
            phase = str(row.get("prosjektfase") or "").strip()
            if phase:
                phases[phase] += 1

        def sort_key(row):
            return (
                parse_year(row.get("prosjektslutt")) or -1,
                parse_year(row.get("prosjektstart")) or -1,
                row.get("prosjektnummer") or "",
            )

        funded_sorted = sorted(funded, key=sort_key, reverse=True)
        all_sorted = sorted(company_rows, key=sort_key, reverse=True)
        selected = funded_sorted[:max_projects_per_company] if funded_sorted else all_sorted[:max_projects_per_company]

        matched.append({
            "organisation_number": org,
            "exact_identity_basis": "Forskningsradet.organisasjonsnummer == target legal organisation_number",
            "project_rows": len(company_rows),
            "funded_project_rows": len(funded),
            "current_year_funded_project_rows": len(current_window),
            "current_year_nonterminal_funded_project_rows": len(current_nonterminal),
            "recent_start_funded_project_rows": len(recent_start),
            "sample_projects": [project_event(row) for row in selected],
        })

    report = {
        "source": "Norges forskningsrad open-data soknader2 dataset.csv",
        "screen_type": "bulk_exact_org_research_project_activity",
        "production_publication_enabled": False,
        "api_access_status": "OPEN_STATIC_DOWNLOAD_NO_REGISTRATION",
        "reuse_rights_status": "NLOD",
        "target_companies": len(targets),
        "unique_exact_orgs_in_source": len(source_orgs),
        "exact_target_company_hits": len(by_org),
        "exact_target_reach": len(by_org) / len(targets) if targets else 0.0,
        "companies_with_funded_project": funded_hits,
        "companies_with_funded_project_spanning_current_year": current_window_hits,
        "companies_with_nonterminal_funded_project_spanning_current_year": current_nonterminal_hits,
        "companies_with_funded_project_started_in_last_2_years": recent_start_hits,
        "observed_project_phases_for_matched_rows": dict(sorted(phases.items())),
        "external_requests": 1,
        "notes": [
            "Only exact 9-digit organisasjonsnummer establishes company identity.",
            "Funded-project metrics require tildelt_belop > 0.",
            "Project-leader personal data is deliberately ignored.",
            "A project is not described as currently active merely because its date range spans the current year; nonterminal source phase is tracked separately.",
            "Prosjektbanken warns that 2026 data is temporarily incomplete during a case-management-system transition; missing 2026 rows must not be interpreted as no activity.",
            "This consumed-only source-selection screen publishes no production claims and touches no fresh evaluator cohort.",
        ],
    }
    return report, matched


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-csv", required=True, type=Path)
    parser.add_argument("--companies", required=True, type=Path)
    parser.add_argument("--current-year", required=True, type=int)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    rows, source_meta = load_source(args.source_csv)
    targets = load_targets(args.companies)
    report, matched = screen(rows, targets, current_year=args.current_year)
    report.update(source_meta)
    report["source_bytes"] = args.source_csv.stat().st_size
    report["source_sha256"] = sha256_file(args.source_csv)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "matched-companies.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in matched),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
