from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.annual_report_description import (
    build_annual_report_description_observation,
    extract_business_description,
)


def test_rejects_accounting_policy_sentence_as_company_description() -> None:
    text = """
    Organisasjonsnummer 123 456 789
    Virksomhetens art
    har ikke endret regnskapsprinsipp fra 2024 til 2025.
    Fortsatt drift
    """
    description, status = extract_business_description(text)
    assert description is None
    assert status == "no_company_activity_section"


def test_cuts_inline_accounting_policy_section_after_real_activity() -> None:
    text = """
    Organisasjonsnummer 123 456 789
    Virksomhetens art
    Selskapet er et konsulentselskap innenfor eiendom og finans. Selskapet ligger i Trondheim kommune. Salgsinntekter Inntektsføring ved salg av varer skjer på leveringstidspunktet. Klassifisering og vurdering av balanseposter Anleggsmidler er eiendeler bestemt til varig eie eller bruk.
    """
    description, status = extract_business_description(text)
    assert status == "accepted"
    assert description is not None
    assert "konsulentselskap" in description
    assert "Salgsinntekter" not in description
    assert "Anleggsmidler" not in description
    assert len(description) < 220


def test_rejects_explicit_different_legal_entity_even_when_target_org_is_elsewhere() -> None:
    profile = {
        "organisation_number": "123456789",
        "name": "SKIPSFJORD HOLDING AS",
        "external_observations": [],
    }
    observation, audit = build_annual_report_description_observation(
        profile,
        text=(
            "Organisasjonsnummer 123 456 789\n"
            "Virksomhetens art\n"
            "Utsatt Skatt AS er et selskap der virksomheten omfatter salg av konsulenttjenester "
            "og rådgivning, samt investeringer i finansielle aktiva og eiendom.\n"
            "Fortsatt drift\n"
        ),
        source_url="https://data.brreg.no/regnskapsregisteret/regnskap/aarsregnskap/kopi/123456789/2025",
        content_sha256="a" * 64,
        retrieved_at="2026-10-01T00:00:00Z",
        effective_at="2025",
    )
    assert observation is None
    assert audit["status"] == "explicit_different_company_name"
    assert audit["named_entity"] == "Utsatt Skatt AS"


def test_accepts_explicit_target_legal_entity_name() -> None:
    profile = {
        "organisation_number": "123456789",
        "name": "EXAMPLE CONSULTING AS",
        "external_observations": [],
    }
    observation, audit = build_annual_report_description_observation(
        profile,
        text=(
            "Organisasjonsnummer 123 456 789\n"
            "Virksomhetens art\n"
            "Example Consulting AS leverer rådgivning og programvare til energibransjen i Norge.\n"
            "Fortsatt drift\n"
        ),
        source_url="https://data.brreg.no/regnskapsregisteret/regnskap/aarsregnskap/kopi/123456789/2025",
        content_sha256="b" * 64,
        retrieved_at="2026-10-01T00:00:00Z",
        effective_at="2025",
    )
    assert audit["status"] == "accepted"
    assert observation is not None
    assert observation["strategy"] == "annual_report_company_description_exact_org_v2"
