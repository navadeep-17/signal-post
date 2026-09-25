from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.structured_jobs import extract_job_postings, hiring_organisation_matches  # noqa: E402


def test_extracts_only_explicit_jobposting_with_title_and_http_url() -> None:
    structured = {
        "json-ld": [
            {
                "@context": "https://schema.org",
                "@type": "JobPosting",
                "title": "Senior Developer",
                "url": "/jobs/senior-developer",
                "datePosted": "2026-09-20",
                "validThrough": "2026-10-20",
                "employmentType": ["FULL_TIME"],
                "hiringOrganization": {"@type": "Organization", "name": "Example AS"},
                "description": "Build reliable systems.",
            },
            {"@type": "Organization", "name": "Example AS"},
        ]
    }
    jobs = extract_job_postings(structured, base_url="https://example.no/")
    assert jobs == [
        {
            "title": "Senior Developer",
            "url": "https://example.no/jobs/senior-developer",
            "hiring_organization": "Example AS",
            "date_posted": "2026-09-20",
            "valid_through": "2026-10-20",
            "employment_type": ["FULL_TIME"],
            "description_excerpt": "Build reliable systems.",
        }
    ]


def test_generic_careers_words_and_incomplete_jobposting_do_not_qualify() -> None:
    structured = {
        "json-ld": [
            {"@type": "WebPage", "name": "Careers - we are hiring"},
            {"@type": "JobPosting", "title": "Developer"},
            {"@type": "JobPosting", "url": "/jobs/no-title"},
        ]
    }
    assert extract_job_postings(structured, base_url="https://example.no/careers") == []


def test_deduplicates_same_role_and_url() -> None:
    job = {"@type": "JobPosting", "title": "Engineer", "url": "/jobs/1", "hiringOrganization": {"name": "Example AS"}}
    jobs = extract_job_postings({"json-ld": [job, dict(job)]}, base_url="https://example.no/")
    assert len(jobs) == 1


def test_hiring_organisation_match_is_conservative() -> None:
    assert hiring_organisation_matches("Example Technology AS", "Example Technology") is True
    assert hiring_organisation_matches("Example Technology AS", "Example Technology Norway AS") is True
    assert hiring_organisation_matches("Example Technology AS", "Different Global AS") is False
    assert hiring_organisation_matches("Example Technology AS", None) is False
