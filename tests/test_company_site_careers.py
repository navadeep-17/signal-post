from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.company_site_careers import (  # noqa: E402
    career_links,
    specific_job_links,
    verified_company_site,
    workforce_observation,
)
from norway_company_agent.external_footprint import publishable_observation  # noqa: E402


def profile():
    return {
        "organisation_number": "999999999",
        "name": "EXAMPLE AS",
        "evidence": {
            "website": {
                "status": "available",
                "source_url": "https://example.no/",
                "retrieved_at": "2026-09-14T12:00:00Z",
                "value": {
                    "final_url": "https://example.no/",
                    "identity_assessment": {
                        "publishable": True,
                        "status": "exact",
                        "score": 0.99,
                        "method": "deterministic_name_org_evidence_v2",
                    },
                },
            }
        },
    }


def test_career_links_are_same_registered_domain_and_bounded():
    html = '''
    <a href="/om-oss">Om oss</a>
    <a href="/karriere">Karriere</a>
    <a href="https://jobs.example.no/careers">Ledige stillinger</a>
    <a href="https://external-ats.test/example">Jobs</a>
    <a href="/kontakt">Kontakt</a>
    '''
    rows = career_links("https://www.example.no/", html, limit=2)
    assert len(rows) == 2
    assert {row["url"] for row in rows} == {
        "https://www.example.no/karriere",
        "https://jobs.example.no/careers",
    }


def test_specific_job_links_require_role_like_child_path_and_non_generic_anchor():
    html = '''
    <a href="/careers">Careers</a>
    <a href="/careers/software-engineer">Software Engineer</a>
    <a href="/jobs/1234">Senior Data Engineer</a>
    <a href="/jobs">See jobs</a>
    <a href="https://ats.example.test/jobs/555">Platform Engineer</a>
    '''
    rows = specific_job_links("https://example.no/careers", html)
    assert rows == [
        {"url": "https://example.no/jobs/1234", "title": "Senior Data Engineer"},
        {"url": "https://example.no/careers/software-engineer", "title": "Software Engineer"},
    ]


def test_unverified_company_site_cannot_seed_careers_connector():
    item = profile()
    item["evidence"]["website"]["value"]["identity_assessment"]["publishable"] = False
    assert verified_company_site(item) is None
    assert workforce_observation(item, [{"url": "https://example.no/careers", "content_sha256": "a" * 64}]) is None


def test_careers_page_becomes_publishable_workforce_snapshot_not_job_posting():
    pages = [
        {
            "url": "https://example.no/careers",
            "title": "Careers at Example",
            "content_sha256": "a" * 64,
            "specific_job_links": [
                {"url": "https://example.no/careers/software-engineer", "title": "Software Engineer"},
                {"url": "https://example.no/jobs/1234", "title": "Senior Data Engineer"},
            ],
        }
    ]
    item = workforce_observation(profile(), pages)
    assert item is not None
    assert item["signal_type"] == "workforce_snapshot"
    assert item["platform"] == "company_site"
    assert item["acquisition_mode"] == "permitted_public_page"
    assert item["rights_status"] == "approved"
    assert item["metrics"]["specific_internal_job_links"] == 2
    assert publishable_observation(item)


def test_generic_careers_page_does_not_claim_active_job_count():
    pages = [
        {
            "url": "https://example.no/karriere",
            "title": "Karriere",
            "content_sha256": "b" * 64,
            "specific_job_links": [],
        }
    ]
    item = workforce_observation(profile(), pages)
    assert item is not None
    assert item["signal_type"] == "workforce_snapshot"
    assert item["metrics"]["specific_internal_job_links"] == 0
    assert "active_job_count" not in item["metrics"]
