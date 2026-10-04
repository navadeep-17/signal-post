from __future__ import annotations

from copy import deepcopy

from norway_company_agent.canonical_projection import (
    project_canonical_profile,
    validate_canonical_projection,
)
from norway_company_agent.official import normalize_entity
from norway_company_agent.v2_registry_projection import (
    MANAGED_FIELDS,
    SOURCE_PATHS,
    project_v2_registry_claims,
)


ORG = "912345678"
LIVE_URL = f"https://data.brreg.no/enhetsregisteret/api/enheter/{ORG}"


def _raw_entity() -> dict:
    return {
        "organisasjonsnummer": ORG,
        "navn": "EXAMPLE AS",
        "organisasjonsform": {"kode": "AS"},
        "stiftelsesdato": "2012-03-04",
        "registrertIForetaksregisteret": True,
        "registreringsdatoForetaksregisteret": "2012-04-05",
        "institusjonellSektorkode": {
            "kode": "2100",
            "beskrivelse": "Private aksjeselskaper mv.",
        },
        "kapital": {
            "belop": 30000,
            "antallAksjer": 300,
            "type": "AKSJEKAPITAL",
            "bundet": False,
            "valuta": "NOK",
            "innbetalt": True,
            "fulltInnbetalt": True,
            "innfortDato": "2024-01-02",
            "unexpected": "must-not-project",
        },
        "registrertIMvaregisteret": False,
        "registreringsdatoMerverdiavgiftsregisteret": None,
    }


def _profile(value: dict | None = None) -> dict:
    return {
        "organisation_number": ORG,
        "name": "EXAMPLE AS",
        # Deliberately conflicting profile-level values prove the projector cannot fallback.
        "foundation_date": "1900-01-01",
        "registered_in_vat_register": True,
        "evidence": {
            "registry_live": {
                "status": "available",
                "source_url": LIVE_URL,
                "retrieved_at": "2026-10-04T11:30:00Z",
                "content_sha256": "a" * 64,
                "value": normalize_entity(_raw_entity()) if value is None else value,
            }
        },
    }


def _contract() -> dict:
    return {
        "organisation_number": ORG,
        "claims": [],
        "evidence": [],
    }


def _claims_by_field(projected: dict) -> dict[str, dict]:
    return {
        str(claim["field"]): claim
        for claim in projected.get("claims") or []
        if claim.get("field") in MANAGED_FIELDS
    }


def _evidence_by_id(projected: dict) -> dict[str, dict]:
    return {str(item["id"]): item for item in projected.get("evidence") or [] if item.get("id")}


def test_normalizer_retains_phasea2_exact_live_fields_losslessly() -> None:
    normalized = normalize_entity(_raw_entity())

    assert normalized["foundation_date"] == "2012-03-04"
    assert normalized["registered_in_enterprise_register"] is True
    assert normalized["enterprise_register_date"] == "2012-04-05"
    assert normalized["institutional_sector"] == {
        "kode": "2100",
        "beskrivelse": "Private aksjeselskaper mv.",
    }
    assert normalized["registered_capital"]["belop"] == 30000
    assert normalized["registered_capital"]["bundet"] is False
    assert normalized["registered_in_vat_register"] is False
    assert normalized["vat_registration_date"] is None


def test_phasea2_projects_exact_values_with_exact_source_paths() -> None:
    projected = project_v2_registry_claims(_contract(), _profile())
    claims = _claims_by_field(projected)
    evidence = _evidence_by_id(projected)

    expected = {
        "foundation_date": "2012-03-04",
        "registered_in_enterprise_register": True,
        "enterprise_register_date": "2012-04-05",
        "institutional_sector": {
            "code": "2100",
            "description": "Private aksjeselskaper mv.",
        },
        "registered_capital": {
            "belop": 30000,
            "antallAksjer": 300,
            "type": "AKSJEKAPITAL",
            "bundet": False,
            "valuta": "NOK",
            "innbetalt": True,
            "fulltInnbetalt": True,
            "innfortDato": "2024-01-02",
        },
        "registered_in_vat_register": False,
    }

    for field, value in expected.items():
        claim = claims[field]
        assert claim["availability"] == "available"
        assert claim["value"] == value
        assert claim["confidence"] == 1.0
        assert len(claim["evidence_ids"]) == 1
        item = evidence[claim["evidence_ids"][0]]
        assert item["source_url"] == LIVE_URL
        assert item["source_class"] == "official"
        assert item["source_field"] == SOURCE_PATHS[field]
        assert item["source_row_key"] == ORG
        assert item["content_sha256"] == "a" * 64

    vat_date = claims["vat_registration_date"]
    assert vat_date["availability"] == "not_available"
    assert vat_date["value"] is None
    vat_evidence = evidence[vat_date["evidence_ids"][0]]
    assert vat_evidence["source_field"] == "/registreringsdatoMerverdiavgiftsregisteret"


def test_false_registry_booleans_are_available_not_missing() -> None:
    value = normalize_entity(_raw_entity())
    value["registered_in_enterprise_register"] = False
    value["registered_in_vat_register"] = False
    projected = project_v2_registry_claims(_contract(), _profile(value))
    claims = _claims_by_field(projected)

    for field in ("registered_in_enterprise_register", "registered_in_vat_register"):
        assert claims[field]["availability"] == "available"
        assert claims[field]["value"] is False


def test_missing_live_fields_never_fallback_to_profile_values() -> None:
    value = normalize_entity(_raw_entity())
    value.pop("foundation_date", None)
    value.pop("registered_in_vat_register", None)

    projected = project_v2_registry_claims(_contract(), _profile(value))
    claims = _claims_by_field(projected)

    assert claims["foundation_date"]["availability"] == "not_available"
    assert claims["foundation_date"]["value"] is None
    assert claims["registered_in_vat_register"]["availability"] == "not_available"
    assert claims["registered_in_vat_register"]["value"] is None


def test_phasea2_projection_is_idempotent() -> None:
    once = project_v2_registry_claims(_contract(), _profile())
    twice = project_v2_registry_claims(deepcopy(once), _profile())

    once_managed = [claim for claim in once["claims"] if claim.get("field") in MANAGED_FIELDS]
    twice_managed = [claim for claim in twice["claims"] if claim.get("field") in MANAGED_FIELDS]
    assert twice_managed == once_managed
    assert twice["evidence"] == once["evidence"]


def test_phasea2_claims_are_exposed_as_company_canonical_facts() -> None:
    projected = project_v2_registry_claims(_contract(), _profile())
    canonical = project_canonical_profile(projected)
    facts = {fact["type"]: fact for fact in canonical["canonical_facts"]}

    expected_canonical_fields = {
        "foundation_date": "company.foundation_date",
        "registered_in_enterprise_register": "company.registered_in_enterprise_register",
        "enterprise_register_date": "company.enterprise_register_date",
        "institutional_sector": "company.institutional_sector",
        "registered_capital": "company.registered_capital",
        "registered_in_vat_register": "company.registered_in_vat_register",
        "vat_registration_date": "company.vat_registration_date",
    }
    for fact_type, canonical_field in expected_canonical_fields.items():
        assert facts[fact_type]["canonical_field"] == canonical_field
        assert facts[fact_type]["source_field"] == fact_type
        assert facts[fact_type] in canonical["canonical_profile"]["company_record"]

    assert facts["registered_in_vat_register"]["availability"] == "available"
    assert facts["registered_in_vat_register"]["value"] is False
    assert facts["vat_registration_date"]["availability"] == "not_available"
    assert facts["vat_registration_date"]["value"] is None
    assert validate_canonical_projection(canonical) == []
