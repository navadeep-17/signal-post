from __future__ import annotations

import norway_company_agent.annual_report_domain_discovery as v6e


def profile(name: str = "FJORD DATA SERVICE AS") -> dict:
    return {
        "organisation_number": "123456789",
        "name": name,
        "municipality": "OSLO",
        "evidence": {
            "website": {"status": "not_found", "value": {}},
        },
    }


def available_record(url: str = "https://fjorddata.no/") -> dict:
    return {
        "status": "available",
        "source_url": url,
        "content_sha256": "a" * 64,
        "value": {
            "final_url": url,
            "title": "Fjord Data Service AS",
            "identity_text_excerpt": "Fjord Data Service AS Org.nr 123 456 789 Oslo",
            "main_text_excerpt": "Fjord Data Service AS provides data services from Oslo.",
            "structured_organisations": [],
            "social_links": [],
            "pages": [],
        },
    }


def test_explicit_company_url_beats_auditor_and_free_mail():
    row = profile()
    text = """
    FJORD DATA SERVICE AS
    Kontakt og nettside: www.fjorddata.no
    Revisor: audit partner@example.pwc.no
    Privat kontakt: owner@gmail.com
    """
    candidates = v6e.extract_annual_report_domain_candidates(row, text)
    assert candidates
    assert candidates[0]["domain"] == "fjorddata.no"
    assert candidates[0]["strategy"] == "explicit_url"
    assert all(item["domain"] not in {"gmail.com", "pwc.no"} for item in candidates)


def test_company_style_email_domain_can_nominate_but_is_not_evidence():
    row = profile()
    text = "FJORD DATA SERVICE AS kontakt e-post info@fjorddata.no"
    candidates = v6e.extract_annual_report_domain_candidates(row, text)
    assert candidates == [
        {
            "domain": "fjorddata.no",
            "url": "https://fjorddata.no/",
            "strategy": "email_domain",
            "rank_score": candidates[0]["rank_score"],
            "rank_reasons": candidates[0]["rank_reasons"],
            "context": candidates[0]["context"],
            "email_local_part": "info",
        }
    ]
    assert candidates[0]["rank_score"] >= 60


def test_auditor_context_rejects_unknown_accounting_domain():
    row = profile()
    text = "Revisor og kontakt audit@example-regnskap.no for revisjon av FJORD DATA SERVICE AS"
    assert v6e.extract_annual_report_domain_candidates(row, text) == []


def test_single_token_company_requires_org_number(monkeypatch):
    row = profile("NOVA AS")
    row["annual_report_website_candidates"] = [{
        "domain": "nova.no", "url": "https://nova.no/", "strategy": "explicit_url", "rank_score": 90, "rank_reasons": [], "context": ""
    }]
    record = available_record("https://nova.no/")
    monkeypatch.setattr(v6e, "fetch_bounded_homepage", lambda *a, **k: (record, {"requests": 2, "bytes": 10, "latencies_ms": [1]}))
    monkeypatch.setattr(v6e, "apply_website_identity_gate", lambda p, r: {"website": r, "assessment": {"publishable": True, "score": 0.95, "status": "exact", "reasons": []}})
    monkeypatch.setattr(v6e, "_has_conflicting_explicit_org_number", lambda p, r: False)
    monkeypatch.setattr(v6e, "_page_contains_org_number", lambda p, r: False)
    monkeypatch.setattr(v6e, "_page_matches_registry_location", lambda p, r: True)

    result = v6e.probe_annual_report_candidates([row], max_logical_requests=2)
    assert result["verified"] == 0
    assert row["evidence"]["website"]["status"] == "not_found"


def test_multitoken_name_plus_registry_location_can_publish(monkeypatch):
    row = profile()
    row["annual_report_website_candidates"] = [{
        "domain": "fjorddata.no", "url": "https://fjorddata.no/", "strategy": "explicit_url", "rank_score": 100, "rank_reasons": [], "context": ""
    }]
    record = available_record()
    monkeypatch.setattr(v6e, "fetch_bounded_homepage", lambda *a, **k: (record, {"requests": 2, "bytes": 10, "latencies_ms": [1]}))
    monkeypatch.setattr(v6e, "apply_website_identity_gate", lambda p, r: {"website": r, "assessment": {"publishable": True, "score": 0.95, "status": "exact", "reasons": ["exact name"]}})
    monkeypatch.setattr(v6e, "_has_conflicting_explicit_org_number", lambda p, r: False)
    monkeypatch.setattr(v6e, "_page_contains_org_number", lambda p, r: False)
    monkeypatch.setattr(v6e, "_page_matches_registry_location", lambda p, r: True)

    result = v6e.probe_annual_report_candidates([row], max_logical_requests=2)
    assert result["verified"] == 1
    assert row["evidence"]["website"]["value"]["identity_assessment"]["publishable"] is True
    assert row["website"] == "https://fjorddata.no/"


def test_conflicting_org_number_always_rejects(monkeypatch):
    row = profile()
    row["annual_report_website_candidates"] = [{
        "domain": "fjorddata.no", "url": "https://fjorddata.no/", "strategy": "explicit_url", "rank_score": 100, "rank_reasons": [], "context": ""
    }]
    record = available_record()
    monkeypatch.setattr(v6e, "fetch_bounded_homepage", lambda *a, **k: (record, {"requests": 2, "bytes": 10, "latencies_ms": [1]}))
    monkeypatch.setattr(v6e, "apply_website_identity_gate", lambda p, r: {"website": r, "assessment": {"publishable": True, "score": 1.0, "status": "exact", "reasons": []}})
    monkeypatch.setattr(v6e, "_has_conflicting_explicit_org_number", lambda p, r: True)
    monkeypatch.setattr(v6e, "_page_contains_org_number", lambda p, r: True)

    result = v6e.probe_annual_report_candidates([row], max_logical_requests=2)
    assert result["verified"] == 0


def test_global_request_allowance_prevents_probe_when_two_requests_do_not_fit(monkeypatch):
    row = profile()
    row["annual_report_website_candidates"] = [{
        "domain": "fjorddata.no", "url": "https://fjorddata.no/", "strategy": "explicit_url", "rank_score": 100, "rank_reasons": [], "context": ""
    }]
    monkeypatch.setattr(v6e, "fetch_bounded_homepage", lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not fetch")))
    result = v6e.probe_annual_report_candidates([row], max_logical_requests=1)
    assert result["attempts"] == 0
    assert result["logical_requests"] == 0
