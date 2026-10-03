from __future__ import annotations

from norway_company_agent.homepage_dated_updates import extract_dated_update_links


def test_extracts_specific_same_domain_news_card_with_time_datetime() -> None:
    raw = b"""
    <html><body>
      <article>
        <time datetime="2026-09-22">22 September 2026</time>
        <a href="/news/new-rehabilitation-study-published">New rehabilitation study published</a>
      </article>
    </body></html>
    """
    rows = extract_dated_update_links(
        verified_url="https://example.no/",
        final_url="https://example.no/",
        raw=raw,
        content_type="text/html",
    )
    assert len(rows) == 1
    assert rows[0]["url"] == "https://example.no/news/new-rehabilitation-study-published"
    assert rows[0]["published_date"] == "2026-09-22"
    assert rows[0]["date_source"] == "time"
    assert "New rehabilitation study published" in rows[0]["evidence_span"]


def test_extracts_norwegian_dated_update_from_card_text() -> None:
    raw = b"""
    <html><body>
      <div class="news-card">
        <p>22.09.2026</p>
        <a href="/aktuelt/nytt-forskningsprosjekt-er-i-gang">Nytt forskningsprosjekt er i gang</a>
      </div>
    </body></html>
    """
    rows = extract_dated_update_links(
        verified_url="https://example.no/",
        final_url="https://example.no/",
        raw=raw,
        content_type="text/html",
    )
    assert len(rows) == 1
    assert rows[0]["published_date"] == "2026-09-22"


def test_rejects_undated_news_link() -> None:
    raw = b"<html><body><a href='/news/important-company-update'>Important company update today</a></body></html>"
    assert extract_dated_update_links(
        verified_url="https://example.no/",
        final_url="https://example.no/",
        raw=raw,
        content_type="text/html",
    ) == []


def test_rejects_generic_news_section_root_even_with_date_nearby() -> None:
    raw = b"<html><body><div><time datetime='2026-09-22'></time><a href='/news'>Company News</a></div></body></html>"
    assert extract_dated_update_links(
        verified_url="https://example.no/",
        final_url="https://example.no/",
        raw=raw,
        content_type="text/html",
    ) == []


def test_rejects_external_article_link() -> None:
    raw = b"""
    <html><body><article><time datetime="2026-09-22"></time>
    <a href="https://publisher.example/news/example-story">Example launches major new service</a>
    </article></body></html>
    """
    assert extract_dated_update_links(
        verified_url="https://example.no/",
        final_url="https://example.no/",
        raw=raw,
        content_type="text/html",
    ) == []
