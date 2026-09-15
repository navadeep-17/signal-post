from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "signalpost_final_runner_h1g_test",
    ROOT / "scripts" / "run_signalpost_final.py",
)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)

from norway_company_agent.run_budget import RunBudget  # noqa: E402


def _profile() -> dict:
    return {
        "organisation_number": "912345678",
        "name": "EXAMPLE SYSTEMS AS",
        "website": "",
        "evidence": {},
    }


def test_final_runner_places_h1g_after_wikidata_and_charges_added_requests(monkeypatch):
    order: list[str] = []

    official_results = [
        SimpleNamespace(request_count=1, elapsed_ms=1, bytes_received=10)
        for _ in range(runner.OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE)
    ]

    monkeypatch.setattr(
        runner,
        "fetch_official_modules",
        lambda org, modules, fetcher: ({}, official_results),
    )

    def fake_discover(profile, *, wikidata_candidate, timeout):
        order.append("wikidata")
        return profile, {
            "requests": 2,
            "bytes": 100,
            "latencies_ms": [3],
            "promoted": False,
            "selected_source": None,
        }

    seen: dict[str, int] = {}

    def fake_h1g(profile, *, timeout, base_site_logical_requests):
        order.append("h1g")
        seen["base_site_logical_requests"] = base_site_logical_requests
        return profile, {
            "candidate_available": True,
            "attempted": True,
            "verified": False,
            "requests_added": 2,
            "bytes_added": 20,
            "latencies_ms": [4],
            "skipped_reason": None,
            "guard_reasons": [],
        }

    monkeypatch.setattr(runner, "discover_final_website_with_wikidata", fake_discover)
    monkeypatch.setattr(runner, "evaluate_hyphenated_no_fallback", fake_h1g)
    monkeypatch.setattr(runner, "attach_company_site_social_observations", lambda profile: profile)
    monkeypatch.setattr(runner, "attach_company_site_contact_email_observations", lambda profile: profile)

    budget = RunBudget(max_challenge_requests=1802)
    enriched, report = runner._enrich_profile(
        _profile(),
        budget=budget,
        site_timeout=6.0,
        wikidata_candidate={"url": "https://example.no/"},
    )

    assert order == ["wikidata", "h1g"]
    assert seen["base_site_logical_requests"] == 2
    assert report["site_logical_requests"] == 4
    assert report["logical_requests"] == 9
    assert report["conservative_challenge_request_charge"] == 18
    assert report["site"]["h1g_attempted"] is True
    assert report["site"]["h1g_verified"] is False
    assert report["site"]["requests"] == 4
    assert report["site"]["bytes"] == 120
    assert report["site"]["latencies_ms"] == [3, 4]
    assert enriched["run_metrics"]["logical_requests"] == 9
    assert enriched["run_metrics"]["requests"] == 18


def test_final_runner_marks_h1g_as_selected_source_when_promoted(monkeypatch):
    official_results = [
        SimpleNamespace(request_count=1, elapsed_ms=1, bytes_received=0)
        for _ in range(runner.OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE)
    ]
    monkeypatch.setattr(
        runner,
        "fetch_official_modules",
        lambda org, modules, fetcher: ({}, official_results),
    )
    monkeypatch.setattr(
        runner,
        "discover_final_website_with_wikidata",
        lambda profile, *, wikidata_candidate, timeout: (
            profile,
            {
                "requests": 2,
                "bytes": 0,
                "latencies_ms": [],
                "promoted": False,
                "selected_source": None,
            },
        ),
    )
    monkeypatch.setattr(
        runner,
        "evaluate_hyphenated_no_fallback",
        lambda profile, *, timeout, base_site_logical_requests: (
            profile,
            {
                "candidate_available": True,
                "attempted": True,
                "verified": True,
                "requests_added": 2,
                "bytes_added": 0,
                "latencies_ms": [],
                "skipped_reason": None,
                "guard_reasons": [],
            },
        ),
    )
    monkeypatch.setattr(runner, "attach_company_site_social_observations", lambda profile: profile)
    monkeypatch.setattr(runner, "attach_company_site_contact_email_observations", lambda profile: profile)

    _, report = runner._enrich_profile(
        _profile(),
        budget=RunBudget(max_challenge_requests=1802),
        site_timeout=6.0,
        wikidata_candidate=None,
    )

    assert report["site"]["promoted"] is True
    assert report["site"]["selected_source"] == "h1g_hyphenated_no"
    assert report["site"]["requests"] == 4
