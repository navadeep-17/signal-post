#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any


def read_target_orgs(path: Path) -> set[str]:
    orgs: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        org = re.sub(r"\D", "", str(row.get("organisation_number") or ""))
        if len(org) == 9:
            orgs.add(org)
    return orgs


def parse_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def parse_float(value: Any) -> float:
    text = str(value or "").strip().replace(" ", "")
    if not text:
        return 0.0
    try:
        return float(text.replace(",", "."))
    except ValueError:
        return 0.0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Research-only exact-organisation-number reach screen over Forskningsrådet open data."
    )
    parser.add_argument("--targets", required=True, help="Consumed/frozen JSONL containing organisation_number")
    parser.add_argument("--dataset", required=True, help="Pinned Forskningsrådet soknader2 dataset.csv")
    parser.add_argument("--report", required=True)
    parser.add_argument("--as-of", default="2026-10-05", help="Audit reference date YYYY-MM-DD")
    parser.add_argument("--recent-years", type=int, default=5)
    parser.add_argument("--sample-limit", type=int, default=20)
    args = parser.parse_args()

    as_of = date.fromisoformat(args.as_of)
    if args.recent_years < 1:
        parser.error("--recent-years must be positive")
    cutoff = date(as_of.year - args.recent_years, as_of.month, as_of.day)

    targets = read_target_orgs(Path(args.targets))
    if not targets:
        raise SystemExit("No valid 9-digit target organisation numbers")

    dataset_path = Path(args.dataset)
    rows_scanned = 0
    matched_rows = 0
    matched_orgs: set[str] = set()
    recent_application_orgs: set[str] = set()
    awarded_orgs: set[str] = set()
    recent_awarded_orgs: set[str] = set()
    active_awarded_orgs: set[str] = set()
    phases: Counter[str] = Counter()
    matches_by_org: dict[str, list[dict[str, Any]]] = defaultdict(list)

    with dataset_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "prosjektnummer",
            "prosjekttittel",
            "soknadsdato",
            "prosjektfase",
            "prosjektansvarlig_navn",
            "organisasjonsnummer",
            "sektor",
            "sokt_belop",
            "tildelt_belop",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"Missing required source columns: {sorted(missing)}")

        for row in reader:
            rows_scanned += 1
            org = re.sub(r"\D", "", str(row.get("organisasjonsnummer") or ""))
            if org not in targets:
                continue

            matched_rows += 1
            matched_orgs.add(org)
            application_date = parse_date(row.get("soknadsdato"))
            phase = " ".join(str(row.get("prosjektfase") or "").split())
            awarded_amount = parse_float(row.get("tildelt_belop"))
            awarded = awarded_amount > 0 and phase.casefold() in {"bevilgning", "avsluttet"}
            recent = bool(application_date and application_date >= cutoff and application_date <= as_of)

            phases[phase or "unknown"] += 1
            if recent:
                recent_application_orgs.add(org)
            if awarded:
                awarded_orgs.add(org)
                if recent:
                    recent_awarded_orgs.add(org)
                if phase.casefold() == "bevilgning":
                    active_awarded_orgs.add(org)

            if len(matches_by_org[org]) < args.sample_limit:
                matches_by_org[org].append(
                    {
                        "prosjektnummer": str(row.get("prosjektnummer") or ""),
                        "prosjekttittel": str(row.get("prosjekttittel") or "")[:500],
                        "soknadsdato": application_date.isoformat() if application_date else None,
                        "prosjektfase": phase or None,
                        "prosjektansvarlig_navn": str(row.get("prosjektansvarlig_navn") or "")[:300],
                        "sektor": str(row.get("sektor") or "")[:120],
                        "sokt_belop": parse_float(row.get("sokt_belop")),
                        "tildelt_belop": awarded_amount,
                        "awarded": awarded,
                        "recent": recent,
                    }
                )

    total = len(targets)

    def coverage(orgs: set[str]) -> dict[str, Any]:
        count = len(orgs)
        return {
            "companies": count,
            "total_companies": total,
            "coverage_pct": round(100.0 * count / total, 1) if total else 0.0,
            "organisation_numbers": sorted(orgs),
        }

    report = {
        "source": {
            "publisher": "Norges forskningsråd",
            "dataset": "soknader2",
            "dataset_sha256": sha256_file(dataset_path),
            "dataset_bytes": dataset_path.stat().st_size,
            "license": "NLOD",
            "identity_join": "exact organisasjonsnummer from Enhetsregisteret field",
        },
        "audit": {
            "as_of": as_of.isoformat(),
            "recent_years": args.recent_years,
            "recent_cutoff": cutoff.isoformat(),
            "target_companies": total,
            "rows_scanned": rows_scanned,
            "matched_rows": matched_rows,
        },
        "coverage": {
            "any_application": coverage(matched_orgs),
            "recent_application": coverage(recent_application_orgs),
            "any_awarded_project": coverage(awarded_orgs),
            "recent_awarded_project": coverage(recent_awarded_orgs),
            "active_awarded_project": coverage(active_awarded_orgs),
        },
        "matched_phase_counts": dict(sorted(phases.items())),
        "matches_by_organisation_number": dict(sorted(matches_by_org.items())),
        "publication_enabled": False,
        "fresh_cohort_consumed": False,
        "policy": (
            "Research/source-selection only. Exact organisation-number overlap demonstrates potential reach, "
            "not production qualification or permission to relabel research applications as other signal families."
        ),
    }

    output = Path(args.report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
