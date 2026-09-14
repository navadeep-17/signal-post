from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.company_site_careers import (  # noqa: E402
    career_links,
    parse_career_page,
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


def page(url="https://example.no/careers", digest="a" * 64, jobs=None):
    return {
        "url": url,
        "title": "Careers at Example",
        "content_sha256": digest,
        "retrieved_at": "2026-09-14T13:00:00Z",
        "specific_job_links": jobs or [],
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


def test_parse_career_page_records_its_own_retrieval_time_and_hash():
    parsed = parse_career_page(
        "https://example.no/careers",
        b'<html><head><title>Careers</title></head><body><a href="/careers/dev">Developer</a></body></html>',
    )
    assert parsed["retrieved_at"].endswith("Z")
    assert len(parsed["content_sha256"]) == 64
    assert parsed["specific_job_links"] == [{"url": "https://example.no/careers/dev", "title": "Developer"}]


def test_unverified_company_site_cannot_seed_careers_connector():
    item = profile()
    item["evidence"]["website"]["value"]["identity_assessment"]["publishable"] = False
    assert verified_company_site(item) is None
    assert workforce_observation(item, [page()]) is None


def test_careers_page_becomes_publishable_workforce_snapshot_not_job_posting():
    pages = [page(jobs=[
        {"url": "https://example.no/careers/software-engineer", "title": "Software Engineer"},
        {"url": "https://example.no/jobs/1234", "title": "Senior Data Engineer"},
    ])]
    item = workforce_observation(profile(), pages)
    assert item is not None
    assert item["signal_type"] == "workforce_snapshot"
    assert item["platform"] == "company_site"
    assert item["acquisition_mode"] == "permitted_public_page"
    assert item["rights_status"] == "approved"
    assert item["retrieved_at"] == "2026-09-14T13:00:00Z"
    assert item["metrics"]["specific_internal_job_links"] == 2
    assert publishable_observation(item)


def test_generic_careers_page_does_not_claim_active_job_count():
    item = workforce_observation(profile(), [page(url="https://example.no/karriere", digest="b" * 64)])
    assert item is not None
    assert item["signal_type"] == "workforce_snapshot"
    assert item["metrics"]["specific_internal_job_links"] == 0
    assert "active_job_count" not in item["metrics"]


def test_missing_page_retrieval_time_blocks_observation():
    item_page = page()
    item_page.pop("retrieved_at")
    assert workforce_observation(profile(), [item_page]) is None
