#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
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
from norway_company_agent.annual_report_workforce import attach_annual_report_workforce_batch  # noqa: E402
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
from norway_company_agent.h1g_hyphenated_no_recall import (  # noqa: E402
    evaluate_hyphenated_no_fallback,
    hyphenated_no_candidate,
)
from norway_company_agent.v9_m13_budget import allocate_m13_search_budget  # noqa: E402
from norway_company_agent.v9_m13_search_slot import evaluate_m13_search_slot  # noqa: E402
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
DEFAULT_MAX_CHALLENGE_REQUESTS = 2000


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
        "v9_m13_search_candidate_website": "m13_search_candidate",
    }
    return mapping.get(source_type, f"verified:{source_type}" if source_type else "verified:unknown")


def _enrich_profile(
    profile: dict[str, Any],
    *,
    budget: RunBudget,
    site_timeout: float,
    wikidata_candidate: dict[str, Any] | None,
    search_enabled: bool = False,
    search_api_key: str = "",
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

    # M13 can replace H1g's existing final two-request site slot with one independently
    # verified search-nominated page. The provider call is accounted separately and reserved
    # from annual-report capacity by the structural theorem. Search output is nomination only.
    profile, m13_result = evaluate_m13_search_slot(
        profile,
        enabled=search_enabled,
        api_key=search_api_key,
        timeout=site_timeout,
        base_site_logical_requests=int(site_metrics.get("requests") or 0),
        h1g_evaluator=evaluate_hyphenated_no_fallback,
    )
    h1g_result = m13_result.get("h1g_result") or {}
    site_metrics["h1g_candidate_available"] = bool(h1g_result.get("candidate_available"))
    site_metrics["h1g_attempted"] = bool(h1g_result.get("attempted"))
    site_metrics["h1g_verified"] = bool(h1g_result.get("verified"))
    if h1g_result.get("skipped_reason"):
        site_metrics["h1g_skipped_reason"] = str(h1g_result["skipped_reason"])
    if h1g_result.get("guard_reasons"):
        site_metrics["h1g_guard_reasons"] = list(h1g_result["guard_reasons"])

    if h1g_result:
        site_metrics["requests"] = int(site_metrics.get("requests") or 0) + int(h1g_result.get("requests_added") or 0)
        site_metrics["bytes"] = int(site_metrics.get("bytes") or 0) + int(h1g_result.get("bytes_added") or 0)
        site_metrics.setdefault("latencies_ms", []).extend(
            int(value) for value in (h1g_result.get("latencies_ms") or []) if value is not None
        )
        if h1g_result.get("verified"):
            site_metrics["selected_source"] = "h1g_hyphenated_no"
            site_metrics["promoted"] = True
    else:
        site_metrics["requests"] = int(site_metrics.get("requests") or 0) + int(
            m13_result.get("candidate_fetch_logical_requests") or 0
        )
        site_metrics["bytes"] = int(site_metrics.get("bytes") or 0) + int(
            m13_result.get("candidate_fetch_bytes") or 0
        )
        site_metrics.setdefault("latencies_ms", []).extend(
            int(value)
            for value in (m13_result.get("candidate_fetch_latencies_ms") or [])
            if value is not None
        )
        if m13_result.get("verified"):
            site_metrics["selected_source"] = "m13_search_candidate"
            site_metrics["promoted"] = True

    site_metrics["m13_search"] = {
        "strategy": m13_result.get("strategy"),
        "search_eligible": bool(m13_result.get("search_eligible")),
        "provider_attempted": bool(m13_result.get("provider_attempted")),
        "provider_api_requests": int(m13_result.get("provider_api_requests") or 0),
        "provider_web_search_calls": int(m13_result.get("provider_web_search_calls") or 0),
        "provider_estimated_cost_usd": float(m13_result.get("provider_estimated_cost_usd") or 0.0),
        "provider_status": m13_result.get("provider_status"),
        "candidate_count": int(m13_result.get("candidate_count") or 0),
        "candidate_fetch_attempted": bool(m13_result.get("candidate_fetch_attempted")),
        "verified": bool(m13_result.get("verified")),
        "registry_risk_reasons": list(m13_result.get("registry_risk_reasons") or []),
    }

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

    provider_api_requests = int(m13_result.get("provider_api_requests") or 0)
    provider_cost_usd = float(m13_result.get("provider_estimated_cost_usd") or 0.0)
    logical_requests = official_logical_requests + site_logical_requests + provider_api_requests
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
        "third_party_cost_usd": provider_cost_usd,
        "search_api_requests": provider_api_requests,
        "search_web_tool_calls": int(m13_result.get("provider_web_search_calls") or 0),
        "search_provider_cost_usd": provider_cost_usd,
        "m13_search_strategy": m13_result.get("strategy"),
    }
    return profile, {
        "organisation_number": profile["organisation_number"],
        "official_logical_requests": official_logical_requests,
        "site_logical_requests": site_logical_requests,
        "provider_api_requests": provider_api_requests,
        "provider_cost_usd": provider_cost_usd,
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
    parser.add_argument("--enable-openai-web-search", action="store_true")
    parser.add_argument(
        "--max-search-calls",
        type=int,
        default=0,
        help="Maximum Responses API web-search requests reserved inside the existing request theorem.",
    )
    parser.add_argument("--max-wall-runtime-seconds", type=int, default=2400)
    parser.add_argument("--refresh-report", help="Optional refresh report with events[]")
    parser.add_argument("--annual-workforce-workers", type=int, default=4)
    parser.add_argument("--annual-workforce-timeout", type=float, default=60.0)
    parser.add_argument("--annual-workforce-min-start-interval", type=float, default=2.1)
    parser.add_argument("--annual-workforce-ocr-pages", type=int, default=8)
    parser.add_argument("--annual-workforce-ocr-dpi", type=int, default=110)
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
    if args.max_search_calls < 0:
        parser.error("--max-search-calls cannot be negative")
    if args.enable_openai_web_search:
        if args.max_search_calls < 1:
            parser.error("--enable-openai-web-search requires --max-search-calls >= 1")
        if args.max_third_party_cost_usd <= 0:
            parser.error("--enable-openai-web-search requires a positive --max-third-party-cost-usd")
        if not str(os.environ.get("OPENAI_API_KEY") or "").strip():
            parser.error("--enable-openai-web-search requires OPENAI_API_KEY")
    elif args.max_search_calls != 0:
        parser.error("--max-search-calls must be 0 unless --enable-openai-web-search is set")
    if args.max_wall_runtime_seconds < 1:
        parser.error("--max-wall-runtime-seconds must be positive")
    if args.annual_workforce_workers < 1:
        parser.error("--annual-workforce-workers must be positive")
    if args.annual_workforce_timeout <= 0:
        parser.error("--annual-workforce-timeout must be positive")
    if args.annual_workforce_min_start_interval < 0:
        parser.error("--annual-workforce-min-start-interval cannot be negative")
    if args.annual_workforce_ocr_pages < 0:
        parser.error("--annual-workforce-ocr-pages cannot be negative")
    if args.annual_workforce_ocr_dpi < 50:
        parser.error("--annual-workforce-ocr-dpi must be at least 50")

    budget = RunBudget(
        max_challenge_requests=args.max_challenge_requests,
        max_third_party_cost_usd=args.max_third_party_cost_usd,
        max_wall_runtime_seconds=args.max_wall_runtime_seconds,
        max_redirects_per_logical_request=1,
    )
    m13_allocation = allocate_m13_search_budget(
        expected_count=args.expected_count,
        max_challenge_requests=args.max_challenge_requests,
        max_search_calls=args.max_search_calls if args.enable_openai_web_search else 0,
        request_charge_multiplier=budget.request_charge_multiplier,
    )
    per_profile_logical_ceiling = (
        OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE + MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE
    )
    theoretical_shared_wikidata_requests = int(
        m13_allocation["shared_wikidata_logical_request_ceiling"]
    )
    base_theoretical_logical_ceiling = int(
        m13_allocation["base_theoretical_logical_request_ceiling"]
    )
    base_theoretical_charge_ceiling = int(
        m13_allocation["base_theoretical_conservative_charge_ceiling"]
    )
    provider_search_logical_request_ceiling = int(
        m13_allocation["provider_search_logical_request_ceiling"]
    )
    provider_search_conservative_charge_ceiling = int(
        m13_allocation["provider_search_conservative_charge_ceiling"]
    )
    annual_workforce_logical_request_ceiling = int(
        m13_allocation["annual_report_workforce_logical_request_ceiling"]
    )
    theoretical_logical_ceiling = int(m13_allocation["theoretical_logical_request_ceiling"])
    theoretical_charge_ceiling = int(
        m13_allocation["theoretical_challenge_request_charge_ceiling"]
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

    search_api_key = str(os.environ.get("OPENAI_API_KEY") or "").strip()
    statically_search_eligible_orgs = sorted(
        str(profile.get("organisation_number") or "")
        for profile in profiles
        if not str(profile.get("website") or "").strip()
        and hyphenated_no_candidate(profile) is not None
    )
    search_target_orgs = set(
        statically_search_eligible_orgs[:provider_search_logical_request_ceiling]
        if args.enable_openai_web_search
        else []
    )

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
                search_enabled=(
                    args.enable_openai_web_search
                    and profile["organisation_number"] in search_target_orgs
                ),
                search_api_key=search_api_key,
            ): profile["organisation_number"]
            for profile in profiles
        }
        for future in as_completed(futures):
            profile, _profile_report = future.result()
            state[profile["organisation_number"]] = profile

    ordered_profiles = [state[org] for org in orgs]
    annual_workforce_report = attach_annual_report_workforce_batch(
        ordered_profiles,
        max_requests=annual_workforce_logical_request_ceiling,
        workers=args.annual_workforce_workers,
        min_start_interval=args.annual_workforce_min_start_interval,
        timeout=args.annual_workforce_timeout,
        ocr_pages=args.annual_workforce_ocr_pages,
        ocr_dpi=args.annual_workforce_ocr_dpi,
        request_charge_multiplier=budget.request_charge_multiplier,
    )
    completed_at = utc_now()
    external_observation_errors, profile_handle_observations, contact_email_observations = _external_observation_audit(
        ordered_profiles
    )
    workforce_observations = [
        observation
        for profile in ordered_profiles
        for observation in (profile.get("external_observations") or [])
        if isinstance(observation, dict) and observation.get("signal_type") == "workforce_snapshot"
    ]

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
        profile_cost = float(
            ((envelope.get("profile") or {}).get("run_metrics") or {}).get(
                "third_party_cost_usd"
            )
            or 0.0
        )
        contract = project_terminal_envelope(
            envelope,
            third_party_cost_usd=profile_cost,
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
    total_third_party_cost_usd = round(
        sum(
            float((profile.get("run_metrics") or {}).get("third_party_cost_usd") or 0.0)
            for profile in ordered_profiles
        ),
        6,
    )
    observed_search_api_requests = sum(
        int((profile.get("run_metrics") or {}).get("search_api_requests") or 0)
        for profile in ordered_profiles
    )
    observed_search_web_tool_calls = sum(
        int((profile.get("run_metrics") or {}).get("search_web_tool_calls") or 0)
        for profile in ordered_profiles
    )
    budget_errors = budget.validate(
        logical_requests=total_logical_requests,
        third_party_cost_usd=total_third_party_cost_usd,
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
    companies_with_workforce = len(
        {str(item.get("organisation_number") or "") for item in workforce_observations}
    )
    annual_workforce_observations = [
        item for item in workforce_observations if item.get("source_class") == "official_annual_account_copy"
    ]

    checks = {
        "internal_envelopes_valid": bool(internal_validation.get("passed")),
        "exact_final_count": len(projected) == args.expected_count,
        "unique_final_organisation_numbers": len(output_orgs) == len(set(output_orgs)),
        "all_contract_objects_valid": not contract_errors,
        "all_refresh_changes_valid": not change_errors,
        "all_refresh_events_attached_once": sum(len(item.get("changes") or []) for item in projected) == len(refresh_events),
        "all_external_observations_valid": not external_observation_errors,
        "budget_valid": not budget_errors,
        "third_party_cost_within_budget": total_third_party_cost_usd <= args.max_third_party_cost_usd,
        "search_api_requests_bounded": observed_search_api_requests <= provider_search_logical_request_ceiling,
        "search_tool_calls_bounded": observed_search_web_tool_calls <= observed_search_api_requests,
        "search_disabled_is_zero_cost": (
            args.enable_openai_web_search
            or (
                observed_search_api_requests == 0
                and observed_search_web_tool_calls == 0
                and total_third_party_cost_usd == 0.0
            )
        ),
        "search_targets_bounded": len(search_target_orgs) <= provider_search_logical_request_ceiling,
        "theoretical_request_ceiling_within_budget": theoretical_charge_ceiling <= args.max_challenge_requests,
        "wikidata_lookup_bounded": shared_wikidata_logical_requests <= theoretical_shared_wikidata_requests,
        "site_source_accounting_consistent": sum(selected_sources.values()) == len(ordered_profiles),
        "annual_workforce_request_bounded": int(annual_workforce_report.get("requests") or 0) <= annual_workforce_logical_request_ceiling,
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
            "third_party_cost_usd": total_third_party_cost_usd,
            "search_api_requests": observed_search_api_requests,
            "search_web_tool_calls": observed_search_web_tool_calls,
            "experimental_connectors_enabled": bool(args.enable_openai_web_search),
            "openai_web_search_enabled": bool(args.enable_openai_web_search),
            "openai_web_search_provider": (
                "openai_responses_web_search_v2" if args.enable_openai_web_search else None
            ),
            "openai_web_search_model": "gpt-6-luna" if args.enable_openai_web_search else None,
            "openai_search_results_are_publication_evidence": False,
            "search_target_count": len(search_target_orgs),
            "max_search_calls": provider_search_logical_request_ceiling,
            "official_attempts_per_endpoint": 1,
            "max_site_homepage_probes_per_company": 2,
            "wikidata_candidate_discovery_enabled": True,
            "wikidata_batch_size": WIKIDATA_BATCH_SIZE,
            "h1g_hyphenated_no_fallback_enabled": True,
            "company_page_social_handle_extraction_enabled": True,
            "company_page_contact_email_extraction_enabled": True,
            "registry_workforce_snapshot_enabled": True,
            "registry_workforce_network_requests": 0,
            "annual_report_workforce_enabled": annual_workforce_logical_request_ceiling > 0,
            "annual_report_workforce_ocr_runtime_available": bool(annual_workforce_report.get("runtime_available")),
            "annual_report_workforce_network_requests": int(annual_workforce_report.get("requests") or 0),
            "social_platform_requests": 0,
            "contact_email_network_requests": 0,
            "max_redirects_per_logical_request": 1,
        },
        "request_budget": {
            "official_logical_requests_per_profile_ceiling": OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE,
            "site_logical_requests_per_profile_ceiling": MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE,
            "total_logical_requests_per_profile_ceiling": per_profile_logical_ceiling,
            "shared_wikidata_logical_request_ceiling": theoretical_shared_wikidata_requests,
            "base_theoretical_logical_request_ceiling": base_theoretical_logical_ceiling,
            "base_theoretical_challenge_request_charge_ceiling": base_theoretical_charge_ceiling,
            "provider_search_logical_request_ceiling": provider_search_logical_request_ceiling,
            "provider_search_conservative_charge_ceiling": provider_search_conservative_charge_ceiling,
            "provider_search_observed_logical_requests": observed_search_api_requests,
            "provider_search_observed_conservative_charge": budget.charge_requests(
                observed_search_api_requests
            ),
            "annual_report_workforce_logical_request_ceiling": annual_workforce_logical_request_ceiling,
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
            "m13_search": {
                "enabled": bool(args.enable_openai_web_search),
                "statically_eligible": len(statically_search_eligible_orgs),
                "targeted": len(search_target_orgs),
                "provider_api_requests": observed_search_api_requests,
                "provider_web_search_calls": observed_search_web_tool_calls,
                "provider_estimated_cost_usd": total_third_party_cost_usd,
                "verified": int(selected_sources.get("m13_search_candidate") or 0),
                "candidate_fetch_additional_site_slots": 0,
                "candidate_fetch_policy": "replaces existing H1g final two-logical-request slot",
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
            "workforce_observations": len(workforce_observations),
            "companies_with_workforce": companies_with_workforce,
            "annual_report_workforce_observations": len(annual_workforce_observations),
            "annual_report_workforce_network_requests": int(annual_workforce_report.get("requests") or 0),
            "validation_errors": external_observation_errors,
        },
        "annual_report_workforce": {
            "runtime_available": bool(annual_workforce_report.get("runtime_available")),
            "eligible": int(annual_workforce_report.get("eligible") or 0),
            "selected": int(annual_workforce_report.get("selected") or 0),
            "requests": int(annual_workforce_report.get("requests") or 0),
            "accepted": int(annual_workforce_report.get("accepted") or 0),
            "added_conservative_challenge_request_charge": int(annual_workforce_report.get("added_conservative_challenge_request_charge") or 0),
            "status_counts": dict(annual_workforce_report.get("status_counts") or {}),
            "runtime_seconds": float(annual_workforce_report.get("runtime_seconds") or 0.0),
            "execution_errors": list(annual_workforce_report.get("execution_errors") or []),
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