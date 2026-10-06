#!/usr/bin/env python3
"""Screen the archived Norge.no/Etatsbasen org->URL join on a consumed cohort.

Research-only. The archive is historical and NLOD/open. Organisation rows carry
exact Norwegian organisation numbers and URL rows share the same TailID. URLs
remain discovery candidates only; no archived URL is publication proof.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any


def norm_org(value: Any) -> str | None:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits if len(digits) == 9 else None


def read_targets(path: Path) -> set[str]:
    result: set[str] = set()
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
        if org in result:
            raise ValueError(f"duplicate target org: {org}")
        result.add(org)
    if not result:
        raise ValueError("empty target cohort")
    return result


def current_verified_websites(path: Path, targets: set[str]) -> set[str]:
    found: set[str] = set()
    seen: set[str] = set()
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            org = norm_org(row.get("organisation_number"))
            if not org or org not in targets:
                continue
            if org in seen:
                raise ValueError(f"duplicate production output org: {org}")
            seen.add(org)
            for claim in row.get("claims") or []:
                if (
                    isinstance(claim, dict)
                    and claim.get("field") == "official_website"
                    and claim.get("availability") == "available"
                    and claim.get("value")
                ):
                    found.add(org)
                    break
    if seen != targets:
        raise ValueError(f"production output missing {len(targets - seen)} target companies")
    return found


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def scan(
    organisations_csv: Path,
    urls_csv: Path,
    targets: set[str],
    current_web: set[str],
) -> dict[str, Any]:
    tail_to_target_org: dict[str, str] = {}
    organisation_rows = 0
    exact_org_rows = 0
    target_org_rows = 0

    with organisations_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"tailid", "orgid"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError(f"organisation CSV missing {sorted(required)}")
        for row in reader:
            organisation_rows += 1
            org = norm_org(row.get("orgid"))
            if not org:
                continue
            exact_org_rows += 1
            if org not in targets:
                continue
            tail = str(row.get("tailid") or "").strip()
            if not tail:
                continue
            previous = tail_to_target_org.get(tail)
            if previous and previous != org:
                raise ValueError(f"TailID {tail} maps to multiple target organisation numbers")
            tail_to_target_org[tail] = org
            target_org_rows += 1

    url_rows = 0
    matched_url_rows = 0
    website_hits: set[str] = set()
    with urls_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"tailid", "url"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError(f"URL CSV missing {sorted(required)}")
        for row in reader:
            url_rows += 1
            tail = str(row.get("tailid") or "").strip()
            org = tail_to_target_org.get(tail)
            if not org:
                continue
            raw_url = str(row.get("url") or "").strip()
            if not raw_url:
                continue
            matched_url_rows += 1
            website_hits.add(org)

    exact_hits = set(tail_to_target_org.values())
    overlap = website_hits & current_web
    net_new = website_hits - current_web
    return {
        "organisation_rows": organisation_rows,
        "organisation_rows_with_exact_org": exact_org_rows,
        "target_organisation_rows": target_org_rows,
        "url_rows": url_rows,
        "matched_target_url_rows": matched_url_rows,
        "exact_company_hits": len(exact_hits),
        "website_candidate_companies": len(website_hits),
        "website_overlap_current_verified": len(overlap),
        "website_net_new_candidates": len(net_new),
        "post_candidate_upper_bound_website_companies": len(current_web | website_hits),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--organisations-csv", required=True, type=Path)
    ap.add_argument("--urls-csv", required=True, type=Path)
    ap.add_argument("--companies", required=True, type=Path)
    ap.add_argument("--production-output-gz", required=True, type=Path)
    ap.add_argument("--report", required=True, type=Path)
    args = ap.parse_args()

    targets = read_targets(args.companies)
    current_web = current_verified_websites(args.production_output_gz, targets)
    result = scan(args.organisations_csv, args.urls_csv, targets, current_web)
    n = len(targets)
    report = {
        "source": "Digitaliseringsdirektoratet archived Etatsbasen organisation + URL datasets",
        "screen_type": "historical_nlod_exact_org_tailid_url_join",
        "cohort_companies": n,
        "current_verified_website_companies": len(current_web),
        "current_verified_website_reach": round(len(current_web) / n, 6),
        "organisation_source_bytes": args.organisations_csv.stat().st_size,
        "organisation_source_sha256": sha256_file(args.organisations_csv),
        "url_source_bytes": args.urls_csv.stat().st_size,
        "url_source_sha256": sha256_file(args.urls_csv),
        **result,
        "exact_company_reach": round(result["exact_company_hits"] / n, 6),
        "website_candidate_reach": round(result["website_candidate_companies"] / n, 6),
        "website_net_new_candidate_reach": round(result["website_net_new_candidates"] / n, 6),
        "post_candidate_upper_bound_website_reach": round(
            result["post_candidate_upper_bound_website_companies"] / n, 6
        ),
        "external_requests": 2,
        "reuse_rights_status": "NLOD_OPEN",
        "freshness_status": "HISTORICAL_ARCHIVE_NOT_MAINTAINED",
        "production_publication_enabled": False,
        "matched_org_lists_retained": False,
        "raw_candidate_urls_retained": False,
        "notes": [
            "Exact nine-digit organisation number from the archived organisation table is the identity anchor.",
            "URL rows join only through the archived TailID relation.",
            "The archive is historical and no longer maintained; URLs are discovery candidates only.",
            "Any candidate would require fresh independent Signalpost exact-company website verification.",
            "The report persists aggregate counts only.",
        ],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
