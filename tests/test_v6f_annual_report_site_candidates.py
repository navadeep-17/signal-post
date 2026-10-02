from __future__ import annotations

from norway_company_agent.annual_report_site_candidates import extract_annual_report_site_candidates


def profile() -> dict:
    return {
        "organisation_number": "912345678",
        "name": "FJORD DATA SERVICE AS",
    }


def test_exact_company_url_in_company_header_is_high_priority() -> None:
    text = """
    FJORD DATA SERVICE AS
    Organisasjonsnummer 912 345 678
    Hjemmeside: https://www.fjorddataservice.no/kontakt
    Selskapet leverer programvaretjenester.
    """
    rows = extract_annual_report_site_candidates(profile(), text)
    assert rows
    assert rows[0]["domain"] == "www.fjorddataservice.no"
    assert rows[0]["probe_recommendation"] == "high"
    assert rows[0]["publication_evidence"] is False


def test_company_email_domain_can_nominate_but_generic_mail_is_filtered() -> None:
    text = """
    Fjord Data Service AS, org.nr. 912345678
    Kontakt: post@fjorddataservice.no
    Daglig leder: dagligleder@gmail.com
    """
    rows = extract_annual_report_site_candidates(profile(), text)
    domains = {row["domain"] for row in rows}
    assert "fjorddataservice.no" in domains
    assert "gmail.com" not in domains


def test_auditor_context_is_penalized_and_not_high_probe() -> None:
    text = """
    Revisor: Revisjonspartner AS
    E-post audit@revisjonspartner.no
    www.revisjonspartner.no
    """
    rows = extract_annual_report_site_candidates(profile(), text)
    row = next(item for item in rows if item["domain"] == "revisjonspartner.no")
    assert "professional_service_provider_context" in row["negative_reasons"]
    assert row["probe_recommendation"] == "reject"


def test_bare_unrelated_domain_without_website_label_is_ignored() -> None:
    text = "Dokumentet er generert med informasjon fra unrelated-example.no og andre kilder."
    assert extract_annual_report_site_candidates(profile(), text) == []


def test_explicit_unrelated_url_is_retained_for_screening_but_not_recommended_when_weak() -> None:
    text = "Se https://external-provider.no/reference for standardvilkår."
    rows = extract_annual_report_site_candidates(profile(), text)
    assert len(rows) == 1
    assert rows[0]["domain"] == "external-provider.no"
    assert rows[0]["probe_recommendation"] == "reject"
