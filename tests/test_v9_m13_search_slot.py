from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent import v9_m13_search_slot as m13  # noqa: E402


def _profile() -> dict:
    return {
        "organisation_number": "923368876",
        "name": "TRE FOR EN AS",
        "municipality": "RISØR",
        "website": "",
        "evidence": {
            "website": {"status": "not_found"},
            "registry": {
                "status": "available",
                "value": {
                    "forretningsadresse.kommune": "RISØR",
                },
            },
        },
    }


def _h1g_marker(*, verified: bool = False):
    calls = {"count": 0}

    def run(profile, *, timeout, base_site_logical_requests):
        calls["count"] += 1
        return profile, {
            "candidate_available": True,
            "attempted": True,
            "verified": verified,
            "requests_added": 2,
            "bytes_added": 0,
            "latencies_ms": [],
        }

    return calls, run


def test_search_disabled_preserves_h1g_exactly() -> None:
    calls, h1g = _h1g_marker()
    row, result = m13.evaluate_m13_search_slot(
        _profile(),
        enabled=False,
        api_key="",
        base_site_logical_requests=2,
        h1g_evaluator=h1g,
    )
    assert row["organisation_number"] == "923368876"
    assert calls["count"] == 1
    assert result["provider_attempted"] is False
    assert result["provider_api_requests"] == 0
    assert result["h1g_fallback_attempted"] is True
    assert result["strategy"] == "preserve_h1g_search_disabled"


def test_no_provider_candidate_spends_one_api_request_then_preserves_h1g() -> None:
    calls, h1g = _h1g_marker()

    def search(profile, *, api_key):
        return {
            "status": "no_candidate",
            "candidate_urls": [],
            "query_sha256": ["a" * 64],
            "cost": {
                "web_search_calls": 1,
                "input_tokens": 100,
                "output_tokens": 10,
                "estimated_cost_usd": 0.010015,
            },
        }

    _, result = m13.evaluate_m13_search_slot(
        _profile(),
        enabled=True,
        api_key="evaluator-test-key",
        base_site_logical_requests=2,
        search_fn=search,
        h1g_evaluator=h1g,
    )
    assert calls["count"] == 1
    assert result["search_eligible"] is True
    assert result["provider_api_requests"] == 1
    assert result["provider_web_search_calls"] == 1
    assert result["candidate_fetch_attempted"] is False
    assert result["h1g_fallback_attempted"] is True
    assert result["strategy"] == "search_no_candidate_then_h1g"


def test_verified_search_candidate_replaces_h1g_and_keeps_site_ceiling(monkeypatch) -> None:
    h1g_calls, h1g = _h1g_marker()

    def search(profile, *, api_key):
        return {
            "status": "candidates_found",
            "candidate_urls": ["https://hauglidhelse.no/"],
            "query_sha256": ["b" * 64],
            "cost": {
                "web_search_calls": 1,
                "input_tokens": 100,
                "output_tokens": 10,
                "estimated_cost_usd": 0.010015,
            },
        }

    def fetch(url, *, source_type, timeout):
        return (
            {
                "status": "available",
                "source_url": url,
                "source_type": source_type,
                "content_sha256": "c" * 64,
                "value": {
                    "final_url": url,
                    "registered_domain": "hauglidhelse.no",
                    "content_sha256": "c" * 64,
                    "title": "TRE FOR EN AS",
                    "identity_text_excerpt": "Organisasjonsnummer 923 368 876",
                    "main_text_excerpt": "TRE FOR EN AS RISØR",
                    "structured_organisations": [],
                    "pages": [],
                },
            },
            {"requests": 2, "bytes": 100, "latencies_ms": [1]},
        )

    monkeypatch.setattr(
        m13,
        "apply_website_identity_gate",
        lambda profile, website: {
            "website": website,
            "assessment": {
                "status": "exact",
                "score": 1.0,
                "publishable": True,
                "method": "fixture_identity",
                "reasons": [],
            },
        },
    )
    monkeypatch.setattr(
        m13,
        "qualify_search_discovered_website",
        lambda profile, website, assessment: {
            **assessment,
            "status": "exact",
            "score": 1.0,
            "publishable": True,
            "method": "search_discovered_page_identity_guard_v1",
        },
    )
    monkeypatch.setattr(m13, "apply_registry_risk_guard", lambda profile: (profile, []))

    row, result = m13.evaluate_m13_search_slot(
        _profile(),
        enabled=True,
        api_key="evaluator-test-key",
        base_site_logical_requests=2,
        search_fn=search,
        fetch_fn=fetch,
        h1g_evaluator=h1g,
    )
    assert h1g_calls["count"] == 0
    assert result["provider_api_requests"] == 1
    assert result["candidate_fetch_logical_requests"] == 2
    assert 2 + result["candidate_fetch_logical_requests"] == 4
    assert result["verified"] is True
    assert result["strategy"] == "m13_search_replaced_h1g"
    assert row["website"] == "https://hauglidhelse.no/"
    audit = row["discovery_audit"]["m13_search"]
    assert audit["provider_result_text_persisted"] is False
    assert audit["provider_is_publication_evidence"] is False


def test_rejected_fetched_candidate_consumes_slot_and_never_adds_h1g(monkeypatch) -> None:
    h1g_calls, h1g = _h1g_marker()

    def search(profile, *, api_key):
        return {
            "status": "candidates_found",
            "candidate_urls": ["https://wrong.example/"],
            "query_sha256": ["d" * 64],
            "cost": {
                "web_search_calls": 1,
                "input_tokens": 0,
                "output_tokens": 0,
                "estimated_cost_usd": 0.01,
            },
        }

    def fetch(url, *, source_type, timeout):
        return (
            {
                "status": "available",
                "source_url": url,
                "source_type": source_type,
                "content_sha256": "e" * 64,
                "value": {
                    "final_url": url,
                    "registered_domain": "wrong.example",
                    "content_sha256": "e" * 64,
                    "title": "WRONG COMPANY AS",
                    "identity_text_excerpt": "Org nr 999 999 999",
                    "main_text_excerpt": "Wrong entity",
                    "structured_organisations": [],
                    "pages": [],
                },
            },
            {"requests": 2, "bytes": 100, "latencies_ms": [1]},
        )

    monkeypatch.setattr(
        m13,
        "apply_website_identity_gate",
        lambda profile, website: {
            "website": website,
            "assessment": {
                "status": "review",
                "score": 0.3,
                "publishable": False,
                "method": "fixture_identity",
                "reasons": ["wrong"],
            },
        },
    )

    _, result = m13.evaluate_m13_search_slot(
        _profile(),
        enabled=True,
        api_key="evaluator-test-key",
        base_site_logical_requests=2,
        search_fn=search,
        fetch_fn=fetch,
        h1g_evaluator=h1g,
    )
    assert h1g_calls["count"] == 0
    assert result["candidate_fetch_logical_requests"] == 2
    assert result["verified"] is False
    assert result["strategy"] == "m13_search_candidate_rejected_slot_consumed"


def test_no_replaceable_h1g_slot_never_calls_provider() -> None:
    calls = {"search": 0}
    h1g_calls, h1g = _h1g_marker()

    def search(profile, *, api_key):
        calls["search"] += 1
        raise AssertionError("provider must not be called without a baseline H1g slot")

    _, result = m13.evaluate_m13_search_slot(
        _profile(),
        enabled=True,
        api_key="evaluator-test-key",
        base_site_logical_requests=4,
        search_fn=search,
        h1g_evaluator=h1g,
    )
    assert calls["search"] == 0
    assert h1g_calls["count"] == 1
    assert result["provider_api_requests"] == 0
    assert result["strategy"] == "preserve_h1g_no_replaceable_slot"
