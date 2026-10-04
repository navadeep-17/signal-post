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
            "published_date_candidates": [],
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
                "published_date_candidates": [],
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


def test_dated_homepage_card_can_nominate_specific_root_slug() -> None:
    html = """
    <html><body>
      <section class="news-card">
        <span>03.06.26</span>
        <h2>Elbilladere i fokus hos det lokale eltilsyn</h2>
        <a href="/elbilladere-i-fokus-hos-det-lokale-eltilsyn">Les mer</a>
      </section>
      <a href="/om-oss">Om oss</a>
    </body></html>
    """
    rows = extract_news_detail_links(
        verified_url="https://example.no/",
        final_url="https://example.no/",
        soup=BeautifulSoup(html, "lxml"),
        homepage_content_sha256="a" * 64,
    )
    assert [row["url"] for row in rows] == [
        "https://example.no/elbilladere-i-fokus-hos-det-lokale-eltilsyn"
    ]
    assert rows[0]["marker"] == "dated_homepage_card"
    assert "03.06.26" in str(rows[0]["dated_context"])
    assert rows[0]["nomination_only"] is True


def test_root_slug_without_local_date_is_not_news_nomination() -> None:
    html = "<html><body><div><a href='/ordinary-product-page'>Les mer</a></div></body></html>"
    assert extract_news_detail_links(
        verified_url="https://example.no/",
        final_url="https://example.no/",
        soup=BeautifulSoup(html, "lxml"),
        homepage_content_sha256="a" * 64,
    ) == []


def test_page_date_candidates_retain_semantic_and_labelled_page_dates() -> None:
    soup = BeautifulSoup(
        """
        <html><head><meta property="article:published_time" content="2026-06-03T12:11:00+02:00"></head>
        <body><span class="published-date">03.06.26, kl 12:11</span></body></html>
        """,
        "lxml",
    )
    candidates = final_site._page_date_candidates(soup)
    assert {item["raw"] for item in candidates} >= {
        "2026-06-03T12:11:00+02:00",
        "03.06.26, kl 12:11",
    }


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


def _profile_with_detail(
    *,
    linked: bool = True,
    dated: bool = True,
    root_slug: bool = False,
    short_year_date: bool = False,
    page_date_candidate: bool = False,
) -> dict:
    homepage = _website_record()
    homepage["value"]["identity_assessment"] = {
        "status": "exact",
        "score": 1.0,
        "publishable": True,
        "method": "fixture",
    }
    article_url = (
        "https://example.no/elbilladere-i-fokus-hos-det-lokale-eltilsyn"
        if root_slug
        else "https://example.no/aktuelt/fersk-nyhet/"
    )
    if linked:
        homepage["value"]["news_detail_links"] = [{
            "url": article_url,
            "nomination_only": True,
            "marker": "dated_homepage_card" if root_slug else "aktuelt",
        }]
    date_text = "03.06.26" if short_year_date else "2026-10-03"
    detail = _website_record(
        url=article_url,
        title=(
            "Elbilladere i fokus hos det lokale eltilsyn"
            if root_slug
            else "Fersk nyhet fra Example AS"
        ),
        text=(
            f"Konkret selskapsoppdatering. Publisert {date_text}. Dette er detaljsiden med innhold."
            if dated else
            "Konkret selskapsoppdatering uten publiseringsdato i ekstraktet. Dette er detaljsiden med innhold."
        ),
    )
    if page_date_candidate:
        detail["value"]["published_date_candidates"] = [
            {"raw": "03.06.26, kl 12:11", "method": "date_labelled_element"}
        ]
        detail["value"]["pages"][0]["published_date_candidates"] = list(
            detail["value"]["published_date_candidates"]
        )
    detail["source_type"] = "verified_company_news_detail_candidate"
    return {
        "organisation_number": "923609016",
        "name": "Example AS",
        "evidence": {"website": homepage, "website_news_detail": detail},
    }


def _company_update_claims(profile: dict) -> list[dict]:
    projected = project_first_party_activity_claims(
        {"organisation_number": "923609016", "claims": [], "evidence": [], "changes": [], "errors": []},
        profile,
    )
    return [item for item in projected["claims"] if item.get("field") == "external.company_update"]


def test_retained_linked_dated_detail_projects_material_company_update() -> None:
    claims = _company_update_claims(_profile_with_detail())
    assert len(claims) == 1
    assert claims[0]["value"]["url"] == "https://example.no/aktuelt/fersk-nyhet/"
    assert claims[0]["value"]["published_date"] == "2026-10-03"


def test_homepage_nominated_root_slug_with_short_year_date_projects_update() -> None:
    claims = _company_update_claims(
        _profile_with_detail(root_slug=True, short_year_date=True)
    )
    assert len(claims) == 1
    assert claims[0]["value"]["url"] == "https://example.no/elbilladere-i-fokus-hos-det-lokale-eltilsyn"
    assert claims[0]["value"]["published_date"] == "2026-06-03"


def test_page_local_date_candidate_can_supply_date_when_text_extractor_omits_it() -> None:
    claims = _company_update_claims(
        _profile_with_detail(
            dated=False,
            root_slug=True,
            page_date_candidate=True,
        )
    )
    assert len(claims) == 1
    assert claims[0]["value"]["published_date"] == "2026-06-03"


def test_unlinked_or_undated_detail_remains_unpublished() -> None:
    profiles = (
        _profile_with_detail(linked=False),
        _profile_with_detail(dated=False),
        _profile_with_detail(linked=False, root_slug=True, short_year_date=True),
    )
    for profile in profiles:
        assert _company_update_claims(profile) == []
