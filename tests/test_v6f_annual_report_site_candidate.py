from __future__ import annotations

from norway_company_agent.annual_report_site_candidate import extract_annual_report_site_candidates


def profile() -> dict:
    return {
        "organisation_number": "123456789",
        "name": "FJORD DATA SERVICE AS",
        "municipality": "OSLO",
        "evidence": {},
    }


def test_explicit_company_url_is_ranked():
    text = """
    Organisasjonsnummer 123 456 789
    FJORD DATA SERVICE AS
    Nettside: https://www.fjorddataservice.no/kontakt
    """
    rows = extract_annual_report_site_candidates(
        profile(), text=text, source_url="https://brreg.example/report.pdf", content_sha256="a" * 64
    )
    assert rows
    assert rows[0]["domain"] == "fjorddataservice.no"
    assert rows[0]["source_kind"] == "explicit_url"
    assert rows[0]["publication_status"].startswith("candidate_only")


def test_company_email_domain_can_nominate_candidate():
    text = """
    Org.nr. 123456789
    Kontakt FJORD DATA SERVICE AS på e-post post@fjorddataservice.no.
    """
    rows = extract_annual_report_site_candidates(
        profile(), text=text, source_url="https://brreg.example/report.pdf", content_sha256="b" * 64
    )
    assert rows and rows[0]["domain"] == "fjorddataservice.no"
    assert rows[0]["source_kind"] == "email_domain"


def test_auditor_domain_is_filtered_by_context():
    text = """
    Organisasjonsnummer 123456789
    FJORD DATA SERVICE AS
    Revisor: Audit Partner AS, auditor@example-audit.no
    """
    rows = extract_annual_report_site_candidates(
        profile(), text=text, source_url="https://brreg.example/report.pdf", content_sha256="c" * 64
    )
    assert rows == []


def test_unrelated_url_is_not_worth_a_probe():
    text = """
    Organisasjonsnummer 123456789
    FJORD DATA SERVICE AS årsregnskap.
    Dokumentasjon finnes på https://example-vendor.no/docs
    """
    rows = extract_annual_report_site_candidates(
        profile(), text=text, source_url="https://brreg.example/report.pdf", content_sha256="d" * 64
    )
    assert rows == []


def test_social_and_public_mail_domains_are_blocked():
    text = """
    Organisasjonsnummer 123456789
    FJORD DATA SERVICE AS
    Kontakt: fjorddataservice@gmail.com
    https://facebook.com/fjorddataservice
    """
    rows = extract_annual_report_site_candidates(
        profile(), text=text, source_url="https://brreg.example/report.pdf", content_sha256="e" * 64
    )
    assert rows == []


def test_wrong_org_report_cannot_nominate_anything():
    text = "FJORD DATA SERVICE AS nettside https://fjorddataservice.no organisasjonsnummer 987654321"
    rows = extract_annual_report_site_candidates(
        profile(), text=text, source_url="https://brreg.example/report.pdf", content_sha256="f" * 64
    )
    assert rows == []
