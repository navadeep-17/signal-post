from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.canonical_projection import (
    project_canonical_profile,
    validate_canonical_projection,
)
from norway_company_agent.company_site_phone import (
    attach_company_site_contact_phone_observations,
)
from norway_company_agent.external_contract import project_contact_phone_observations
from norway_company_agent.output_contract import (
    project_terminal_envelope,
    validate_contract_object,
)


def _profile() -> dict:
    digest = "c" * 64
    source_url = "https://example.no/"
    return {
        "organisation_number": "912345678",
        "name": "EXAMPLE AS",
        "legal_form": "AS",
        "external_observations": [],
        "evidence": {
            "registry": {
                "status": "available",
                "source_type": "official_registry_bulk",
                "source_url": "https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv",
                "retrieved_at": "2026-09-15T09:00:00Z",
                "content_sha256": "d" * 64,
                "value": {},
            },
            "website": {
                "status": "available",
                "source_type": "registry_linked_company_website",
                "source_url": source_url,
                "retrieved_at": "2026-09-15T09:00:00Z",
                "content_sha256": digest,
                "value": {
                    "final_url": source_url,
                    "content_sha256": digest,
                    "identity_assessment": {
                        "status": "exact",
                        "score": 1.0,
                        "publishable": True,
                        "method": "test_exact_identity",
                    },
                    "structured_organisations": [
                        {
                            "@type": "Organization",
                            "name": "EXAMPLE AS",
                            "telephone": "+47 98 76 54 32",
                        }
                    ],
                    "pages": [{"url": source_url, "content_sha256": digest}],
                },
            },
        },
        "run_metrics": {"requests": 4, "latencies_ms": [10, 20]},
    }


def _envelope(profile: dict) -> dict:
    return {
        "run_id": "phone-test",
        "organisation_number": profile["organisation_number"],
        "state": "complete",
        "started_at": "2026-09-15T09:00:00Z",
        "completed_at": "2026-09-15T09:00:01Z",
        "profile": profile,
    }


def test_contract_projects_structured_contact_phone() -> None:
    profile = attach_company_site_contact_phone_observations(_profile())
    base = project_terminal_envelope(_envelope(profile))
    projected = project_contact_phone_observations(base, profile)

    assert validate_contract_object(projected) == []
    claims = [
        claim for claim in projected["claims"]
        if claim["field"] == "external.contact_phone"
    ]
    assert len(claims) == 1
    assert claims[0]["value"] == "+4798765432"
    assert claims[0]["signal_type"] == "company_profile"

    evidence_by_id = {item["id"]: item for item in projected["evidence"]}
    evidence = evidence_by_id[claims[0]["evidence_ids"][0]]
    assert evidence["source_url"] == "https://example.no/"
    assert evidence["content_sha256"] == "c" * 64
    assert "+4798765432" in evidence["claim_span"]


def test_contact_phone_projection_is_idempotent() -> None:
    profile = attach_company_site_contact_phone_observations(_profile())
    base = project_terminal_envelope(_envelope(profile))
    once = project_contact_phone_observations(base, profile)
    twice = project_contact_phone_observations(once, profile)

    once_claims = [
        claim for claim in once["claims"]
        if claim["field"] == "external.contact_phone"
    ]
    twice_claims = [
        claim for claim in twice["claims"]
        if claim["field"] == "external.contact_phone"
    ]
    assert twice_claims == once_claims


def test_canonical_projection_exposes_contact_phone() -> None:
    profile = attach_company_site_contact_phone_observations(_profile())
    base = project_terminal_envelope(_envelope(profile))
    projected = project_contact_phone_observations(base, profile)
    canonical = project_canonical_profile(projected)

    assert validate_canonical_projection(canonical) == []
    facts = [
        fact for fact in canonical["canonical_facts"]
        if fact["type"] == "contact_phone"
    ]
    assert len(facts) == 1
    assert facts[0]["canonical_field"] == "website.contact_phone"
    assert facts[0]["value"] == "+4798765432"
    assert facts[0] in canonical["canonical_profile"]["company_website"]
