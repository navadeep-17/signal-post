from __future__ import annotations

from bs4 import BeautifulSoup

from norway_company_agent.company_site_activity import (
    activity_navigation_links,
    dated_activity_items,
    probe_company_activity,
)
from norway_company_agent.external_footprint import validate_observation


def _profile() -> dict:
    return {
        "organisation_number": "123456789",
        "evidence": {
            "website": {
                "status": "available",
                "source_url": "https://example.no/",
                "retrieved_at": "2026-09-15T10:00:00Z",
                "content_sha256": "a" * 64,
                "value": {
                    "final_url": "https://example.no/",
                    "content_sha256": "a" * 64,
                    "identity_assessment": {
                        "status": "exact",
                        "score": 0.99,
                        "publishable": True,
                        "method": "test_exact_identity",
                    },
                },
            }
        },
    }


def _page(url: str, html: str, digest: str) -> dict:
    return {
        "status": "available",
        "source_url": url,
        "retrieved_at": "2026-09-15T11:00:00Z",
        "content_sha256": digest,
        "soup": BeautifulSoup(html, "lxml"),
    }


def test_activity_navigation_links_are_declared_same_domain_only() -> None:
    soup = BeautifulSoup(
        """
        <nav>
          <a href="/nyheter/">Nyheter</a>
          <a href="https://example.no/blog?utm_source=x">Blogg</a>
          <a href="https://other.no/news">News</a>
          <a href="/files/news.pdf">Nyheter PDF</a>
          <a href="/contact">Kontakt</a>
        </nav>
        """,
        "lxml",
    )
    assert activity_navigation_links("https://example.no/", soup) == [
        "https://example.no/nyheter/",
        "https://example.no/blog",
    ]


def test_dated_activity_items_require_explicit_dates() -> None:
    soup = BeautifulSoup(
        """
        <html><body>
          <script type="application/ld+json">
          {"@context":"https://schema.org","@type":"NewsArticle","headline":"Factory expansion announced","datePublished":"2026-09-12","url":"/nyheter/factory-expansion"}
          </script>
          <article>
            <h2><a href="/blog/new-team">New team joins the company</a></h2>
            <time datetime="2026-09-10T08:30:00+02:00">10 September</time>
          </article>
          <article><h2>Undated announcement</h2></article>
        </body></html>
        """,
        "lxml",
    )
    items = dated_activity_items("https://example.no/nyheter", soup)
    assert len(items) == 2
    assert items[0]["title"] == "Factory expansion announced"
    assert items[0]["published_at"].startswith("2026-09-12T00:00:00")
    assert items[0]["item_url"] == "https://example.no/nyheter/factory-expansion"
    assert items[1]["title"] == "New team joins the company"


def test_probe_publishes_narrow_valid_public_post_observation() -> None:
    pages = [
        _page(
            "https://example.no/",
            '<a href="/nyheter">Nyheter</a>',
            "b" * 64,
        ),
        _page(
            "https://example.no/nyheter",
            """
            <article>
              <h2><a href="/nyheter/contract">Ny kontrakt signert</a></h2>
              <time datetime="2026-09-14">14. september 2026</time>
            </article>
            """,
            "c" * 64,
        ),
    ]

    def fetcher(url: str, *, timeout: float):
        page = pages.pop(0)
        assert url.rstrip("/") == str(page["source_url"]).rstrip("/")
        return page, {"requests": 2, "bytes": 100, "latencies_ms": [5]}

    observations, metrics = probe_company_activity(_profile(), fetcher=fetcher)
    assert metrics["requests"] == 4
    assert metrics["status"] == "qualified_items"
    assert len(observations) == 1
    observation = observations[0]
    assert observation["signal_type"] == "public_post"
    assert observation["platform"] == "company_site"
    assert observation["title"] == "Ny kontrakt signert"
    assert observation["item_url"] == "https://example.no/nyheter/contract"
    assert observation["source_url"] == "https://example.no/nyheter"
    assert observation["content_sha256"] == "c" * 64
    assert validate_observation(observation) == []
    assert "article body was not fetched" in observation["metrics"]["claim_scope"]


def test_probe_abstains_on_cross_domain_activity_redirect() -> None:
    pages = [
        _page("https://example.no/", '<a href="/news">News</a>', "b" * 64),
        _page(
            "https://other.no/news",
            '<article><h2>Wrong domain</h2><time datetime="2026-09-14">date</time></article>',
            "c" * 64,
        ),
    ]

    def fetcher(url: str, *, timeout: float):
        return pages.pop(0), {"requests": 2, "bytes": 100, "latencies_ms": [5]}

    observations, metrics = probe_company_activity(_profile(), fetcher=fetcher)
    assert observations == []
    assert metrics["status"] == "activity_page_cross_domain"
    assert metrics["requests"] == 4


def test_probe_abstains_when_activity_page_has_no_explicit_dated_items() -> None:
    pages = [
        _page("https://example.no/", '<a href="/blog">Blog</a>', "b" * 64),
        _page("https://example.no/blog", '<article><h2>Latest update</h2></article>', "c" * 64),
    ]

    def fetcher(url: str, *, timeout: float):
        return pages.pop(0), {"requests": 2, "bytes": 100, "latencies_ms": [5]}

    observations, metrics = probe_company_activity(_profile(), fetcher=fetcher)
    assert observations == []
    assert metrics["status"] == "no_dated_items"
    assert metrics["requests"] == 4


def test_probe_skips_unverified_website_without_network_calls() -> None:
    profile = _profile()
    profile["evidence"]["website"]["value"]["identity_assessment"]["publishable"] = False
    calls = []

    def fetcher(url: str, *, timeout: float):
        calls.append(url)
        raise AssertionError("fetch should not run")

    observations, metrics = probe_company_activity(profile, fetcher=fetcher)
    assert observations == []
    assert calls == []
    assert metrics["requests"] == 0
    assert metrics["status"] == "not_applicable"
