from __future__ import annotations

from bs4 import BeautifulSoup

from norway_company_agent.first_party_activity import project_first_party_activity_claims
from norway_company_agent.first_party_feed import parse_company_feed
from norway_company_agent.first_party_feed_contract import project_first_party_feed_updates
from norway_company_agent.homepage_careers_signal import extract_careers_links
from norway_company_agent.homepage_news_signal import extract_news_detail_links


def _site_profile(*, retrieved_at: str = "2026-10-05T18:00:00Z") -> dict:
    homepage_hash = "a" * 64
    return {
        "organisation_number": "996533174",
        "name": "HYBEL AS",
        "evidence": {
            "website": {
                "status": "available",
                "source_url": "https://hybel.no/",
                "retrieved_at": retrieved_at,
                "content_sha256": homepage_hash,
                "value": {
                    "final_url": "https://hybel.no/",
                    "registered_domain": "hybel.no",
                    "identity_assessment": {
                        "status": "exact",
                        "score": 0.95,
                        "publishable": True,
                        "method": "fixture",
                    },
                    "pages": [],
                    "news_detail_links": [],
                    "careers_links": [],
                },
            }
        },
    }


def test_careers_signal_rejects_service_job_word_and_tenant_profile_but_keeps_karriere() -> None:
    html = """
    <html><body>
      <a href="https://jobb.hybel.no/">Karriere</a>
      <a href="/for-naering/">SMÅJOBBER - NÆRINGSBYGG</a>
      <a href="/profil/238397/kvinne-29-ar-soker-bolig-for-1-person-fra-01-01-2027/?siste=1">
        Diella 29 år Antall 1 pers Maks 10 000,- Fra dato 01.01.27
        Hei, Jeg heter Diella og jobber fulltid som en miljøterapeut.
      </a>
    </body></html>
    """
    rows = extract_careers_links(
        verified_url="https://hybel.no/",
        final_url="https://hybel.no/",
        soup=BeautifulSoup(html, "lxml"),
        homepage_content_sha256="a" * 64,
    )

    assert [row["url"] for row in rows] == ["https://jobb.hybel.no/"]


def test_dated_homepage_profile_card_is_not_news_nomination() -> None:
    html = """
    <html><body>
      <section>
        <a href="/profil/575477/mann-27-ar-soker-bolig-for-2-personer-fra-01-12-2026/">
          Harald 27 år Antall 2 pers Maks 18 000,- Fra dato 01.12.26.
          Jeg har fast jobb, stabil økonomi og søker et hjem.
        </a>
      </section>
    </body></html>
    """
    rows = extract_news_detail_links(
        verified_url="https://hybel.no/",
        final_url="https://hybel.no/",
        soup=BeautifulSoup(html, "lxml"),
        homepage_content_sha256="a" * 64,
    )

    assert rows == []


def test_future_page_date_cannot_be_published_as_company_update() -> None:
    profile = _site_profile()
    article_url = "https://hybel.no/profil/575477/mann-27-ar-soker-bolig-for-2-personer-fra-01-12-2026/"
    profile["evidence"]["website"]["value"]["news_detail_links"] = [
        {"url": article_url, "marker": "dated_homepage_card", "nomination_only": True}
    ]
    profile["evidence"]["website_news_detail"] = {
        "status": "available",
        "source_type": "verified_company_news_detail_candidate",
        "source_url": article_url,
        "retrieved_at": "2026-10-05T18:00:01Z",
        "content_sha256": "b" * 64,
        "value": {
            "final_url": article_url,
            "registered_domain": "hybel.no",
            "pages": [
                {
                    "url": article_url,
                    "title": "Mann 27 år søker bolig for 2 personer fra 01.12.2026",
                    "main_text_excerpt": "Fra dato 01.12.2026. Fast jobb og stabil økonomi.",
                    "identity_text_excerpt": "",
                    "published_date_candidates": [],
                    "content_sha256": "b" * 64,
                }
            ],
        },
    }

    projected = project_first_party_activity_claims(
        {"organisation_number": "996533174", "claims": [], "evidence": []},
        profile,
    )

    assert [claim for claim in projected["claims"] if claim.get("field") == "external.company_update"] == []


def test_feed_rejects_localized_default_wordpress_post() -> None:
    raw = b"""<rss version='2.0'><channel>
      <item>
        <title>Hei verden!</title>
        <link>https://www.medinovo.no/2019/04/22/hello-world/</link>
        <pubDate>Mon, 22 Apr 2019 16:39:28 +0000</pubDate>
      </item>
    </channel></rss>"""

    report = parse_company_feed(
        raw,
        feed_url="https://www.medinovo.no/feed/",
        verified_url="https://www.medinovo.no/",
    )

    assert report["entries"] == []


def test_future_feed_entry_is_not_projected() -> None:
    profile = _site_profile(retrieved_at="2026-10-05T18:00:00Z")
    profile["evidence"]["website_activity_feed"] = {
        "status": "available",
        "source_type": "verified_company_activity_feed",
        "source_url": "https://hybel.no/feed/",
        "retrieved_at": "2026-10-05T18:00:05Z",
        "content_sha256": "c" * 64,
        "value": {
            "verified_website_url": "https://hybel.no/",
            "feed_type": "rss",
            "entries": [
                {
                    "title": "Scheduled company announcement",
                    "url": "https://hybel.no/news/scheduled-company-announcement",
                    "published_date": "2026-12-01",
                    "date_extraction_method": "feed_pubdate",
                    "date_evidence": "Tue, 01 Dec 2026 08:00:00 +0100",
                    "evidence_span": "Scheduled company announcement; published date 2026-12-01",
                }
            ],
        },
    }

    projected = project_first_party_feed_updates(
        {"organisation_number": "996533174", "claims": [], "evidence": []},
        profile,
    )

    assert [claim for claim in projected["claims"] if claim.get("field") == "external.company_update"] == []
