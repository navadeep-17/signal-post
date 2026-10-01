from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.annual_report_description import (
    build_annual_report_description_observation,
    extract_business_description,
)
from norway_company_agent.annual_report_description_contract import (
    project_annual_report_company_description,
)
from norway_company_agent.canonical_projection import project_canonical_profile


def _profile(org: str = "123456789") -> dict:
    return {"organisation_number": org, "external_observations": []}


def _observation(org: str = "123456789", description: str = "") -> dict:
    description = description or "Selskapet utvikler og leverer programvare for energibransjen i Norge."
    return {
        "id": "annual-description-test",
        "organisation_number": org,
        "platform": "brreg",
        "signal_type": "company_profile",
        "source_url": f"https://data.brreg.no/regnskapsregisteret/regnskap/aarsregnskap/kopi/{org}/2025",
        "retrieved_at": "2026-10-01T00:00:00Z",
        "content_sha256": "a" * 64,
        "exact_entity": True,
        "identity_proof": [{"type": "organisation_number_in_report_text", "value": org}],
        "acquisition_mode": "official_api",
        "rights_status": "approved",
        "source_class": "official_annual_account_copy",
        "evidence_span": description,
        "effective_at": "2025",
        "company_description": description,
        "metrics": {"claim_scope": "Official annual-account company activity description."},
    }


def test_extract_business_description_from_explicit_company_section() -> None:
    text = """
    Organisasjonsnummer 123 456 789
    Virksomhetens art
    Selskapet utvikler og leverer programvare for energibransjen i Norge og Sverige.
    Fortsatt drift
    Styret bekrefter forutsetningen om fortsatt drift.
    """
    description, status = extract_business_description(text)
    assert status == "accepted"
    assert description is not None
    assert "programvare" in description
    assert "fortsatt drift" not in description.casefold()


def test_extract_business_description_rejects_group_only_section() -> None:
    text = """
    Organisasjonsnummer 123 456 789
    Virksomhetens art
    Konsernet driver virksomhet innen eiendom, finans og teknologi i Norden.
    Fortsatt drift
    """
    description, status = extract_business_description(text)
    assert description is None
    assert status == "no_company_activity_section"


def test_build_observation_requires_exact_org_in_report_text() -> None:
    profile = _profile()
    observation, audit = build_annual_report_description_observation(
        profile,
        text="Organisasjonsnummer 987 654 321\nVirksomhetens art\nSelskapet utvikler programvare for norske kunder.",
        source_url="https://data.brreg.no/regnskapsregisteret/regnskap/aarsregnskap/kopi/123456789/2025",
        content_sha256="a" * 64,
        retrieved_at="2026-10-01T00:00:00Z",
        effective_at="2025",
    )
    assert observation is None
    assert audit["status"] == "organisation_number_not_in_report_text"


def test_build_and_project_official_description() -> None:
    profile = _profile()
    observation, audit = build_annual_report_description_observation(
        profile,
        text=(
            "Organisasjonsnummer 123 456 789\n"
            "Virksomhetens art\n"
            "Selskapet utvikler og leverer programvare for energibransjen i Norge.\n"
            "Fortsatt drift\n"
        ),
        source_url="https://data.brreg.no/regnskapsregisteret/regnskap/aarsregnskap/kopi/123456789/2025",
        content_sha256="a" * 64,
        retrieved_at="2026-10-01T00:00:00Z",
        effective_at="2025",
    )
    assert audit["status"] == "accepted"
    assert observation is not None
    profile["external_observations"].append(observation)

    contract = {
        "organisation_number": "123456789",
        "claims": [],
        "evidence": [],
    }
    projected = project_annual_report_company_description(contract, profile)
    description_claims = [row for row in projected["claims"] if row.get("field") == "company_description"]
    assert len(description_claims) == 1
    assert description_claims[0]["availability"] == "available"
    assert description_claims[0]["effective_at"] == "2025"
    assert description_claims[0]["evidence_ids"]

    canonical = project_canonical_profile(projected)
    website_facts = canonical["canonical_profile"]["company_website"]
    assert any(row.get("type") == "company_description" for row in website_facts)


def test_verified_company_site_description_has_precedence() -> None:
    profile = _profile()
    profile["external_observations"] = [_observation()]
    contract = {
        "organisation_number": "123456789",
        "claims": [
            {
                "field": "company_description",
                "value": "Verified company-site description.",
                "availability": "available",
                "confidence": 0.95,
                "evidence_ids": ["ev-site"],
            }
        ],
        "evidence": [
            {
                "id": "ev-site",
                "source_url": "https://example.no/",
                "source_class": "company_owned",
                "retrieved_at": "2026-10-01T00:00:00Z",
                "content_sha256": "b" * 64,
                "claim_span": "Verified company-site description.",
            }
        ],
    }
    projected = project_annual_report_company_description(contract, profile)
    descriptions = [row for row in projected["claims"] if row.get("field") == "company_description"]
    assert len(descriptions) == 1
    assert descriptions[0]["value"] == "Verified company-site description."
