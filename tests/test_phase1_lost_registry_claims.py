from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.canonical_projection import (  # noqa: E402
    project_canonical_profile,
    validate_canonical_projection,
)
from norway_company_agent.official import normalize_entity  # noqa: E402
from norway_company_agent.output_contract import project_terminal_envelope, validate_contract_object  # noqa: E402
from norway_company_agent.v2_registry_projection import project_v2_registry_claims  # noqa: E402


ORG = "923609016"
LIVE_URL = f"https://data.brreg.no/enhetsregisteret/api/enheter/{ORG}"


def _raw_live_body() -> dict:
    return {
        "organisasjonsnummer": ORG,
        "navn": "ACME AS",
        "organisasjonsform": {"kode": "AS"},
        "antallAnsatte": 12,
        "konkurs": False,
        "underAvvikling": False,
        "hjemmeside": "https://acme.no",
        "naeringskode1": {"kode": "62.100", "beskrivelse": "Programmeringstjenester"},
        "forretningsadresse": {
            "adresse": ["Testgata 1"],
            "postnummer": "0123",
            "poststed": "OSLO",
            "kommune": "OSLO",
            "kommunenummer": "0301",
            "land": "Norge",
            "landkode": "NO",
        },
        "postadresse": {"postnummer": "0123", "poststed": "OSLO"},
        "sisteInnsendteAarsregnskap": "2025",
        "registreringsdatoEnhetsregisteret": "2019-08-22",
        "aktivitet": "Utvikling og salg av programvare.",
        "vedtektsfestetFormaal": "Utvikle og selge programvare og beslektede tjenester.",
        "epostadresse": "post@acme.no",
        "telefon": "22112211",
        "mobil": "91122334",
    }


def _profile() -> dict:
    normalized = normalize_entity(_raw_live_body())
    return {
        "organisation_number": ORG,
        "name": "ACME AS",
        "legal_form": "AS",
        "employees": 12,
        "municipality": "OSLO",
        "municipality_number": "0301",
        "industry_code": "62.100",
        "industry_label": "Programmeringstjenester",
        "bankrupt": False,
        "liquidating": False,
        "latest_submitted_accounts": "2025",
        "evidence": {
            "registry": {
                "status": "available",
                "source_type": "official_registry_bulk",
                "source_url": "https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv",
                "retrieved_at": "2026-10-04T06:00:00Z",
                "content_sha256": "a" * 64,
                "source_row_key": ORG,
                "value": {"organisasjonsnummer": ORG},
            },
            "registry_live": {
                "status": "available",
                "source_type": "official_registry_live",
                "source_url": LIVE_URL,
                "retrieved_at": "2026-10-04T06:01:00Z",
                "content_sha256": "b" * 64,
                "value": normalized,
            },
        },
        "run_metrics": {"requests": 0, "latencies_ms": [], "third_party_cost_usd": 0.0},
    }


def _base_contract(profile: dict) -> dict:
    return project_terminal_envelope(
        {
            "run_id": "phase1-lost-registry-claims-test",
            "organisation_number": ORG,
            "state": "complete",
            "started_at": "2026-10-04T06:00:00Z",
            "completed_at": "2026-10-04T06:01:00Z",
            "profile": profile,
        }
    )


def _project(profile: dict | None = None) -> dict:
    profile = profile or _profile()
    contract = project_v2_registry_claims(_base_contract(profile), profile)
    return project_canonical_profile(contract)


def _claims(item: dict) -> dict[str, dict]:
    return {str(claim["field"]): claim for claim in item["claims"]}


def _facts(item: dict) -> dict[str, dict]:
    return {str(fact["canonical_field"]): fact for fact in item["canonical_facts"]}


def test_normalize_entity_retains_evaluator_relevant_live_fields() -> None:
    value = normalize_entity(_raw_live_body())
    assert value["registration_date"] == "2019-08-22"
    assert value["activity"] == "Utvikling og salg av programvare."
    assert value["registered_purpose"].startswith("Utvikle og selge")
    assert value["contact_email"] == "post@acme.no"
    assert value["contact_phone"] == "22112211"
    assert value["contact_mobile"] == "91122334"


def test_exact_live_lost_fields_reach_claims_with_exact_paths() -> None:
    item = _project()
    assert validate_contract_object(item) == []
    claims = _claims(item)

    assert claims["registration_date"]["value"] == "2019-08-22"
    assert claims["registered_address"]["value"]["adresse"] == ["Testgata 1"]
    assert claims["registered_contact_email"]["value"] == "post@acme.no"
    assert claims["registered_phone"]["value"] == "22112211"
    assert claims["registered_mobile"]["value"] == "91122334"
    assert claims["company_description"]["value"] == "Utvikling og salg av programvare."
    assert claims["registered_purpose"]["value"].startswith("Utvikle og selge")

    expected_paths = {
        "registration_date": "/registreringsdatoEnhetsregisteret",
        "registered_address": "/forretningsadresse",
        "registered_contact_email": "/epostadresse",
        "registered_phone": "/telefon",
        "registered_mobile": "/mobil",
        "company_description": "/aktivitet",
        "registered_purpose": "/vedtektsfestetFormaal",
    }
    evidence = {row["id"]: row for row in item["evidence"]}
    for field, source_field in expected_paths.items():
        claim = claims[field]
        row = evidence[claim["evidence_ids"][0]]
        assert row["source_field"] == source_field
        assert row["source_url"] == LIVE_URL
        assert row["source_row_key"] == ORG


def test_lost_registry_claims_are_explicit_canonical_company_facts() -> None:
    item = _project()
    assert validate_canonical_projection(item) == []
    facts = _facts(item)

    assert facts["company.registration_date"]["value"] == "2019-08-22"
    assert facts["company.registered_address"]["value"]["kommunenummer"] == "0301"
    assert facts["company.registered_purpose"]["value"].startswith("Utvikle og selge")
    assert facts["company.contact.email"]["value"] == "post@acme.no"
    assert facts["company.contact.phone"]["value"] == "22112211"
    assert facts["company.contact.mobile"]["value"] == "91122334"
    assert facts["website.description"]["value"] == "Utvikling og salg av programvare."
    for field in (
        "company.registration_date",
        "company.registered_address",
        "company.registered_purpose",
        "company.contact.email",
        "company.contact.phone",
        "company.contact.mobile",
        "website.description",
    ):
        assert facts[field]["evidence_ids"]


def test_missing_live_values_fail_closed_without_bulk_fallback() -> None:
    profile = deepcopy(_profile())
    live = profile["evidence"]["registry_live"]["value"]
    live["registration_date"] = None
    live["business_address"] = None
    live["activity"] = None
    live["registered_purpose"] = None
    live["contact_email"] = None
    live["contact_phone"] = None
    live["contact_mobile"] = None
    profile["registration_date"] = "1999-01-01"
    profile["registered_address"] = {"adresse": ["Wrong bulk address"]}
    profile["contact_email"] = "wrong@example.com"

    item = _project(profile)
    claims = _claims(item)

    for field in (
        "registration_date",
        "registered_address",
        "registered_contact_email",
        "registered_phone",
        "registered_mobile",
    ):
        assert claims[field]["availability"] == "not_available"
        assert claims[field]["value"] is None
    assert "registered_purpose" not in claims
    assert not any(
        claim.get("signal_type") == "official_registry_narrative_projection"
        and claim.get("field") == "company_description"
        for claim in item["claims"]
    )


def test_projection_is_idempotent_for_new_live_fields() -> None:
    profile = _profile()
    once = project_v2_registry_claims(_base_contract(profile), profile)
    twice = project_v2_registry_claims(once, profile)
    assert twice == once
