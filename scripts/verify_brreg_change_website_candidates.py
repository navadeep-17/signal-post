#!/usr/bin/env python3
"""Verify frozen BRREG change-feed website candidates with existing Signalpost gates.

Research-only transfer test:
- candidate nomination comes only from the already-frozen exact-org BRREG change-feed screen;
- no BRREG source request is repeated here;
- only currently uncovered companies are attempted;
- existing bounded homepage fetch, exact-company identity gate and registry-risk guard are reused;
- only aggregate metrics are persisted.
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
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.final_site_discovery import fetch_bounded_homepage  # noqa: E402
from norway_company_agent.identity import apply_website_identity_gate  # noqa: E402
from norway_company_agent.zero_cost_registry_guard import apply_registry_risk_guard  # noqa: E402


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


def normalize_candidate(value: Any) -> str:
    text = " ".join(str(value or "").strip().split())
    if not text or len(text) > 2048:
        raise ValueError("empty or oversized website candidate")
    if any(ch in text for ch in ("\x00", "\r", "\n")):
        raise ValueError("invalid control character in website candidate")
    if "://" not in text:
        text = "https://" + text.lstrip("/")
    parsed = urlsplit(text)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"invalid website candidate: {value!r}")
    return text


def read_candidates(
    path: Path,
    *,
    profiles: dict[str, dict[str, Any]],
    current_websites: set[str],
) -> list[tuple[str, dict[str, Any], str]]:
    rows: list[tuple[str, dict[str, Any], str]] = []
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError("candidate rows must be JSON objects")
        org = re.sub(r"\D", "", str(row.get("organisation_number") or ""))
        if len(org) != 9:
            raise ValueError(f"invalid candidate org: {org!r}")
        if org in seen:
            raise ValueError(f"duplicate candidate org: {org}")
        seen.add(org)
        if org not in profiles:
            raise ValueError(f"candidate org not in consumed profiles: {org}")
        if org in current_websites:
            raise ValueError(f"candidate already has verified website: {org}")
        rows.append((org, profiles[org], normalize_candidate(row.get("candidate"))))
    if not rows:
        raise ValueError("empty candidate set")
    return rows


def verify_one(
    row: tuple[str, dict[str, Any], str],
    *,
    timeout: float,
) -> dict[str, Any]:
    org, profile, candidate = row
    record, ops = fetch_bounded_homepage(
        candidate,
        source_type="brreg_change_feed_website_candidate",
        timeout=timeout,
    )
    gated = apply_website_identity_gate(profile, record)
    candidate_record = gated["website"]
    assessment = gated.get("assessment") or {}

    identity_publishable = bool(
        assessment.get("publishable")
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
            guarded.get("status") == "available"
            and guarded_assessment.get("publishable")
        )

    observed = [str(x) for x in assessment.get("observed_organisation_numbers") or []]
    wrong_explicit_org = bool(observed and org not in observed)
    return {
        "fetch_status": candidate_record.get("status") or "none",
        "site_requests": int(ops.get("requests") or 0),
        "identity_status": assessment.get("status") or "none",
        "identity_publishable": identity_publishable,
        "guard_publishable": guard_publishable,
        "wrong_explicit_org": wrong_explicit_org,
        "identity_reasons": list(assessment.get("reasons") or []) + [str(x) for x in guard_reasons],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles-dir", type=Path, required=True)
    ap.add_argument("--output-contract-gz", type=Path, required=True)
    ap.add_argument("--candidates", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--timeout", type=float, default=8.0)
    args = ap.parse_args()

    profiles = read_profiles(args.profiles_dir)
    current_web = current_website_orgs(args.output_contract_gz)
    candidates = read_candidates(
        args.candidates,
        profiles=profiles,
        current_websites=current_web,
    )

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        attempts = list(pool.map(lambda row: verify_one(row, timeout=args.timeout), candidates))

    fetch_counts = Counter(str(x.get("fetch_status") or "none") for x in attempts)
    identity_counts = Counter(str(x.get("identity_status") or "none") for x in attempts)
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
        "screen_type": "brreg_change_feed_website_existing_identity_gate_transfer",
        "companies": len(profiles),
        "current_verified_website_companies": len(current_web),
        "candidate_companies": len(candidates),
        "fetch_status_counts": dict(sorted(fetch_counts.items())),
        "identity_status_counts": dict(sorted(identity_counts.items())),
        "identity_publishable_companies": identity_ok,
        "registry_guard_publishable_companies": guard_ok,
        "wrong_explicit_org_companies": wrong_org,
        "logical_site_requests": requests,
        "verified_yield_per_candidate_company": round(guard_ok / len(candidates), 6),
        "verified_companies_per_logical_request": round(guard_ok / requests, 6) if requests else 0.0,
        "net_new_verified_website_reach": round(guard_ok / len(profiles), 6),
        "post_verified_website_companies": len(current_web) + guard_ok,
        "post_verified_website_reach": round((len(current_web) + guard_ok) / len(profiles), 6),
        "identity_reason_counts": dict(reason_counts.most_common()),
        "incremental_brreg_source_requests": 0,
        "third_party_cost_usd": 0.0,
        "search_api_requests": 0,
        "reuse_rights_status": "NLOD_2_0_BRREG_SOURCE",
        "candidate_values_retained": False,
        "organisation_lists_retained": False,
        "raw_page_values_retained": False,
        "production_publication_enabled": False,
        "notes": [
            "Candidate rows come from the frozen <=365-day exact-org BRREG change-feed website screen.",
            "No BRREG source request is repeated in this transfer test.",
            "The existing bounded homepage fetch, exact-company identity gate and registry-risk guard are reused unchanged.",
            "Only aggregate metrics are persisted.",
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
