from __future__ import annotations

from pathlib import Path
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import norway_company_agent.h1f_tld_recall as h1f  # noqa: E402
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
                h1f.BRREG_BULK_URL,
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
                h1f.BRREG_BULK_URL,
                note="fixture",
                retrieved_at="2026-09-15T00:00:00Z",
            ),
        },
    }


def _site(
    *,
    url: str = "https://examplesystems.com/",
    title: str = "EXAMPLE SYSTEMS AS",
    text: str = "EXAMPLE SYSTEMS AS Organisasjonsnummer 912 345 678",
    identity_text: str | None = None,
) -> dict:
    domain = (urlparse(url).hostname or "").removeprefix("www.")
    excerpt = identity_text if identity_text is not None else text
    return evidence(
        "website",
        "available",
        "deterministic_legal_name_com_fallback",
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


def test_compact_com_candidate_uses_same_legal_name_tokens_without_legal_form():
    candidate = h1f.compact_com_candidate(_profile(name="MASTER SURGERY SYSTEMS AS"))
    assert candidate == {
        "domain": "mastersurgerysystems.com",
        "url": "https://mastersurgerysystems.com/",
        "strategy": "legal_name_compact_com",
    }


def test_compact_com_candidate_abstains_when_legal_name_has_no_distinctive_tokens():
    assert h1f.compact_com_candidate(_profile(name="AS")) is None


def test_exact_org_number_is_sufficient_h1f_homepage_proof():
    assessment = h1f.qualify_compact_com_identity(
        _profile(),
        _site(),
        _general_assessment(),
    )
    assert assessment is not None
    assert assessment["publishable"] is True
    assert assessment["score"] == 1.0
    assert assessment["method"] == "h1f_compact_com_homepage_identity_v1"


def test_full_legal_name_plus_registry_location_can_publish_without_org_number():
    site = _site(
        text="EXAMPLE SYSTEMS AS. Karl Johans gate 1, 0154 Oslo.",
        identity_text="EXAMPLE SYSTEMS AS. Karl Johans gate 1, 0154 Oslo.",
    )
    assessment = h1f.qualify_compact_com_identity(
        _profile(),
        site,
        _general_assessment(),
    )
    assert assessment is not None
    assert assessment["publishable"] is True
    assert assessment["score"] >= 0.98


def test_title_and_domain_similarity_alone_are_not_enough_for_h1f():
    site = _site(
        title="EXAMPLE SYSTEMS AS",
        text="Example Systems builds software worldwide.",
        identity_text="",
    )
    assessment = h1f.qualify_compact_com_identity(
        _profile(),
        site,
        _general_assessment(),
    )
    assert assessment is not None
    assert assessment["publishable"] is False
    assert assessment["status"] == "review"


def test_explicit_wrong_org_number_quarantines_h1f_candidate():
    site = _site(
        text="EXAMPLE SYSTEMS AS. Organisasjonsnummer 999 999 999. Karl Johans gate 1, 0154 Oslo.",
    )
    assessment = h1f.qualify_compact_com_identity(
        _profile(),
        site,
        _general_assessment(),
    )
    assert assessment is not None
    assert assessment["publishable"] is False
    assert "different organisation number" in " ".join(assessment["reasons"]).casefold()


def test_fallback_uses_only_remaining_two_site_requests_and_can_promote(monkeypatch):
    profile = _profile(logical_requests=7)  # 5 official + 2 site already used.
    site = _site()

    def fake_fetch(url, *, source_type, timeout=6.0, max_bytes=750_000):
        assert url == "https://examplesystems.com/"
        return site, {"requests": 2, "bytes": 123, "latencies_ms": [7]}

    monkeypatch.setattr(h1f, "fetch_bounded_homepage", fake_fetch)
    monkeypatch.setattr(
        h1f,
        "apply_website_identity_gate",
        lambda row, record: {"website": record, "assessment": _general_assessment()},
    )
    monkeypatch.setattr(h1f, "apply_registry_risk_guard", lambda row: (row, []))

    row, metrics = h1f.evaluate_compact_com_fallback(profile)

    assert metrics["attempted"] is True
    assert metrics["verified"] is True
    assert metrics["base_site_logical_requests"] == 2
    assert metrics["requests_added"] == 2
    assert metrics["post_site_logical_requests"] == h1f.MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE == 4
    assert row["website"] == "https://examplesystems.com/"
    assert row["evidence"]["website"]["value"]["identity_assessment"]["publishable"] is True


def test_fallback_never_replaces_existing_verified_website(monkeypatch):
    profile = _profile(logical_requests=7)
    verified = _site(url="https://existing.no/")
    verified["value"]["identity_assessment"] = _general_assessment()
    profile["evidence"]["website"] = verified

    def should_not_fetch(*args, **kwargs):
        raise AssertionError("H1f must not fetch when a verified website already exists")

    monkeypatch.setattr(h1f, "fetch_bounded_homepage", should_not_fetch)
    row, metrics = h1f.evaluate_compact_com_fallback(profile)

    assert metrics["attempted"] is False
    assert metrics["skipped_reason"] == "verified_website_present"
    assert row["evidence"]["website"]["source_url"] == "https://existing.no/"


def test_fallback_abstains_when_existing_pipeline_consumed_site_budget(monkeypatch):
    profile = _profile(logical_requests=9)  # 5 official + all 4 site requests used.

    def should_not_fetch(*args, **kwargs):
        raise AssertionError("H1f must not exceed the existing site request ceiling")

    monkeypatch.setattr(h1f, "fetch_bounded_homepage", should_not_fetch)
    _, metrics = h1f.evaluate_compact_com_fallback(profile)

    assert metrics["attempted"] is False
    assert metrics["skipped_reason"] == "site_request_budget_consumed"
    assert metrics["base_site_logical_requests"] == 4


def test_registry_guard_rejection_does_not_replace_base_terminal_website(monkeypatch):
    profile = _profile(logical_requests=7)
    original = profile["evidence"]["website"]
    site = _site()

    monkeypatch.setattr(
        h1f,
        "fetch_bounded_homepage",
        lambda *args, **kwargs: (site, {"requests": 2, "bytes": 10, "latencies_ms": [1]}),
    )
    monkeypatch.setattr(
        h1f,
        "apply_website_identity_gate",
        lambda row, record: {"website": record, "assessment": _general_assessment()},
    )

    def reject(row):
        row["evidence"]["website"]["value"]["identity_assessment"]["publishable"] = False
        return row, ["fixture registry risk"]

    monkeypatch.setattr(h1f, "apply_registry_risk_guard", reject)
    row, metrics = h1f.evaluate_compact_com_fallback(profile)

    assert metrics["attempted"] is True
    assert metrics["verified"] is False
    assert metrics["guard_reasons"] == ["fixture registry risk"]
    assert row["evidence"]["website"]["status"] == original["status"] == "not_found"
    assert "website_h1f_candidate" in row["evidence"]
