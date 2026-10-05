from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from screen_q5_external_recruitment_links import extract_external_recruitment_links, verified_website  # noqa: E402


def test_extracts_external_ats_link_declared_by_exact_homepage() -> None:
    html = '''
    <html><body>
      <a href="https://example.teamtailor.com/jobs">Se ledige stillinger</a>
      <a href="https://facebook.com/example">Følg oss</a>
    </body></html>
    '''
    rows = extract_external_recruitment_links(html=html, final_url="https://example.no/")
    assert len(rows) == 1
    row = rows[0]
    assert row["host"] == "example.teamtailor.com"
    assert row["known_recruitment_host"] == "teamtailor.com"
    assert "ledige stillinger" in row["markers"]


def test_known_ats_host_can_surface_generic_link_but_same_host_cannot() -> None:
    html = '''
    <html><body>
      <a href="https://company.webcruiter.com/Main/Recruit/Public/123">Søk her</a>
      <a href="/karriere/">Karriere</a>
    </body></html>
    '''
    rows = extract_external_recruitment_links(html=html, final_url="https://example.no/")
    assert [row["known_recruitment_host"] for row in rows] == ["webcruiter.com"]
    assert rows[0]["url"].startswith("https://company.webcruiter.com/")


def test_external_non_recruitment_link_is_rejected() -> None:
    html = '''
    <html><body>
      <a href="https://partner.example.org/about">Les mer om partneren vår</a>
      <iframe src="https://video.example.org/embed/1"></iframe>
    </body></html>
    '''
    assert extract_external_recruitment_links(html=html, final_url="https://example.no/") == []


def test_external_marker_link_is_retained_without_known_ats_domain() -> None:
    html = '<a href="https://recruit.example.org/openings">Join our team</a>'
    rows = extract_external_recruitment_links(html=html, final_url="https://example.no/")
    assert len(rows) == 1
    assert rows[0]["known_recruitment_host"] is None
    assert rows[0]["markers"] == ["join our team"]


def test_verified_website_requires_existing_publishable_exact_site() -> None:
    profile = {
        "evidence": {
            "website": {
                "status": "available",
                "source_url": "https://example.no/",
                "value": {
                    "final_url": "https://example.no/",
                    "identity_assessment": {"publishable": True},
                },
            }
        }
    }
    assert verified_website(profile) == "https://example.no/"
    profile["evidence"]["website"]["value"]["identity_assessment"]["publishable"] = False
    assert verified_website(profile) is None
