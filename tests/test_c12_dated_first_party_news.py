from __future__ import annotations

from pathlib import Path
import sys

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import norway_company_agent.final_site_discovery as final_site
from norway_company_agent.evidence import evidence
from norway_company_agent.first_party_activity import project_first_party_activity_claims
from norway_company_agent.homepage_news_signal import extract_news_detail_links


def _website_record(*, url: str = "https://example.no/", title: str = "Example AS", text: str = "Example AS org 923609016 Oslo") -> dict:
    digest = "a" * 64 if url.rstrip("/") == "https://example.no" else "b" * 64
    return evidence(
        "website",
        "available",
        "test_company_site",
        url,
        value={
            "requested_url": url,
            "final_url": url,
            "registered_domain": "example.no",
            "title": title,
            "description": "",
            "identity_text_excerpt": text,
            "main_text_excerpt": text,
            "social_links": [],
            "careers_links": [],
            "news_detail_links": [],
            "structured_organisations": [],
            "content_sha256": digest,
            "extraction_state": "static_complete",
            "identity_links": [],
            "pages": [{
                "url": url,
                "title": title,
                "identity_text_excerpt": text,
                "main_text_excerpt": text,
                "content_sha256": digest,
            }],
            "crawl_errors": [],
        },
        content_sha256=digest,
        retrieved_at="2026-10-04T00:00:00Z",
    )


def _profile() -> dict:
    return {
        "organisation_number": "923609016",
        "name": "Example AS",
        "website": "https://example.no/",
        "municipality": "OSLO",
        "evidence": {},
    }


def test_homepage_news_nomination_rejects_archive_and_external_links() -> None:
    html = "<html><body><a href='/aktuelt/'>Aktuelt</a><a href='/medlem/aktuelt/fersk-nyhet/'>Fersk nyhet fra Example</a><a href='https://other.no/aktuelt/fremmed/'>Fremmed nyhet</a></body></html>"
    rows = extract_news_detail_links(
        verified_url="https://example.no/",
        final_url="https://example.no/",
        soup=BeautifulSoup(html, "lxml"),
        homepage_content_sha256="a" * 64,
    )
    assert [row["url"] for row in rows] == ["https://example.no/medlem/aktuelt/fersk-nyhet/"]
    assert rows[0]["nomination_only"] is True


def test_verified_registry_site_uses_remaining_two_requests_for_one_news_detail(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    def fake_fetch(url, *, source_type, timeout=6.0, max_bytes=750_000):
        calls.append((str(url), source_type))
        if len(calls) == 1:
            record = _website_record()
            record["value"]["news_detail_links"] = [{
                "url": "https://example.no/aktuelt/fersk-nyhet/",
                "anchor_text": "Fersk nyhet",
                "marker": "aktuelt",
                "homepage_url": "https://example.no/",
                "homepage_content_sha256": "a" * 64,
                "nomination_only": True,
            }]
            return record, {"requests": 2, "bytes": 100, "latencies_ms": [5]}
        detail = _website_record(
            url="https://example.no/aktuelt/fersk-nyhet/",
            title="Fersk nyhet fra Example AS",
            text="Fersk nyhet fra Example AS publisert 2026-10-03. Viktig oppdatering.",
        )
        detail["source_type"] = source_type
        detail["source_class"] = source_type
        return detail, {"requests": 2, "bytes": 200, "latencies_ms": [6]}

    monkeypatch.setattr(final_site, "fetch_bounded_homepage", fake_fetch)
    row, metrics = final_site.discover_final_website(_profile())
    assert metrics["requests"] == final_site.MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE == 4
    assert metrics["news_detail_attempted"] is True
    assert metrics["news_detail_retained"] is True
    assert len(calls) == 2
    assert len(row["evidence"]["website"]["value"]["pages"]) == 1
    assert row["evidence"]["website_news_detail"]["source_type"] == "verified_company_news_detail_candidate"


def _profile_with_detail(*, linked: bool = True, dated: bool = True) -> dict:
    homepage = _website_record()
    homepage["value"]["identity_assessment"] = {
        "status": "exact",
        "score": 1.0,
        "publishable": True,
        "method": "fixture",
    }
    article_url = "https://example.no/aktuelt/fersk-nyhet/"
    if linked:
        homepage["value"]["news_detail_links"] = [{"url": article_url, "nomination_only": True}]
    detail = _website_record(
        url=article_url,
        title="Fersk nyhet fra Example AS",
        text=(
            "Fersk nyhet fra Example AS. Publisert 2026-10-03. Dette er en konkret oppdatering fra selskapet."
            if dated else
            "Fersk nyhet fra Example AS. Dette er en konkret oppdatering fra selskapet."
        ),
    )
    detail["source_type"] = "verified_company_news_detail_candidate"
    return {
        "organisation_number": "923609016",
        "name": "Example AS",
        "evidence": {"website": homepage, "website_news_detail": detail},
    }


def test_retained_linked_dated_detail_projects_material_company_update() -> None:
    profile = _profile_with_detail()
    projected = project_first_party_activity_claims(
        {"organisation_number": "923609016", "claims": [], "evidence": [], "changes": [], "errors": []},
        profile,
    )
    claims = [item for item in projected["claims"] if item.get("field") == "external.company_update"]
    assert len(claims) == 1
    assert claims[0]["value"]["url"] == "https://example.no/aktuelt/fersk-nyhet/"
    assert claims[0]["value"]["published_date"] == "2026-10-03"


def test_unlinked_or_undated_detail_remains_unpublished() -> None:
    for profile in (_profile_with_detail(linked=False), _profile_with_detail(dated=False)):
        projected = project_first_party_activity_claims(
            {"organisation_number": "923609016", "claims": [], "evidence": [], "changes": [], "errors": []},
            profile,
        )
        assert not [item for item in projected["claims"] if item.get("field") == "external.company_update"]
