from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.canonical_contract import project_canonical_contract, validate_canonical_contract  # noqa: E402
from norway_company_agent.output_contract import validate_contract_object  # noqa: E402
from norway_company_agent.registry_live_contract import project_registry_live_claims  # noqa: E402


def _base_contract(*, existing_name: str | None = None) -> dict:
    claims = []
    evidence = []
    if existing_name is not None:
        claims.append(
            {
                "field": "legal_name",
                "value": existing_name,
                "availability": "available",
                "confidence": 1.0,
                "evidence_ids": ["ev-bulk"],
            }
        )
        evidence.append(
            {
                "id": "ev-bulk",
                "source_url": "https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv",
                "source_class": "official",
                "retrieved_at": "2026-09-25T00:00:00Z",
                "content_sha256": "bulkhash",
                "claim_span": f"legal_name={existing_name}",
            }
        )
    return {
        "organisation_number": "123456789",
        "run": {
            "run_id": "v2-test",
            "started_at": "2026-09-25T00:00:00Z",
            "completed_at": "2026-09-25T00:00:01Z",
            "terminal_status": "completed",
        },
        "claims": claims,
        "evidence": evidence,
        "changes": [],
        "errors": [],
        "operations": {"requests": 0, "runtime_ms": 1, "third_party_cost_usd": 0.0},
    }


def _profile() -> dict:
    return {
        "organisation_number": "123456789",
        "evidence": {
            "registry_live": {
                "status": "available",
                "source_url": "https://data.brreg.no/enhetsregisteret/api/enheter/123456789",
                "source_type": "official_registry_live",
                "retrieved_at": "2026-09-25T00:00:00Z",
                "content_sha256": "livehash",
                "value": {
                    "organisation_number": "123456789",
                    "name": "LIVE EXAMPLE AS",
                    "legal_form": "AS",
                    "employees": 12,
                    "bankrupt": False,
                    "liquidating": False,
                    "website": "https://unverified-example.no/",
                    "industry": {"kode": "62.010", "beskrivelse": "Programmeringstjenester"},
                    "business_address": {
                        "adresse": ["Testveien 1"],
                        "postnummer": "0123",
                        "poststed": "OSLO",
                        "kommune": "OSLO",
                        "kommunenummer": "0301",
                    },
                    "postal_address": {
                        "adresse": ["Postboks 1"],
                        "postnummer": "0101",
                        "poststed": "OSLO",
                    },
                    "latest_submitted_accounts": "2025",
                },
            }
        },
    }


def _claims_by_field(item: dict) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    for claim in item.get("claims") or []:
        result.setdefault(str(claim.get("field")), []).append(claim)
    return result


def test_live_registry_recovers_snapshot_drift_official_facts_without_network() -> None:
    projected = project_registry_live_claims(_base_contract(), _profile())
    claims = _claims_by_field(projected)

    assert claims["legal_name"][0]["value"] == "LIVE EXAMPLE AS"
    assert claims["legal_form"][0]["value"] == "AS"
    assert claims["employee_count"][0]["value"] == 12
    assert claims["municipality"][0]["value"] == "OSLO"
    assert claims["industry"][0]["value"] == {"code": "62.010", "label": "Programmeringstjenester"}
    assert claims["business_address"][0]["value"]["postnummer"] == "0123"
    assert claims["postal_address"][0]["value"]["postnummer"] == "0101"
    assert claims["bankrupt"][0]["value"] is False
    assert claims["liquidating"][0]["value"] is False
    assert claims["latest_submitted_accounts"][0]["value"] == "2025"

    assert "official_website" not in claims
    assert all(claim["claim_scope"].startswith("Exact live BRREG") for rows in claims.values() for claim in rows)
    assert validate_contract_object(projected) == []


def test_live_registry_never_overwrites_existing_available_bulk_fact() -> None:
    projected = project_registry_live_claims(_base_contract(existing_name="FROZEN EXAMPLE AS"), _profile())
    names = [claim for claim in projected["claims"] if claim.get("field") == "legal_name"]

    assert len(names) == 1
    assert names[0]["value"] == "FROZEN EXAMPLE AS"


def test_live_registry_website_is_not_promoted_without_identity_verification() -> None:
    projected = project_registry_live_claims(_base_contract(), _profile())
    fields = {claim.get("field") for claim in projected["claims"]}

    assert "official_website" not in fields
    assert "social_links" not in fields


def test_live_registry_facts_flow_into_canonical_projection_with_same_evidence() -> None:
    projected = project_registry_live_claims(_base_contract(), _profile())
    projected = project_canonical_contract(projected)
    canonical = projected["canonical"]

    assert canonical["company"]["legal_name"]["value"] == "LIVE EXAMPLE AS"
    assert canonical["company"]["industry"]["value"]["code"] == "62.010"
    assert canonical["company"]["business_address"]["value"]["kommune"] == "OSLO"
    assert canonical["company"]["bankrupt"]["value"] is False
    assert canonical["accounts"]["latest_submitted"]["value"] == "2025"
    assert validate_canonical_contract(projected) == []

    canonical_ids = {
        evidence_id
        for fact in canonical["facts"]
        for evidence_id in fact.get("evidence_ids") or []
    }
    source_ids = {entry["id"] for entry in projected["evidence"]}
    assert canonical_ids <= source_ids


def test_unavailable_live_registry_adds_nothing() -> None:
    profile = _profile()
    profile["evidence"]["registry_live"]["status"] = "source_error"
    projected = project_registry_live_claims(_base_contract(), profile)
    assert projected["claims"] == []
    assert projected["evidence"] == []
