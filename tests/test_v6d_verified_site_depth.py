from __future__ import annotations

import urllib.robotparser

from bs4 import BeautifulSoup

import norway_company_agent.verified_site_depth as depth


def profile() -> dict:
    return {
        "organisation_number": "123456789",
        "name": "FJORD DATA SERVICE AS",
        "municipality": "OSLO",
        "evidence": {
            "website": {
                "status": "available",
                "source_url": "https://fjorddata.no/",
                "retrieved_at": "2026-10-01T00:00:00Z",
                "value": {
                    "final_url": "https://fjorddata.no/",
                    "identity_assessment": {"status": "exact", "score": 1.0, "publishable": True},
                    "pages": [{"url": "https://fjorddata.no/", "title": "Fjord Data Service"}],
                },
            },
            "roles": {"status": "available", "value": {"roles": []}},
            "locations": {"status": "available", "value": {"locations": []}},
        },
        "external_observations": [],
    }


def test_candidate_discovery_is_same_domain_and_category_bounded():
    soup = BeautifulSoup(
        """
        <a href='/kontakt'>Kontakt</a>
        <a href='/news'>News</a>
        <a href='/careers'>Careers</a>
        <a href='https://evil.example/jobs'>Jobs elsewhere</a>
        <a href='/privacy'>Privacy</a>
        """,
        "lxml",
    )
    rows = depth.discover_same_domain_candidates("https://fjorddata.no/", soup)
    assert [(row["category"], row["url"]) for row in rows] == [
        ("contact", "https://fjorddata.no/kontakt"),
        ("news", "https://fjorddata.no/news"),
        ("careers", "https://fjorddata.no/careers"),
    ]


def test_sitemap_and_feed_never_cross_verified_domain():
    sitemap = b"""<?xml version='1.0'?><urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>
      <url><loc>https://fjorddata.no/news/product-launch</loc></url>
      <url><loc>https://fjorddata.no/careers/software-engineer</loc></url>
      <url><loc>https://other.example/news/wrong-company</loc></url>
    </urlset>"""
    rows = depth.parse_sitemap(sitemap, sitemap_url="https://fjorddata.no/sitemap.xml", verified_url="https://fjorddata.no/")
    assert {row["url"] for row in rows} == {
        "https://fjorddata.no/news/product-launch",
        "https://fjorddata.no/careers/software-engineer",
    }

    feed = b"""<rss><channel>
      <item><title>New product launch</title><link>https://fjorddata.no/news/product-launch</link><pubDate>Thu, 01 Oct 2026 10:00:00 +0000</pubDate></item>
      <item><title>Wrong company</title><link>https://other.example/news/wrong</link><pubDate>Thu, 01 Oct 2026 10:00:00 +0000</pubDate></item>
    </channel></rss>"""
    entries = depth.parse_feed(feed, feed_url="https://fjorddata.no/feed.xml", verified_url="https://fjorddata.no/")
    assert len(entries) == 1
    assert entries[0]["title"] == "New product launch"
    assert entries[0]["published_date"] == "2026-10-01"


def test_depth_facts_keep_per_page_provenance():
    about_html = b"""
    <html><head><title>About Fjord Data Service</title>
      <script type='application/ld+json'>
      {"@context":"https://schema.org","@graph":[
        {"@type":"Organization","name":"Fjord Data Service AS","address":{"@type":"PostalAddress","streetAddress":"Bryggegata 1","postalCode":"0250","addressLocality":"Oslo"},"sameAs":["https://instagram.com/fjorddataservice"]},
        {"@type":"Person","name":"Anna Hansen","jobTitle":"CEO"}
      ]}
      </script>
    </head><body><footer>Kontakt info@fjorddata.no</footer></body></html>
    """
    careers_html = b"""
    <html><head><title>Senior Software Engineer</title>
      <script type='application/ld+json'>
      {"@context":"https://schema.org","@type":"JobPosting","title":"Senior Software Engineer","datePosted":"2026-09-25","employmentType":"FULL_TIME","description":"Build our platform","url":"https://fjorddata.no/careers/senior-software-engineer"}
      </script>
    </head><body>Senior Software Engineer full-time location Oslo. Apply now.</body></html>
    """
    news_html = b"""
    <html><head><title>Fjord Data launches new platform</title><meta property='article:published_time' content='2026-09-30T08:00:00+02:00'></head>
    <body>Fjord Data launches a new platform.</body></html>
    """
    about = depth.parse_page("https://fjorddata.no/about", about_html, "text/html")
    careers = depth.parse_page("https://fjorddata.no/careers/senior-software-engineer", careers_html, "text/html")
    news = depth.parse_page("https://fjorddata.no/news/new-platform", news_html, "text/html")
    assert about and careers and news
    about["category"] = "about"
    careers["category"] = "careers"
    news["category"] = "news"
    for page in (about, careers, news):
        page["retrieved_at"] = "2026-10-02T00:00:00Z"

    facts = depth.extract_depth_facts(profile(), [about, careers, news], [], retrieved_at="2026-10-02T00:00:00Z")
    assert [item["email"] for item in facts["contact_emails"]] == ["info@fjorddata.no"]
    assert facts["contact_emails"][0]["source_url"] == "https://fjorddata.no/about"
    assert facts["social_profiles"][0]["url"] == "https://instagram.com/fjorddataservice"
    assert facts["social_profiles"][0]["source_url"] == "https://fjorddata.no/about"
    assert facts["locations"][0]["locality"] == "Oslo"
    assert facts["leadership"][0]["name"] == "Anna Hansen"
    assert any(item["title"] == "Senior Software Engineer" for item in facts["jobs"])
    assert any(item["strategy"] == "first_party_metadata_dated_update" for item in facts["updates"])


def test_ineligible_profile_never_starts_network(monkeypatch):
    row = profile()
    row["evidence"]["website"]["value"]["identity_assessment"]["publishable"] = False

    def fail(*args, **kwargs):
        raise AssertionError("network helper must not run for an unverified site")

    monkeypatch.setattr(depth, "_fetch_robots", fail)
    result, metrics = depth.crawl_verified_site_depth(row)
    assert result["eligible"] is False
    assert metrics["requests"] == 0


def test_request_allowance_is_hard_ceiling(monkeypatch):
    row = profile()
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url("https://fjorddata.no/robots.txt")
    parser.parse([])
    monkeypatch.setattr(
        depth,
        "_fetch_robots",
        lambda verified_url, timeout: (parser, {"requests": 1, "bytes": 0, "latencies_ms": [1], "errors": []}),
    )
    html = b"<html><head><title>Fjord Data Service</title></head><body><a href='/news'>News</a></body></html>"
    calls = []

    def fake_fetch(url, **kwargs):
        calls.append(url)
        return html, "https://fjorddata.no/", "text/html", {
            "requests": 1,
            "bytes": len(html),
            "latencies_ms": [1],
            "errors": [],
            "outside_domain_rejections": 0,
        }

    monkeypatch.setattr(depth, "_fetch_bytes", fake_fetch)
    result, metrics = depth.crawl_verified_site_depth(row, request_allowance=2)
    assert result["eligible"] is True
    assert metrics["requests"] == 2
    assert calls == ["https://fjorddata.no/"]
    assert len(result["pages"]) == 1
