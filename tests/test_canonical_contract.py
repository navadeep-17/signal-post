from __future__ import annotations

from norway_company_agent.canonical_contract import (
    CANONICAL_SCHEMA_VERSION,
    project_canonical_contract,
    validate_canonical_contract,
)


def _contract() -> dict:
    return {
        "organisation_number": "123456789",
        "claims": [
            {
                "field": "legal_name",
                "value": "Example AS",
                "availability": "available",
                "confidence": 1.0,
                "evidence_ids": ["ev-reg"],
            },
            {
                "field": "financial.revenue",
                "value": 1200000,
                "availability": "available",
                "confidence": 1.0,
                "evidence_ids": ["ev-accounts"],
                "currency": "NOK",
                "reporting_period": {"fraDato": "2025-01-01", "tilDato": "2025-12-31"},
            },
            {
                "field": "roles",
                "value": [
                    {"name": "Ada Example", "role": "daglig leder"},
                    {"name": "Ola Example", "role": "styreleder"},
                ],
                "availability": "available",
                "confidence": 1.0,
                "evidence_ids": ["ev-roles"],
            },
            {
                "field": "locations",
                "value": {"locations": [{"municipality": "OSLO"}, {"municipality": "BERGEN"}]},
                "availability": "available",
                "confidence": 1.0,
                "evidence_ids": ["ev-locations"],
            },
            {
                "field": "official_website",
                "value": "https://example.no/",
                "availability": "available",
                "confidence": 0.99,
                "evidence_ids": ["ev-site"],
            },
            {
                "field": "external.contact_email",
                "value": "post@example.no",
                "availability": "available",
                "confidence": 1.0,
                "evidence_ids": ["ev-contact"],
                "platform": "company_site",
            },
            {
                "field": "external.profile_handle",
                "value": "https://www.linkedin.com/company/example",
                "availability": "available",
                "confidence": 1.0,
                "evidence_ids": ["ev-social"],
                "platform": "linkedin",
                "claim_scope": "Declared by the exact verified company page; platform ownership/current activity not asserted.",
            },
            {
                "field": "external.workforce_snapshot",
                "value": {"measure": "full_time_equivalents", "value": 7, "scope": "company_phrase"},
                "availability": "available",
                "confidence": 1.0,
                "evidence_ids": ["ev-workforce"],
                "platform": "brreg",
            },
        ],
        "evidence": [
            {"id": value, "source_url": f"https://source.invalid/{value}", "retrieved_at": "2026-09-25T00:00:00Z", "claim_span": value}
            for value in (
                "ev-reg",
                "ev-accounts",
                "ev-roles",
                "ev-locations",
                "ev-site",
                "ev-contact",
                "ev-social",
                "ev-workforce",
            )
        ],
    }


def test_projection_exposes_canonical_company_accounts_and_external_facts() -> None:
    item = project_canonical_contract(_contract())
    canonical = item["canonical"]

    assert canonical["schema_version"] == CANONICAL_SCHEMA_VERSION
    assert canonical["company"]["legal_name"]["value"] == "Example AS"
    assert canonical["accounts"]["financials"]["revenue"][0]["value"] == 1200000
    assert canonical["accounts"]["financials"]["revenue"][0]["currency"] == "NOK"
    assert len(canonical["people"]) == 2
    assert len(canonical["locations"]) == 2
    assert canonical["web"]["official_website"]["value"] == "https://example.no/"
    assert canonical["web"]["contact_emails"][0]["value"] == "post@example.no"
    assert canonical["web"]["social_profiles"][0]["platform"] == "linkedin"
    assert canonical["workforce"][0]["value"]["value"] == 7
    assert canonical["hiring"] == []
    assert canonical["public_activity"] == []
    assert validate_canonical_contract(item) == []


def test_projection_never_turns_missing_claims_into_zero_or_hiring() -> None:
    contract = _contract()
    contract["claims"].append(
        {
            "field": "employee_count",
            "value": None,
            "availability": "not_available",
            "confidence": 1.0,
            "evidence_ids": ["ev-reg"],
        }
    )
    item = project_canonical_contract(contract)
    employee = item["canonical"]["company"]["employee_count"]

    assert employee["availability"] == "not_available"
    assert employee["value"] is None
    assert item["canonical"]["hiring"] == []


def test_canonical_facts_reuse_existing_evidence_ids_only() -> None:
    item = project_canonical_contract(_contract())
    original_ids = {e["id"] for e in item["evidence"]}
    projected_ids = {
        evidence_id
        for fact in item["canonical"]["facts"]
        for evidence_id in fact.get("evidence_ids") or []
    }
    assert projected_ids <= original_ids
