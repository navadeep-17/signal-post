from __future__ import annotations

from norway_company_agent.verified_site_depth_hardened_v2 import (
    MAX_UPDATES_PER_COMPANY,
    PAGE_PRIORITY,
    harden_updates,
)


def update(title: str, url: str, published: str, *, strategy: str = "first_party_feed_item", source: str | None = None) -> dict:
    return {
        "title": title,
        "url": url,
        "published_date": published,
        "strategy": strategy,
        "source_url": source or "https://example.no/feed/",
        "content_sha256": "a" * 64,
        "retrieved_at": "2026-10-02T00:00:00Z",
    }


def test_activity_priority_targets_recall_gaps_before_saturated_registry_fields():
    assert PAGE_PRIORITY[:3] == ("careers", "news", "contact")
    assert PAGE_PRIORITY.index("team") > PAGE_PRIORITY.index("news")
    assert PAGE_PRIORITY.index("locations") > PAGE_PRIORITY.index("contact")


def test_hello_world_and_non_news_feed_items_are_rejected():
    rows = [
        update("Hello world!", "https://example.no/news/hello-world/", "2026-05-01"),
        update("New rooftop habitat", "https://example.no/projects/roof-habitat/", "2026-05-02"),
        update("Real company announcement", "https://example.no/news/company-announcement/", "2026-05-03"),
    ]
    result = harden_updates(rows, retrieved_at="2026-10-02T00:00:00Z")
    assert [item["title"] for item in result] == ["Real company announcement"]


def test_stale_feed_item_is_rejected():
    rows = [
        update("Old mountain course announcement", "https://example.no/news/old-course/", "2021-11-23"),
        update("Current mountain course announcement", "https://example.no/news/current-course/", "2026-09-20"),
    ]
    result = harden_updates(rows, retrieved_at="2026-10-02T00:00:00Z")
    assert [item["title"] for item in result] == ["Current mountain course announcement"]


def test_duplicate_feed_and_article_metadata_dedupes_by_url_and_prefers_article_hash():
    url = "https://example.no/nyheter/launch/"
    rows = [
        update("Launch", url, "2026-09-20", strategy="first_party_feed_item"),
        {
            **update("Launch — Example AS", url, "2026-09-20", strategy="first_party_metadata_dated_update", source=url),
            "content_sha256": "b" * 64,
        },
    ]
    result = harden_updates(rows, retrieved_at="2026-10-02T00:00:00Z")
    assert len(result) == 1
    assert result[0]["strategy"] == "first_party_metadata_dated_update"
    assert result[0]["content_sha256"] == "b" * 64


def test_updates_are_newest_first_and_capped():
    rows = [
        update(f"Company announcement {day}", f"https://example.no/news/a-{day}/", f"2026-09-{day:02d}")
        for day in range(1, 8)
    ]
    result = harden_updates(rows, retrieved_at="2026-10-02T00:00:00Z")
    assert len(result) == MAX_UPDATES_PER_COMPANY == 3
    assert [item["published_date"] for item in result] == ["2026-09-07", "2026-09-06", "2026-09-05"]
