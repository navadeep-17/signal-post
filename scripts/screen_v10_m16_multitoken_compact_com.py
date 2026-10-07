#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.h1i_multitoken_compact_com import (
    evaluate_multitoken_compact_com_candidate,
    multitoken_compact_com_candidate,
)

MIN_NET_NEW_VERIFIED_WEBSITES = 2
MAX_REPLACEMENT_LOGICAL_REQUESTS = 2


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        item = json.loads(line)
        if not isinstance(item, dict):
            raise ValueError(f"{path}:{lineno}: object expected")
        rows.append(item)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _website_publishable(profile: dict[str, Any]) -> bool:
    website = ((profile.get("evidence") or {}).get("website") or {})
    assessment = ((website.get("value") or {}).get("identity_assessment") or {})
    return website.get("status") == "available" and bool(assessment.get("publishable"))


def _h1g_attempt(profile: dict[str, Any]) -> dict[str, Any] | None:
    record = ((profile.get("evidence") or {}).get("website_h1g_hyphenated_no_discovery") or {})
    if not record:
        return None
    value = record.get("value") or {}
    try:
        added = int(value.get("requests_added") or 0)
    except (TypeError, ValueError):
        return None
    if added < 1 or added > MAX_REPLACEMENT_LOGICAL_REQUESTS:
        return None
    return {
        "requests_added": added,
        "candidate_domain": value.get("candidate_domain"),
        "status": record.get("status"),
        "base_site_logical_requests": value.get("base_site_logical_requests"),
        "post_site_logical_requests": value.get("post_site_logical_requests"),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--profiles", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--manual-audit", type=Path, required=True)
    p.add_argument("--site-timeout", type=float, default=6.0)
    args = p.parse_args()

    profiles = read_jsonl(args.profiles)
    if len(profiles) != 20:
        raise ValueError(f"M16 development screen requires exactly 20 profiles, got {len(profiles)}")
    orgs = [str(row.get("organisation_number") or "") for row in profiles]
    if len(set(orgs)) != 20 or any(len(org) != 9 or not org.isdigit() for org in orgs):
        raise ValueError("M16 profiles require 20 unique nine-digit organisation numbers")

    rows: list[dict[str, Any]] = []
    manual: list[dict[str, Any]] = []
    evidence_defects: list[dict[str, Any]] = []
    execution_errors: list[dict[str, Any]] = []
    baseline_verified = 0
    h1g_attempted_unresolved = 0
    replacement_eligible = 0
    replacement_requests = 0
    verified = 0

    for profile in profiles:
        org = str(profile["organisation_number"])
        baseline_site = _website_publishable(profile)
        baseline_verified += int(baseline_site)
        old_h1g = _h1g_attempt(profile)
        candidate = multitoken_compact_com_candidate(profile)
        item: dict[str, Any] = {
            "organisation_number": org,
            "baseline_verified_website": baseline_site,
            "h1g_attempt": old_h1g,
            "replacement_candidate_domain": candidate.get("domain") if candidate else None,
            "replacement_evaluation": None,
            "net_new_verified_website": False,
        }

        if baseline_site:
            item["screen_status"] = "baseline_already_verified"
            rows.append(item)
            continue
        if old_h1g is None:
            item["screen_status"] = "h1g_slot_not_actually_spent"
            rows.append(item)
            continue

        h1g_attempted_unresolved += 1
        if candidate is None:
            item["screen_status"] = "no_multitoken_compact_com_candidate"
            rows.append(item)
            continue

        replacement_eligible += 1
        try:
            _enriched, result = evaluate_multitoken_compact_com_candidate(
                profile,
                timeout=args.site_timeout,
            )
        except Exception as exc:
            execution_errors.append(
                {
                    "organisation_number": org,
                    "error": f"{type(exc).__name__}: {str(exc)[:240]}",
                }
            )
            item["screen_status"] = "replacement_execution_error"
            rows.append(item)
            continue

        item["replacement_evaluation"] = result
        added = int(result.get("requests") or 0)
        replacement_requests += added
        if added > MAX_REPLACEMENT_LOGICAL_REQUESTS:
            execution_errors.append(
                {
                    "organisation_number": org,
                    "error": f"replacement used {added} logical site requests; max is 2",
                }
            )

        if not result.get("verified"):
            item["screen_status"] = "replacement_failed_exact_identity_gate"
            rows.append(item)
            continue

        verified += 1
        item["net_new_verified_website"] = True
        item["screen_status"] = "verified"
        defects: list[str] = []
        selected_url = str(result.get("selected_url") or "")
        if not selected_url.startswith(("http://", "https://")):
            defects.append("selected_url_missing")
        if len(str(result.get("website_content_sha256") or "")) != 64:
            defects.append("website_content_hash_missing")
        if not bool(result.get("identity_publishable")):
            defects.append("identity_not_publishable")
        if old_h1g["requests_added"] > MAX_REPLACEMENT_LOGICAL_REQUESTS:
            defects.append("replaced_h1g_slot_not_bounded")
        if defects:
            evidence_defects.append(
                {"organisation_number": org, "defects": defects}
            )
        manual.append(
            {
                "organisation_number": org,
                "legal_name": profile.get("name"),
                "municipality": profile.get("municipality"),
                "replaced_h1g_domain": old_h1g.get("candidate_domain"),
                "replaced_h1g_requests": old_h1g.get("requests_added"),
                "candidate_domain": result.get("candidate_domain"),
                "selected_url": selected_url,
                "website_source_url": result.get("website_source_url"),
                "website_content_sha256": result.get("website_content_sha256"),
                "identity_status": result.get("identity_status"),
                "identity_score": result.get("identity_score"),
                "identity_reasons": result.get("identity_reasons"),
                "registry_guard_reasons": result.get("guard_reasons"),
                "manual_review_finalized": False,
            }
        )
        rows.append(item)

    if len(rows) != 20:
        raise AssertionError("M16 screen lost companies")

    if evidence_defects or execution_errors:
        decision = "BLOCKED"
    elif verified >= MIN_NET_NEW_VERIFIED_WEBSITES:
        decision = "MANUAL_AUDIT_REQUIRED"
    else:
        decision = "SHELVE_LOW_YIELD"

    report = {
        "milestone": "M16",
        "screen": "consumed_h1g_slot_multitoken_compact_com_replacement",
        "machine_decision": decision,
        "companies": 20,
        "fresh_companies_used": 0,
        "baseline_verified_website_companies": baseline_verified,
        "unresolved_companies_where_h1g_actually_spent_slot": h1g_attempted_unresolved,
        "replacement_eligible_companies": replacement_eligible,
        "replacement_logical_requests_observed": replacement_requests,
        "replacement_logical_requests_per_company_ceiling": MAX_REPLACEMENT_LOGICAL_REQUESTS,
        "structural_site_request_ceiling_increase": 0,
        "net_new_verified_website_companies": verified,
        "minimum_net_new_verified_website_companies": MIN_NET_NEW_VERIFIED_WEBSITES,
        "manual_review_rows": len(manual),
        "manual_review_finalized": False,
        "evidence_defects": evidence_defects,
        "execution_errors": execution_errors,
        "third_party_api_cost_usd": 0.0,
        "search_api_requests": 0,
        "publication_authorized": False,
        "production_promotion_authorized": False,
        "fresh_qualification_authorized": False,
        "replacement_contract": (
            "M16 may replace only H1g's already-spent final two-request hyphenated-.no slot "
            "for unresolved multi-token companies. Compact .com nomination itself is never evidence; "
            "the independently fetched page must pass exact-company and registry-risk guards."
        ),
    }
    write_jsonl(args.output, rows)
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
