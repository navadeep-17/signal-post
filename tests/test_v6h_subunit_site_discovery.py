from __future__ import annotations

import norway_company_agent.official as official
import norway_company_agent.subunit_site_discovery as v6h
from norway_company_agent.v6h_subunit_contact_hook import install_subunit_contact_hint_hook


def profile(name: str = "FJORD DATA SERVICE AS") -> dict:
    return {
        "organisation_number": "123456789",
        "name": name,
        "municipality": "OSLO",
        "evidence": {
            "website": {"status": "not_found", "value": {}},
            "locations": {
                "status": "available",
                "value": {
                    "locations": [
                        {
                            "organisation_number": "987654321",
                            "name": "FJORD DATA SERVICE AVD OSLO",
                            "address": {"postnummer": "0250", "poststed": "OSLO"},
                            "website_hint": "https://fjorddata.no/contact",
                            "email_hint": "oslo@fjorddata.no",
                        }
                    ]
                },
            },
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


def test_hook_retains_subunit_website_and_email_without_changing_base_fields():
    body = {
        "_embedded": {
            "underenheter": [
                {
                    "organisasjonsnummer": "987654321",
                    "navn": "FJORD DATA SERVICE AVD OSLO",
                    "beliggenhetsadresse": {"postnummer": "0250", "poststed": "OSLO"},
                    "naeringskode1": {"kode": "62.010"},
                    "antallAnsatte": 5,
                    "hjemmeside": "https://fjorddata.no",
                    "epostadresse": "oslo@fjorddata.no",
                },
                {
                    "organisasjonsnummer": "987654322",
                    "navn": "FJORD DATA SERVICE AVD BERGEN",
                    "beliggenhetsadresse": {"postnummer": "5003", "poststed": "BERGEN"},
                },
            ]
        }
    }
    original = official.normalize_locations
    try:
        install_subunit_contact_hint_hook()
        normalized = official.normalize_locations(body)
    finally:
        official.normalize_locations = original
    first, second = normalized["locations"]
    assert first["organisation_number"] == "987654321"
    assert first["website_hint"] == "https://fjorddata.no"
    assert first["email_hint"] == "oslo@fjorddata.no"
    assert first["employees"] == 5
    assert "website_hint" not in second and "email_hint" not in second


def test_registered_website_outranks_email_domain_and_dedupes_domain():
    rows = v6h.subunit_site_candidates(profile())
    assert len(rows) == 1
    assert rows[0]["domain"] == "fjorddata.no"
    assert rows[0]["strategy"] == "brreg_subunit_registered_website"
    assert rows[0]["hint_frequency"] == 2


def test_repeated_domain_across_subunits_receives_repeat_signal():
    row = profile()
    row["evidence"]["locations"]["value"]["locations"].append(
        {
            "organisation_number": "987654322",
            "name": "FJORD DATA SERVICE AVD BERGEN",
            "website_hint": "https://fjorddata.no/bergen",
        }
    )
    candidate = v6h.subunit_site_candidates(row)[0]
    assert candidate["domain"] == "fjorddata.no"
    assert candidate["hint_frequency"] >= 2
    assert any("repeated" in reason for reason in candidate["rank_reasons"])


def test_free_consumer_email_domain_is_not_a_candidate():
    row = profile()
    row["evidence"]["locations"]["value"]["locations"] = [
        {
            "organisation_number": "987654321",
            "name": "FJORD DATA SERVICE AVD OSLO",
            "email_hint": "owner@gmail.com",
        }
    ]
    assert v6h.subunit_site_candidates(row) == []


def test_conflicting_org_number_rejects_even_if_base_gate_is_exact(monkeypatch):
    row = profile()
    record = available_record()
    monkeypatch.setattr(v6h, "fetch_bounded_homepage", lambda *a, **k: (record, {"requests": 2, "bytes": 10, "latencies_ms": [1]}))
    monkeypatch.setattr(v6h, "apply_website_identity_gate", lambda p, r: {"website": r, "assessment": {"publishable": True, "score": 1.0, "status": "exact", "reasons": []}})
    monkeypatch.setattr(v6h, "_has_conflicting_explicit_org_number", lambda p, r: True)
    monkeypatch.setattr(v6h, "_page_contains_org_number", lambda p, r: True)
    result = v6h.probe_subunit_site_candidates([row], max_logical_requests=2)
    assert result["verified"] == 0
    assert row["evidence"]["website"]["status"] == "not_found"


def test_exact_parent_org_on_fetched_page_can_publish(monkeypatch):
    row = profile()
    record = available_record()
    monkeypatch.setattr(v6h, "fetch_bounded_homepage", lambda *a, **k: (record, {"requests": 2, "bytes": 10, "latencies_ms": [1]}))
    monkeypatch.setattr(v6h, "apply_website_identity_gate", lambda p, r: {"website": r, "assessment": {"publishable": True, "score": 1.0, "status": "exact", "reasons": []}})
    monkeypatch.setattr(v6h, "_has_conflicting_explicit_org_number", lambda p, r: False)
    monkeypatch.setattr(v6h, "_page_contains_org_number", lambda p, r: True)
    result = v6h.probe_subunit_site_candidates([row], max_logical_requests=2)
    assert result["verified"] == 1
    assert row["website"] == "https://fjorddata.no/"


def test_multitoken_parent_name_plus_location_can_publish(monkeypatch):
    row = profile()
    record = available_record()
    monkeypatch.setattr(v6h, "fetch_bounded_homepage", lambda *a, **k: (record, {"requests": 2, "bytes": 10, "latencies_ms": [1]}))
    monkeypatch.setattr(v6h, "apply_website_identity_gate", lambda p, r: {"website": r, "assessment": {"publishable": True, "score": 0.95, "status": "exact", "reasons": ["exact legal name"]}})
    monkeypatch.setattr(v6h, "_has_conflicting_explicit_org_number", lambda p, r: False)
    monkeypatch.setattr(v6h, "_page_contains_org_number", lambda p, r: False)
    monkeypatch.setattr(v6h, "_page_matches_registry_location", lambda p, r: True)
    result = v6h.probe_subunit_site_candidates([row], max_logical_requests=2)
    assert result["verified"] == 1


def test_single_token_parent_plus_location_still_abstains(monkeypatch):
    row = profile("NOVA AS")
    row["evidence"]["locations"]["value"]["locations"][0]["website_hint"] = "https://nova.no"
    row["evidence"]["locations"]["value"]["locations"][0].pop("email_hint", None)
    record = available_record("https://nova.no/")
    monkeypatch.setattr(v6h, "fetch_bounded_homepage", lambda *a, **k: (record, {"requests": 2, "bytes": 10, "latencies_ms": [1]}))
    monkeypatch.setattr(v6h, "apply_website_identity_gate", lambda p, r: {"website": r, "assessment": {"publishable": True, "score": 0.95, "status": "exact", "reasons": []}})
    monkeypatch.setattr(v6h, "_has_conflicting_explicit_org_number", lambda p, r: False)
    monkeypatch.setattr(v6h, "_page_contains_org_number", lambda p, r: False)
    monkeypatch.setattr(v6h, "_page_matches_registry_location", lambda p, r: True)
    result = v6h.probe_subunit_site_candidates([row], max_logical_requests=2)
    assert result["verified"] == 0


def test_request_allowance_prevents_probe_if_robots_plus_homepage_do_not_fit(monkeypatch):
    row = profile()
    monkeypatch.setattr(v6h, "fetch_bounded_homepage", lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not fetch")))
    result = v6h.probe_subunit_site_candidates([row], max_logical_requests=1)
    assert result["attempts"] == 0
    assert result["logical_requests"] == 0
