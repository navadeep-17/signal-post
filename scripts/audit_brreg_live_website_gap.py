#!/usr/bin/env python3
"""Zero-network audit of exact live-BRREG homepage drift vs the bulk/profile website.

This determines whether the already-paid exact registry_live entity response contains
website candidates that the current website discovery path never saw because it relies
on the bulk/profile homepage value.

Research-only. Aggregate counts are persisted; no candidate URLs are written.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
from pathlib import Path
from typing import Any


def norm_org(value: Any) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) != 9:
        raise ValueError(f"invalid org: {value!r}")
    return digits


def norm_url(value: Any) -> str:
    text = str(value or "").strip().casefold()
    if not text:
        return ""
    text = re.sub(r"^https?://", "", text)
    text = re.sub(r"^www\.", "", text)
    return text.rstrip("/")


def read_profiles(root: Path) -> dict[str, dict[str, Any]]:
    files = sorted(root.rglob("profiles.jsonl"))
    if not files:
        raise ValueError("no profiles.jsonl files")
    out: dict[str, dict[str, Any]] = {}
    for file in files:
        for line in file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            org = norm_org(row.get("organisation_number"))
            if org in out:
                raise ValueError(f"duplicate org {org}")
            out[org] = row
    if len(out) != 1000:
        raise ValueError(f"expected 1000 profiles, got {len(out)}")
    return out


def verified_website_orgs(path: Path) -> set[str]:
    out: set[str] = set()
    seen: set[str] = set()
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            org = norm_org(row.get("organisation_number"))
            seen.add(org)
            for claim in row.get("claims") or []:
                if (
                    isinstance(claim, dict)
                    and claim.get("field") == "official_website"
                    and claim.get("availability") == "available"
                    and claim.get("value")
                ):
                    out.add(org)
                    break
    if len(seen) != 1000:
        raise ValueError(f"expected 1000 output orgs, got {len(seen)}")
    return out


def audit(
    profiles: dict[str, dict[str, Any]],
    verified: set[str],
) -> dict[str, Any]:
    live_available = 0
    live_website = 0
    profile_website = 0
    unresolved_live_website = 0
    unresolved_live_same_as_profile = 0
    unresolved_live_changed_from_profile = 0
    unresolved_live_only = 0
    unresolved_profile_only = 0

    for org, profile in profiles.items():
        bulk_site = str(profile.get("website") or "").strip()
        if bulk_site:
            profile_website += 1

        live = ((profile.get("evidence") or {}).get("registry_live") or {})
        if live.get("status") != "available":
            continue
        live_available += 1
        values = live.get("value") if isinstance(live.get("value"), dict) else {}
        live_site = str((values or {}).get("website") or "").strip()
        if live_site:
            live_website += 1

        if org in verified:
            continue
        if live_site:
            unresolved_live_website += 1
            if norm_url(live_site) == norm_url(bulk_site) and bulk_site:
                unresolved_live_same_as_profile += 1
            elif bulk_site:
                unresolved_live_changed_from_profile += 1
            else:
                unresolved_live_only += 1
        elif bulk_site:
            unresolved_profile_only += 1

    genuinely_new = unresolved_live_changed_from_profile + unresolved_live_only
    return {
        "companies": len(profiles),
        "current_verified_website_companies": len(verified),
        "registry_live_available_companies": live_available,
        "profile_bulk_website_companies": profile_website,
        "registry_live_website_companies": live_website,
        "unresolved_with_registry_live_website": unresolved_live_website,
        "unresolved_live_website_same_as_profile": unresolved_live_same_as_profile,
        "unresolved_live_website_changed_from_profile": unresolved_live_changed_from_profile,
        "unresolved_live_website_only_no_profile_website": unresolved_live_only,
        "unresolved_profile_website_but_no_live_website": unresolved_profile_only,
        "genuinely_new_live_website_candidate_companies": genuinely_new,
        "genuinely_new_live_website_candidate_reach": round(genuinely_new / len(profiles), 6),
        "incremental_source_requests_if_used": 0,
        "production_publication_enabled": False,
        "reuse_rights_status": "NLOD_2_0",
        "candidate_values_retained": False,
        "organisation_lists_retained": False,
        "notes": [
            "registry_live is the exact organisation-number BRREG entity response already fetched in V2/V8.",
            "A live homepage equal to the bulk/profile homepage is not a new discovery candidate.",
            "Only live-only or changed homepage values for companies lacking a verified website count as genuinely new.",
            "Any genuinely new homepage remains candidate evidence and must pass the existing exact-site verifier.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles-dir", type=Path, required=True)
    ap.add_argument("--output-contract-gz", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()

    report = audit(
        read_profiles(args.profiles_dir),
        verified_website_orgs(args.output_contract_gz),
    )
    report["screen_type"] = "brreg_registry_live_homepage_drift_vs_bulk_profile"
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
