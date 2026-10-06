#!/usr/bin/env python3
"""Measure aggregate Peppol website-candidate overlap with current verified websites.

Research-only, privacy-minimized source qualification:
- exact Norwegian Peppol scheme 0192 is the only join;
- Peppol names/contact fields are never retained;
- raw Peppol website URLs are never retained;
- matched organisation-number lists are never written;
- output is aggregate counts only.

No production publication or source promotion is performed.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
import urllib.parse
from pathlib import Path
from typing import Any, Iterable

PARTICIPANT_RE = re.compile(
    r"^(?:iso6523-actorid-upis::)?0192:(\d{9})$",
    re.IGNORECASE,
)
EXPECTED_COLUMNS = {"Participant ID", "Websites"}


def norm_org(value: Any) -> str | None:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits if len(digits) == 9 else None


def participant_org(value: str) -> str | None:
    decoded = urllib.parse.unquote(str(value or "").strip())
    match = PARTICIPANT_RE.fullmatch(decoded)
    return match.group(1) if match else None


def has_value(value: str | None) -> bool:
    return bool(value and any(part.strip() for part in str(value).splitlines()))


def read_target_orgs(path: Path) -> set[str]:
    orgs: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        org = norm_org(
            row.get("organisation_number")
            or row.get("organization_number")
            or row.get("orgnr")
        )
        if not org:
            raise ValueError(f"invalid target org: {row!r}")
        if org in orgs:
            raise ValueError(f"duplicate target org: {org}")
        orgs.add(org)
    if not orgs:
        raise ValueError("empty target cohort")
    return orgs


def iter_jsonl_gz(path: Path) -> Iterable[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                if isinstance(row, dict):
                    yield row


def current_verified_website_orgs(path: Path, targets: set[str]) -> set[str]:
    found: set[str] = set()
    seen: set[str] = set()
    for row in iter_jsonl_gz(path):
        org = norm_org(row.get("organisation_number"))
        if not org or org not in targets:
            continue
        if org in seen:
            raise ValueError(f"duplicate production output org: {org}")
        seen.add(org)
        for claim in row.get("claims") or []:
            if not isinstance(claim, dict):
                continue
            if (
                claim.get("field") == "official_website"
                and claim.get("availability") == "available"
                and claim.get("value")
            ):
                found.add(org)
                break
    if seen != targets:
        missing = len(targets - seen)
        raise ValueError(f"production output missing {missing} target companies")
    return found


def iter_peppol_minimal(path: Path) -> Iterable[tuple[str, bool]]:
    with gzip.open(path, "rt", encoding="iso-8859-1", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        actual = set(reader.fieldnames or [])
        missing = EXPECTED_COLUMNS - actual
        if missing:
            raise ValueError(f"Peppol CSV missing expected columns: {sorted(missing)}")
        for row in reader:
            pid = str(row.get("Participant ID") or "")
            decoded = urllib.parse.unquote(pid.strip())
            if "0192:" not in decoded.lower():
                continue
            org = participant_org(pid)
            if org:
                yield org, has_value(str(row.get("Websites") or ""))


def compare(
    export_gz: Path,
    production_output_gz: Path,
    target_orgs: set[str],
) -> dict[str, Any]:
    current_web = current_verified_website_orgs(production_output_gz, target_orgs)

    participant_hits: set[str] = set()
    website_hits: set[str] = set()
    target_rows = 0
    for org, has_website in iter_peppol_minimal(export_gz):
        if org not in target_orgs:
            continue
        target_rows += 1
        participant_hits.add(org)
        if has_website:
            website_hits.add(org)

    overlap = website_hits & current_web
    net_new = website_hits - current_web
    post_upper = current_web | website_hits
    participant_current = participant_hits & current_web

    n = len(target_orgs)
    return {
        "cohort_companies": n,
        "current_verified_website_companies": len(current_web),
        "current_verified_website_reach": round(len(current_web) / n, 6),
        "peppol_exact_participant_companies": len(participant_hits),
        "peppol_exact_participant_reach": round(len(participant_hits) / n, 6),
        "peppol_website_candidate_companies": len(website_hits),
        "peppol_website_candidate_reach": round(len(website_hits) / n, 6),
        "peppol_website_overlap_current_verified": len(overlap),
        "peppol_website_net_new_candidates": len(net_new),
        "peppol_website_net_new_candidate_reach": round(len(net_new) / n, 6),
        "current_verified_websites_among_peppol_participants": len(participant_current),
        "post_candidate_upper_bound_website_companies": len(post_upper),
        "post_candidate_upper_bound_website_reach": round(len(post_upper) / n, 6),
        "target_rows": target_rows,
        "matched_org_lists_retained": False,
        "raw_peppol_websites_retained": False,
        "contact_fields_retained": False,
        "production_publication_enabled": False,
        "reuse_rights_status": "UNRESOLVED_FOR_DIRECTORY_DATA",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--export-gz", type=Path, required=True)
    ap.add_argument("--production-output-gz", type=Path, required=True)
    ap.add_argument("--companies", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()

    targets = read_target_orgs(args.companies)
    report = compare(args.export_gz, args.production_output_gz, targets)
    report.update(
        {
            "screen_type": "aggregate_peppol_website_overlap_vs_current_verified",
            "notes": [
                "Exact 0192 organisation number is the only company join.",
                "Peppol website values are source candidates only and are never publication proof.",
                "This screen persists aggregate counts only.",
                "The post-candidate figure is an upper bound before independent Signalpost website verification.",
                "No production promotion is allowed until Peppol directory-data reuse rights are explicitly cleared.",
            ],
        }
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
