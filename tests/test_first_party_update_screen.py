from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import run_dated_first_party_update_screen as screen


def profile():
    return {
        "organisation_number": "123456789",
        "website": "https://example.no/",
        "evidence": {
            "website": {
                "status": "available",
                "source_url": "https://example.no/",
                "value": {
                    "final_url": "https://example.no/",
                    "identity_assessment": {"status": "exact", "publishable": True, "score": 1.0},
                },
            }
        },
    }


def article_html():
    return """<html><head>
    <meta property='og:title' content='Specific company update'>
    <meta property='article:published_time' content='2026-10-01'>
    </head><body><article><h1>Specific company update</h1><p>Detailed company-owned update text.</p></article></body></html>"""


def test_candidate_priority_prefers_structured_then_feed_then_sitemap():
    rows = [
        {"url": "https://example.no/news/c", "surface_kind": "news_or_article", "discovered_via": "sitemap"},
        {"url": "https://example.no/news/b", "surface_kind": "news_or_article", "discovered_via": "rss_or_atom"},
        {"url": "https://example.no/news/a", "surface_kind": "structured_article", "discovered_via": "jsonld"},
    ]
    ordered = sorted(rows, key=screen.candidate_priority)
    assert [row["url"] for row in ordered] == [
        "https://example.no/news/a",
        "https://example.no/news/b",
        "https://example.no/news/c",
    ]


def test_screen_qualifies_independently_fetched_specific_dated_page(monkeypatch):
    monkeypatch.setattr(screen, "discover_profile", lambda _profile, timeout: (
        {
            "surface_candidates": [
                {"url": "https://example.no/nyheter/specific-update", "surface_kind": "news_or_article", "discovered_via": "sitemap"}
            ]
        },
        {"requests": 3, "bytes": 100},
    ))
    monkeypatch.setattr(screen, "_robots_allowed", lambda url, timeout: True)
    monkeypatch.setattr(screen, "fetch_document", lambda url, timeout, accept: (
        article_html(),
        {"status": 200, "bytes": 500, "final_url": url, "content_sha256": "a" * 64},
    ))

    row, metrics = screen.screen_profile(profile(), timeout=1.0, as_of=date(2026, 10, 3))
    assert len(row["publishable_updates"]) == 1
    assert row["publishable_updates"][0]["status"] == "exact_dated_update"
    assert metrics["requests"] == 5  # 3 discovery + robots + destination
    assert metrics["request_ceiling"] == 9


def test_screen_never_uses_feed_or_sitemap_date_without_page_date(monkeypatch):
    monkeypatch.setattr(screen, "discover_profile", lambda _profile, timeout: (
        {
            "surface_candidates": [
                {
                    "url": "https://example.no/nyheter/specific-update",
                    "surface_kind": "news_or_article",
                    "discovered_via": "rss_or_atom",
                    "published": "2026-10-01",
                    "lastmod": "2026-10-02",
                }
            ]
        },
        {"requests": 2, "bytes": 50},
    ))
    monkeypatch.setattr(screen, "_robots_allowed", lambda url, timeout: True)
    monkeypatch.setattr(screen, "fetch_document", lambda url, timeout, accept: (
        "<html><body><article><h1>Specific update without page date</h1><p>Text.</p></article></body></html>",
        {"status": 200, "bytes": 200, "final_url": url, "content_sha256": "b" * 64},
    ))

    row, _ = screen.screen_profile(profile(), timeout=1.0, as_of=date(2026, 10, 3))
    assert row["publishable_updates"] == []
    assert row["destination_attempts"][0]["status"] == "review"


def test_cross_domain_redirect_cannot_publish(monkeypatch):
    monkeypatch.setattr(screen, "discover_profile", lambda _profile, timeout: (
        {
            "surface_candidates": [
                {"url": "https://example.no/news/update", "surface_kind": "structured_article", "discovered_via": "jsonld"}
            ]
        },
        {"requests": 2, "bytes": 50},
    ))
    monkeypatch.setattr(screen, "_robots_allowed", lambda url, timeout: True)
    monkeypatch.setattr(screen, "fetch_document", lambda url, timeout, accept: (
        article_html(),
        {"status": 200, "bytes": 200, "final_url": "https://other.no/news/update", "content_sha256": "c" * 64},
    ))

    row, _ = screen.screen_profile(profile(), timeout=1.0, as_of=date(2026, 10, 3))
    assert row["publishable_updates"] == []
    assert row["destination_attempts"][0]["status"] == "fetch_failed_or_cross_domain"


def test_only_two_destinations_are_attempted(monkeypatch):
    candidates = [
        {"url": f"https://example.no/news/{i}", "surface_kind": "news_or_article", "discovered_via": "sitemap"}
        for i in range(5)
    ]
    monkeypatch.setattr(screen, "discover_profile", lambda _profile, timeout: (
        {"surface_candidates": candidates},
        {"requests": 1, "bytes": 0},
    ))
    monkeypatch.setattr(screen, "_robots_allowed", lambda url, timeout: False)

    row, metrics = screen.screen_profile(profile(), timeout=1.0, as_of=date(2026, 10, 3))
    assert len(row["destination_attempts"]) == 2
    assert metrics["requests"] == 3
    assert metrics["requests"] <= metrics["request_ceiling"]
