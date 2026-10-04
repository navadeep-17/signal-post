from __future__ import annotations

from copy import deepcopy

import norway_company_agent.wikidata_discovery as wikidata_discovery


def _profile() -> dict:
    return {
        "organisation_number": "912345678",
        "name": "EXAMPLE AS",
        "municipality": "OSLO",
        "evidence": {
            "registry": {
                "status": "available",
                "value": {
                    "forretningsadresse.postnummer": "0123",
                    "forretningsadresse.poststed": "OSLO",
                    "forretningsadresse.kommune": "OSLO",
                    "forretningsadresse.adresse": "Eksempelveien 1",
                },
            },
            "website": _primary(),
        },
    }


def _primary() -> dict:
    return {
        "status": "available",
        "source_type": "registry_linked_company_website",
        "source_url": "https://example.no/",
        "retrieved_at": "2026-10-04T10:00:00Z",
        "content_sha256": "a" * 64,
        "value": {
            "final_url": "https://example.no/",
            "registered_domain": "example.no",
            "content_sha256": "a" * 64,
            "identity_links": ["https://example.no/kontakt/"],
            "identity_assessment": {
                "status": "exact",
                "score": 1.0,
                "publishable": True,
                "method": "test_exact",
            },
        },
    }


def _surface(identity_text: str, *, final_url: str = "https://example.no/kontakt/") -> dict:
    return {
        "status": "available",
        "source_type": "phaseb-test-contact",
        "source_url": final_url,
        "retrieved_at": "2026-10-04T10:00:01Z",
        "content_sha256": "b" * 64,
        "value": {
            "final_url": final_url,
            "registered_domain": "example.no",
            "content_sha256": "b" * 64,
            "identity_text_excerpt": identity_text,
            "main_text_excerpt": identity_text,
            "pages": [
                {
                    "url": final_url,
                    "identity_text_excerpt": identity_text,
                    "main_text_excerpt": identity_text,
                    "content_sha256": "b" * 64,
                }
            ],
        },
    }


def _total(**overrides: object) -> dict:
    value = {
        "requests": 2,
        "bytes": 0,
        "latencies_ms": [],
        "promoted": True,
        "careers_surface_attempted": False,
        "news_detail_attempted": False,
    }
    value.update(overrides)
    return value


def test_idle_contact_surface_uses_only_remaining_two_requests(monkeypatch) -> None:
    profile = _profile()
    calls: list[str] = []

    def fake_fetch(url: str, **_: object):
        calls.append(url)
        return _surface("EXAMPLE AS · Org.nr 912 345 678 · post@example.no · Telefon: 22 33 44 55"), {
            "requests": 2,
            "bytes": 100,
            "latencies_ms": [12],
        }

    monkeypatch.setattr(wikidata_discovery, "fetch_bounded_homepage", fake_fetch)
    row, total = wikidata_discovery._maybe_attach_idle_contact_surface(
        deepcopy(profile), _total(), timeout=1.0
    )

    assert calls == ["https://example.no/kontakt/"]
    assert total["requests"] == 4
    assert total["contact_surface_attempted"] is True
    assert total["contact_surface_retained"] is True
    retained = row["evidence"]["website_contact_surface"]
    assert retained["content_sha256"] == "b" * 64
    identity = retained["value"]["contact_surface_identity"]
    assert identity["publishable"] is True
    assert identity["target_org_number_on_page"] is True


def test_idle_contact_surface_never_displaces_news_or_careers(monkeypatch) -> None:
    def should_not_fetch(*_: object, **__: object):
        raise AssertionError("contact fallback must not fetch when existing slot was attempted")

    monkeypatch.setattr(wikidata_discovery, "fetch_bounded_homepage", should_not_fetch)
    profile = _profile()

    _, news_total = wikidata_discovery._maybe_attach_idle_contact_surface(
        deepcopy(profile), _total(news_detail_attempted=True), timeout=1.0
    )
    _, careers_total = wikidata_discovery._maybe_attach_idle_contact_surface(
        deepcopy(profile), _total(careers_surface_attempted=True), timeout=1.0
    )

    assert news_total["requests"] == 2
    assert careers_total["requests"] == 2
    assert news_total["contact_surface_attempted"] is False
    assert careers_total["contact_surface_attempted"] is False


def test_idle_contact_surface_skips_when_request_budget_is_consumed(monkeypatch) -> None:
    def should_not_fetch(*_: object, **__: object):
        raise AssertionError("contact fallback must stay inside four-request site ceiling")

    monkeypatch.setattr(wikidata_discovery, "fetch_bounded_homepage", should_not_fetch)
    _, total = wikidata_discovery._maybe_attach_idle_contact_surface(
        _profile(), _total(requests=4), timeout=1.0
    )
    assert total["requests"] == 4
    assert total["contact_surface_attempted"] is False


def test_idle_contact_surface_rejects_conflicting_explicit_org(monkeypatch) -> None:
    def fake_fetch(url: str, **_: object):
        return _surface("EXAMPLE AS · Org.nr 999 999 999 · 0123 OSLO"), {
            "requests": 2,
            "bytes": 100,
            "latencies_ms": [12],
        }

    monkeypatch.setattr(wikidata_discovery, "fetch_bounded_homepage", fake_fetch)
    row, total = wikidata_discovery._maybe_attach_idle_contact_surface(
        _profile(), _total(), timeout=1.0
    )

    assert total["requests"] == 4
    assert total["contact_surface_attempted"] is True
    assert total["contact_surface_retained"] is False
    assert total["contact_surface_identity"]["conflicting_explicit_org_number"] is True
    assert "website_contact_surface" not in row["evidence"]


def test_idle_contact_surface_accepts_full_name_plus_registry_location(monkeypatch) -> None:
    def fake_fetch(url: str, **_: object):
        return _surface("EXAMPLE AS · Eksempelveien 1 · 0123 OSLO · Kontakt"), {
            "requests": 2,
            "bytes": 100,
            "latencies_ms": [12],
        }

    monkeypatch.setattr(wikidata_discovery, "fetch_bounded_homepage", fake_fetch)
    row, total = wikidata_discovery._maybe_attach_idle_contact_surface(
        _profile(), _total(), timeout=1.0
    )

    assert total["contact_surface_retained"] is True
    identity = row["evidence"]["website_contact_surface"]["value"]["contact_surface_identity"]
    assert identity["target_org_number_on_page"] is False
    assert identity["full_legal_name_on_page"] is True
    assert identity["registry_location_on_page"] is True
