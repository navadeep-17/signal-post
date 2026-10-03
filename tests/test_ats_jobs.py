from datetime import date
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.ats_jobs import (
    ats_provider,
    extract_linked_ats_candidates,
    qualify_job_postings,
)


def profile(name="EXAMPLE BEDRIFT AS"):
    return {
        "organisation_number": "123456789",
        "name": name,
        "canonical_profile": {"company": {"legal_name": name}},
    }


def ats_candidate(provider="teamtailor", url="https://example.teamtailor.com/jobs"):
    return {
        "url": url,
        "provider": provider,
        "careers_url": "https://example.no/karriere",
        "careers_content_sha256": "c" * 64,
        "trusted_link_chain": True,
    }


def job_html(
    *,
    title="Backend Engineer",
    hiring_name="Example Bedrift AS",
    job_url="https://example.teamtailor.com/jobs/123-backend-engineer",
    date_posted="2026-10-01",
    valid_through="2026-10-31",
    include_apply=True,
):
    payload = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": title,
        "url": job_url,
        "datePosted": date_posted,
        "validThrough": valid_through,
        "employmentType": "FULL_TIME",
        "hiringOrganization": {"@type": "Organization", "name": hiring_name},
        "jobLocation": {
            "@type": "Place",
            "address": {
                "@type": "PostalAddress",
                "addressLocality": "Oslo",
                "addressCountry": "NO",
            },
        },
        "description": "<p>Build reliable systems.</p>",
    }
    apply = (
        '<a href="https://example.teamtailor.com/jobs/123-backend-engineer/apply">Apply now</a>'
        if include_apply
        else ""
    )
    return (
        "<html><body>"
        + apply
        + '<script type="application/ld+json">'
        + json.dumps(payload)
        + "</script></body></html>"
    )


def test_known_ats_hosts_are_recognised_conservatively():
    assert ats_provider("https://example.teamtailor.com/jobs") == "teamtailor"
    assert ats_provider("https://jobs.lever.co/example/job-id") == "lever"
    assert ats_provider("https://boards.greenhouse.io/example/jobs/123") == "greenhouse"
    assert ats_provider("https://example.wd3.myworkdayjobs.com/en-US/External") == "workday"
    assert ats_provider("https://www.jobbnorge.no/ledige-stillinger/stilling/123") == "jobbnorge"
    assert ats_provider("https://jobs.smartrecruiters.com/Example/123") == "smartrecruiters"
    assert ats_provider("https://example.recruitee.com/o/backend") == "recruitee"
    assert ats_provider("https://linkedin.com/jobs/view/123") is None
    assert ats_provider("https://jobs.example.com/") is None


def test_verified_company_careers_page_can_nominate_direct_ats_links_only():
    html = """<html><body>
      <a href="https://example.teamtailor.com/jobs">See open positions</a>
      <a href="https://jobs.lever.co/example">More roles</a>
      <a href="https://linkedin.com/jobs/example">LinkedIn jobs</a>
      <a href="https://teamtailor.com/">Generic provider root</a>
    </body></html>"""
    rows = extract_linked_ats_candidates(
        verified_company_url="https://example.no/",
        careers_url="https://example.no/karriere",
        careers_html=html,
        careers_content_sha256="a" * 64,
    )
    assert [(row["provider"], row["url"]) for row in rows] == [
        ("teamtailor", "https://example.teamtailor.com/jobs"),
        ("lever", "https://jobs.lever.co/example"),
    ]
    assert all(row["trusted_link_chain"] for row in rows)


def test_external_or_unverified_careers_page_cannot_nominate_ats():
    html = '<a href="https://example.teamtailor.com/jobs">Jobs</a>'
    assert extract_linked_ats_candidates(
        verified_company_url="https://example.no/",
        careers_url="https://other.no/karriere",
        careers_html=html,
        careers_content_sha256="a" * 64,
    ) == []
    assert extract_linked_ats_candidates(
        verified_company_url="https://example.no/",
        careers_url="https://example.no/karriere",
        careers_html=html,
        careers_content_sha256="short",
    ) == []


def test_specific_current_jobposting_with_exact_employer_is_publishable():
    rows = qualify_job_postings(
        profile=profile(),
        ats_candidate=ats_candidate(),
        job_page_url="https://example.teamtailor.com/jobs/123-backend-engineer",
        job_html=job_html(),
        content_sha256="b" * 64,
        as_of=date(2026, 10, 3),
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["status"] == "exact_active"
    assert row["publishable"] is True
    assert row["title"] == "Backend Engineer"
    assert row["hiring_organisation_name"] == "Example Bedrift AS"
    assert row["date_posted"] == "2026-10-01"
    assert row["valid_through"] == "2026-10-31"
    assert row["apply_url"] == "https://example.teamtailor.com/jobs/123-backend-engineer/apply"
    assert row["location"]["locality"] == "Oslo"
    assert row["description"] == "Build reliable systems."


def test_corporate_suffix_difference_does_not_break_exact_employer_alignment():
    rows = qualify_job_postings(
        profile=profile("EXAMPLE BEDRIFT AS"),
        ats_candidate=ats_candidate(),
        job_page_url="https://example.teamtailor.com/jobs/123-backend-engineer",
        job_html=job_html(hiring_name="Example Bedrift"),
        content_sha256="b" * 64,
        as_of=date(2026, 10, 3),
    )
    assert rows[0]["publishable"] is True


def test_wrong_parent_or_namesake_employer_is_rejected():
    rows = qualify_job_postings(
        profile=profile(),
        ats_candidate=ats_candidate(),
        job_page_url="https://example.teamtailor.com/jobs/123-backend-engineer",
        job_html=job_html(hiring_name="Example Group AS"),
        content_sha256="b" * 64,
        as_of=date(2026, 10, 3),
    )
    assert rows[0]["status"] == "rejected"
    assert rows[0]["publishable"] is False


def test_expired_job_is_never_publishable():
    rows = qualify_job_postings(
        profile=profile(),
        ats_candidate=ats_candidate(),
        job_page_url="https://example.teamtailor.com/jobs/123-backend-engineer",
        job_html=job_html(valid_through="2026-10-02"),
        content_sha256="b" * 64,
        as_of=date(2026, 10, 3),
    )
    assert rows[0]["status"] == "expired"
    assert rows[0]["publishable"] is False


def test_missing_valid_through_remains_review_not_active():
    rows = qualify_job_postings(
        profile=profile(),
        ats_candidate=ats_candidate(),
        job_page_url="https://example.teamtailor.com/jobs/123-backend-engineer",
        job_html=job_html(valid_through=""),
        content_sha256="b" * 64,
        as_of=date(2026, 10, 3),
    )
    assert rows[0]["status"] == "review"
    assert rows[0]["publishable"] is False


def test_missing_date_posted_remains_review_not_active():
    rows = qualify_job_postings(
        profile=profile(),
        ats_candidate=ats_candidate(),
        job_page_url="https://example.teamtailor.com/jobs/123-backend-engineer",
        job_html=job_html(date_posted=""),
        content_sha256="b" * 64,
        as_of=date(2026, 10, 3),
    )
    assert rows[0]["status"] == "review"
    assert rows[0]["publishable"] is False


def test_missing_specific_title_is_rejected():
    rows = qualify_job_postings(
        profile=profile(),
        ats_candidate=ats_candidate(),
        job_page_url="https://example.teamtailor.com/jobs/123-backend-engineer",
        job_html=job_html(title=""),
        content_sha256="b" * 64,
        as_of=date(2026, 10, 3),
    )
    assert rows[0]["status"] == "rejected"
    assert rows[0]["publishable"] is False


def test_job_page_must_stay_on_company_linked_ats_provider():
    rows = qualify_job_postings(
        profile=profile(),
        ats_candidate=ats_candidate(),
        job_page_url="https://jobs.lever.co/example/123",
        job_html=job_html(job_url="https://jobs.lever.co/example/123"),
        content_sha256="b" * 64,
        as_of=date(2026, 10, 3),
    )
    assert rows == []


def test_untrusted_ats_candidate_can_never_publish():
    candidate = ats_candidate()
    candidate["trusted_link_chain"] = False
    assert qualify_job_postings(
        profile=profile(),
        ats_candidate=candidate,
        job_page_url="https://example.teamtailor.com/jobs/123-backend-engineer",
        job_html=job_html(),
        content_sha256="b" * 64,
        as_of=date(2026, 10, 3),
    ) == []
