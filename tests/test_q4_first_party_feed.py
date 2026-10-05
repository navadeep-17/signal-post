from __future__ import annotations

from norway_company_agent.first_party_feed import feed_candidate_urls, parse_company_feed


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
