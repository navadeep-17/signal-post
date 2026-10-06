#!/usr/bin/env python3
"""Verify net-new BRREG change-feed website candidates on the frozen consumed cohort.

Research-only transfer test. Candidate URLs are exact-org /hjemmeside values from the
official BRREG change feed and remain nomination evidence until the existing website
identity gate and registry-risk guard both accept the independently fetched page.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.final_site_discovery import fetch_bounded_homepage  # noqa: E402
from norway_company_agent.identity import apply_website_identity_gate  # noqa: E402
from norway_company_agent.zero_cost_registry_guard import apply_registry_risk_guard  # noqa: E402


def _org(value: Any) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) != 9:
        raise ValueError(f"invalid org number: {value!r}")
    return digits


def read_profiles(root: Path) -> dict[str, dict[str, Any]]:
    files = sorted(root.rglob("profiles.jsonl"))
    if not files:
        raise ValueError("no archived profiles.jsonl found")
    out: dict[str, dict[str, Any]] = {}
    for path in files:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            org = _org(row.get("organisation_number"))
            if org in out:
                raise ValueError(f"duplicate profile {org}")
            out[org] = row
    if len(out) != 1000:
        raise ValueError(f"expected 1000 archived profiles, got {len(out)}")
    return out


def read_candidates(path: Path) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        org = _org(row.get("organisation_number"))
        candidate = str(row.get("candidate") or "").strip()
        if not candidate or org in seen:
            raise ValueError("candidate rows require unique org + nonempty candidate")
        seen.add(org)
        out.append({"organisation_number": org, "candidate": candidate})
    return out


def verify_candidate(
    profile: dict[str, Any],
    candidate: str,
    *,
    timeout: float,
) -> dict[str, Any]:
    website, ops = fetch_bounded_homepage(
        candidate,
        source_type="brreg_change_feed_hjemmeside_shadow_candidate",
        timeout=timeout,
    )
    gated = apply_website_identity_gate(profile, website)
    assessment = gated.get("assessment") or {}
    candidate_record = gated["website"]

    guard_publishable = False
    guard_reasons: list[str] = []
    if (
        candidate_record.get("status") == "available"
        and assessment.get("publishable")
    ):
        trial = dict(profile)
        trial["evidence"] = {
            **(profile.get("evidence") or {}),
            "website": candidate_record,
        }
        trial["website"] = (
            (candidate_record.get("value") or {}).get("final_url")
            or candidate_record.get("source_url")
            or ""
        )
        trial, guard_reasons = apply_registry_risk_guard(trial)
        guarded = ((trial.get("evidence") or {}).get("website") or {})
        guarded_assessment = (guarded.get("value") or {}).get("identity_assessment") or {}
        guard_publishable = bool(
            guarded.get("status") == "available"
            and guarded_assessment.get("publishable")
        )

    org = _org(profile.get("organisation_number"))
    observed = {
        re.sub(r"\D", "", str(value or ""))
        for value in assessment.get("observed_organisation_numbers") or []
    }
    observed.discard("")
    wrong_explicit_org = bool(observed and org not in observed)

    return {
        "fetch_status": str(candidate_record.get("status") or "unknown"),
        "logical_site_requests": int(ops.get("requests") or 0),
        "identity_status": str(assessment.get("status") or "none"),
        "identity_publishable": bool(assessment.get("publishable")),
        "registry_guard_publishable": guard_publishable,
        "wrong_explicit_org": wrong_explicit_org,
        "reasons": [
            *[str(x) for x in assessment.get("reasons") or []],
            *[str(x) for x in guard_reasons],
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles-dir", type=Path, required=True)
    ap.add_argument("--candidates", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--timeout", type=float, default=8.0)
    args = ap.parse_args()

    profiles = read_profiles(args.profiles_dir)
    candidates = read_candidates(args.candidates)
    missing = [row["organisation_number"] for row in candidates if row["organisation_number"] not in profiles]
    if missing:
        raise ValueError(f"candidate profiles missing: {len(missing)}")

    results = [
        verify_candidate(profiles[row["organisation_number"]], row["candidate"], timeout=args.timeout)
        for row in candidates
    ]

    fetch = Counter(x["fetch_status"] for x in results)
    identity = Counter(x["identity_status"] for x in results)
    reasons = Counter(reason for x in results for reason in x["reasons"] if reason)
    accepted = sum(x["registry_guard_publishable"] for x in results)
    requests = sum(x["logical_site_requests"] for x in results)
    wrong = sum(x["wrong_explicit_org"] for x in results)

    report = {
        "screen_type": "brreg_change_feed_hjemmeside_exact_site_transfer",
        "candidate_companies": len(candidates),
        "fetch_status_counts": dict(sorted(fetch.items())),
        "identity_status_counts": dict(sorted(identity.items())),
        "identity_publishable_companies": sum(x["identity_publishable"] for x in results),
        "registry_guard_publishable_companies": accepted,
        "verified_yield_per_candidate_company": round(accepted / len(candidates), 6) if candidates else 0.0,
        "wrong_explicit_org_companies": wrong,
        "logical_site_requests": requests,
        "verified_companies_per_logical_request": round(accepted / requests, 6) if requests else 0.0,
        "net_new_verified_website_reach_on_consumed_1000": round(accepted / 1000, 6),
        "identity_reason_counts": dict(reasons.most_common()),
        "incremental_source_requests_if_integrated": 0,
        "third_party_cost_usd": 0.0,
        "search_api_requests": 0,
        "reuse_rights_status": "NLOD_2_0",
        "candidate_values_retained_in_report": False,
        "organisation_lists_retained_in_report": False,
        "production_publication_enabled": False,
        "notes": [
            "Candidate values come from the latest recent exact-org BRREG /hjemmeside change.",
            "Remove/blank latest changes were excluded by the upstream net-new screen.",
            "The independently fetched homepage must pass the existing identity gate and registry-risk guard.",
            "The BRREG change-feed source request family is already paid for in production; only site verification can add logical requests.",
            "This run uses only the frozen consumed 1000 and does not touch a fresh evaluator cohort.",
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
