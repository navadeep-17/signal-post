#!/usr/bin/env python3
"""Audit zero-network hiring/news recovery from retained exact-site pages.

Research-only. This audit performs no network access and writes aggregate counts only.
It measures:
- current frozen careers/job/update claim coverage;
- current strict first-party job/update extraction over archived retained pages;
- explicit retained same-company careers pages that were already fetched but may not have
  been projected as a careers-presence claim.

No new claims are published by this script.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.first_party_activity import extract_strict_first_party_facts
from norway_company_agent.homepage_careers_signal import _same_company_host

CAREER_SEGMENTS = {
    "career", "careers", "karriere", "karrierer",
    "jobb", "jobber", "stilling", "stillinger",
    "ledige-stillinger", "ledigestillinger", "vacancy", "vacancies",
    "join-us", "join-our-team", "work-with-us", "jobb-hos-oss", "jobbe-hos-oss",
}
CAREER_TITLE_PHRASES = (
    "career", "careers", "karriere", "jobb hos oss", "jobbe hos oss",
    "ledige stillinger", "vacancies", "vacancy", "join our team", "work with us",
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def read_jsonl_gz(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as h:
        return [json.loads(line) for line in h if line.strip()]


def _verified_site(profile: dict[str, Any]) -> tuple[dict[str, Any], str] | None:
    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") or {}
    assessment = value.get("identity_assessment") or {}
    final_url = str(value.get("final_url") or website.get("source_url") or "").strip()
    if (
        website.get("status") != "available"
        or not assessment.get("publishable")
        or not final_url.startswith(("http://", "https://"))
    ):
        return None
    return website, final_url


def _career_marker(url: str, title: str) -> str | None:
    try:
        path = urllib.parse.unquote(urllib.parse.urlparse(url).path or "")
    except ValueError:
        return None
    segments = [
        re.sub(r"[^a-z0-9æøå-]+", "-", part.casefold()).strip("-")
        for part in path.split("/")
        if part.strip()
    ]
    for segment in segments:
        if segment in CAREER_SEGMENTS:
            return f"path:{segment}"
    folded_title = " ".join(str(title or "").casefold().split())
    for phrase in CAREER_TITLE_PHRASES:
        if phrase in folded_title:
            return f"title:{phrase}"
    return None


def retained_careers_pages(profile: dict[str, Any]) -> list[dict[str, str]]:
    ctx = _verified_site(profile)
    if ctx is None:
        return []
    website, final_url = ctx
    value = website.get("value") or {}
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for page in value.get("pages") or []:
        if not isinstance(page, dict):
            continue
        url = str(page.get("url") or "").strip()
        title = str(page.get("title") or "").strip()
        content_hash = str(page.get("content_sha256") or "").strip()
        if (
            not url.startswith(("http://", "https://"))
            or url.rstrip("/") == final_url.rstrip("/")
            or url in seen
            or len(content_hash) != 64
            or not _same_company_host(url, final_url)
        ):
            continue
        marker = _career_marker(url, title)
        if not marker:
            continue
        seen.add(url)
        rows.append(
            {
                "url": url,
                "title": title[:300],
                "content_sha256": content_hash,
                "marker": marker,
            }
        )
    rows.sort(key=lambda x: (x["url"], x["title"]))
    return rows


def available_orgs(contracts: list[dict[str, Any]], field: str) -> set[str]:
    out: set[str] = set()
    for row in contracts:
        org = str(row.get("organisation_number") or "")
        if not org:
            continue
        if any(
            isinstance(c, dict)
            and c.get("field") == field
            and c.get("availability") == "available"
            for c in row.get("claims") or []
        ):
            out.add(org)
    return out


def audit(profiles: list[dict[str, Any]], contracts: list[dict[str, Any]]) -> dict[str, Any]:
    pindex = {str(p.get("organisation_number") or ""): p for p in profiles}
    cindex = {str(c.get("organisation_number") or ""): c for c in contracts}
    if len(pindex) != len(profiles) or len(cindex) != len(contracts) or set(pindex) != set(cindex):
        raise ValueError("profile/contract organisation sets differ or contain duplicates")

    verified: set[str] = set()
    retained_page_orgs: set[str] = set()
    strict_job_orgs: set[str] = set()
    strict_update_orgs: set[str] = set()
    retained_page_count = 0
    strict_job_count = 0
    strict_update_count = 0

    for org, profile in pindex.items():
        if _verified_site(profile):
            verified.add(org)
        careers = retained_careers_pages(profile)
        if careers:
            retained_page_orgs.add(org)
            retained_page_count += len(careers)
        facts = extract_strict_first_party_facts(profile)
        jobs = facts.get("jobs") or []
        updates = facts.get("updates") or []
        if jobs:
            strict_job_orgs.add(org)
            strict_job_count += len(jobs)
        if updates:
            strict_update_orgs.add(org)
            strict_update_count += len(updates)

    baseline_careers = available_orgs(contracts, "external.careers_page")
    baseline_jobs = available_orgs(contracts, "external.job_posting")
    baseline_updates = available_orgs(contracts, "external.company_update")
    baseline_social = available_orgs(contracts, "external.profile_handle")

    n = len(contracts)
    report = {
        "screen_type": "zero_network_retained_first_party_surface_audit_frozen1000",
        "companies": n,
        "verified_site_companies": len(verified),
        "baseline_careers_companies": len(baseline_careers),
        "baseline_job_companies": len(baseline_jobs),
        "baseline_dated_update_companies": len(baseline_updates),
        "baseline_social_profile_companies": len(baseline_social),
        "retained_explicit_careers_page_companies": len(retained_page_orgs),
        "retained_explicit_careers_pages": retained_page_count,
        "retained_careers_net_new_vs_baseline": len(retained_page_orgs - baseline_careers),
        "strict_retained_job_companies": len(strict_job_orgs),
        "strict_retained_job_facts": strict_job_count,
        "strict_jobs_net_new_vs_baseline": len(strict_job_orgs - baseline_jobs),
        "strict_retained_dated_update_companies": len(strict_update_orgs),
        "strict_retained_dated_update_facts": strict_update_count,
        "strict_updates_net_new_vs_baseline": len(strict_update_orgs - baseline_updates),
        "verified_site_conditional_careers_pct": round(
            100 * len(retained_page_orgs) / len(verified), 3
        ) if verified else 0.0,
        "verified_site_conditional_jobs_pct": round(
            100 * len(strict_job_orgs) / len(verified), 3
        ) if verified else 0.0,
        "verified_site_conditional_updates_pct": round(
            100 * len(strict_update_orgs) / len(verified), 3
        ) if verified else 0.0,
        "logical_requests_added": 0,
        "third_party_api_cost_usd_added": 0.0,
        "organisation_lists_retained": False,
        "raw_page_values_retained": False,
        "notes": [
            "Retained careers pages are already-fetched same-company pages with explicit careers markers in URL path or title.",
            "A careers page is a hiring-presence signal only; it is never an active vacancy.",
            "Strict jobs/updates reuse the current production first-party extractor and its existing semantic gates.",
            "This audit publishes no claims and performs no network access.",
        ],
    }
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles-dir", type=Path, required=True)
    ap.add_argument("--output-contract-gz", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()

    profiles: list[dict[str, Any]] = []
    for path in sorted(args.profiles_dir.rglob("profiles.jsonl")):
        profiles.extend(read_jsonl(path))
    contracts = read_jsonl_gz(args.output_contract_gz)
    if len(profiles) != 1000 or len(contracts) != 1000:
        raise SystemExit(f"expected 1000 profiles/contracts, got {len(profiles)}/{len(contracts)}")
    report = audit(profiles, contracts)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
