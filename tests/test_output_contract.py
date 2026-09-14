from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.output_contract import (  # noqa: E402
    ALLOWED_AVAILABILITY,
    project_terminal_envelope,
    validate_contract_object,
)


def record(field, status="available", value=None, source_type="official_registry_bulk", note=None):
    return {
        "field": field,
        "status": status,
        "source_type": source_type,
        "source_class": source_type,
        "source_url": f"https://example.test/{field}",
        "retrieved_at": "2026-09-14T12:00:00Z",
        "value": value,
        "as_of": None,
        "note": note,
        "content_sha256": "a" * 64,
        "source_row_key": "923609016",
        "effective_at": None,
    }


def envelope():
    website_value = {
        "final_url": "https://acme.no/",
        "description": "ACME builds reliable systems.",
        "social_links": [{"platform": "linkedin", "url": "https://linkedin.com/company/acme"}],
        "identity_assessment": {"status": "exact", "score": 0.99, "publishable": True},
    }
    financial_value = {
        "records": [
            {
                "period": {"fraDato": "2025-01-01", "tilDato": "2025-12-31"},
                "currency": "NOK",
                "revenue": 0,
                "operating_result": 125000,
                "profit_before_tax": None,
                "annual_result": 100000,
                "assets": 500000,
                "equity": 250000,
                "debt": 250000,
            }
        ]
    }
    profile = {
        "organisation_number": "923609016",
        "name": "ACME NORGE AS",
        "legal_form": "AS",
        "employees": 0,
        "municipality": "OSLO",
        "industry": {"kode": "62.010", "beskrivelse": "Programmeringstjenester"},
        "latest_submitted_accounts": "2025",
        "run_metrics": {"requests": 7, "bytes": 1234, "latencies_ms": [100, 200]},
        "evidence": {
            "registry": record("registry", value={"navn": "ACME NORGE AS"}),
            "website": record(
                "website",
                value=website_value,
                source_type="registry_linked_company_website",
            ),
            "financials": record("financials", value=financial_value, source_type="official_annual_accounts"),
            "roles": record("roles", value={"roles": [{"name": "Ada", "role_code": "DAGL"}]}, source_type="official_roles"),
            "locations": record("locations", value={"locations": []}, source_type="official_subunits"),
            "group": record("group", status="not_found", source_type="official_group_structure"),
            "accounting_obligation": record("accounting_obligation", value={"classification": "required_by_legal_form"}, source_type="official_rule_interpretation"),
        },
    }
    return {
        "run_id": "test-run",
        "organisation_number": "923609016",
        "state": "complete",
        "started_at": "2026-09-14T12:00:00Z",
        "completed_at": "2026-09-14T12:00:08Z",
        "modules": {},
        "profile": profile,
    }


def claim(item, field):
    matches = [entry for entry in item["claims"] if entry["field"] == field]
    assert matches, field
    return matches[0]


def evidence_for_claim(item, field):
    item_claim = claim(item, field)
    evidence = {entry["id"]: entry for entry in item["evidence"]}
    assert len(item_claim["evidence_ids"]) == 1
    return evidence[item_claim["evidence_ids"][0]]


def test_projection_matches_required_top_level_shape_and_validates():
    item = project_terminal_envelope(envelope())
    assert set(item) == {"organisation_number", "run", "claims", "evidence", "changes", "errors", "operations"}
    assert item["organisation_number"] == "923609016"
    assert item["run"]["terminal_status"] == "completed"
    assert item["operations"]["requests"] == 7
    assert item["operations"]["runtime_ms"] == 300
    assert item["operations"]["third_party_cost_usd"] == 0.0
    assert validate_contract_object(item) == []


def test_available_zero_values_are_preserved_not_treated_as_missing():
    item = project_terminal_envelope(envelope())
    assert claim(item, "employee_count")["value"] == 0
    revenue = claim(item, "financial.revenue")
    assert revenue["value"] == 0
    assert revenue["availability"] == "available"
    assert revenue["currency"] == "NOK"
    assert revenue["reporting_period"] == {"fraDato": "2025-01-01", "tilDato": "2025-12-31"}


def test_not_found_is_not_available_and_never_silently_zero():
    item = project_terminal_envelope(envelope())
    group = claim(item, "group_structure")
    assert group["availability"] == "not_available"
    assert group["value"] is None


def test_unverified_website_is_ambiguous_not_available():
    source = envelope()
    source["profile"]["evidence"]["website"]["value"]["identity_assessment"] = {
        "status": "review",
        "score": 0.84,
        "publishable": False,
    }
    item = project_terminal_envelope(source)
    website = claim(item, "official_website")
    assert website["availability"] == "ambiguous"
    assert website["value"] is None
    assert not [entry for entry in item["claims"] if entry["field"] == "company_description"]


def test_blocked_failed_and_not_fetched_remain_distinct_in_errors():
    source = envelope()
    source["profile"]["evidence"]["website"] = record(
        "website", status="blocked", source_type="registry_linked_company_website", note="robots.txt disallows page"
    )
    source["profile"]["evidence"]["financial_history"] = record(
        "financial_history", status="not_fetched", source_type="official_annual_account_copies", note="not requested"
    )
    source["profile"]["evidence"]["roles"] = record(
        "roles", status="source_error", source_type="official_roles", note="HTTP 503"
    )
    item = project_terminal_envelope(source)
    assert claim(item, "official_website")["availability"] == "blocked"
    assert claim(item, "roles")["availability"] == "failed"
    states = {(error["module"], error["status"]) for error in item["errors"]}
    assert ("website", "blocked") in states
    assert ("financial_history", "not_fetched") in states
    assert ("roles", "source_error") in states


def test_every_available_claim_has_existing_evidence_with_source_and_time():
    item = project_terminal_envelope(envelope())
    evidence = {entry["id"]: entry for entry in item["evidence"]}
    for item_claim in item["claims"]:
        assert item_claim["availability"] in ALLOWED_AVAILABILITY
        if item_claim["availability"] == "available":
            assert item_claim["evidence_ids"]
            for evidence_id in item_claim["evidence_ids"]:
                assert evidence_id in evidence
                assert evidence[evidence_id]["source_url"]
                assert evidence[evidence_id]["retrieved_at"]
                assert evidence[evidence_id]["claim_span"]


def test_claims_from_same_source_keep_distinct_claim_level_evidence_spans():
    item = project_terminal_envelope(envelope())
    legal_name = evidence_for_claim(item, "legal_name")
    employees = evidence_for_claim(item, "employee_count")
    revenue = evidence_for_claim(item, "financial.revenue")
    operating = evidence_for_claim(item, "financial.operating_result")
    assert legal_name["id"] != employees["id"]
    assert legal_name["claim_span"] == "legal_name=ACME NORGE AS"
    assert employees["claim_span"] == "employee_count=0"
    assert revenue["id"] != operating["id"]
    assert "revenue=0" in revenue["claim_span"]
    assert "operating_result=125000" in operating["claim_span"]


def test_financial_none_is_omitted_but_zero_is_preserved():
    item = project_terminal_envelope(envelope())
    fields = [entry["field"] for entry in item["claims"]]
    assert "financial.profit_before_tax" not in fields
    assert "financial.revenue" in fields
