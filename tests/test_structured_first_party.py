from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.structured_first_party import (
    classify_first_party_url,
    discover_feed_links,
    extract_structured_surfaces,
    parse_feed_xml,
    parse_sitemap_xml,
    verified_site_url,
)


def profile(*, publishable=True, final_url="https://example.no/"):
    return {
        "website": final_url,
        "evidence": {
            "website": {
                "status": "available",
                "source_url": final_url,
                "value": {
                    "final_url": final_url,
                    "identity_assessment": {
                        "status": "exact" if publishable else "review",
                        "publishable": publishable,
                        "score": 0.99 if publishable else 0.5,
                    },
                },
            }
        },
    }


def test_m2_requires_already_verified_company_site():
    assert verified_site_url(profile()) == "https://example.no/"
    assert verified_site_url(profile(publishable=False)) is None
    assert verified_site_url({}) is None


def test_surface_classifier_is_conservative():
    assert classify_first_party_url("https://example.no/nyheter/lansering") == "news_or_article"
    assert classify_first_party_url("https://example.no/karriere/ledige-stillinger") == "careers_or_jobs"
    assert classify_first_party_url("https://example.no/produkter/widget") is None


def test_sitemap_index_keeps_only_same_registered_domain_nested_sitemaps():
    xml = """<?xml version='1.0'?>
    <sitemapindex xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>
      <sitemap><loc>https://example.no/news-sitemap.xml</loc></sitemap>
      <sitemap><loc>https://www.example.no/jobs-sitemap.xml</loc></sitemap>
      <sitemap><loc>https://evil.example.com/sitemap.xml</loc></sitemap>
      <sitemap><loc>https://other.no/sitemap.xml</loc></sitemap>
    </sitemapindex>"""
    parsed = parse_sitemap_xml(xml, sitemap_url="https://example.no/sitemap.xml", verified_url="https://example.no/")
    assert parsed["kind"] == "sitemapindex"
    assert parsed["nested_sitemaps"] == [
        "https://example.no/news-sitemap.xml",
        "https://www.example.no/jobs-sitemap.xml",
    ]
    assert parsed["surface_candidates"] == []


def test_sitemap_urlset_emits_only_relevant_same_domain_surfaces():
    xml = """<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>
      <url><loc>https://example.no/nyheter/new-product</loc><lastmod>2026-10-01</lastmod></url>
      <url><loc>https://example.no/karriere/stilling/backend</loc><lastmod>2026-09-29</lastmod></url>
      <url><loc>https://example.no/produkter/widget</loc><lastmod>2026-09-20</lastmod></url>
      <url><loc>https://other.no/news/not-ours</loc></url>
    </urlset>"""
    parsed = parse_sitemap_xml(xml, sitemap_url="https://example.no/sitemap.xml", verified_url="https://example.no/")
    assert parsed["kind"] == "urlset"
    assert parsed["surface_candidates"] == [
        {
            "url": "https://example.no/nyheter/new-product",
            "surface_kind": "news_or_article",
            "lastmod": "2026-10-01",
            "discovered_via": "sitemap",
        },
        {
            "url": "https://example.no/karriere/stilling/backend",
            "surface_kind": "careers_or_jobs",
            "lastmod": "2026-09-29",
            "discovered_via": "sitemap",
        },
    ]


def test_sitemap_does_not_accept_unverified_sitemap_domain_or_malformed_xml():
    assert parse_sitemap_xml("<urlset>", sitemap_url="https://example.no/sitemap.xml", verified_url="https://example.no/")["kind"] == "invalid"
    assert parse_sitemap_xml("<urlset/>", sitemap_url="https://other.no/sitemap.xml", verified_url="https://example.no/")["kind"] == "invalid"


def test_rss_entries_keep_same_domain_links_and_dates():
    xml = """<rss version='2.0'><channel>
      <item><title>Launch</title><link>https://example.no/nyheter/launch</link><pubDate>Thu, 01 Oct 2026 10:00:00 GMT</pubDate></item>
      <item><title>External</title><link>https://other.no/article</link><pubDate>Thu, 01 Oct 2026 10:00:00 GMT</pubDate></item>
    </channel></rss>"""
    rows = parse_feed_xml(xml, feed_url="https://example.no/feed.xml", verified_url="https://example.no/")
    assert rows == [{
        "url": "https://example.no/nyheter/launch",
        "title": "Launch",
        "published": "Thu, 01 Oct 2026 10:00:00 GMT",
        "surface_kind": "news_or_article",
        "discovered_via": "rss_or_atom",
    }]


def test_atom_entry_link_is_supported():
    xml = """<feed xmlns='http://www.w3.org/2005/Atom'>
      <entry>
        <title>Company update</title>
        <link rel='alternate' href='/aktuelt/update'/>
        <published>2026-10-02T09:00:00+02:00</published>
      </entry>
    </feed>"""
    rows = parse_feed_xml(xml, feed_url="https://example.no/atom.xml", verified_url="https://example.no/")
    assert rows[0]["url"] == "https://example.no/aktuelt/update"
    assert rows[0]["published"] == "2026-10-02T09:00:00+02:00"


def test_declared_feed_links_are_same_domain_only():
    html = """<html><head>
      <link rel='alternate' type='application/rss+xml' href='/feed.xml'>
      <link rel='alternate' type='application/atom+xml' href='https://news.example.no/atom.xml'>
      <link rel='alternate' type='application/rss+xml' href='https://other.no/feed.xml'>
    </head></html>"""
    assert discover_feed_links(html, page_url="https://example.no/", verified_url="https://example.no/") == [
        "https://example.no/feed.xml",
        "https://news.example.no/atom.xml",
    ]


def test_jsonld_article_and_job_are_discovery_only_same_domain_records():
    html = """<html><head>
    <script type='application/ld+json'>
    {
      "@graph": [
        {
          "@type": "NewsArticle",
          "headline": "A real company update",
          "url": "https://example.no/nyheter/update",
          "datePublished": "2026-10-02T08:30:00+02:00",
          "dateModified": "2026-10-02T10:00:00+02:00"
        },
        {
          "@type": "JobPosting",
          "title": "Backend Engineer",
          "url": "https://example.no/karriere/backend-engineer",
          "datePosted": "2026-10-01",
          "validThrough": "2026-10-31",
          "hiringOrganization": {"@type": "Organization", "name": "Example AS"}
        }
      ]
    }
    </script>
    </head></html>"""
    rows = extract_structured_surfaces(html, page_url="https://example.no/", verified_url="https://example.no/")
    assert rows == [
        {
            "url": "https://example.no/nyheter/update",
            "surface_kind": "structured_article",
            "title": "A real company update",
            "discovered_via": "jsonld",
            "date_published": "2026-10-02T08:30:00+02:00",
            "date_modified": "2026-10-02T10:00:00+02:00",
        },
        {
            "url": "https://example.no/karriere/backend-engineer",
            "surface_kind": "structured_job",
            "title": "Backend Engineer",
            "discovered_via": "jsonld",
            "date_posted": "2026-10-01",
            "valid_through": "2026-10-31",
            "hiring_organisation_name": "Example AS",
        },
    ]


def test_jsonld_off_domain_surface_is_rejected():
    html = """<script type='application/ld+json'>
    {"@type":"NewsArticle","headline":"Wrong domain","url":"https://other.no/news/x","datePublished":"2026-10-01"}
    </script>"""
    assert extract_structured_surfaces(html, page_url="https://example.no/", verified_url="https://example.no/") == []


def test_jsonld_uses_page_url_when_structured_url_is_missing():
    html = """<script type='application/ld+json'>
    {"@type":"Article","headline":"Current article","datePublished":"2026-10-01"}
    </script>"""
    rows = extract_structured_surfaces(
        html,
        page_url="https://example.no/aktuelt/current-article",
        verified_url="https://example.no/",
    )
    assert rows[0]["url"] == "https://example.no/aktuelt/current-article"
    assert rows[0]["surface_kind"] == "structured_article"
