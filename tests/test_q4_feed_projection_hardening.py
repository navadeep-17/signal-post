from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.first_party_feed_contract import project_first_party_feed_updates  # noqa: E402


def _profile() -> dict:
    return {
        "organisation_number": "936252494",
        "evidence": {
            "website": {
                "status": "available",
                "source_url": "https://www.pubspill.no/",
                "value": {
                    "final_url": "https://www.pubspill.no/",
                    "identity_assessment": {
                        "status": "exact",
                        "publishable": True,
                        "score": 1.0,
                    },
                },
            },
            "website_activity_feed": {
                "status": "available",
                "source_type": "verified_company_activity_feed",
                "source_url": "https://www.pubspill.no/feed",
                "retrieved_at": "2026-10-05T12:05:00Z",
                "content_sha256": "b" * 64,
                "value": {
                    "verified_website_url": "https://www.pubspill.no/",
                    "entries": [
                        {
                            "title": "En mester iblant oss",
                            "url": "https://www.pubspill.no/en-mester-iblant-oss",
                            "published_date": "2026-10-05",
                            "evidence_span": "En mester iblant oss; published date 2026-10-05",
                        }
                    ],
                },
            },
        },
    }


def _contract() -> dict:
    return {"organisation_number": "936252494", "claims": [], "evidence": []}


def test_projection_rejects_cross_domain_retained_article_url() -> None:
    profile = _profile()
    profile["evidence"]["website_activity_feed"]["value"]["entries"][0]["url"] = (
        "https://other.example/news/copied"
    )

    assert project_first_party_feed_updates(_contract(), profile) == _contract()


def test_projection_rejects_invalid_retained_publication_date() -> None:
    profile = _profile()
    profile["evidence"]["website_activity_feed"]["value"]["entries"][0]["published_date"] = (
        "2026-13-40"
    )

    assert project_first_party_feed_updates(_contract(), profile) == _contract()


def test_projection_rejects_cross_domain_feed_snapshot() -> None:
    profile = _profile()
    profile["evidence"]["website_activity_feed"]["source_url"] = "https://feeds.example.net/rss"

    assert project_first_party_feed_updates(_contract(), profile) == _contract()


def test_projection_rejects_malformed_feed_hash() -> None:
    profile = _profile()
    profile["evidence"]["website_activity_feed"]["content_sha256"] = "not-a-sha256"

    assert project_first_party_feed_updates(_contract(), profile) == _contract()
