from __future__ import annotations

from copy import deepcopy

from norway_company_agent.first_party_activity_provenance import (
    project_first_party_activity_provenance,
)
from norway_company_agent.first_party_feed_contract import project_first_party_feed_updates


ORG = "885588522"
WEBSITE = "https://www.hemsedalmobler.no/"
IDENTITY_PROOF = {
    "status": "exact",
    "score": 0.95,
    "publishable": True,
    "method": "deterministic_name_org_evidence_v4",
}


def _contract(*, field: str = "external.company_update", source_url: str | None = None) -> dict:
    if field == "external.company_update":
        value = {
            "title": "Garderobe – Hemsedal Møbler AS",
            "url": "https://www.hemsedalmobler.no/garderobe/",
            "published_date": "2026-04-05",
        }
        signal_type = "company_update"
        effective_at = "2026-04-05"
    else:
        value = {
            "title": "Møbelsnekker",
            "url": "https://www.hemsedalmobler.no/jobb/mobelsnekker/",
            "deadline": "2026-11-01",
        }
        signal_type = "job_posting"
        effective_at = None

    activity_evidence = {
        "id": "ev-first-party-legacy123",
        "source_url": source_url or value["url"],
        "source_class": "company_owned",
        "retrieved_at": "2026-10-05T17:22:34Z",
        "content_sha256": "9" * 64,
        "claim_span": "specific retained first-party detail page",
    }
    if effective_at is not None:
        activity_evidence["effective_at"] = effective_at

    return {
        "organisation_number": ORG,
        "claims": [
            {
                "field": "official_website",
                "value": WEBSITE,
                "availability": "available",
                "confidence": 0.95,
                "evidence_ids": ["ev-website"],
            },
            {
                "field": field,
                "value": value,
                "availability": "available",
                "confidence": 0.99,
                "evidence_ids": ["ev-first-party-legacy123"],
                "platform": "company_site",
                "signal_type": signal_type,
                "claim_scope": "strict first-party detail page",
            },
        ],
        "evidence": [
            {
                "id": "ev-website",
                "source_url": WEBSITE,
                "source_class": "company_owned",
                "retrieved_at": "2026-10-05T17:22:30Z",
                "content_sha256": "8" * 64,
                "claim_span": "Verified company website",
                "identity_proof": deepcopy(IDENTITY_PROOF),
                "extraction_method": "deterministic_name_org_evidence_v4",
            },
            activity_evidence,
        ],
        "changes": [],
        "errors": [],
    }


def _evidence(result: dict, evidence_id: str = "ev-first-party-legacy123") -> dict:
    return next(item for item in result["evidence"] if item.get("id") == evidence_id)


def test_backfills_legacy_page_update_without_changing_claims() -> None:
    contract = _contract()
    claims_before = deepcopy(contract["claims"])
    result = project_first_party_activity_provenance(contract)

    assert result["claims"] == claims_before
    row = _evidence(result)
    assert row["identity_proof"] == IDENTITY_PROOF
    assert row["extraction_method"] == "verified_same_site_dated_detail_page_v1"


def test_backfills_legacy_page_job_with_job_specific_method() -> None:
    result = project_first_party_activity_provenance(_contract(field="external.job_posting"))
    row = _evidence(result)
    assert row["identity_proof"] == IDENTITY_PROOF
    assert row["extraction_method"] == "verified_same_site_job_detail_page_v1"


def test_cross_domain_legacy_evidence_does_not_inherit_company_identity() -> None:
    result = project_first_party_activity_provenance(
        _contract(source_url="https://recruiter.example/jobs/mobelsnekker")
    )
    row = _evidence(result)
    assert "identity_proof" not in row
    assert "extraction_method" not in row


def test_invalid_hash_or_wrong_effective_date_abstains() -> None:
    invalid_hash = _contract()
    _evidence(invalid_hash)["content_sha256"] = "bad"
    result = project_first_party_activity_provenance(invalid_hash)
    assert "identity_proof" not in _evidence(result)

    wrong_date = _contract()
    _evidence(wrong_date)["effective_at"] = "2026-04-06"
    result = project_first_party_activity_provenance(wrong_date)
    assert "identity_proof" not in _evidence(result)


def test_feed_evidence_is_not_relabelled_as_legacy_detail_page() -> None:
    contract = _contract()
    activity = _evidence(contract)
    activity["id"] = "ev-first-party-feed-123"
    contract["claims"][1]["evidence_ids"] = ["ev-first-party-feed-123"]
    result = project_first_party_activity_provenance(contract)
    row = _evidence(result, "ev-first-party-feed-123")
    assert "identity_proof" not in row
    assert "extraction_method" not in row


def test_existing_provenance_is_never_overwritten_and_pass_is_idempotent() -> None:
    contract = _contract()
    row = _evidence(contract)
    row["identity_proof"] = {"status": "existing"}
    row["extraction_method"] = "existing_method"

    once = project_first_party_activity_provenance(contract)
    twice = project_first_party_activity_provenance(once)
    assert once == twice
    row = _evidence(twice)
    assert row["identity_proof"] == {"status": "existing"}
    assert row["extraction_method"] == "existing_method"


def test_v8_feed_postprojection_backfills_legacy_rows_even_without_feed() -> None:
    contract = _contract()
    profile = {"organisation_number": ORG, "evidence": {}}
    result = project_first_party_feed_updates(contract, profile)
    row = _evidence(result)
    assert row["identity_proof"] == IDENTITY_PROOF
    assert row["extraction_method"] == "verified_same_site_dated_detail_page_v1"
