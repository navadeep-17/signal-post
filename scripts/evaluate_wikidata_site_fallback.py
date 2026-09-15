#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.run_signalpost_final import OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE  # noqa: E402
from norway_company_agent.final_site_discovery import MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE  # noqa: E402
from norway_company_agent.run_budget import RunBudget  # noqa: E402
from norway_company_agent.wikidata_discovery import (  # noqa: E402
    fetch_wikidata_website_candidates,
    theoretical_wikidata_lookup_requests,
)
from norway_company_agent.wikidata_fallback import apply_wikidata_fallback_to_existing_profile  # noqa: E402


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def verified_site(profile: dict[str, Any]) -> dict[str, Any] | None:
    website = (profile.get("evidence") or {}).get("website") or {}
    identity = (website.get("value") or {}).get("identity_assessment") or {}
    if website.get("status") != "available" or not identity.get("publishable"):
        return None
    return website


def source_name(website: dict[str, Any] | None) -> str:
    if not website:
        return "none"
    source_type = str(website.get("source_type") or "")
    return {
        "registry_linked_company_website": "registry_website",
        "registry_email_domain_candidate_website": "registry_email_domain",
        "deterministic_legal_name_domain_guess": "h1c_deterministic_domain",
        "wikidata_official_website_candidate": "wikidata_candidate",
    }.get(source_type, f"verified:{source_type}" if source_type else "verified:unknown")


def audit_row(profile: dict[str, Any]) -> dict[str, Any]:
    website = verified_site(profile) or {}
    value = website.get("value") or {}
    return {
        "organisation_number": profile.get("organisation_number"),
        "name": profile.get("name"),
        "municipality": profile.get("municipality"),
        "website": value.get("final_url") or website.get("source_url"),
        "source_type": website.get("source_type"),
        "content_sha256": website.get("content_sha256"),
        "identity_assessment": value.get("identity_assessment"),
        "identity_text_excerpt": value.get("identity_text_excerpt"),
        "main_text_excerpt": value.get("main_text_excerpt"),
        "wikidata_discovery": (profile.get("evidence") or {}).get("website_wikidata_discovery"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure incremental H1e Wikidata website fallback on completed H1d profiles.")
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--baseline-report", required=True)
    parser.add_argument("--output-profiles", required=True)
    parser.add_argument("--output-audit", required=True)
    parser.add_argument("--output-gained", required=True)
    parser.add_argument("--output-summary", required=True)
    parser.add_argument("--site-timeout", type=float, default=6.0)
    parser.add_argument("--wikidata-timeout", type=float, default=10.0)
    parser.add_argument("--max-challenge-requests", type=int, default=6000)
    args = parser.parse_args()

    profiles = load_jsonl(Path(args.profiles))
    baseline_report = json.loads(Path(args.baseline_report).read_text(encoding="utf-8"))
    if not profiles:
        raise SystemExit("No profiles supplied")
    orgs = [str(row.get("organisation_number") or "") for row in profiles]
    if len(orgs) != len(set(orgs)):
        raise SystemExit("Profiles contain duplicate organisation numbers")
    if baseline_report.get("passed") is not True:
        raise SystemExit("Baseline run report did not pass")

    candidates, wikidata_metrics = fetch_wikidata_website_candidates(
        orgs,
        timeout=args.wikidata_timeout,
    )

    baseline_verified = {org for org, row in zip(orgs, profiles) if verified_site(row)}
    updated: list[dict[str, Any]] = []
    added_site_requests = 0
    attempted = 0
    budget_skipped = 0

    for profile in profiles:
        org = str(profile["organisation_number"])
        run_metrics = profile.get("run_metrics") or {}
        logical_requests = int(run_metrics.get("logical_requests") or 0)
        current_site_requests = logical_requests - OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE
        if not 0 <= current_site_requests <= MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE:
            raise RuntimeError(
                f"Cannot derive H1d site requests for {org}: logical={logical_requests}, "
                f"official_ceiling={OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE}"
            )

        row, metrics = apply_wikidata_fallback_to_existing_profile(
            profile,
            wikidata_candidate=candidates.get(org),
            current_site_requests=current_site_requests,
            timeout=args.site_timeout,
        )
        added = int(metrics.get("added_requests") or 0)
        added_site_requests += added
        attempted += int(bool(metrics.get("wikidata_attempted")))
        budget_skipped += int(metrics.get("wikidata_skipped_reason") == "site_request_budget_consumed")

        if added:
            row_metrics = dict(row.get("run_metrics") or {})
            row_metrics["logical_requests"] = int(row_metrics.get("logical_requests") or 0) + added
            row_metrics["requests"] = int(row_metrics.get("requests") or 0) + (2 * added)
            row_metrics["bytes"] = int(row_metrics.get("bytes") or 0) + int(metrics.get("bytes") or 0)
            row_metrics["latencies_ms"] = [
                *list(row_metrics.get("latencies_ms") or []),
                *list(metrics.get("latencies_ms") or []),
            ]
            row_metrics["h1e_wikidata_added_logical_requests"] = added
            row["run_metrics"] = row_metrics
        updated.append(row)

    final_verified = {str(row["organisation_number"]) for row in updated if verified_site(row)}
    gained = sorted(final_verified - baseline_verified)
    lost = sorted(baseline_verified - final_verified)

    baseline_logical = int((baseline_report.get("request_budget") or {}).get("observed_logical_requests") or 0)
    baseline_conservative = int((baseline_report.get("request_budget") or {}).get("observed_conservative_challenge_request_charge") or 0)
    shared_lookup_requests = int(wikidata_metrics.get("requests") or 0)
    observed_logical = baseline_logical + shared_lookup_requests + added_site_requests
    observed_conservative = baseline_conservative + 2 * (shared_lookup_requests + added_site_requests)

    budget = RunBudget(max_challenge_requests=args.max_challenge_requests)
    theoretical_shared = theoretical_wikidata_lookup_requests(len(profiles))
    theoretical_profile_logical = len(profiles) * (
        OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE + MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE
    )
    theoretical_logical = theoretical_profile_logical + theoretical_shared
    theoretical_conservative = budget.charge_requests(theoretical_logical)

    source_mix: dict[str, int] = {}
    audit = []
    for row in updated:
        website = verified_site(row)
        source = source_name(website)
        source_mix[source] = source_mix.get(source, 0) + 1
        if website:
            audit.append(audit_row(row))

    gained_rows = [audit_row(row) for row in updated if str(row["organisation_number"]) in gained]
    errors = list(wikidata_metrics.get("errors") or [])
    checks = {
        "baseline_passed": baseline_report.get("passed") is True,
        "wikidata_lookup_clean": not errors,
        "zero_lost_verified_sites": not lost,
        "observed_request_budget_ok": observed_conservative <= args.max_challenge_requests,
        "theoretical_request_budget_ok": theoretical_conservative <= args.max_challenge_requests,
        "zero_third_party_cost": float((baseline_report.get("source_policy") or {}).get("third_party_cost_usd") or 0.0) == 0.0,
        "zero_search_api_requests": int((baseline_report.get("source_policy") or {}).get("search_api_requests") or 0) == 0,
    }

    summary = {
        "companies": len(profiles),
        "baseline_verified_sites": len(baseline_verified),
        "h1e_verified_sites": len(final_verified),
        "net_verified_site_gain": len(final_verified) - len(baseline_verified),
        "gained_orgs": gained,
        "lost_orgs": lost,
        "source_mix": dict(sorted(source_mix.items())),
        "wikidata": {
            **wikidata_metrics,
            "attempted_candidate_pages": attempted,
            "budget_skipped_candidates": budget_skipped,
            "verified_promotions": len(gained),
        },
        "request_budget": {
            "baseline_logical_requests": baseline_logical,
            "shared_wikidata_lookup_requests": shared_lookup_requests,
            "added_candidate_page_logical_requests": added_site_requests,
            "observed_logical_requests": observed_logical,
            "baseline_conservative_requests": baseline_conservative,
            "observed_conservative_requests": observed_conservative,
            "theoretical_shared_wikidata_requests": theoretical_shared,
            "theoretical_logical_request_ceiling": theoretical_logical,
            "theoretical_conservative_request_ceiling": theoretical_conservative,
            "max_challenge_requests": args.max_challenge_requests,
        },
        "third_party_cost_usd": 0.0,
        "search_api_requests": 0,
        "checks": checks,
        "passed": all(checks.values()),
    }

    write_jsonl(Path(args.output_profiles), updated)
    write_jsonl(Path(args.output_audit), audit)
    write_jsonl(Path(args.output_gained), gained_rows)
    output_summary = Path(args.output_summary)
    output_summary.parent.mkdir(parents=True, exist_ok=True)
    output_summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    raise SystemExit(0 if summary["passed"] else 1)


if __name__ == "__main__":
    main()
