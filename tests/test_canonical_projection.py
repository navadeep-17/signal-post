from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.canonical_projection import (  # noqa: E402
    CANONICAL_SCHEMA_VERSION,
    project_canonical_profile,
    validate_canonical_projection,
)


def evidence(eid: str) -> dict:
    return {
        "id": eid,
        "source_url": f"https://example.test/{eid}",
        "source_class": "official",
        "retrieved_at": "2026-09-25T10:00:00Z",
        "content_sha256": "a" * 64,
        "claim_span": eid,
    }


def claim(field: str, value, eid: str, **extra) -> dict:
    return {
        "field": field,
        "value": value,
        "availability": "available",
        "confidence": 1.0,
        "evidence_ids": [eid],
        **extra,
    }


def contract() -> dict:
    claims = [
        claim("legal_name", "ACME AS", "ev-reg"),
        claim("legal_form", "AS", "ev-reg"),
        claim("municipality", "OSLO", "ev-reg"),
        claim("industry", {"kode": "62.100", "beskrivelse": "Programmeringstjenester"}, "ev-reg"),
        claim("employee_count", 12, "ev-reg"),
        claim("latest_submitted_accounts", "2025", "ev-reg"),
        claim(
            "financial.revenue",
            1000000,
            "ev-fin",
            currency="NOK",
            reporting_period={"fraDato": "2025-01-01", "tilDato": "2025-12-31"},
        ),
        claim(
            "financial.operating_result",
            120000,
            "ev-fin",
            currency="NOK",
            reporting_period={"fraDato": "2025-01-01", "tilDato": "2025-12-31"},
        ),
        claim(
            "roles",
            {
                "roles": [
                    {"name": "Ada Example", "role_code": "DAGL", "role": "Daglig leder", "inactive": False},
                    {"name": "Ola Example", "role_code": "LEDE", "role": "Styrets leder", "inactive": False},
                ]
            },
            "ev-role",
        ),
        claim(
            "locations",
            {
                "locations": [
                    {
                        "organisation_number": "999999991",
                        "name": "ACME AS AVD OSLO",
                        "address": {"adresse": ["Testveien 1"], "postnummer": "0001", "poststed": "OSLO"},
                        "employees": 8,
                    }
                ]
            },
            "ev-loc",
        ),
        claim("official_website", "https://acme.no/", "ev-web"),
        claim("company_description", "ACME builds software.", "ev-web"),
        claim(
            "external.profile_handle",
            "https://www.linkedin.com/company/acme",
            "ev-social",
            platform="linkedin",
            signal_type="profile_handle",
        ),
        claim("external.contact_email", "hello@acme.no", "ev-email", platform="company_site"),
        claim(
            "external.workforce_snapshot",
            {"measure": "full_time_equivalents", "value": 11, "scope": "company_phrase"},
            "ev-work",
            platform="brreg",
            signal_type="workforce_snapshot",
        ),
    ]
    ids = {eid for row in claims for eid in row["evidence_ids"]}
    return {
        "organisation_number": "923609016",
        "run": {"run_id": "v2-test", "started_at": "x", "completed_at": "y", "terminal_status": "completed"},
        "claims": claims,
        "evidence": [evidence(eid) for eid in sorted(ids)],
        "changes": [],
        "errors": [],
        "operations": {"requests": 10, "runtime_ms": 100, "third_party_cost_usd": 0.0},
    }


def facts_of_type(item: dict, fact_type: str) -> list[dict]:
    return [row for row in item["canonical_facts"] if row["type"] == fact_type]


def test_projection_flattens_official_people_locations_and_financials():
    projected = project_canonical_profile(contract())
    assert projected["canonical_profile"]["schema_version"] == CANONICAL_SCHEMA_VERSION
    assert facts_of_type(projected, "company_name")[0]["value"] == "ACME AS"
    assert facts_of_type(projected, "industry")[0]["value"] == {
        "code": "62.100",
        "description": "Programmeringstjenester",
    }
    assert len(facts_of_type(projected, "person_role")) == 2
    assert facts_of_type(projected, "person_role")[0]["value"]["role_code"] == "DAGL"
    assert len(facts_of_type(projected, "registered_location")) == 1
    revenue = facts_of_type(projected, "financial_revenue")[0]
    assert revenue["value"] == 1000000
    assert revenue["currency"] == "NOK"
    assert revenue["reporting_period"]["tilDato"] == "2025-12-31"


def test_projection_exposes_first_party_external_facts_without_platform_inference():
    projected = project_canonical_profile(contract())
    social = facts_of_type(projected, "social_profile")[0]
    assert social["platform"] == "linkedin"
    assert social["value"] == "https://www.linkedin.com/company/acme"
    assert facts_of_type(projected, "contact_email")[0]["value"] == "hello@acme.no"
    assert facts_of_type(projected, "workforce_snapshot")[0]["value"]["value"] == 11
    assert projected["canonical_profile"]["jobs"] == []
    assert projected["canonical_profile"]["public_activity"] == []
    assert projected["canonical_profile"]["data_areas"]["company_website"] is True
    assert projected["canonical_profile"]["data_areas"]["hiring_and_public_activity"] is False


def test_projection_reuses_existing_evidence_and_validates():
    original = contract()
    projected = project_canonical_profile(original)
    assert projected["claims"] == original["claims"]
    assert projected["evidence"] == original["evidence"]
    assert validate_canonical_projection(projected) == []
    existing = {row["id"] for row in projected["evidence"]}
    for fact in projected["canonical_facts"]:
        assert fact["evidence_ids"]
        assert set(fact["evidence_ids"]).issubset(existing)


def test_unavailable_scalar_remains_unavailable_and_never_becomes_zero():
    source = contract()
    source["claims"].append(
        {
            "field": "group_structure",
            "value": None,
            "availability": "not_available",
            "confidence": 1.0,
            "evidence_ids": ["ev-group"],
        }
    )
    source["evidence"].append(evidence("ev-group"))
    projected = project_canonical_profile(source)
    group = facts_of_type(projected, "group_structure")[0]
    assert group["availability"] == "not_available"
    assert group["value"] is None
    assert validate_canonical_projection(projected) == []
