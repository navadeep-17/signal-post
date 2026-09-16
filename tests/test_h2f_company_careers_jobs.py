from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.company_careers_jobs import (  # noqa: E402
    discover_career_links,
    extract_structured_job_observations,
)
from norway_company_agent.external_footprint import validate_observation  # noqa: E402


def _profile(domain: str = "example.no") -> dict:
    return {
        "organisation_number": "912345678",
        "external_observations": [],
        "evidence": {
            "website": {
                "status": "available",
                "source_type": "registry_linked_company_website",
                "source_url": f"https://{domain}/",
                "value": {
                    "final_url": f"https://{domain}/",
                    "registered_domain": domain,
                    "identity_assessment": {"publishable": True, "score": 1.0},
                },
            }
        },
    }


def _career_page(*, valid_through: str = "2027-01-31") -> dict:
    html = f'''<!doctype html><html><head>
    <script type="application/ld+json">{{
      "@context": "https://schema.org",
      "@type": "JobPosting",
      "title": "Senior Data Engineer",
      "datePosted": "2026-09-10",
      "validThrough": "{valid_through}",
      "employmentType": "FULL_TIME",
      "description": "Build reliable data products for our Oslo team.",
      "jobLocation": {{
        "@type": "Place",
        "address": {{"@type":"PostalAddress","addressLocality":"Oslo","addressCountry":"NO"}}
      }}
    }}</script></head><body><h1>Senior Data Engineer</h1></body></html>'''
    return {
        "url": "https://example.no/careers",
        "html": html,
        "content_sha256": "a" * 64,
        "retrieved_at": "2026-09-16T03:00:00Z",
    }


def test_career_link_discovery_uses_strong_same_domain_terms():
    html = '''
    <a href="/om-oss">Om oss</a>
    <a href="/karriere">Karriere</a>
    <a href="https://jobs.other.example/open">Careers</a>
    <a href="/slik-jobber-vi">Slik jobber vi</a>
    '''
    links = discover_career_links("https://example.no/", html)
    assert links == ["https://example.no/karriere"]


def test_structured_jobposting_becomes_publishable_observation():
    observations, rejected = extract_structured_job_observations(
        _profile(),
        _career_page(),
        now=datetime(2026, 9, 16, tzinfo=timezone.utc),
    )
    assert rejected == []
    assert len(observations) == 1
    row = observations[0]
    assert row["signal_type"] == "job_posting"
    assert row["platform"] == "company_site"
    assert row["metrics"]["job_title"] == "Senior Data Engineer"
    assert row["metrics"]["location"] == "Oslo, NO"
    assert validate_observation(row) == []


def test_expired_structured_jobposting_abstains():
    observations, rejected = extract_structured_job_observations(
        _profile(),
        _career_page(valid_through="2026-09-01"),
        now=datetime(2026, 9, 16, tzinfo=timezone.utc),
    )
    assert observations == []
    assert rejected and rejected[0]["reason"] == "expired"


def test_unverified_or_cross_domain_career_page_abstains():
    unverified = _profile()
    unverified["evidence"]["website"]["value"]["identity_assessment"]["publishable"] = False
    observations, _ = extract_structured_job_observations(
        unverified,
        _career_page(),
        now=datetime(2026, 9, 16, tzinfo=timezone.utc),
    )
    assert observations == []

    page = _career_page()
    page["url"] = "https://other.no/careers"
    observations, _ = extract_structured_job_observations(
        _profile(),
        page,
        now=datetime(2026, 9, 16, tzinfo=timezone.utc),
    )
    assert observations == []
