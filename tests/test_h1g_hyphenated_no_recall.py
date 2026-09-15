from __future__ import annotations

from pathlib import Path
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import norway_company_agent.h1g_hyphenated_no_recall as h1g  # noqa: E402
from norway_company_agent.evidence import evidence  # noqa: E402


def _profile(
    *,
    organisation_number: str = "912345678",
    name: str = "EXAMPLE SYSTEMS AS",
    municipality: str = "OSLO",
    address: str = "Karl Johans gate 1",
    postcode: str = "0154",
    poststed: str = "OSLO",
    logical_requests: int = 7,
) -> dict:
    return {
        "organisation_number": organisation_number,
        "name": name,
        "municipality": municipality,
        "website": "",
        "run_metrics": {"logical_requests": logical_requests},
        "evidence": {
            "registry": evidence(
                "registry",
                "available",
                "official_registry_bulk",
                h1g.BRREG_BULK_URL,
                value={
                    "navn": name,
                    "forretningsadresse.adresse": address,
                    "forretningsadresse.postnummer": postcode,
                    "forretningsadresse.poststed": poststed,
                    "forretningsadresse.kommune": municipality,
                },
                source_row_key=organisation_number,
                content_sha256="b" * 64,
                retrieved_at="2026-09-15T00:00:00Z",
            ),
            "website": evidence(
                "website",
                "not_found",
                "bounded_final_website_discovery",
                h1g.BRREG_BULK_URL,
                note="fixture",
                retrieved_at="2026-09-15T00:00:00Z",
            ),
        },
    }


def _site(
    *,
    url: str = "https://example-systems.no/",
    title: str = "EXAMPLE SYSTEMS AS",
    text: str = "EXAMPLE SYSTEMS AS Organisasjonsnummer 912 345 678",
    identity_text: str | None = None,
) -> dict:
    domain = (urlparse(url).hostname or "").removeprefix("www.")
    excerpt = identity_text if identity_text is not None else text
    return evidence(
        "website",
        "available",
        "deterministic_legal_name_hyphenated_no_fallback",
        url,
        value={
            "requested_url": url,
            "final_url": url,
            "registered_domain": domain,
            "title": title,
            "description": "",
            "identity_text_excerpt": excerpt,
            "main_text_excerpt": text,
            "structured_organisations": [],
            "social_links": [],
            "pages": [{
                "url": url,
                "title": title,
                "identity_text_excerpt": excerpt,
                "main_text_excerpt": text,
                "content_sha256": "a" * 64,
            }],
            "content_sha256": "a" * 64,
        },
        content_sha256="a" * 64,
        retrieved_at="2026-09-15T00:00:00Z",
    )


def _general_assessment() -> dict:
    return {
        "status": "exact",
        "score": 0.95,
        "publishable": True,
        "reasons": ["general website identity gate passed"],
        "method": "fixture",
    }


def test_hyphenated_no_candidate_is_second_legal_name_form():
    candidate = h1g.hyphenated_no_candidate(_profile(name="MASTER SURGERY SYSTEMS AS"))
    assert candidate == {
        "domain": "master-surgery-systems.no",
        "url": "https://master-surgery-systems.no/",
        "strategy": "legal_name_hyphenated_no",
    }


def test_single_distinctive_token_has_no_distinct_hyphenated_candidate():
    assert h1g.hyphenated_no_candidate(_profile(name="MESCO AS")) is None


def test_exact_org_number_is_sufficient_h1g_homepage_proof():
    assessment = h1g.qualify_hyphenated_no_identity(_profile(), _site(), _general_assessment())
    assert assessment is not None
    assert assessment["publishable"] is True
    assert assessment["score"] == 1.0
    assert assessment["method"] == "h1g_hyphenated_no_homepage_identity_v1"


def test_full_legal_name_plus_registry_location_can_publish_without_org_number():
    site = _site(
        text="EXAMPLE SYSTEMS AS. Karl Johans gate 1, 0154 Oslo.",
        identity_text="EXAMPLE SYSTEMS AS. Karl Johans gate 1, 0154 Oslo.",
    )
    assessment = h1g.qualify_hyphenated_no_identity(_profile(), site, _general_assessment())
    assert assessment is not None
    assert assessment["publishable"] is True
    assert assessment["score"] >= 0.98


def test_title_and_hyphenated_domain_alone_do_not_publish():
    site = _site(
        title="EXAMPLE SYSTEMS AS",
        text="Example Systems builds software.",
        identity_text="",
    )
    assessment = h1g.qualify_hyphenated_no_identity(_profile(), site, _general_assessment())
    assert assessment is not None
    assert assessment["publishable"] is False
    assert assessment["status"] == "review"


def test_explicit_wrong_org_number_quarantines_candidate():
    site = _site(text="EXAMPLE SYSTEMS AS. Organisasjonsnummer 999 999 999. Karl Johans gate 1, 0154 Oslo.")
    assessment = h1g.qualify_hyphenated_no_identity(_profile(), site, _general_assessment())
    assert assessment is not None
    assert assessment["publishable"] is False
    assert "different organisation number" in " ".join(assessment["reasons"]).casefold()


def test_fallback_uses_only_remaining_two_site_requests_and_can_promote(monkeypatch):
    profile = _profile(logical_requests=7)
    site = _site()

    def fake_fetch(url, *, source_type, timeout=6.0, max_bytes=750_000):
        assert url == "https://example-systems.no/"
        return site, {"requests": 2, "bytes": 123, "latencies_ms": [7]}

    monkeypatch.setattr(h1g, "fetch_bounded_homepage", fake_fetch)
    monkeypatch.setattr(
        h1g,
        "apply_website_identity_gate",
        lambda row, record: {"website": record, "assessment": _general_assessment()},
    )
    monkeypatch.setattr(h1g, "apply_registry_risk_guard", lambda row: (row, []))

    row, metrics = h1g.evaluate_hyphenated_no_fallback(profile)
    assert metrics["attempted"] is True
    assert metrics["verified"] is True
    assert metrics["base_site_logical_requests"] == 2
    assert metrics["requests_added"] == 2
    assert metrics["post_site_logical_requests"] == h1g.MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE == 4
    assert row["website"] == "https://example-systems.no/"


def test_existing_verified_website_is_never_replaced(monkeypatch):
    profile = _profile(logical_requests=7)
    verified = _site(url="https://existing.no/")
    verified["value"]["identity_assessment"] = _general_assessment()
    profile["evidence"]["website"] = verified

    def should_not_fetch(*args, **kwargs):
        raise AssertionError("H1g must not fetch when a verified website already exists")

    monkeypatch.setattr(h1g, "fetch_bounded_homepage", should_not_fetch)
    row, metrics = h1g.evaluate_hyphenated_no_fallback(profile)
    assert metrics["attempted"] is False
    assert metrics["skipped_reason"] == "verified_website_present"
    assert row["evidence"]["website"]["source_url"] == "https://existing.no/"


def test_site_budget_consumed_prevents_attempt(monkeypatch):
    profile = _profile(logical_requests=9)

    def should_not_fetch(*args, **kwargs):
        raise AssertionError("H1g must not exceed the existing site request ceiling")

    monkeypatch.setattr(h1g, "fetch_bounded_homepage", should_not_fetch)
    _, metrics = h1g.evaluate_hyphenated_no_fallback(profile)
    assert metrics["attempted"] is False
    assert metrics["skipped_reason"] == "site_request_budget_consumed"
    assert metrics["base_site_logical_requests"] == 4
