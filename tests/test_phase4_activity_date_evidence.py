from __future__ import annotations

from bs4 import BeautifulSoup

from norway_company_agent.evidence import evidence
from norway_company_agent.final_site_discovery import _page_date_candidates
from norway_company_agent.first_party_activity import extract_strict_first_party_facts


def _profile(*, title: str, text: str, candidates: list[dict[str, str]]) -> dict:
    homepage_url = "https://example.no/"
    detail_url = "https://example.no/aktuelt/konkret-oppdatering/"
    homepage = evidence(
        "website",
        "available",
        "test_company_site",
        homepage_url,
        value={
            "final_url": homepage_url,
            "registered_domain": "example.no",
            "identity_assessment": {"status": "exact", "score": 1.0, "publishable": True},
            "news_detail_links": [{"url": detail_url, "nomination_only": True, "marker": "aktuelt"}],
            "pages": [{
                "url": homepage_url,
                "title": "Example AS",
                "main_text_excerpt": "Example AS",
                "identity_text_excerpt": "",
                "content_sha256": "a" * 64,
            }],
        },
        content_sha256="a" * 64,
        retrieved_at="2026-10-04T00:00:00Z",
    )
    detail = evidence(
        "website",
        "available",
        "verified_company_news_detail_candidate",
        detail_url,
        value={
            "final_url": detail_url,
            "registered_domain": "example.no",
            "pages": [{
                "url": detail_url,
                "title": title,
                "main_text_excerpt": text,
                "identity_text_excerpt": "",
                "published_date_candidates": candidates,
                "content_sha256": "b" * 64,
            }],
        },
        content_sha256="b" * 64,
        retrieved_at="2026-10-03T12:34:56Z",
    )
    return {
        "organisation_number": "923609016",
        "name": "Example AS",
        "evidence": {"website": homepage, "website_news_detail": detail},
    }


def test_strong_publication_metadata_beats_dynamic_labelled_date() -> None:
    profile = _profile(
        title="Example lanserer ny tjeneste",
        text="Example AS lanserer en ny tjeneste. Sist besøkt 04/10/2026.",
        candidates=[
            {"raw": "2021-11-16T09:30:00+01:00", "method": "meta_article_published_time"},
            {"raw": "04/10/2026", "method": "date_labelled_element"},
        ],
    )
    updates = extract_strict_first_party_facts(profile)["updates"]
    assert len(updates) == 1
    assert updates[0]["published_date"] == "2021-11-16"
    assert updates[0]["date_extraction_method"] == "meta_article_published_time"
    assert updates[0]["date_evidence"] == "2021-11-16T09:30:00+01:00"
    assert updates[0]["retrieved_at"] == "2026-10-03T12:34:56Z"


def test_equally_strong_conflicting_publication_dates_abstain() -> None:
    profile = _profile(
        title="Example lanserer ny tjeneste",
        text="Example AS lanserer en ny tjeneste.",
        candidates=[
            {"raw": "2026-09-01T09:30:00+02:00", "method": "meta_article_published_time"},
            {"raw": "2026-09-02T09:30:00+02:00", "method": "meta_article_published_time"},
        ],
    )
    assert extract_strict_first_party_facts(profile)["updates"] == []


def test_unambiguous_text_date_remains_supported_when_no_semantic_candidate_exists() -> None:
    profile = _profile(
        title="Example lanserer ny tjeneste",
        text="Example AS lanserer en ny tjeneste. Publisert 2026-09-01.",
        candidates=[],
    )
    updates = extract_strict_first_party_facts(profile)["updates"]
    assert len(updates) == 1
    assert updates[0]["published_date"] == "2026-09-01"
    assert updates[0]["date_extraction_method"] == "unambiguous_page_text"


def test_multiple_unstructured_page_dates_abstain() -> None:
    profile = _profile(
        title="Example lanserer ny tjeneste",
        text="Publisert 2026-09-01. Oppdatert 2026-09-02.",
        candidates=[],
    )
    assert extract_strict_first_party_facts(profile)["updates"] == []


def test_default_wordpress_placeholder_is_never_company_activity() -> None:
    profile = _profile(
        title="Hello world!",
        text="Welcome to WordPress. This is your first post. Edit or delete it, then start writing!",
        candidates=[{"raw": "2021-11-16", "method": "meta_article_published_time"}],
    )
    assert extract_strict_first_party_facts(profile)["updates"] == []


def test_page_date_candidates_retain_jsonld_article_publication_dates() -> None:
    soup = BeautifulSoup("<html><head></head><body></body></html>", "lxml")
    candidates = _page_date_candidates(
        soup,
        structured={
            "json-ld": [
                {
                    "@type": "NewsArticle",
                    "headline": "Specific company update",
                    "datePublished": "2026-09-18T09:00:00+02:00",
                },
                {
                    "@type": "BlogPosting",
                    "headline": "Another company update",
                    "datePublished": "2026-09-17",
                },
            ]
        },
    )
    assert candidates == [
        {
            "raw": "2026-09-18T09:00:00+02:00",
            "method": "jsonld_newsarticle_date_published",
        },
        {
            "raw": "2026-09-17",
            "method": "jsonld_blogposting_date_published",
        },
    ]


def test_blogposting_jsonld_date_is_strict_page_local_metadata() -> None:
    profile = _profile(
        title="Example publishes new sustainability update",
        text="Example AS publishes a detailed sustainability update.",
        candidates=[
            {"raw": "2026-09-19", "method": "jsonld_blogposting_date_published"}
        ],
    )
    updates = extract_strict_first_party_facts(profile)["updates"]
    assert len(updates) == 1
    assert updates[0]["published_date"] == "2026-09-19"
    assert updates[0]["date_extraction_method"] == "jsonld_blogposting_date_published"
