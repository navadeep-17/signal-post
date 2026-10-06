from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.hiring_intent import (  # noqa: E402
    extract_company_authored_hiring_intent,
    hiring_intent_match,
)


def _website(text: str, *, publishable: bool = True) -> dict:
    return {
        "status": "available",
        "source_type": "registry_linked_company_website",
        "source_url": "https://example.no/",
        "retrieved_at": "2026-10-06T10:00:00Z",
        "content_sha256": "a" * 64,
        "value": {
            "final_url": "https://example.no/",
            "content_sha256": "a" * 64,
            "main_text_excerpt": text,
            "identity_assessment": {
                "status": "exact" if publishable else "review",
                "score": 1.0 if publishable else 0.8,
                "publishable": publishable,
                "method": "fixture",
            },
            "careers_links": [
                {
                    "url": "https://example.no/karriere/",
                    "homepage_url": "https://example.no/",
                    "homepage_content_sha256": "a" * 64,
                }
            ],
            "pages": [],
        },
    }


def _profile(text: str, *, publishable: bool = True) -> dict:
    return {
        "organisation_number": "123456789",
        "name": "EXAMPLE AS",
        "evidence": {"website": _website(text, publishable=publishable)},
    }


def test_explicit_norwegian_people_recruitment_is_intent() -> None:
    result = hiring_intent_match("Vi søker etter dyktige medarbeidere til teamet vårt.")
    assert result is not None
    assert result["match_type"] == "no_vi_soker"


def test_vi_soker_without_people_context_abstains() -> None:
    assert hiring_intent_match("Vi søker etter bedre løsninger for kundene våre.") is None


def test_negative_hiring_statement_abstains() -> None:
    assert hiring_intent_match("Vi har ingen ledige stillinger akkurat nå.") is None
    assert hiring_intent_match("We are not hiring at this time.") is None


def test_generic_careers_navigation_is_not_intent() -> None:
    assert hiring_intent_match("Karriere") is None
    assert hiring_intent_match("Join our team") is None


def test_explicit_english_hiring_is_intent() -> None:
    result = hiring_intent_match("We are hiring engineers to join our product team.")
    assert result is not None
    assert result["match_type"] == "en_we_are_hiring"


def test_unverified_site_never_emits_intent() -> None:
    assert extract_company_authored_hiring_intent(
        _profile("Vi søker dyktige medarbeidere.", publishable=False)
    ) == []


def test_homepage_intent_uses_exact_page_hash() -> None:
    rows = extract_company_authored_hiring_intent(
        _profile("Vi søker dyktige medarbeidere til teamet vårt.")
    )
    assert len(rows) == 1
    assert rows[0]["source_url"] == "https://example.no/"
    assert rows[0]["content_sha256"] == "a" * 64
    assert rows[0]["network_requests_added"] == 0
    assert "not a claim that a specific vacancy" in rows[0]["claim_scope"]


def test_homepage_nominated_retained_careers_surface_can_supply_intent() -> None:
    profile = _profile("Velkommen til Example.")
    profile["evidence"]["website_careers_surface"] = {
        "status": "available",
        "source_type": "verified_company_careers_surface_candidate",
        "source_url": "https://example.no/karriere/",
        "retrieved_at": "2026-10-06T10:01:00Z",
        "content_sha256": "b" * 64,
        "value": {
            "final_url": "https://example.no/karriere/",
            "content_sha256": "b" * 64,
            "main_text_excerpt": "We are hiring engineers and product managers.",
        },
    }
    rows = extract_company_authored_hiring_intent(profile)
    assert len(rows) == 1
    assert rows[0]["source_url"] == "https://example.no/karriere/"
    assert rows[0]["content_sha256"] == "b" * 64
    assert rows[0]["provenance"] == "homepage_nominated_careers_surface"


def test_cross_domain_surface_is_not_first_party_intent() -> None:
    profile = _profile("Velkommen til Example.")
    profile["evidence"]["website_careers_surface"] = {
        "status": "available",
        "source_type": "verified_company_careers_surface_candidate",
        "source_url": "https://jobs.vendor.example/karriere/",
        "retrieved_at": "2026-10-06T10:01:00Z",
        "content_sha256": "b" * 64,
        "value": {
            "final_url": "https://jobs.vendor.example/karriere/",
            "content_sha256": "b" * 64,
            "main_text_excerpt": "We are hiring engineers.",
        },
    }
    assert extract_company_authored_hiring_intent(profile) == []
