#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.batch import (  # noqa: E402
    profiles_from_bulk,
    read_organisation_inputs,
    terminal_envelope,
    validate_envelopes,
)
from norway_company_agent.company_site_contact import attach_company_site_contact_email_observations  # noqa: E402
from norway_company_agent.company_site_social import attach_company_site_social_observations  # noqa: E402
from norway_company_agent.registry_workforce import attach_registry_workforce_observations  # noqa: E402
from norway_company_agent.evidence import utc_now  # noqa: E402
from norway_company_agent.external_contract import (  # noqa: E402
    project_contact_email_observations,
    project_profile_handle_observations,
)
from norway_company_agent.external_footprint import validate_observation  # noqa: E402
from norway_company_agent.workforce_contract import project_workforce_observations  # noqa: E402
from norway_company_agent.final_site_discovery import (  # noqa: E402
    MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE,
)
from norway_company_agent.h1g_hyphenated_no_recall import evaluate_hyphenated_no_fallback  # noqa: E402
from norway_company_agent.http import fetch_json  # noqa: E402
from norway_company_agent.official import fetch_official_modules  # noqa: E402
from norway_company_agent.output_contract import (  # noqa: E402
    project_terminal_envelope,
    validate_contract_object,
)
from norway_company_agent.refresh_contract import (  # noqa: E402
    group_refresh_events,
    validate_refresh_change,
)
from norway_company_agent.run_budget import RunBudget  # noqa: E402
from norway_company_agent.wikidata_discovery import (  # noqa: E402
    WIKIDATA_BATCH_SIZE,
    discover_final_website_with_wikidata,
    fetch_wikidata_website_candidates,
    theoretical_wikidata_lookup_requests,
)

OFFICIAL_FETCH_MODULES = {"registry_live", "financials", "roles", "group", "locations"}
FINAL_MODULES = [
    "registry",
    "accounting_obligation",
    "registry_live",
    "financials",
    "roles",
    "group",
    "locations",
    "website",
]
OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE = len(OFFICIAL_FETCH_MODULES)
THIRD_PARTY_COST_USD = 0.0
DEFAULT_MAX_CHALLENGE_REQUESTS = 1802


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    temporary.replace(path)


def _read_refresh_events(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    body = json.loads(path.read_text(encoding="utf-8"))
    events = body.get("events", []) if isinstance(body, dict) else body
    if not isinstance(events, list) or not all(isinstance(item, dict) for item in events):
        raise ValueError("Refresh report must contain an events[] list of objects")
    return events


def _percentile(values: list[int], fraction: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * fraction))]


def _canonical_verified_site_source(profile: dict[str, Any]) -> str:
    """Classify the final canonical website evidence, not transient discovery metrics."""
    website = ((profile.get("evidence") or {}).get("website") or {})
    assessment = ((website.get("value") or {}).get("identity_assessment") or {})
    if website.get("status") != "available" or not assessment.get("publishable"):
        return "none"
    source_type = str(website.get("source_type") or "")
    mapping = {
        "registry_linked_company_website": "registry_website",
        "registry_email_domain_candidate_website": "registry_email_domain",
        "deterministic_legal_name_domain_guess": "h1c_deterministic_domain",
        "wikidata_official_website_candidate": "wikidata_candidate",
        "deterministic_legal_name_hyphenated_no_fallback": "h1g_hyphenated_no",
    }
    return mapping.get(source_type, f"verified:{source_type}" if source_type else "verified:unknown")


def _enrich_profile(
    profile: dict[str, Any],
    *,
    budget: RunBudget,
    site_timeout: float,
    wikidata_candidate: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    # One official attempt per endpoint. Redirects are bounded separately and covered by
    # the conservative challenge charge multiplier.
    official_fetcher = partial(fetch_json, attempts=1)
    records, official_results = fetch_official_modules(
        profile["organisation_number"],
        OFFICIAL_FETCH_MODULES,
        fetcher=official_fetcher,
    )
    profile.setdefault("evidence", {}).update(records)

    official_logical_requests = sum(int(getattr(result, "request_count", 1)) for result in official_results)
    if official_logical_requests > OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE:
        raise RuntimeError(
            f"Official request ceiling exceeded for {profile['organisation_number']}: "
            f"{official_logical_requests}>{OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE}"
        )

    profile, site_metrics = discover_final_website_with_wikidata(
        profile,
        wikidata_candidate=wikidata_candidate,
        timeout=site_timeout,
    )

    # H1g is deliberately last in website discovery. It receives the request count already
    # consumed by H1d/H1e and can run only when two of the existing four logical site-request
    # slots remain. This preserves Wikidata priority and does not raise the structural ceiling.
    profile, h1g_result = evaluate_hyphenated_no_fallback(
        profile,
        timeout=site_timeout,
        base_site_logical_requests=int(site_metrics.get("requests") or 0),
    )
    site_metrics["h1g_candidate_available"] = bool(h1g_result.get("candidate_available"))
    site_metrics["h1g_attempted"] = bool(h1g_result.get("attempted"))
    site_metrics["h1g_verified"] = bool(h1g_result.get("verified"))
    if h1g_result.get("skipped_reason"):
        site_metrics["h1g_skipped_reason"] = str(h1g_result["skipped_reason"])
    if h1g_result.get("guard_reasons"):
        site_metrics["h1g_guard_reasons"] = list(h1g_result["guard_reasons"])
    site_metrics["requests"] = int(site_metrics.get("requests") or 0) + int(h1g_result.get("requests_added") or 0)
    site_metrics["bytes"] = int(site_metrics.get("bytes") or 0) + int(h1g_result.get("bytes_added") or 0)
    site_metrics.setdefault("latencies_ms", []).extend(
        int(value) for value in (h1g_result.get("latencies_ms") or []) if value is not None
    )
    if h1g_result.get("verified"):
        site_metrics["selected_source"] = "h1g_hyphenated_no"
        site_metrics["promoted"] = True

    site_logical_requests = int(site_metrics.get("requests") or 0)
    if site_logical_requests > MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE:
        raise RuntimeError(
            f"Site request ceiling exceeded for {profile['organisation_number']}: "
            f"{site_logical_requests}>{MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE}"
        )

    # H2a and H2c are zero-network projections over the already-qualified company-page
    # snapshot. Neither fetches an external platform nor changes request accounting.
    attach_company_site_social_observations(profile)
    attach_company_site_contact_email_observations(profile)
    attach_registry_workforce_observations(profile)

    logical_requests = official_logical_requests + site_logical_requests
    conservative_charge = budget.charge_requests(logical_requests)
    latencies = [int(result.elapsed_ms) for result in official_results if result.elapsed_ms is not None]
    latencies.extend(int(value) for value in site_metrics.get("latencies_ms") or [] if value is not None)
    bytes_received = sum(int(result.bytes_received) for result in official_results) + int(site_metrics.get("bytes") or 0)
    profile["run_metrics"] = {
        "logical_requests": logical_requests,
        # OUTPUT_CONTRACT operations.requests deliberately reports the conservative upper
        # bound for requests attributable to this company. Shared batch discovery is
        # counted separately in the global run report.
        "requests": conservative_charge,
        "bytes": bytes_received,
        "latencies_ms": latencies,
        "third_party_cost_usd": THIRD_PARTY_COST_USD,
    }
    return profile, {
        "organisation_number": profile["organisation_number"],
        "official_logical_requests": official_logical_requests,
        "site_logical_requests": site_logical_requests,
        "logical_requests": logical_requests,
        "conservative_challenge_request_charge": conservative_charge,
        "site": site_metrics,
    }


def _external_observation_audit(
    profiles: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], list[dict[str, Any]], list[dict[str, Any]]]:
    errors: list[dict[str, str]] = []
    handles: list[dict[str, Any]] = []
    contact_emails: list[dict[str, Any]] = []
    for profile in profiles:
        org = str(profile.get("organisation_number") or "")
        for observation in profile.get("external_observations") or []:
            if not isinstance(observation, dict):
                continue
            observation_id = str(observation.get("id") or "")
            if str(observation.get("organisation_number") or "") != org:
                errors.append(
                    {
                        "organisation_number": org,
                        "observation_id": observation_id,
                        "error": "external observation organisation number mismatch",
                    }
                )
            for error in validate_observation(observation):
                errors.append(
                    {
                        "organisation_number": org,
                        "observation_id": observation_id,
                        "error": error,
                    }
                )
            if observation.get("signal_type") == "profile_handle":
                handles.append(observation)
            elif observation.get("signal_type") == "company_profile" and observation.get("contact_email"):
                contact_emails.append(observation)
    return errors, handles, contact_emails


def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-command Signalpost evaluator runner using only qualified zero-cost sources."
    )
    parser.add_argument("--organisations", required=True, help="JSON/JSONL/text organisation-number input")
    parser.add_argument("--bulk", required=True, help="Frozen BRREG entity bulk CSV")
    parser.add_argument("--output", required=True, help="Final OUTPUT_CONTRACT.md JSONL")
    parser.add_argument("--report", required=True, help="Machine-readable final run report")
    parser.add_argument("--work-dir", default="out/final-run")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--expected-count", type=int, default=100)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--site-timeout", type=float, default=6.0)
    parser.add_argument("--wikidata-timeout", type=float, default=8.0)
    parser.add_argument("--max-challenge-requests", type=int, default=DEFAULT_MAX_CHALLENGE_REQUESTS)
    parser.add_argument("--max-third-party-cost-usd", type=float, default=0.0)
    parser.add_argument("--max-wall-runtime-seconds", type=int, default=2400)
    parser.add_argument("--refresh-report", help="Optional refresh report with events[]")
    args = parser.parse_args()

    if args.expected_count < 1:
        parser.error("--expected-count must be positive")
    if args.workers < 1:
        parser.error("--workers must be positive")
    if args.site_timeout <= 0:
        parser.error("--site-timeout must be positive")
    if args.wikidata_timeout <= 0:
        parser.error("--wikidata-timeout must be positive")
    if args.max_challenge_requests < 1:
        parser.error("--max-challenge-requests must be positive")
    if args.max_third_party_cost_usd < 0:
        parser.error("--max-third-party-cost-usd cannot be negative")
    if args.max_wall_runtime_seconds < 1:
        parser.error("--max-wall-runtime-seconds must be positive")

    budget = RunBudget(
        max_challenge_requests=args.max_challenge_requests,
        max_third_party_cost_usd=args.max_third_party_cost_usd,
        max_wall_runtime_seconds=args.max_wall_runtime_seconds,
        max_redirects_per_logical_request=1,
    )
    per_profile_logical_ceiling = OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE + MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE
    theoretical_shared_wikidata_requests = theoretical_wikidata_lookup_requests(args.expected_count)
    theoretical_logical_ceiling = (
        args.expected_count * per_profile_logical_ceiling
        + theoretical_shared_wikidata_requests
    )
    theoretical_charge_ceiling = budget.charge_requests(theoretical_logical_ceiling)
    if theoretical_charge_ceiling > args.max_challenge_requests:
        raise SystemExit(
            f"Configured pipeline cannot prove request safety: theoretical charge "
            f"{theoretical_charge_ceiling}>{args.max_challenge_requests}. "
            "Reduce expected count or raise the explicit budget only within the challenge's request cap."
        )

    wall_start = time.monotonic()
    started_at = utc_now()
    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    organisation_inputs = read_organisation_inputs(args.organisations)
    if len(organisation_inputs) != args.expected_count:
        raise SystemExit(
            f"Expected {args.expected_count} organisations, received {len(organisation_inputs)}"
        )
    orgs = [item["organisation_number"] for item in organisation_inputs]
    profiles, registry_metadata = profiles_from_bulk(args.bulk, orgs)
    annotations = {item["organisation_number"]: item for item in organisation_inputs}
    for profile in profiles:
        for key in ("evaluation_split", "sample_slice"):
            if key in annotations[profile["organisation_number"]]:
                profile[key] = annotations[profile["organisation_number"]][key]

    # H1e is a shared, exact-ID candidate lookup. It is deliberately non-fatal: if the
    # public WDQS endpoint is unavailable or throttled, the candidate map is empty/partial
    # and every company still completes through the already-qualified H1d path.
    wikidata_candidates, wikidata_metrics = fetch_wikidata_website_candidates(
        orgs,
        timeout=args.wikidata_timeout,
    )
    shared_wikidata_logical_requests = int(wikidata_metrics.get("requests") or 0)
    if shared_wikidata_logical_requests > theoretical_shared_wikidata_requests:
        raise RuntimeError(
            "Wikidata lookup exceeded theoretical batch-request ceiling: "
            f"{shared_wikidata_logical_requests}>{theoretical_shared_wikidata_requests}"
        )

    state: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(
                _enrich_profile,
                profile,
                budget=budget,
                site_timeout=args.site_timeout,
                wikidata_candidate=wikidata_candidates.get(profile["organisation_number"]),
            ): profile["organisation_number"]
            for profile in profiles
        }
        for future in as_completed(futures):
            profile, _profile_report = future.result()
            state[profile["organisation_number"]] = profile

    completed_at = utc_now()
    ordered_profiles = [state[org] for org in orgs]
    external_observation_errors, profile_handle_observations, contact_email_observations = _external_observation_audit(
        ordered_profiles
    )

    envelopes = [
        terminal_envelope(
            profile,
            run_id=args.run_id,
            modules=FINAL_MODULES,
            started_at=started_at,
            completed_at=completed_at,
        )
        for profile in ordered_profiles
    ]
    internal_validation = validate_envelopes(envelopes, args.expected_count)

    refresh_events = _read_refresh_events(Path(args.refresh_report) if args.refresh_report else None)
    changes_by_org = group_refresh_events(refresh_events, expected_organisation_numbers=set(orgs))
    projected: list[dict[str, Any]] = []
    for envelope in envelopes:
        contract = project_terminal_envelope(
            envelope,
            third_party_cost_usd=THIRD_PARTY_COST_USD,
            changes=changes_by_org[envelope["organisation_number"]],
        )
        contract = project_profile_handle_observations(contract, envelope["profile"])
        contract = project_contact_email_observations(contract, envelope["profile"])
        projected.append(project_workforce_observations(contract, envelope["profile"]))

    contract_errors: list[dict[str, str]] = []
    change_errors: list[dict[str, str]] = []
    for item in projected:
        org = item["organisation_number"]
        contract_errors.extend(
            {"organisation_number": org, "error": error}
            for error in validate_contract_object(item)
        )
        for change in item.get("changes") or []:
            change_errors.extend(
                {"organisation_number": org, "field": str(change.get("field") or ""), "error": error}
                for error in validate_refresh_change(change, expected_org=org)
            )

    wall_runtime_seconds = time.monotonic() - wall_start
    profile_logical_requests = sum(
        int((profile.get("run_metrics") or {}).get("logical_requests") or 0)
        for profile in ordered_profiles
    )
    profile_charged_requests = sum(
        int((profile.get("run_metrics") or {}).get("requests") or 0)
        for profile in ordered_profiles
    )
    total_logical_requests = profile_logical_requests + shared_wikidata_logical_requests
    shared_wikidata_charged_requests = budget.charge_requests(shared_wikidata_logical_requests)
    total_charged_requests = profile_charged_requests + shared_wikidata_charged_requests
    budget_errors = budget.validate(
        logical_requests=total_logical_requests,
        third_party_cost_usd=THIRD_PARTY_COST_USD,
        wall_runtime_seconds=wall_runtime_seconds,
    )
    if total_charged_requests != budget.charge_requests(total_logical_requests):
        budget_errors.append("profile plus shared request charges do not sum to global conservative charge")

    output_orgs = [item["organisation_number"] for item in projected]
    latencies = [
        int(value)
        for profile in ordered_profiles
        for value in ((profile.get("run_metrics") or {}).get("latencies_ms") or [])
        if value is not None
    ]
    latencies.extend(
        int(value) for value in (wikidata_metrics.get("latencies_ms") or []) if value is not None
    )
    selected_sources: dict[str, int] = {}
    for profile in ordered_profiles:
        source = _canonical_verified_site_source(profile)
        selected_sources[source] = selected_sources.get(source, 0) + 1
    verified_site_count = sum(
        count for source, count in selected_sources.items() if source != "none"
    )
    h1g_attempted = sum(
        1
        for profile in ordered_profiles
        if "website_h1g_hyphenated_no_discovery" in (profile.get("evidence") or {})
    )
    h1g_verified = int(selected_sources.get("h1g_hyphenated_no") or 0)

    handle_platform_counts = dict(
        sorted(Counter(str(item.get("platform") or "unknown") for item in profile_handle_observations).items())
    )
    companies_with_handles = len(
        {str(item.get("organisation_number") or "") for item in profile_handle_observations}
    )
    companies_with_contact_emails = len(
        {str(item.get("organisation_number") or "") for item in contact_email_observations}
    )

    checks = {
        "internal_envelopes_valid": bool(internal_validation.get("passed")),
        "exact_final_count": len(projected) == args.expected_count,
        "unique_final_organisation_numbers": len(output_orgs) == len(set(output_orgs)),
        "all_contract_objects_valid": not contract_errors,
        "all_refresh_changes_valid": not change_errors,
        "all_refresh_events_attached_once": sum(len(item.get("changes") or []) for item in projected) == len(refresh_events),
        "all_external_observations_valid": not external_observation_errors,
        "budget_valid": not budget_errors,
        "zero_third_party_cost": THIRD_PARTY_COST_USD == 0.0,
        "theoretical_request_ceiling_within_budget": theoretical_charge_ceiling <= args.max_challenge_requests,
        "wikidata_lookup_bounded": shared_wikidata_logical_requests <= theoretical_shared_wikidata_requests,
        "site_source_accounting_consistent": sum(selected_sources.values()) == len(ordered_profiles),
    }

    write_jsonl(work_dir / "profiles.jsonl", ordered_profiles)
    write_jsonl(work_dir / "internal-envelopes.jsonl", envelopes)
    write_jsonl(Path(args.output), projected)

    report = {
        "run_id": args.run_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "expected_count": args.expected_count,
        "final_objects": len(projected),
        "modules": FINAL_MODULES,
        "registry": registry_metadata,
        "source_policy": {
            "third_party_cost_usd": THIRD_PARTY_COST_USD,
            "search_api_requests": 0,
            "experimental_connectors_enabled": False,
            "official_attempts_per_endpoint": 1,
            "max_site_homepage_probes_per_company": 2,
            "wikidata_candidate_discovery_enabled": True,
            "wikidata_batch_size": WIKIDATA_BATCH_SIZE,
            "h1g_hyphenated_no_fallback_enabled": True,
            "company_page_social_handle_extraction_enabled": True,
            "company_page_contact_email_extraction_enabled": True,
            "registry_workforce_snapshot_enabled": True,
            "registry_workforce_network_requests": 0,
            "social_platform_requests": 0,
            "contact_email_network_requests": 0,
            "max_redirects_per_logical_request": 1,
        },
        "request_budget": {
            "official_logical_requests_per_profile_ceiling": OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE,
            "site_logical_requests_per_profile_ceiling": MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE,
            "total_logical_requests_per_profile_ceiling": per_profile_logical_ceiling,
            "shared_wikidata_logical_request_ceiling": theoretical_shared_wikidata_requests,
            "theoretical_logical_request_ceiling": theoretical_logical_ceiling,
            "request_charge_multiplier": budget.request_charge_multiplier,
            "theoretical_challenge_request_charge_ceiling": theoretical_charge_ceiling,
            "profile_logical_requests": profile_logical_requests,
            "shared_wikidata_logical_requests": shared_wikidata_logical_requests,
            "observed_logical_requests": total_logical_requests,
            "profile_conservative_challenge_request_charge": profile_charged_requests,
            "shared_wikidata_conservative_challenge_request_charge": shared_wikidata_charged_requests,
            "observed_conservative_challenge_request_charge": total_charged_requests,
            "max_challenge_requests": args.max_challenge_requests,
        },
        "runtime": {
            "wall_runtime_seconds": round(wall_runtime_seconds, 3),
            "max_wall_runtime_seconds": args.max_wall_runtime_seconds,
            "request_latency_ms": {
                "p50": _percentile(latencies, 0.5),
                "p95": _percentile(latencies, 0.95),
            },
        },
        "site_discovery": {
            "selected_sources": dict(sorted(selected_sources.items())),
            "profiles_with_verified_site": verified_site_count,
            "h1g": {
                "attempted": h1g_attempted,
                "verified": h1g_verified,
            },
            "wikidata": {
                "requests": shared_wikidata_logical_requests,
                "batches": int(wikidata_metrics.get("batches") or 0),
                "requested_organisations": int(wikidata_metrics.get("requested_organisations") or 0),
                "candidate_count": int(wikidata_metrics.get("candidate_count") or 0),
                "ambiguous_count": int(wikidata_metrics.get("ambiguous_count") or 0),
                "missing_count": int(wikidata_metrics.get("missing_count") or 0),
                "bytes": int(wikidata_metrics.get("bytes") or 0),
                "errors": list(wikidata_metrics.get("errors") or []),
            },
        },
        "external_signals": {
            "profile_handle_observations": len(profile_handle_observations),
            "companies_with_profile_handles": companies_with_handles,
            "platform_counts": handle_platform_counts,
            "social_platform_requests": 0,
            "contact_email_observations": len(contact_email_observations),
            "companies_with_contact_emails": companies_with_contact_emails,
            "contact_email_network_requests": 0,
            "validation_errors": external_observation_errors,
        },
        "refresh_events": len(refresh_events),
        "claims": sum(len(item.get("claims") or []) for item in projected),
        "evidence_items": sum(len(item.get("evidence") or []) for item in projected),
        "errors": sum(len(item.get("errors") or []) for item in projected),
        "contract_errors": contract_errors,
        "change_errors": change_errors,
        "budget_errors": budget_errors,
        "internal_validation": internal_validation,
        "checks": checks,
        "passed": all(checks.values()),
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()