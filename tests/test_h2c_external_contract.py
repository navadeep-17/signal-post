from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.company_site_contact import attach_company_site_contact_email_observations  # noqa: E402
from norway_company_agent.external_contract import project_contact_email_observations  # noqa: E402
from norway_company_agent.output_contract import project_terminal_envelope, validate_contract_object  # noqa: E402


def _profile() -> dict:
    digest = "c" * 64
    source_url = "https://example.no/"
    return {
        "organisation_number": "912345678",
        "name": "EXAMPLE AS",
        "legal_form": "AS",
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
                    "identity_text_excerpt": "Kontakt oss på post@example.no",
                    "identity_assessment": {
                        "status": "exact",
                        "score": 1.0,
                        "publishable": True,
                        "method": "test_exact_identity",
                    },
                    "pages": [{"url": source_url, "content_sha256": digest}],
                },
            },
        },
        "run_metrics": {"requests": 4, "latencies_ms": [10, 20]},
    }


def _envelope(profile: dict) -> dict:
    return {
        "run_id": "h2c-test",
        "organisation_number": profile["organisation_number"],
        "state": "complete",
        "started_at": "2026-09-15T09:00:00Z",
        "completed_at": "2026-09-15T09:00:01Z",
        "profile": profile,
    }


def test_contract_projects_contact_email_with_exact_company_page_evidence() -> None:
    profile = attach_company_site_contact_email_observations(_profile())
    base = project_terminal_envelope(_envelope(profile))
    projected = project_contact_email_observations(base, profile)

    assert validate_contract_object(projected) == []
    claims = [claim for claim in projected["claims"] if claim["field"] == "external.contact_email"]
    assert len(claims) == 1
    assert claims[0]["value"] == "post@example.no"
    assert claims[0]["signal_type"] == "company_profile"
    assert "deliver" not in claims[0]["claim_scope"].lower()

    evidence_by_id = {item["id"]: item for item in projected["evidence"]}
    evidence = evidence_by_id[claims[0]["evidence_ids"][0]]
    assert evidence["source_url"] == "https://example.no/"
    assert evidence["content_sha256"] == "c" * 64
    assert "post@example.no" in evidence["claim_span"]


def test_contact_email_projection_is_idempotent() -> None:
    profile = attach_company_site_contact_email_observations(_profile())
    base = project_terminal_envelope(_envelope(profile))
    once = project_contact_email_observations(base, profile)
    twice = project_contact_email_observations(once, profile)

    once_claims = [claim for claim in once["claims"] if claim["field"] == "external.contact_email"]
    twice_claims = [claim for claim in twice["claims"] if claim["field"] == "external.contact_email"]
    assert twice_claims == once_claims
    assert len([item for item in twice["evidence"] if str(item["id"]).startswith("ev-external-")]) == 1


def test_contact_email_projection_does_not_remove_other_external_claims() -> None:
    profile = attach_company_site_contact_email_observations(_profile())
    base = project_terminal_envelope(_envelope(profile))
    base["claims"].append(
        {
            "field": "external.profile_handle",
            "value": "https://linkedin.com/company/example-as",
            "availability": "available",
            "confidence": 0.98,
            "evidence_ids": [],
        }
    )

    projected = project_contact_email_observations(base, profile)
    assert any(claim["field"] == "external.profile_handle" for claim in projected["claims"])
    assert any(claim["field"] == "external.contact_email" for claim in projected["claims"])
