from __future__ import annotations

from norway_company_agent.canonical_projection import project_canonical_profile, validate_canonical_projection
from norway_company_agent.v2_registry_projection import project_v2_registry_claims


def _profile(postal_address: dict | None) -> dict:
    return {
        "organisation_number": "912345678",
        "evidence": {
            "registry_live": {
                "status": "available",
                "source_url": "https://data.brreg.no/enhetsregisteret/api/enheter/912345678",
                "retrieved_at": "2026-10-04T10:00:00Z",
                "content_sha256": "a" * 64,
                "value": {
                    "industry": {"kode": "62.100", "beskrivelse": "Programmeringstjenester"},
                    "business_address": {
                        "adresse": ["Forretningsveien 1"],
                        "postnummer": "0101",
                        "poststed": "OSLO",
                        "kommune": "OSLO",
                        "kommunenummer": "0301",
                        "land": "Norge",
                        "landkode": "NO",
                    },
                    "postal_address": postal_address,
                    "bankrupt": False,
                    "liquidating": False,
                    "registration_date": "2020-01-02",
                    "registered_purpose": None,
                    "contact_email": None,
                    "contact_phone": None,
                    "contact_mobile": None,
                },
            }
        },
    }


def _contract() -> dict:
    return {
        "organisation_number": "912345678",
        "claims": [],
        "evidence": [],
    }


def _claim(projected: dict, field: str) -> dict:
    rows = [item for item in projected["claims"] if item.get("field") == field]
    assert len(rows) == 1
    return rows[0]


def test_projects_exact_distinct_postal_address_with_live_brreg_lineage() -> None:
    postal = {
        "adresse": ["Postboks 42"],
        "postnummer": "0150",
        "poststed": "OSLO",
        "kommune": "OSLO",
        "kommunenummer": "0301",
        "land": "Norge",
        "landkode": "NO",
    }
    projected = project_v2_registry_claims(_contract(), _profile(postal))

    business = _claim(projected, "registered_address")
    mailing = _claim(projected, "postal_address")
    assert business["availability"] == "available"
    assert mailing["availability"] == "available"
    assert business["value"] != mailing["value"]
    assert mailing["value"] == postal

    evidence_by_id = {item["id"]: item for item in projected["evidence"]}
    evidence = evidence_by_id[mailing["evidence_ids"][0]]
    assert evidence["source_field"] == "/postadresse"
    assert evidence["source_row_key"] == "912345678"
    assert evidence["source_url"].endswith("/912345678")
    assert evidence["content_sha256"] == "a" * 64
    assert "/postadresse=" in evidence["claim_span"]

    canonical = project_canonical_profile(projected)
    facts = [item for item in canonical["canonical_facts"] if item.get("type") == "postal_address"]
    assert len(facts) == 1
    assert facts[0]["canonical_field"] == "company.postal_address"
    assert facts[0]["source_field"] == "postal_address"
    assert facts[0]["value"] == postal
    assert validate_canonical_projection(canonical) == []


def test_missing_postal_address_is_not_available_and_never_falls_back_to_business_address() -> None:
    projected = project_v2_registry_claims(_contract(), _profile(None))
    business = _claim(projected, "registered_address")
    mailing = _claim(projected, "postal_address")

    assert business["availability"] == "available"
    assert mailing["availability"] == "not_available"
    assert mailing["value"] is None

    evidence_by_id = {item["id"]: item for item in projected["evidence"]}
    evidence = evidence_by_id[mailing["evidence_ids"][0]]
    assert evidence["source_field"] == "/postadresse"
    assert "not resolved" in evidence["claim_span"]


def test_postal_address_projection_is_idempotent() -> None:
    postal = {"adresse": ["Postboks 42"], "postnummer": "0150", "poststed": "OSLO"}
    profile = _profile(postal)
    once = project_v2_registry_claims(_contract(), profile)
    twice = project_v2_registry_claims(once, profile)

    once_claim = _claim(once, "postal_address")
    twice_claim = _claim(twice, "postal_address")
    assert twice_claim == once_claim

    evidence_ids = [
        item["id"]
        for item in twice["evidence"]
        if item.get("source_field") == "/postadresse"
    ]
    assert len(evidence_ids) == 1
