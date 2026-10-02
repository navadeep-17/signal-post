#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.first_party_activity import extract_strict_first_party_facts  # noqa: E402
from norway_company_agent.verified_site_depth import crawl_verified_site_depth  # noqa: E402


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _fold(value: Any) -> str:
    text = str(value or "").translate(str.maketrans({"ø": "o", "Ø": "O", "å": "a", "Å": "A", "æ": "ae", "Æ": "AE"})).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", text))


def _verified_site(profile: dict[str, Any]) -> bool:
    website = ((profile.get("evidence") or {}).get("website") or {})
    identity = ((website.get("value") or {}).get("identity_assessment") or {})
    return website.get("status") == "available" and bool(identity.get("publishable"))


def _baseline_sets(profile: dict[str, Any]) -> dict[str, set[Any]]:
    observations = [item for item in (profile.get("external_observations") or []) if isinstance(item, dict)]
    contacts = {str(item.get("contact_email") or "").strip().casefold() for item in observations if item.get("contact_email")}
    socials = {
        (str(item.get("platform") or "").strip().casefold(), str(item.get("profile_url") or "").strip().rstrip("/"))
        for item in observations
        if item.get("profile_url")
    }
    first_party = extract_strict_first_party_facts(profile)
    jobs = {
        (str(item.get("title") or "").strip().casefold(), str(item.get("url") or "").strip().rstrip("/"))
        for item in first_party.get("jobs") or []
    }
    updates = {
        (str(item.get("title") or "").strip().casefold(), str(item.get("url") or "").strip().rstrip("/"))
        for item in first_party.get("updates") or []
    }

    role_names: set[str] = set()
    roles_record = ((profile.get("evidence") or {}).get("roles") or {})
    for item in ((roles_record.get("value") or {}).get("roles") or []):
        if not isinstance(item, dict) or item.get("inactive"):
            continue
        name = item.get("name")
        if isinstance(name, list):
            for value in name:
                if _fold(value):
                    role_names.add(_fold(value))
        elif _fold(name):
            role_names.add(_fold(name))

    locations: set[tuple[str, str]] = set()
    location_record = ((profile.get("evidence") or {}).get("locations") or {})
    for item in ((location_record.get("value") or {}).get("locations") or []):
        if not isinstance(item, dict):
            continue
        address = item.get("address") or {}
        postal = _fold(address.get("postnummer"))
        locality = _fold(address.get("poststed") or address.get("kommune"))
        if postal or locality:
            locations.add((postal, locality))

    return {
        "contact_emails": contacts,
        "social_profiles": socials,
        "jobs": jobs,
        "updates": updates,
        "leadership": role_names,
        "locations": locations,
    }


def _is_new(fact_type: str, item: dict[str, Any], baseline: dict[str, set[Any]]) -> bool:
    if fact_type == "contact_emails":
        return str(item.get("email") or "").strip().casefold() not in baseline[fact_type]
    if fact_type == "social_profiles":
        key = (str(item.get("platform") or "").strip().casefold(), str(item.get("url") or "").strip().rstrip("/"))
        return key not in baseline[fact_type]
    if fact_type in {"jobs", "updates"}:
        key = (str(item.get("title") or "").strip().casefold(), str(item.get("url") or "").strip().rstrip("/"))
        return key not in baseline[fact_type]
    if fact_type == "leadership":
        return bool(_fold(item.get("name"))) and _fold(item.get("name")) not in baseline[fact_type]
    if fact_type == "locations":
        key = (_fold(item.get("postal_code")), _fold(item.get("locality")))
        return bool(key[0] or key[1]) and key not in baseline[fact_type]
    return False


def _audit_fact(profile: dict[str, Any], fact_type: str, item: dict[str, Any]) -> dict[str, Any]:
    return {
        "organisation_number": str(profile.get("organisation_number") or ""),
        "company_name": profile.get("name"),
        "fact_type": fact_type,
        "value": item,
        "source_url": item.get("source_url") or item.get("url"),
        "content_sha256": item.get("content_sha256"),
        "retrieved_at": item.get("retrieved_at"),
        "strategy": item.get("strategy") or f"v6d_{fact_type}",
        "exact_site_precondition": True,
        "requires_manual_audit_before_promotion": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="V6d bounded depth extraction over V5 exact verified company sites.")
    parser.add_argument("--input-profiles", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--new-facts", required=True)
    parser.add_argument("--site-audit", required=True)
    parser.add_argument("--timeout", type=float, default=6.0)
    parser.add_argument("--max-added-logical-requests", type=int, default=180)
    parser.add_argument("--max-requests-per-site", type=int, default=10)
    parser.add_argument("--max-section-pages", type=int, default=4)
    parser.add_argument("--max-detail-pages", type=int, default=2)
    args = parser.parse_args()
    if args.max_added_logical_requests < 1 or args.max_requests_per_site < 2:
        raise SystemExit("V6d request ceilings must be positive and per-site ceiling must be at least 2")

    rows = read_jsonl(Path(args.input_profiles))
    verified = [row for row in rows if _verified_site(row)]
    started = time.monotonic()
    total_requests = 0
    total_bytes = 0
    total_latencies: list[int] = []
    total_errors: list[str] = []
    outside_rejections = 0
    robots_blocked = 0
    site_audit: list[dict[str, Any]] = []
    new_facts: list[dict[str, Any]] = []
    all_fact_counts = {key: 0 for key in ("contact_emails", "social_profiles", "locations", "leadership", "jobs", "updates")}
    new_fact_counts = dict(all_fact_counts)
    companies_by_new_fact = {key: set() for key in all_fact_counts}
    sites_crawled = 0
    sites_with_new_facts = 0
    budget_exhausted = False

    for profile in verified:
        remaining = args.max_added_logical_requests - total_requests
        if remaining < 2:
            budget_exhausted = True
            break
        allowance = min(args.max_requests_per_site, remaining)
        result, metrics = crawl_verified_site_depth(
            profile,
            timeout=args.timeout,
            max_section_pages=args.max_section_pages,
            max_detail_pages=args.max_detail_pages,
            request_allowance=allowance,
        )
        used = int(metrics.get("requests") or 0)
        if used > allowance:
            raise SystemExit(f"V6d per-site request ceiling violated for {profile.get('organisation_number')}: {used}>{allowance}")
        total_requests += used
        total_bytes += int(metrics.get("bytes") or 0)
        total_latencies.extend(int(value) for value in metrics.get("latencies_ms") or [])
        total_errors.extend(str(value) for value in metrics.get("errors") or [])
        outside_rejections += int(metrics.get("outside_domain_rejections") or 0)
        robots_blocked += int(metrics.get("robots_blocked") or 0)
        sites_crawled += int(bool(result.get("eligible") and result.get("pages")))

        baseline = _baseline_sets(profile)
        site_new = 0
        site_counts = {key: 0 for key in all_fact_counts}
        site_new_counts = dict(site_counts)
        for fact_type, items in (result.get("facts") or {}).items():
            if fact_type not in all_fact_counts:
                continue
            for item in items or []:
                if not isinstance(item, dict):
                    continue
                all_fact_counts[fact_type] += 1
                site_counts[fact_type] += 1
                if not _is_new(fact_type, item, baseline):
                    continue
                audit = _audit_fact(profile, fact_type, item)
                if not str(audit.get("source_url") or "").startswith(("http://", "https://")):
                    continue
                if not str(audit.get("content_sha256") or "") or len(str(audit.get("content_sha256"))) != 64:
                    continue
                new_facts.append(audit)
                new_fact_counts[fact_type] += 1
                site_new_counts[fact_type] += 1
                companies_by_new_fact[fact_type].add(str(profile.get("organisation_number") or ""))
                site_new += 1
        if site_new:
            sites_with_new_facts += 1

        site_audit.append({
            "organisation_number": str(profile.get("organisation_number") or ""),
            "name": profile.get("name"),
            "verified_site_url": result.get("verified_site_url"),
            "eligible": result.get("eligible"),
            "reason": result.get("reason"),
            "pages_fetched": len(result.get("pages") or []),
            "sitemap_candidate_count": result.get("sitemap_candidate_count", 0),
            "feed_entries": len(result.get("feed_entries") or []),
            "fact_counts": site_counts,
            "net_new_fact_counts": site_new_counts,
            "logical_requests": used,
            "bytes": int(metrics.get("bytes") or 0),
            "errors": list(metrics.get("errors") or []),
            "outside_domain_rejections": int(metrics.get("outside_domain_rejections") or 0),
            "robots_blocked": int(metrics.get("robots_blocked") or 0),
        })

    if total_requests > args.max_added_logical_requests:
        raise SystemExit("V6d global request ceiling violated")

    write_jsonl(Path(args.new_facts), new_facts)
    write_jsonl(Path(args.site_audit), site_audit)
    elapsed = time.monotonic() - started
    conservative_charge = total_requests * 2
    report = {
        "experiment": "V6d verified-site depth",
        "input_profiles": len(rows),
        "exact_verified_sites": len(verified),
        "sites_crawled": sites_crawled,
        "sites_with_net_new_facts": sites_with_new_facts,
        "max_added_logical_requests": args.max_added_logical_requests,
        "max_requests_per_site": args.max_requests_per_site,
        "logical_requests_added": total_requests,
        "conservative_request_charge_added": conservative_charge,
        "bytes_added": total_bytes,
        "wall_runtime_seconds": round(elapsed, 3),
        "request_latency_ms": {
            "p50": sorted(total_latencies)[len(total_latencies) // 2] if total_latencies else None,
            "max": max(total_latencies) if total_latencies else None,
        },
        "all_extracted_fact_counts": all_fact_counts,
        "net_new_fact_counts": new_fact_counts,
        "net_new_facts": len(new_facts),
        "companies_with_net_new_fact_by_type": {key: len(value) for key, value in companies_by_new_fact.items()},
        "net_new_facts_per_conservative_request": len(new_facts) / conservative_charge if conservative_charge else 0.0,
        "outside_domain_rejections": outside_rejections,
        "robots_blocked": robots_blocked,
        "errors": total_errors,
        "budget_exhausted": budget_exhausted,
        "automatic_identity_conflicts_published": 0,
        "third_party_api_cost_usd": 0.0,
        "publication_status": "experiment_only_manual_audit_required",
        "identity_policy": "V6d runs only after the existing V5 exact-company website gate; it cannot create or upgrade website identity.",
        "promotion_metric": "net-new accepted decision-useful facts / added conservative request charge",
    }
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
