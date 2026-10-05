from __future__ import annotations

from datetime import date

from norway_company_agent.first_party_feed import parse_company_feed


AS_OF = date(2026, 10, 5)


def _parse(items: str) -> dict:
    raw = f"<rss version='2.0'><channel>{items}</channel></rss>".encode()
    return parse_company_feed(
        raw,
        feed_url="https://example.no/feed/",
        verified_url="https://example.no/",
        as_of_date=AS_OF,
    )


def test_rejects_fresh_generic_cms_placeholder_title() -> None:
    report = _parse(
        "<item><title>Hello world!</title><link>https://example.no/hello-world/</link>"
        "<pubDate>Mon, 05 Oct 2026 08:00:00 +0200</pubDate></item>"
    )
    assert report["status"] == "empty"
    assert report["entries"] == []


def test_rejects_specific_but_stale_template_like_post_without_topic_blacklist() -> None:
    report = _parse(
        "<item><title>How can an introductory class make you stronger</title>"
        "<link>https://example.no/introductory-class/</link>"
        "<pubDate>Fri, 13 Apr 2018 08:00:00 +0200</pubDate></item>"
    )
    assert report["status"] == "empty"
    assert report["entries"] == []


def test_five_year_boundary_is_inclusive() -> None:
    report = _parse(
        "<item><title>Company anniversary event announced</title>"
        "<link>https://example.no/company-anniversary/</link>"
        "<pubDate>Tue, 05 Oct 2021 08:00:00 +0200</pubDate></item>"
    )
    assert report["status"] == "available"
    assert report["entries"][0]["published_date"] == "2021-10-05"


def test_one_day_before_five_year_boundary_is_rejected() -> None:
    report = _parse(
        "<item><title>Older company anniversary event</title>"
        "<link>https://example.no/older-anniversary/</link>"
        "<pubDate>Mon, 04 Oct 2021 08:00:00 +0200</pubDate></item>"
    )
    assert report["status"] == "empty"


def test_future_dated_feed_entry_is_rejected() -> None:
    report = _parse(
        "<item><title>Future company event announced</title>"
        "<link>https://example.no/future-event/</link>"
        "<pubDate>Tue, 06 Oct 2026 08:00:00 +0200</pubDate></item>"
    )
    assert report["status"] == "empty"


def test_current_specific_company_update_survives() -> None:
    report = _parse(
        "<item><title>New production line opened</title>"
        "<link>https://example.no/news/new-production-line/</link>"
        "<pubDate>Mon, 05 Oct 2026 08:00:00 +0200</pubDate></item>"
    )
    assert report["status"] == "available"
    assert len(report["entries"]) == 1
    assert report["entries"][0]["title"] == "New production line opened"
