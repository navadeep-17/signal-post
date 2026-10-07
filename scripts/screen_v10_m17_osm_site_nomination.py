#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.batch import profiles_from_bulk, read_organisation_inputs  # noqa: E402
from norway_company_agent.osm_site_nomination import (  # noqa: E402
    DEFAULT_NOMINATIM_BASE_URL,
    DEFAULT_USER_AGENT,
    OSM_ATTRIBUTION,
    evaluate_osm_candidate,
    nominate_osm_website,
)

MIN_NET_NEW_VERIFIED_WEBSITES = 2


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        item = json.loads(line)
        if not isinstance(item, dict):
            raise ValueError(f"{path}:{lineno}: expected object")
        rows.append(item)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def baseline_has_verified_website(row: dict[str, Any]) -> bool:
    return any(
        isinstance(claim, dict)
        and claim.get("field") == "official_website"
        and claim.get("availability") == "available"
        and claim.get("value")
        for claim in (row.get("claims") or [])
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--bulk", type=Path, required=True)
    p.add_argument("--baseline-output", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--nominatim-audit", type=Path, required=True)
    p.add_argument("--manual-audit", type=Path, required=True)
    p.add_argument("--nominatim-base-url", default=os.environ.get("NOMINATIM_BASE_URL", DEFAULT_NOMINATIM_BASE_URL))
    p.add_argument("--nominatim-user-agent", default=os.environ.get("NOMINATIM_USER_AGENT", DEFAULT_USER_AGENT))
    p.add_argument("--nominatim-timeout", type=float, default=12.0)
    p.add_argument("--nominatim-min-interval-seconds", type=float, default=1.05)
    p.add_argument("--site-timeout", type=float, default=6.0)
    args = p.parse_args()

    if args.nominatim_min_interval_seconds < 1.0:
        raise ValueError("public Nominatim screen must be paced at >=1 request/second")
    if not str(args.nominatim_user_agent).strip():
        raise ValueError("Nominatim requires an identifying User-Agent")

    manifest = read_organisation_inputs(args.manifest)
    orgs = [str(row["organisation_number"]) for row in manifest]
    if len(orgs) != 20 or len(set(orgs)) != 20:
        raise ValueError(f"M17 requires exactly 20 unique companies, got {len(orgs)}")

    baseline_rows = read_jsonl(args.baseline_output)
    baseline = {str(row.get("organisation_number") or ""): row for row in baseline_rows}
    if set(baseline) != set(orgs):
        raise ValueError("baseline output company set differs from frozen M17 manifest")

    profiles, snapshot = profiles_from_bulk(args.bulk, orgs)
    profile_by_org = {str(row.get("organisation_number") or ""): row for row in profiles}

    rows: list[dict[str, Any]] = []
    nominatim_audit: list[dict[str, Any]] = []
    manual: list[dict[str, Any]] = []
    source_errors: list[dict[str, Any]] = []
    evidence_defects: list[dict[str, Any]] = []

    baseline_verified = 0
    nominatim_requests = 0
    matched_candidate_companies = 0
    candidate_site_requests = 0
    candidate_site_bytes = 0
    verified = 0

    for org in orgs:
        profile = profile_by_org[org]
        baseline_site = baseline_has_verified_website(baseline[org])
        baseline_verified += int(baseline_site)
        item: dict[str, Any] = {
            "organisation_number": org,
            "baseline_verified_website": baseline_site,
            "nominatim_selected_candidate": False,
            "net_new_verified_website": False,
        }

        if baseline_site:
            item["screen_status"] = "baseline_already_verified"
            rows.append(item)
            continue

        candidate, nom_audit = nominate_osm_website(
            profile,
            base_url=args.nominatim_base_url,
            user_agent=args.nominatim_user_agent,
            timeout=args.nominatim_timeout,
            min_interval_seconds=args.nominatim_min_interval_seconds,
        )
        nominatim_requests += int(nom_audit.get("requests") or 0)
        nominatim_audit.append(nom_audit)
        item["nominatim_selected_candidate"] = candidate is not None
        item["nominatim_status"] = nom_audit.get("status")
        item["nominatim_result_count"] = len(nom_audit.get("reviewed_results") or [])

        if nom_audit.get("status") == "source_error":
            source_errors.append({
                "organisation_number": org,
                "error": nom_audit.get("error"),
            })
            item["screen_status"] = "nominatim_source_error"
            rows.append(item)
            continue

        if candidate is None:
            item["screen_status"] = "no_exact_name_location_osm_website_candidate"
            rows.append(item)
            continue

        matched_candidate_companies += 1
        enriched, site_result = evaluate_osm_candidate(
            profile,
            candidate,
            timeout=args.site_timeout,
        )
        candidate_site_requests += int(site_result.get("requests") or 0)
        candidate_site_bytes += int(site_result.get("bytes") or 0)
        item["site_evaluation"] = site_result

        if not site_result.get("verified"):
            item["screen_status"] = "candidate_failed_independent_exact_site_gate"
            rows.append(item)
            continue

        verified += 1
        item["net_new_verified_website"] = True
        item["screen_status"] = "verified"
        identity = site_result.get("identity_assessment") or {}
        website_hash = str(site_result.get("website_content_sha256") or "")
        defects: list[str] = []
        if len(website_hash) != 64:
            defects.append("website_content_sha256_missing")
        if not bool(identity.get("publishable")):
            defects.append("identity_assessment_not_publishable")
        if str(identity.get("status") or "") != "exact":
            defects.append("identity_status_not_exact")
        if defects:
            evidence_defects.append({
                "organisation_number": org,
                "defects": defects,
            })

        manual.append({
            "organisation_number": org,
            "selected_url": site_result.get("selected_url"),
            "website_content_sha256": website_hash,
            "identity_status": identity.get("status"),
            "identity_score": identity.get("score"),
            "identity_method": identity.get("method"),
            "identity_reasons": identity.get("reasons"),
            "registry_guard_reasons": site_result.get("guard_reasons"),
            "osm_type": candidate.get("osm_type"),
            "osm_id": candidate.get("osm_id"),
            "osm_display_name": candidate.get("display_name"),
            "osm_matched_name_tokens": candidate.get("matched_name_tokens"),
            "osm_location_basis": candidate.get("location_basis"),
            "osm_attribution": candidate.get("attribution"),
            "osm_is_nomination_only": True,
            "manual_review_finalized": False,
        })
        rows.append(item)

    if len(rows) != 20:
        raise AssertionError("M17 output lost companies")

    if source_errors or evidence_defects:
        decision = "BLOCKED"
    elif verified >= MIN_NET_NEW_VERIFIED_WEBSITES:
        decision = "MANUAL_AUDIT_REQUIRED"
    else:
        decision = "SHELVE_LOW_YIELD"

    report = {
        "milestone": "M17",
        "screen": "consumed_osm_nominatim_site_nomination",
        "machine_decision": decision,
        "companies": 20,
        "fresh_companies_used": 0,
        "baseline_verified_website_companies": baseline_verified,
        "nominatim_requests": nominatim_requests,
        "nominatim_min_interval_seconds": args.nominatim_min_interval_seconds,
        "nominatim_single_threaded": True,
        "nominatim_results_cached_in_artifact": True,
        "nominatim_provider_switchable": True,
        "nominatim_attribution": OSM_ATTRIBUTION,
        "companies_with_exact_name_location_website_candidate": matched_candidate_companies,
        "candidate_site_requests": candidate_site_requests,
        "candidate_site_bytes": candidate_site_bytes,
        "total_screen_logical_requests": nominatim_requests + candidate_site_requests,
        "net_new_verified_website_companies": verified,
        "minimum_net_new_verified_website_companies": MIN_NET_NEW_VERIFIED_WEBSITES,
        "manual_review_rows": len(manual),
        "manual_review_finalized": False,
        "source_errors": source_errors,
        "evidence_defects": evidence_defects,
        "third_party_api_cost_usd": 0.0,
        "search_engine_api_requests": 0,
        "publication_authorized": False,
        "production_promotion_authorized": False,
        "fresh_qualification_authorized": False,
        "production_policy_review_required": True,
        "candidate_boundary": (
            "Nominatim/OSM name+registry-location matching nominates a website tag only. "
            "OSM data is not website publication evidence; only the independently fetched "
            "company page passing exact identity and registry-risk gates can count."
        ),
        "registry_snapshot_sha256": snapshot.get("registry_snapshot_sha256"),
    }

    write_jsonl(args.output, rows)
    write_jsonl(args.nominatim_audit, nominatim_audit)
    write_jsonl(args.manual_audit, manual)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if decision == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
