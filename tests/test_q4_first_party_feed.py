from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import norway_company_agent.h1g_hyphenated_no_recall as h1g  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402
from norway_company_agent.first_party_feed import (  # noqa: E402
    advertised_feed_links,
    feed_candidate_urls,
    parse_company_feed,
)
from norway_company_agent.first_party_feed_contract import project_first_party_feed_updates  # noqa: E402




def test_homepage_advertised_feed_links_are_rss_atom_and_same_site_only() -> None:
    soup = BeautifulSoup(
        """
        <html><head>
          <link rel="alternate" type="application/atom+xml" href="/updates.atom">
          <link rel="alternate" type="application/rss+xml; charset=utf-8" href="https://news.example.no/rss">
          <link rel="alternate" type="application/rss+xml" href="https://other.no/feed">
          <link rel="alternate" type="text/html" href="/news/">
        </head></html>
        """,
        "lxml",
    )
    assert advertised_feed_links("https://example.no/", soup) == [
        "https://example.no/updates.atom",
        "https://news.example.no/rss",
    ]


def test_homepage_feed_nomination_is_bounded() -> None:
    soup = BeautifulSoup(
        "<html><head>"
        + "".join(
            f'<link rel="alternate" type="application/rss+xml" href="/feed-{i}.xml">'
            for i in range(8)
        )
        + "</head></html>",
        "lxml",
    )
    assert len(advertised_feed_links("https://example.no/", soup, limit=2)) == 2

def test_feed_candidates_are_bounded_and_same_origin() -> None:
    urls = feed_candidate_urls("https://www.example.no/about", limit=2)

    assert urls == ["https://www.example.no/feed/", "https://www.example.no/rss.xml"]


def test_rss_feed_extracts_dated_same_site_entries() -> None:
    raw = b"""<?xml version='1.0' encoding='UTF-8'?>
    <rss version='2.0'><channel><title>Example News</title>
      <item>
        <title>New production line opened</title>
        <link>https://example.no/news/new-production-line</link>
        <pubDate>Mon, 05 Oct 2026 08:00:00 +0200</pubDate>
      </item>
      <item>
        <title>External repost should be ignored</title>
        <link>https://other.example.org/post</link>
        <pubDate>Sun, 04 Oct 2026 08:00:00 +0200</pubDate>
      </item>
    </channel></rss>"""

    report = parse_company_feed(
        raw,
        feed_url="https://example.no/feed/",
        verified_url="https://example.no/",
    )

    assert report["status"] == "available"
    assert report["feed_type"] == "rss"
    assert len(report["entries"]) == 1
    assert report["entries"][0]["published_date"] == "2026-10-05"
    assert report["entries"][0]["url"] == "https://example.no/news/new-production-line"
    assert report["entries"][0]["date_extraction_method"] == "feed_pubdate"


def test_atom_feed_supports_namespaced_entries_and_iso_dates() -> None:
    raw = b"""<?xml version='1.0' encoding='utf-8'?>
    <feed xmlns='http://www.w3.org/2005/Atom'>
      <title>Example updates</title>
      <entry>
        <title>Quarterly customer event announced</title>
        <link href='https://updates.example.no/posts/customer-event' rel='alternate'/>
        <published>2026-09-29T10:30:00Z</published>
      </entry>
    </feed>"""

    report = parse_company_feed(
        raw,
        feed_url="https://example.no/atom.xml",
        verified_url="https://example.no/",
    )

    assert report["status"] == "available"
    assert report["feed_type"] == "atom"
    assert report["entries"][0]["published_date"] == "2026-09-29"
    assert report["entries"][0]["date_extraction_method"] == "feed_published"


def test_feed_rejects_cross_domain_source_even_if_xml_is_valid() -> None:
    raw = b"<rss version='2.0'><channel><item><title>Company update today</title><link>https://example.no/post</link><pubDate>Mon, 05 Oct 2026 08:00:00 +0200</pubDate></item></channel></rss>"

    report = parse_company_feed(
        raw,
        feed_url="https://feeds.example.net/rss.xml",
        verified_url="https://example.no/",
    )

    assert report["status"] == "rejected"
    assert report["entries"] == []


def test_feed_requires_explicit_date_and_specific_title() -> None:
    raw = b"""<rss version='2.0'><channel>
      <item><title>News</title><link>https://example.no/news/one</link><pubDate>Mon, 05 Oct 2026 08:00:00 +0200</pubDate></item>
      <item><title>Specific but undated company update</title><link>https://example.no/news/two</link></item>
    </channel></rss>"""

    report = parse_company_feed(
        raw,
        feed_url="https://example.no/feed/",
        verified_url="https://example.no/",
    )

    assert report["status"] == "empty"
    assert report["entries"] == []


def test_entry_limit_is_hard_bounded() -> None:
    items = "".join(
        f"<item><title>Company update number {index}</title><link>https://example.no/news/{index}</link><pubDate>Mon, 05 Oct 2026 08:00:00 +0200</pubDate></item>"
        for index in range(10)
    )
    report = parse_company_feed(
        f"<rss version='2.0'><channel>{items}</channel></rss>".encode(),
        feed_url="https://example.no/feed/",
        verified_url="https://example.no/",
        max_entries=3,
    )

    assert len(report["entries"]) == 3


def _verified_profile() -> dict:
    return {
        "organisation_number": "936252494",
        "name": "PUBSPILL AS",
        "website": "https://www.pubspill.no/",
        "evidence": {
            "website": {
                "status": "available",
                "source_url": "https://www.pubspill.no/",
                "retrieved_at": "2026-10-05T12:00:00Z",
                "content_sha256": "a" * 64,
                "value": {
                    "final_url": "https://www.pubspill.no/",
                    "identity_assessment": {
                        "status": "exact",
                        "score": 1.0,
                        "publishable": True,
                        "reasons": ["exact organisation number"],
                        "method": "deterministic_name_org_evidence_v4",
                    },
                },
            }
        },
    }


def _feed_record() -> dict:
    return {
        "status": "available",
        "source_type": "verified_company_activity_feed",
        "source_url": "https://www.pubspill.no/feed",
        "retrieved_at": "2026-10-05T12:05:00Z",
        "content_sha256": "b" * 64,
        "value": {
            "verified_website_url": "https://www.pubspill.no/",
            "feed_type": "rss",
            "entries": [
                {
                    "title": "En mester iblant oss",
                    "url": "https://www.pubspill.no/en-mester-iblant-oss",
                    "published_date": "2026-10-05",
                    "date_extraction_method": "feed_pubdate",
                    "date_evidence": "Sun, 05 Oct 2026 08:00:00 +0200",
                    "evidence_span": "En mester iblant oss; published date 2026-10-05; feed date evidence feed_pubdate",
                }
            ],
        },
    }


def test_verified_site_uses_only_spare_two_request_slot_for_feed(monkeypatch) -> None:
    profile = _verified_profile()
    monkeypatch.setattr(
        h1g,
        "fetch_verified_activity_feed",
        lambda verified_url, candidate_url=None, timeout=6.0: (
            _feed_record(),
            {"requests": 2, "bytes": 900, "latencies_ms": [20]},
        ),
    )

    enriched, result = h1g.evaluate_hyphenated_no_fallback(
        profile,
        timeout=5.0,
        base_site_logical_requests=2,
    )

    assert result["skipped_reason"] == "verified_website_present"
    assert result["attempted"] is False
    assert result["activity_feed_attempted"] is True
    assert result["activity_feed_retained"] is True
    assert result["requests_added"] == 2
    assert result["post_site_logical_requests"] == 4
    assert enriched["evidence"]["website_activity_feed"]["status"] == "available"


def test_verified_site_does_not_steal_consumed_site_budget(monkeypatch) -> None:
    profile = _verified_profile()

    def forbidden(*args, **kwargs):
        raise AssertionError("feed must not run after the four-request site budget is consumed")

    monkeypatch.setattr(h1g, "fetch_verified_activity_feed", forbidden)
    enriched, result = h1g.evaluate_hyphenated_no_fallback(
        profile,
        timeout=5.0,
        base_site_logical_requests=4,
    )

    assert result["activity_feed_attempted"] is False
    assert result["activity_feed_skipped_reason"] == "site_request_budget_consumed"
    assert result["requests_added"] == 0
    assert "website_activity_feed" not in enriched["evidence"]


def test_feed_projection_cites_feed_snapshot_and_exposes_identity_proof() -> None:
    profile = _verified_profile()
    profile["evidence"]["website_activity_feed"] = _feed_record()
    contract = {"organisation_number": "936252494", "claims": [], "evidence": []}

    projected = project_first_party_feed_updates(contract, profile)

    assert len(projected["claims"]) == 1
    claim = projected["claims"][0]
    assert claim["field"] == "external.company_update"
    assert claim["value"]["url"] == "https://www.pubspill.no/en-mester-iblant-oss"
    assert claim["value"]["published_date"] == "2026-10-05"
    evidence = projected["evidence"][0]
    assert evidence["source_url"] == "https://www.pubspill.no/feed"
    assert evidence["content_sha256"] == "b" * 64
    assert evidence["effective_at"] == "2026-10-05"
    assert evidence["identity_proof"]["status"] == "exact"
    assert evidence["extraction_method"] == "verified_same_site_rss_atom_entry_v1"

    repeated = project_first_party_feed_updates(projected, profile)
    assert len(repeated["claims"]) == 1
    assert len(repeated["evidence"]) == 1


def test_verified_site_prefers_homepage_advertised_feed_without_extra_requests(monkeypatch) -> None:
    profile = _verified_profile()
    profile["evidence"]["website"]["value"]["activity_feed_links"] = [
        "https://www.pubspill.no/atom.xml"
    ]
    seen = {}

    def fake_feed(verified_url, *, candidate_url=None, timeout=6.0):
        seen["verified_url"] = verified_url
        seen["candidate_url"] = candidate_url
        return _feed_record(), {"requests": 2, "bytes": 900, "latencies_ms": [20]}

    monkeypatch.setattr(h1g, "fetch_verified_activity_feed", fake_feed)
    _, result = h1g.evaluate_hyphenated_no_fallback(
        profile,
        timeout=5.0,
        base_site_logical_requests=2,
    )

    assert seen == {
        "verified_url": "https://www.pubspill.no/",
        "candidate_url": "https://www.pubspill.no/atom.xml",
    }
    assert result["activity_feed_candidate_source"] == "homepage_advertised_rss_atom"
    assert result["requests_added"] == 2
    assert result["post_site_logical_requests"] == 4
