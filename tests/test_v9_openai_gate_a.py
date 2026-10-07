from __future__ import annotations

from norway_company_agent.evidence import evidence
from norway_company_agent.v9_openai_gate_a import (
    GateAProviderConfig,
    preflight_gate_a_provider,
    run_gate_a_provider_screen,
)


def profiles(count: int = 20) -> list[dict]:
    return [
        {
            "organisation_number": f"{910000000 + index:09d}",
            "name": f"EXAMPLE COMPANY {index:02d} AS",
            "municipality": "OSLO",
        }
        for index in range(count)
    ]


def available_fetch(url: str, *, source_type: str, timeout: float):
    org = url.rstrip("/").rsplit("-", 1)[-1].split(".", 1)[0]
    record = evidence(
        "website",
        "available",
        source_type,
        url,
        value={
            "requested_url": url,
            "final_url": url,
            "registered_domain": url.split("//", 1)[-1].rstrip("/"),
            "title": "Official company site",
            "description": "",
            "identity_text_excerpt": f"Organisasjonsnummer: {org}",
            "main_text_excerpt": "Official company information " * 10,
            "structured_organisations": [],
            "social_links": [],
            "pages": [],
            "content_sha256": "a" * 64,
        },
        content_sha256="a" * 64,
    )
    return record, {"requests": 2, "bytes": 1234, "latencies_ms": [1]}


def test_preflight_fails_closed_by_default() -> None:
    decision = preflight_gate_a_provider(
        GateAProviderConfig(
            enable_live_provider=False,
            evaluator_reproducible=False,
            rights_status="unknown",
            challenge_cost_budget_usd=10.0,
            project_third_party_budget_usd=0.0,
        ),
        company_count=20,
        api_key_available=False,
    )

    assert decision["allowed_for_live_v9_experiment"] is False
    assert "explicit_live_enable_required" in decision["reasons"]
    assert "provider_key_missing" in decision["reasons"]
    assert "evaluator_supplied_credential_not_confirmed" in decision["reasons"]
    assert "provider_not_evaluator_reproducible" in decision["reasons"]
    assert "provider_rights_not_confirmed" in decision["reasons"]
    assert "project_zero_cost_policy" in decision["reasons"]
    assert "reserved_provider_cost_exceeds_effective_budget" in decision["reasons"]


def test_preflight_requires_budget_for_search_plus_model_reserve() -> None:
    decision = preflight_gate_a_provider(
        GateAProviderConfig(
            enable_live_provider=True,
            evaluator_reproducible=True,
            rights_status="contract_confirmed",
            challenge_cost_budget_usd=10.0,
            project_third_party_budget_usd=0.20,
            evaluator_supplied_credential=True,
        ),
        company_count=20,
        api_key_available=True,
    )

    assert decision["allowed_for_live_v9_experiment"] is False
    assert decision["projected_provider_cost_usd"] == 0.2
    assert decision["reserved_provider_cost_total_usd"] == 0.3
    assert "reserved_provider_cost_exceeds_effective_budget" in decision["reasons"]


def test_blocked_screen_never_calls_provider() -> None:
    calls = {"search": 0}

    def search_fn(profile, *, api_key):
        calls["search"] += 1
        raise AssertionError("provider must not be called when preflight is blocked")

    report = run_gate_a_provider_screen(
        profiles(),
        api_key="",
        config=GateAProviderConfig(
            enable_live_provider=False,
            evaluator_reproducible=False,
            rights_status="unknown",
            challenge_cost_budget_usd=10.0,
            project_third_party_budget_usd=0.0,
        ),
        search_fn=search_fn,
        fetch_fn=available_fetch,
    )

    assert report["status"] == "provider_gate_blocked"
    assert report["company_results"] == []
    assert report["production_publications"] == 0
    assert calls["search"] == 0


def test_machine_yield_never_auto_passes_gate_a() -> None:
    rows = profiles()
    exact_orgs = {row["organisation_number"] for row in rows[:5]}
    calls = {"search": 0}

    def search_fn(profile, *, api_key):
        calls["search"] += 1
        org = profile["organisation_number"]
        candidates = [f"https://company-{org}.no/"] if org in exact_orgs else []
        return {
            "organisation_number": org,
            "status": "candidates_found" if candidates else "no_candidate",
            "candidate_urls": candidates,
            "candidate_count": len(candidates),
            "publication_authorized": False,
            "provider_result_text_retained": False,
            "provider_message_text_consumed": False,
            "provider_response_id": f"resp_{org}",
            "query_sha256": ["b" * 64],
            "cost": {
                "web_search_calls": 1,
                "input_tokens": 500,
                "output_tokens": 50,
                "estimated_cost_usd": 0.010075,
            },
        }

    report = run_gate_a_provider_screen(
        rows,
        api_key="test-only-key",
        config=GateAProviderConfig(
            enable_live_provider=True,
            evaluator_reproducible=True,
            rights_status="contract_confirmed",
            challenge_cost_budget_usd=10.0,
            project_third_party_budget_usd=0.50,
            evaluator_supplied_credential=True,
        ),
        search_fn=search_fn,
        fetch_fn=available_fetch,
    )

    assert report["status"] == "completed"
    assert calls["search"] == 20
    assert report["provider_search_calls"] == 20
    assert report["machine_verified_organisations"] == 5
    assert report["verified_organisations"] == sorted(exact_orgs)
    assert report["machine_yield_pass"] is True
    assert report["gate_a_pass"] is False
    assert report["publication_enabled"] is False
    assert report["production_publications"] == 0
    assert report["provider_result_text_persisted"] is False
    assert report["provider_message_text_consumed"] is False
    assert report["manual_wrong_company_audit"] == "required_for_all_new_machine_verified_sites"
    assert report["evidence_defect_audit"] == "required_for_all_new_machine_verified_sites"


def test_under_five_machine_verifications_stays_retune() -> None:
    rows = profiles()
    exact_orgs = {row["organisation_number"] for row in rows[:4]}

    def search_fn(profile, *, api_key):
        org = profile["organisation_number"]
        candidates = [f"https://company-{org}.no/"] if org in exact_orgs else []
        return {
            "status": "candidates_found" if candidates else "no_candidate",
            "candidate_urls": candidates,
            "query_sha256": [],
            "cost": {
                "web_search_calls": 1,
                "input_tokens": 0,
                "output_tokens": 0,
                "estimated_cost_usd": 0.01,
            },
        }

    report = run_gate_a_provider_screen(
        rows,
        api_key="test-only-key",
        config=GateAProviderConfig(
            enable_live_provider=True,
            evaluator_reproducible=True,
            rights_status="approved",
            challenge_cost_budget_usd=1.0,
            project_third_party_budget_usd=0.50,
            evaluator_supplied_credential=True,
        ),
        search_fn=search_fn,
        fetch_fn=available_fetch,
    )

    assert report["machine_verified_organisations"] == 4
    assert report["machine_yield_pass"] is False
    assert report["gate_a_pass"] is False
    assert report["manual_wrong_company_audit"] == "not_reached_yield_threshold"


def test_existing_verified_site_skips_provider_and_cost() -> None:
    rows = profiles(1)
    rows[0]["evidence"] = {
        "website": {
            "status": "available",
            "source_url": "https://already.example/",
            "value": {
                "final_url": "https://already.example/",
                "identity_assessment": {
                    "status": "exact",
                    "score": 1.0,
                    "publishable": True,
                    "method": "fixture",
                },
            },
        }
    }
    calls = {"search": 0}

    def search_fn(profile, *, api_key):
        calls["search"] += 1
        raise AssertionError("verified sites must not spend provider search")

    report = run_gate_a_provider_screen(
        rows,
        api_key="test-only-key",
        config=GateAProviderConfig(
            enable_live_provider=True,
            evaluator_reproducible=True,
            rights_status="contract_confirmed",
            challenge_cost_budget_usd=10.0,
            project_third_party_budget_usd=0.50,
            evaluator_supplied_credential=True,
        ),
        search_fn=search_fn,
        fetch_fn=available_fetch,
    )
    assert calls["search"] == 0
    assert report["provider_search_calls"] == 0
    assert report["provider_estimated_cost_usd"] == 0.0
    assert report["company_results"][0]["provider_status"] == "skipped_verified_site"
    assert report["production_publications"] == 0
