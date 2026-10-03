import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_structured_first_party_discovery",
    ROOT / "scripts" / "run_structured_first_party_discovery.py",
)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


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


def op(url, *, body="", status=200, final_url=None):
    return body, {
        "status": status,
        "bytes": len(body.encode()),
        "latency_ms": 3,
        "final_url": final_url or url,
        "content_type": "text/plain",
        "content_sha256": "a" * 64,
    }


def test_m2b_bounded_runner_discovers_homepage_sitemap_and_feed(monkeypatch):
    homepage = """<html><head>
      <link rel='alternate' type='application/rss+xml' href='/feed.xml'>
      <script type='application/ld+json'>
        {"@type":"NewsArticle","headline":"Homepage update","url":"https://example.no/nyheter/home","datePublished":"2026-10-02"}
      </script>
    </head></html>"""
    sitemap = """<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>
      <url><loc>https://example.no/nyheter/from-sitemap</loc><lastmod>2026-10-01</lastmod></url>
      <url><loc>https://example.no/karriere/backend</loc></url>
    </urlset>"""
    feed = """<rss version='2.0'><channel>
      <item><title>Feed update</title><link>https://example.no/aktuelt/feed-update</link><pubDate>Thu, 01 Oct 2026 10:00:00 GMT</pubDate></item>
    </channel></rss>"""

    calls = []

    def fake_fetch(url, *, timeout, accept):
        calls.append(url)
        if url.endswith("/robots.txt"):
            return op(url, body="User-agent: *\nAllow: /\nSitemap: https://example.no/sitemap.xml\n")
        if url == "https://example.no/":
            return op(url, body=homepage)
        if url.endswith("/sitemap.xml"):
            return op(url, body=sitemap)
        if url.endswith("/feed.xml"):
            return op(url, body=feed)
        raise AssertionError(url)

    monkeypatch.setattr(runner, "fetch_document", fake_fetch)
    observation, metrics = runner.discover_profile(profile(), timeout=1)

    assert metrics["requests"] == 4
    assert metrics["requests"] <= runner.MAX_REQUESTS_PER_VERIFIED_SITE
    assert calls == [
        "https://example.no/robots.txt",
        "https://example.no/",
        "https://example.no/sitemap.xml",
        "https://example.no/feed.xml",
    ]
    assert {item["url"] for item in observation["surface_candidates"]} == {
        "https://example.no/nyheter/home",
        "https://example.no/nyheter/from-sitemap",
        "https://example.no/karriere/backend",
        "https://example.no/aktuelt/feed-update",
    }
    assert observation["claim_boundary"].startswith("Discovery only")


def test_m2b_cross_domain_sitemap_redirect_is_not_parsed(monkeypatch):
    malicious_sitemap = """<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>
      <url><loc>https://example.no/nyheter/should-not-be-trusted</loc></url>
    </urlset>"""

    def fake_fetch(url, *, timeout, accept):
        if url.endswith("/robots.txt"):
            return op(url, body="User-agent: *\nAllow: /\nSitemap: https://example.no/sitemap.xml\n")
        if url == "https://example.no/":
            return op(url, body="<html></html>")
        if url.endswith("/sitemap.xml"):
            return op(url, body=malicious_sitemap, final_url="https://other.no/sitemap.xml")
        raise AssertionError(url)

    monkeypatch.setattr(runner, "fetch_document", fake_fetch)
    observation, metrics = runner.discover_profile(profile(), timeout=1)
    assert metrics["requests"] == 3
    assert observation["surface_candidates"] == []
    sitemap_source = next(source for source in observation["sources"] if source["kind"] == "sitemap")
    assert sitemap_source["error"] == "redirected_outside_verified_domain"


def test_m2b_cross_domain_homepage_redirect_yields_no_structured_or_feed_surfaces(monkeypatch):
    html = """<html><head>
      <link rel='alternate' type='application/rss+xml' href='https://example.no/feed.xml'>
      <script type='application/ld+json'>
        {"@type":"NewsArticle","headline":"Do not trust","url":"https://example.no/news/x","datePublished":"2026-10-01"}
      </script>
    </head></html>"""

    def fake_fetch(url, *, timeout, accept):
        if url.endswith("/robots.txt"):
            return op(url, body="User-agent: *\nAllow: /\n")
        if url == "https://example.no/":
            return op(url, body=html, final_url="https://other.no/")
        if url.endswith("/sitemap.xml"):
            return op(url, body="<urlset/>")
        raise AssertionError(url)

    monkeypatch.setattr(runner, "fetch_document", fake_fetch)
    observation, metrics = runner.discover_profile(profile(), timeout=1)
    assert metrics["requests"] == 3
    assert observation["surface_candidates"] == []
    homepage_source = next(source for source in observation["sources"] if source["kind"] == "homepage")
    assert homepage_source["error"] == "redirected_outside_verified_domain"


def test_m2b_robots_disallow_stops_deeper_discovery(monkeypatch):
    calls = []

    def fake_fetch(url, *, timeout, accept):
        calls.append(url)
        assert url.endswith("/robots.txt")
        return op(url, body="User-agent: *\nDisallow: /\n")

    monkeypatch.setattr(runner, "fetch_document", fake_fetch)
    observation, metrics = runner.discover_profile(profile(), timeout=1)
    assert calls == ["https://example.no/robots.txt"]
    assert metrics["requests"] == 1
    assert observation["surface_candidates"] == []
    homepage_source = next(source for source in observation["sources"] if source["kind"] == "homepage")
    assert homepage_source["status"] == "robots_disallowed"


def test_m2b_unverified_profile_never_networks(monkeypatch):
    row = profile()
    row["evidence"]["website"]["value"]["identity_assessment"]["publishable"] = False

    def forbidden(*args, **kwargs):
        raise AssertionError("network should not be called")

    monkeypatch.setattr(runner, "fetch_document", forbidden)
    observation, metrics = runner.discover_profile(row, timeout=1)
    assert observation is None
    assert metrics["requests"] == 0
    assert metrics["reason"] == "no_verified_site"
