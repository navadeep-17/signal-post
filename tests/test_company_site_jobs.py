from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.company_site_jobs import (  # noqa: E402
    build_job_observation,
    career_link_candidates,
    extract_structured_job_postings,
    posting_matches_company,
)
from norway_company_agent.external_footprint import publishable_observation  # noqa: E402


def profile(name="ACME NORGE AS"):
    return {
        "organisation_number": "923609016",
        "name": name,
        "evidence": {
            "website": {
                "status": "available",
                "source_url": "https://acme.no/",
                "value": {
                    "final_url": "https://acme.no/",
                    "identity_assessment": {
                        "status": "exact",
                        "score": 0.99,
                        "publishable": True,
                    },
                },
            }
        },
    }


def job_html(hiring_name="ACME NORGE AS"):
    return f'''<html><head><script type="application/ld+json">{{
      "@context":"https://schema.org",
      "@type":"JobPosting",
      "title":"Senior Backend Engineer",
      "datePosted":"2026-09-10",
      "validThrough":"2026-10-10T23:59:00+02:00",
      "employmentType":"FULL_TIME",
      "hiringOrganization":{{"@type":"Organization","name":"{hiring_name}"}},
      "jobLocation":{{"@type":"Place","address":{{"addressLocality":"Oslo","addressCountry":"NO"}}}},
      "description":"<p>Build reliable APIs.</p>"
    }}</script></head><body></body></html>'''


def test_career_links_are_bounded_same_registered_domain_and_prioritized():
    html = '''
    <a href="/news">News</a>
    <a href="/karriere">Karriere</a>
    <a href="https://careers.acme.no/ledige-stillinger">Ledige stillinger</a>
    <a href="https://linkedin.com/company/acme/jobs">Jobs on LinkedIn</a>
    '''
    links = career_link_candidates("https://www.acme.no/", html, limit=2)
    assert links == [
        "https://careers.acme.no/ledige-stillinger",
        "https://www.acme.no/karriere",
    ]


def test_jsonld_job_posting_is_extracted_without_inventing_fields():
    postings = extract_structured_job_postings(job_html(), base_url="https://acme.no/karriere")
    assert len(postings) == 1
    item = postings[0]
    assert item["title"] == "Senior Backend Engineer"
    assert item["hiring_organization"] == "ACME NORGE AS"
    assert item["date_posted"] == "2026-09-10"
    assert "Build reliable APIs." in item["description"]


def test_generic_careers_page_without_jobposting_schema_emits_no_jobs():
    html = "<html><body><h1>Careers</h1><p>We are always interested in talented people.</p></body></html>"
    assert extract_structured_job_postings(html, base_url="https://acme.no/careers") == []


def test_wrong_hiring_organization_is_rejected_even_on_verified_site():
    posting = extract_structured_job_postings(
        job_html(hiring_name="ACME SWEDEN AB"), base_url="https://acme.no/careers"
    )[0]
    assert posting_matches_company(profile(), posting) is False
    assert build_job_observation(
        profile(),
        source_url="https://acme.no/careers",
        retrieved_at="2026-09-14T12:00:00Z",
        content_sha256="a" * 64,
        posting=posting,
        index=0,
    ) is None


def test_exact_hiring_organization_produces_publishable_zero_cost_observation():
    posting = extract_structured_job_postings(job_html(), base_url="https://acme.no/careers")[0]
    item = build_job_observation(
        profile(),
        source_url="https://acme.no/careers",
        retrieved_at="2026-09-14T12:00:00Z",
        content_sha256="a" * 64,
        posting=posting,
        index=0,
    )
    assert item is not None
    assert item["signal_type"] == "job_posting"
    assert item["acquisition_mode"] == "permitted_public_page"
    assert item["rights_status"] == "approved"
    assert publishable_observation(item) is True


def test_unverified_company_site_cannot_publish_job_even_with_valid_schema():
    item_profile = profile()
    item_profile["evidence"]["website"]["value"]["identity_assessment"]["publishable"] = False
    posting = extract_structured_job_postings(job_html(), base_url="https://acme.no/careers")[0]
    assert build_job_observation(
        item_profile,
        source_url="https://acme.no/careers",
        retrieved_at="2026-09-14T12:00:00Z",
        content_sha256="a" * 64,
        posting=posting,
        index=0,
    ) is None
