from __future__ import annotations

from norway_company_agent.canonical_projection import project_canonical_profile, validate_canonical_projection
from norway_company_agent.registry_contact import project_registry_contact_email, registered_contact_email
from norway_company_agent.v2_registry_projection import project_v2_registry_claims


def profile(email: str = "post@example.no") -> dict:
    return {
        "organisation_number": "123456789",
        "name": "EXAMPLE AS",
        "evidence": {
            "registry": {
                "status": "available",
                "source_url": "https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv",
                "retrieved_at": "2026-10-02T00:00:00Z",
                "content_sha256": "a" * 64,
                "source_row_key": "123456789",
                "value": {"epostadresse": email},
            }
        },
    }


def contract() -> dict:
    return {
        "organisation_number": "123456789",
        "claims": [],
        "evidence": [],
        "changes": [],
        "errors": [],
    }


def test_exact_org_registry_email_projects_with_narrow_semantics():
    out = project_registry_contact_email(contract(), profile("Info@Example.no"))
    claims = [item for item in out["claims"] if item.get("field") == "external.contact_email"]
    assert len(claims) == 1
    assert claims[0]["value"] == "info@example.no"
    assert claims[0]["confidence"] == 1.0
    assert claims[0]["platform"] == "brreg_registry"
    assert claims[0]["signal_type"] == "official_registry_contact"
    assert "does not assert website-domain ownership" in claims[0]["claim_scope"]
    evidence = {item["id"]: item for item in out["evidence"]}
    ev = evidence[claims[0]["evidence_ids"][0]]
    assert ev["source_class"] == "official"
    assert ev["source_row_key"] == "123456789"
    assert ev["claim_span"] == "epostadresse=info@example.no"


def test_existing_first_party_contact_has_precedence():
    c = contract()
    c["claims"].append(
        {
            "field": "external.contact_email",
            "value": "hello@example.no",
            "availability": "available",
            "confidence": 0.99,
            "evidence_ids": ["ev-site"],
            "platform": "company_site",
            "signal_type": "company_profile",
        }
    )
    c["evidence"].append(
        {
            "id": "ev-site",
            "source_url": "https://example.no/",
            "source_class": "company_owned",
            "retrieved_at": "2026-10-02T00:00:00Z",
            "content_sha256": "b" * 64,
            "claim_span": "hello@example.no",
        }
    )
    out = project_registry_contact_email(c, profile("registry@example.no"))
    contacts = [item for item in out["claims"] if item.get("field") == "external.contact_email"]
    assert [item["value"] for item in contacts] == ["hello@example.no"]
    assert not any(item.get("signal_type") == "official_registry_contact" for item in contacts)


def test_wrong_registry_row_never_projects():
    p = profile()
    p["evidence"]["registry"]["source_row_key"] = "987654321"
    assert registered_contact_email(p) == ""
    assert project_registry_contact_email(contract(), p)["claims"] == []


def test_non_brreg_source_never_projects():
    p = profile()
    p["evidence"]["registry"]["source_url"] = "https://example.org/data.csv"
    assert registered_contact_email(p) == ""


def test_malformed_email_abstains():
    for value in ("", "not-an-email", "two@example.no second@example.no", "a@localhost", "x @ example.no"):
        assert registered_contact_email(profile(value)) == ""


def test_projector_is_idempotent():
    once = project_registry_contact_email(contract(), profile())
    twice = project_registry_contact_email(once, profile())
    contacts = [item for item in twice["claims"] if item.get("field") == "external.contact_email"]
    assert len(contacts) == 1
    assert len(twice["evidence"]) == 1
    assert once == twice


def test_registry_contact_flows_through_existing_canonical_contact_type():
    projected = project_registry_contact_email(contract(), profile())
    canonical = project_canonical_profile(projected)
    facts = [item for item in canonical["canonical_facts"] if item.get("type") == "contact_email"]
    assert len(facts) == 1
    assert facts[0]["value"] == "post@example.no"
    assert facts[0]["platform"] == "brreg_registry"
    assert facts[0]["signal_type"] == "official_registry_contact"
    assert validate_canonical_projection(canonical) == []


def test_v2_registry_projection_invokes_registered_contact_fallback():
    projected = project_v2_registry_claims(contract(), profile("registry@example.no"))
    contacts = [item for item in projected["claims"] if item.get("field") == "external.contact_email"]
    assert len(contacts) == 1
    assert contacts[0]["value"] == "registry@example.no"
    assert contacts[0]["signal_type"] == "official_registry_contact"
