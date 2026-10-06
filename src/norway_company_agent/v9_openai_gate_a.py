from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .discovery import qualify_search_discovered_website
from .final_site_discovery import fetch_bounded_homepage
from .identity import apply_website_identity_gate
from .v9_openai_websearch_v2 import provider_readiness, search_candidate_urls
from .zero_cost_registry_guard import registry_risk_reasons

MAX_GATE_A_COMPANIES = 20
MAX_CANDIDATES_PER_COMPANY = 3
RESERVED_PROVIDER_COST_PER_COMPANY_USD = 0.011


@dataclass(frozen=True)
class GateAProviderConfig:
    enable_live_provider: bool
    evaluator_reproducible: bool
    rights_status: str
    challenge_cost_budget_usd: float
    project_third_party_budget_usd: float
    evaluator_supplied_credential: bool = False

    def __post_init__(self) -> None:
        if self.challenge_cost_budget_usd < 0:
            raise ValueError("challenge_cost_budget_usd cannot be negative")
        if self.project_third_party_budget_usd < 0:
            raise ValueError("project_third_party_budget_usd cannot be negative")


def preflight_gate_a_provider(
    config: GateAProviderConfig,
    *,
    company_count: int,
    api_key_available: bool,
) -> dict[str, Any]:
    if company_count < 1 or company_count > MAX_GATE_A_COMPANIES:
        raise ValueError(f"company_count must be in 1..{MAX_GATE_A_COMPANIES}")

    decision = provider_readiness(
        max_searches=company_count,
        evaluator_key_available=config.evaluator_reproducible,
        rights_status=config.rights_status,
        challenge_cost_budget_usd=config.challenge_cost_budget_usd,
        project_third_party_budget_usd=config.project_third_party_budget_usd,
    )
    reasons = list(decision.get("reasons") or [])
    reserved_total = round(
        RESERVED_PROVIDER_COST_PER_COMPANY_USD * company_count,
        6,
    )
    effective_budget = min(
        config.challenge_cost_budget_usd,
        config.project_third_party_budget_usd,
    )

    if not config.enable_live_provider:
        reasons.append("explicit_live_enable_required")
    if not api_key_available:
        reasons.append("provider_key_missing")
    if not config.evaluator_supplied_credential:
        reasons.append("evaluator_supplied_credential_not_confirmed")
    if reserved_total > effective_budget:
        reasons.append("reserved_provider_cost_exceeds_effective_budget")

    reasons = list(dict.fromkeys(reasons))
    allowed = bool(decision.get("allowed_for_live_v9_experiment")) and not reasons
    return {
        **decision,
        "allowed_for_live_v9_experiment": allowed,
        "enable_live_provider": config.enable_live_provider,
        "api_key_available": api_key_available,
        "evaluator_supplied_credential": config.evaluator_supplied_credential,
        "reserved_provider_cost_per_company_usd": RESERVED_PROVIDER_COST_PER_COMPANY_USD,
        "reserved_provider_cost_total_usd": reserved_total,
        "effective_experiment_budget_usd": effective_budget,
        "reasons": reasons,
    }


def _publishable(record: dict[str, Any]) -> bool:
    assessment = ((record.get("value") or {}).get("identity_assessment") or {})
    return record.get("status") == "available" and bool(assessment.get("publishable"))


def _sanitize_fetch(record: dict[str, Any]) -> dict[str, Any]:
    value = record.get("value") or {}
    assessment = value.get("identity_assessment") or {}
    return {
        "status": record.get("status"),
        "source_url": record.get("source_url"),
        "final_url": value.get("final_url"),
        "registered_domain": value.get("registered_domain"),
        "content_sha256": record.get("content_sha256") or value.get("content_sha256"),
        "identity_assessment": {
            "status": assessment.get("status"),
            "score": assessment.get("score"),
            "publishable": assessment.get("publishable"),
            "method": assessment.get("method"),
            "reasons": list(assessment.get("reasons") or []),
        },
    }


def verify_candidate(
    profile: dict[str, Any],
    candidate_url: str,
    *,
    site_timeout: float,
    fetch_fn: Callable[..., tuple[dict[str, Any], dict[str, Any]]] = fetch_bounded_homepage,
) -> tuple[dict[str, Any], dict[str, Any]]:
    fetched, metrics = fetch_fn(
        candidate_url,
        source_type="v9_openai_websearch_candidate",
        timeout=site_timeout,
    )
    gated = apply_website_identity_gate(profile, fetched)
    website = gated["website"]
    assessment = qualify_search_discovered_website(
        profile,
        website,
        gated.get("assessment"),
    )
    if assessment is not None:
        value = website.get("value") or {}
        value["identity_assessment"] = assessment
        website["value"] = value

    risks = registry_risk_reasons(profile, website)
    accepted = _publishable(website) and not risks
    final_url = str(
        (website.get("value") or {}).get("final_url")
        or website.get("source_url")
        or ""
    )
    return {
        "candidate_url": candidate_url,
        "accepted": accepted,
        "registry_risk_reasons": list(risks or []),
        "fetch": _sanitize_fetch(website),
        "logical_requests": int(metrics.get("requests") or 0),
        "bytes": int(metrics.get("bytes") or 0),
        "final_url": final_url if accepted else None,
    }, metrics


def run_gate_a_provider_screen(
    profiles: list[dict[str, Any]],
    *,
    api_key: str,
    config: GateAProviderConfig,
    site_timeout: float = 8.0,
    search_fn: Callable[..., dict[str, Any]] = search_candidate_urls,
    fetch_fn: Callable[..., tuple[dict[str, Any], dict[str, Any]]] = fetch_bounded_homepage,
) -> dict[str, Any]:
    if not profiles or len(profiles) > MAX_GATE_A_COMPANIES:
        raise ValueError(f"profiles must contain 1..{MAX_GATE_A_COMPANIES} companies")

    preflight = preflight_gate_a_provider(
        config,
        company_count=len(profiles),
        api_key_available=bool(str(api_key or "").strip()),
    )
    if not preflight["allowed_for_live_v9_experiment"]:
        return {
            "schema_version": "signalpost-v9-openai-websearch-gate-a-v1",
            "status": "provider_gate_blocked",
            "cohort": "consumed_gate_a_20",
            "fresh_qualification_credit": False,
            "publication_enabled": False,
            "production_publications": 0,
            "provider_preflight": preflight,
            "companies": len(profiles),
            "company_results": [],
        }

    provider_cost = 0.0
    provider_search_calls = 0
    provider_input_tokens = 0
    provider_output_tokens = 0
    site_logical_requests = 0
    site_bytes = 0
    candidate_fetches = 0
    verified_orgs: list[str] = []
    company_results: list[dict[str, Any]] = []

    for profile in profiles:
        org = str(profile.get("organisation_number") or "")
        if provider_cost + RESERVED_PROVIDER_COST_PER_COMPANY_USD > preflight["effective_experiment_budget_usd"]:
            raise RuntimeError("provider reserve would exceed effective experiment budget")

        nomination = search_fn(profile, api_key=api_key)
        cost = nomination.get("cost") or {}
        provider_cost = round(
            provider_cost + float(cost.get("estimated_cost_usd") or 0.0),
            6,
        )
        provider_search_calls += int(cost.get("web_search_calls") or 0)
        provider_input_tokens += int(cost.get("input_tokens") or 0)
        provider_output_tokens += int(cost.get("output_tokens") or 0)

        if provider_cost > preflight["effective_experiment_budget_usd"]:
            raise RuntimeError("observed provider cost exceeded effective experiment budget")

        candidates = list(nomination.get("candidate_urls") or [])[:MAX_CANDIDATES_PER_COMPANY]
        attempts: list[dict[str, Any]] = []
        verified_url = None
        for candidate_url in candidates:
            candidate_fetches += 1
            attempt, metrics = verify_candidate(
                profile,
                str(candidate_url),
                site_timeout=site_timeout,
                fetch_fn=fetch_fn,
            )
            attempts.append(attempt)
            site_logical_requests += int(metrics.get("requests") or 0)
            site_bytes += int(metrics.get("bytes") or 0)
            if attempt["accepted"]:
                verified_url = str(attempt["final_url"] or "")
                verified_orgs.append(org)
                break

        company_results.append(
            {
                "organisation_number": org,
                "name": profile.get("name"),
                "provider_status": nomination.get("status"),
                "candidate_urls": candidates,
                "candidate_count": len(candidates),
                "query_sha256": list(nomination.get("query_sha256") or []),
                "provider_response_id": nomination.get("provider_response_id"),
                "provider_cost": {
                    "web_search_calls": int(cost.get("web_search_calls") or 0),
                    "input_tokens": int(cost.get("input_tokens") or 0),
                    "output_tokens": int(cost.get("output_tokens") or 0),
                    "estimated_cost_usd": float(cost.get("estimated_cost_usd") or 0.0),
                },
                "attempts": attempts,
                "verified_url": verified_url,
                "publication_authorized_by_provider": False,
            }
        )

    verified_orgs = sorted(set(verified_orgs))
    machine_yield_pass = len(verified_orgs) >= 5
    return {
        "schema_version": "signalpost-v9-openai-websearch-gate-a-v1",
        "status": "completed",
        "cohort": "consumed_gate_a_20",
        "fresh_qualification_credit": False,
        "publication_enabled": False,
        "production_publications": 0,
        "provider_preflight": preflight,
        "companies": len(profiles),
        "provider_search_calls": provider_search_calls,
        "provider_input_tokens": provider_input_tokens,
        "provider_output_tokens": provider_output_tokens,
        "provider_estimated_cost_usd": provider_cost,
        "candidate_fetches": candidate_fetches,
        "site_logical_requests": site_logical_requests,
        "site_bytes": site_bytes,
        "machine_verified_organisations": len(verified_orgs),
        "verified_organisations": verified_orgs,
        "gate_a_minimum": 5,
        "machine_yield_pass": machine_yield_pass,
        "gate_a_pass": False,
        "manual_wrong_company_audit": (
            "required_for_all_new_machine_verified_sites"
            if machine_yield_pass
            else "not_reached_yield_threshold"
        ),
        "evidence_defect_audit": (
            "required_for_all_new_machine_verified_sites"
            if machine_yield_pass
            else "not_reached_yield_threshold"
        ),
        "provider_result_text_persisted": False,
        "provider_message_text_consumed": False,
        "note": (
            "A machine yield >=5/20 does not by itself pass Gate A. Manual wrong-company "
            "and evidence audits remain mandatory, and this experiment never publishes."
        ),
        "company_results": company_results,
    }
