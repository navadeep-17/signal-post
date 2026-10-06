from __future__ import annotations

from pathlib import Path
import sys

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import norway_company_agent.final_site_discovery as final_site  # noqa: E402
from norway_company_agent.evidence import evidence  # noqa: E402
from norway_company_agent.first_party_activity import extract_strict_first_party_facts  # noqa: E402


def test_jsonld_article_dates_are_retained_as_page_local_candidates() -> None:
    soup = BeautifulSoup("<html><head><title>News</title></head><body></body></html>", "lxml")
    structured = {
        "json-ld": [
            {
                "@type": "NewsArticle",
                "headline": "Example launches new service",
                "datePublished": "2026-09-20T08:30:00+02:00",
            },
            {
                "@type": "Organization",
                "name": "Example AS",
                "foundingDate": "2001-01-01",
            },
        ]
    }
    candidates = final_site._page_date_candidates(soup, structured=structured)
    assert {
        "raw": "2026-09-20T08:30:00+02:00",
        "method": "jsonld_newsarticle_date_published",
    } in candidates
    assert not any(item["raw"] == "2001-01-01" for item in candidates)


def test_blogposting_date_is_retained_with_distinct_method() -> None:
    soup = BeautifulSoup("<html><body><article>Update</article></body></html>", "lxml")
    candidates = final_site._page_date_candidates(
        soup,
        structured={
            "json-ld": [
                {
                    "@type": "BlogPosting",
                    "headline": "Example opens new office",
                    "datePublished": "2026-09-21",
                }
            ]
        },
    )
    assert candidates == [
        {
            "raw": "2026-09-21",
            "method": "jsonld_blogposting_date_published",
        }
    ]


def _profile_with_structured_date(
    candidates: list[dict[str, str]],
    *,
    retrieved_at: str = "2026-10-06T10:00:00Z",
) -> dict:
    homepage_url = "https://example.no/"
    detail_url = "https://example.no/news/new-office/"
    homepage = evidence(
        "website",
        "available",
        "registry_linked_company_website",
        homepage_url,
        value={
            "final_url": homepage_url,
            "identity_assessment": {
                "status": "exact",
                "score": 1.0,
                "publishable": True,
            },
            "news_detail_links": [{"url": detail_url, "nomination_only": True}],
            "pages": [
                {
                    "url": homepage_url,
                    "title": "Example AS",
                    "main_text_excerpt": "Example AS",
                    "identity_text_excerpt": "",
                    "content_sha256": "a" * 64,
                }
            ],
        },
        content_sha256="a" * 64,
        retrieved_at=retrieved_at,
    )
    detail = evidence(
        "website",
        "available",
        "verified_company_news_detail_candidate",
        detail_url,
        value={
            "final_url": detail_url,
            "pages": [
                {
                    "url": detail_url,
                    "title": "Example opens a new office in Oslo",
                    "main_text_excerpt": "Example AS has opened a new office in Oslo.",
                    "identity_text_excerpt": "",
                    "published_date_candidates": candidates,
                    "content_sha256": "b" * 64,
                }
            ],
        },
        content_sha256="b" * 64,
        retrieved_at=retrieved_at,
    )
    return {
        "organisation_number": "923609016",
        "name": "Example AS",
        "evidence": {
            "website": homepage,
            "website_news_detail": detail,
        },
    }


def test_structured_article_date_can_publish_dated_detail_when_text_has_no_date() -> None:
    profile = _profile_with_structured_date(
        [
            {
                "raw": "2026-09-21T09:00:00+02:00",
                "method": "jsonld_blogposting_date_published",
            }
        ]
    )
    updates = extract_strict_first_party_facts(profile)["updates"]
    assert len(updates) == 1
    assert updates[0]["published_date"] == "2026-09-21"
    assert updates[0]["date_extraction_method"] == "jsonld_blogposting_date_published"
    assert updates[0]["content_sha256"] == "b" * 64


def test_conflicting_structured_article_dates_fail_closed() -> None:
    profile = _profile_with_structured_date(
        [
            {
                "raw": "2026-09-20",
                "method": "jsonld_newsarticle_date_published",
            },
            {
                "raw": "2026-09-21",
                "method": "jsonld_article_date_published",
            },
        ]
    )
    assert extract_strict_first_party_facts(profile)["updates"] == []


def test_future_structured_article_date_is_rejected() -> None:
    profile = _profile_with_structured_date(
        [
            {
                "raw": "2026-10-07",
                "method": "jsonld_newsarticle_date_published",
            }
        ]
    )
    assert extract_strict_first_party_facts(profile)["updates"] == []
