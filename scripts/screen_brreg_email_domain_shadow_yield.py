#!/usr/bin/env python3
"""Consumed-only live yield screen for strong BRREG email-domain website candidates.

Exact BRREG registry email domains are nomination evidence only. Publication-worthiness
is measured with the existing production homepage fetch, website identity gate, email-
domain hardening and registry-risk guard unchanged.

Research only:
- frozen consumed 1000;
- no search provider;
- no fresh evaluator cohort;
- one strong domain candidate per uncovered company;
- aggregate report only; no raw domains/pages/organisation lists persisted.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import gzip
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.domain_discovery import (  # noqa: E402
    GENERIC_EMAIL_DOMAINS,
    _domain_identity_strength,
    qualify_registry_email_domain_identity,
    registry_email_domain_candidates,
)
from norway_company_agent.final_site_discovery import fetch_bounded_homepage  # noqa: E402
from norway_company_agent.identity import apply_website_identity_gate  # noqa: E402
from norway_company_agent.zero_cost_registry_guard import apply_registry_risk_guard  # noqa: E402


STRONG = {"exact", "multi", "acronym"}
RANK = {"exact": 3, "acronym": 2, "multi": 1}


def _claims(row: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for claim in row.get("claims") or []:
        if isinstance(claim, dict) and claim.get("field"):
            out.setdefault(str(claim["field"]), []).append(claim)
    return out


def _available_value(claims: dict[str, list[dict[str, Any]]], field: str) -> Any:
    for claim in claims.get(field) or []:
        if claim.get("availability") == "available" and claim.get("value") not in (None, ""):
            return claim.get("value")
    return None


def read_profiles(path: Path) -> dict[str, dict[str, Any]]:
    files = sorted(path.rglob("profiles.jsonl"))
    if not files:
        raise ValueError("no profiles.jsonl found")
    out: dict[str, dict[str, Any]] = {}
    for file in files:
        for line in file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            org = re.sub(r"\D", "", str(row.get("organisation_number") or ""))
            if len(org) != 9 or org in out:
                raise ValueError(f"invalid or duplicate profile org: {org!r}")
            out[org] = row
    if len(out) != 1000:
        raise ValueError(f"expected 1000 archived profiles, got {len(out)}")
    return out


def current_website_orgs(path: Path) -> set[str]:
    out: set[str] = set()
    seen: set[str] = set()
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            org = re.sub(r"\D", "", str(row.get("organisation_number") or ""))
            if len(org) != 9 or org in seen:
                raise ValueError(f"invalid or duplicate output org: {org!r}")
            seen.add(org)
            if _available_value(_claims(row), "official_website"):
                out.add(org)
    if len(seen) != 1000:
        raise ValueError(f"expected 1000 output companies, got {len(seen)}")
    return out


def select_candidate(profile: dict[str, Any]) -> dict[str, Any] | None:
    plan = registry_email_domain_candidates(profile)
    if not plan.get("eligible"):
        return None
    ranked: list[tuple[int, str, dict[str, Any]]] = []
    for candidate in plan.get("candidates") or []:
        domain = str(candidate.get("domain") or "").strip().casefold()
        if not domain or domain in GENERIC_EMAIL_DOMAINS:
            continue
        strength = _domain_identity_strength(profile, domain)
        if strength not in STRONG:
            continue
        ranked.append((RANK[strength], domain, {**candidate, "strength": strength}))
    if not ranked:
        return None
    ranked.sort(key=lambda row: (-row[0], row[1]))
    return ranked[0][2]


def strong_candidates(
    profiles: dict[str, dict[str, Any]],
    current_websites: set[str],
) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    rows: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    for org in sorted(profiles):
        if org in current_websites:
            continue
        profile = profiles[org]
        candidate = select_candidate(profile)
        if candidate:
            rows.append((org, profile, candidate))
    return rows


def verify_one(
    row: tuple[str, dict[str, Any], dict[str, Any]],
    *,
    timeout: float,
) -> dict[str, Any]:
    org, profile, candidate = row
    domain = str(candidate["domain"])
    record, ops = fetch_bounded_homepage(
        candidate.get("url") or domain,
        source_type="brreg_registry_email_domain_shadow_candidate",
        timeout=timeout,
    )
    gated = apply_website_identity_gate(profile, record)
    candidate_record = gated["website"]
    assessment = qualify_registry_email_domain_identity(
        profile,
        domain,
        candidate_record,
        gated.get("assessment"),
    )
    if assessment is not None:
        value = candidate_record.get("value") or {}
        value["identity_assessment"] = assessment
        candidate_record["value"] = value

    identity_publishable = bool(
        assessment
        and assessment.get("publishable")
        and candidate_record.get("status") == "available"
    )
    guard_publishable = False
    guard_reasons: list[str] = []
    if identity_publishable:
        trial = dict(profile)
        trial["evidence"] = {**(profile.get("evidence") or {}), "website": candidate_record}
        trial["website"] = (
            (candidate_record.get("value") or {}).get("final_url")
            or candidate_record.get("source_url")
            or ""
        )
        trial, guard_reasons = apply_registry_risk_guard(trial)
        guarded = ((trial.get("evidence") or {}).get("website") or {})
        guarded_assessment = (guarded.get("value") or {}).get("identity_assessment") or {}
        guard_publishable = bool(
            guarded.get("status") == "available" and guarded_assessment.get("publishable")
        )

    observed = list((assessment or {}).get("observed_organisation_numbers") or [])
    wrong_explicit_org = bool(observed and org not in observed)
    return {
        "candidate_strength": candidate.get("strength"),
        "fetch_status": candidate_record.get("status"),
        "site_requests": int(ops.get("requests") or 0),
        "identity_status": (assessment or {}).get("status") or "none",
        "identity_publishable": identity_publishable,
        "guard_publishable": guard_publishable,
        "wrong_explicit_org": wrong_explicit_org,
        "identity_reasons": list((assessment or {}).get("reasons") or []) + [str(x) for x in guard_reasons],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles-dir", type=Path, required=True)
    ap.add_argument("--output-contract-gz", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--timeout", type=float, default=8.0)
    args = ap.parse_args()

    profiles = read_profiles(args.profiles_dir)
    current_web = current_website_orgs(args.output_contract_gz)
    candidates = strong_candidates(profiles, current_web)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        attempts = list(pool.map(lambda row: verify_one(row, timeout=args.timeout), candidates))

    fetch_counts = Counter(str(x.get("fetch_status") or "none") for x in attempts)
    identity_counts = Counter(str(x.get("identity_status") or "none") for x in attempts)
    strength_counts = Counter(str(x.get("candidate_strength") or "none") for x in attempts)
    reason_counts = Counter(
        str(reason)
        for x in attempts
        for reason in x.get("identity_reasons") or []
        if str(reason).strip()
    )
    identity_ok = sum(bool(x.get("identity_publishable")) for x in attempts)
    guard_ok = sum(bool(x.get("guard_publishable")) for x in attempts)
    wrong_org = sum(bool(x.get("wrong_explicit_org")) for x in attempts)
    requests = sum(int(x.get("site_requests") or 0) for x in attempts)

    report = {
        "screen_type": "brreg_strong_email_domain_existing_identity_gate_shadow_yield",
        "companies": len(profiles),
        "current_verified_website_companies": len(current_web),
        "strong_candidate_companies": len(candidates),
        "candidate_strength_counts": dict(sorted(strength_counts.items())),
        "fetch_status_counts": dict(sorted(fetch_counts.items())),
        "identity_status_counts": dict(sorted(identity_counts.items())),
        "identity_publishable_companies": identity_ok,
        "registry_guard_publishable_companies": guard_ok,
        "verified_yield_per_candidate_company": round(guard_ok / len(candidates), 6) if candidates else 0.0,
        "net_new_verified_website_reach": round(guard_ok / len(profiles), 6),
        "post_verified_website_companies": len(current_web) + guard_ok,
        "post_verified_website_reach": round((len(current_web) + guard_ok) / len(profiles), 6),
        "wrong_explicit_org_companies": wrong_org,
        "logical_site_requests": requests,
        "verified_companies_per_logical_request": round(guard_ok / requests, 6) if requests else 0.0,
        "identity_reason_counts": dict(reason_counts.most_common()),
        "third_party_cost_usd": 0.0,
        "search_api_requests": 0,
        "reuse_rights_status": "NLOD_2_0_BRREG_SOURCE",
        "candidate_values_retained": False,
        "organisation_lists_retained": False,
        "raw_page_values_retained": False,
        "production_publication_enabled": False,
        "notes": [
            "Raw candidate domains come only from exact BRREG registry email evidence.",
            "Only exact/multi/acronym legal-name/domain candidates for currently uncovered consumed companies are attempted.",
            "The existing bounded homepage fetch, website identity gate, email-domain hardening and registry-risk guard are reused unchanged.",
            "No search provider, paid API or fresh evaluator cohort is used.",
            "Only aggregate research metrics are persisted.",
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
