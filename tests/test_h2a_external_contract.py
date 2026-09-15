from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.company_site_social import attach_company_site_social_observations  # noqa: E402
from norway_company_agent.external_contract import project_profile_handle_observations  # noqa: E402
from norway_company_agent.output_contract import project_terminal_envelope, validate_contract_object  # noqa: E402


def _profile(*, publish_handle: bool = True) -> dict:
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
                    "identity_assessment": {
                        "status": "exact",
                        "score": 1.0,
                        "publishable": True,
                        "method": "test_exact_identity",
                    },
                    "pages": [{"url": source_url, "content_sha256": digest}],
                    "social_links": [
                        {"platform": "linkedin", "url": "https://linkedin.com/company/example-as"},
                        {"platform": "facebook", "url": "https://facebook.com/unrelated-brand"},
                    ],
                    "social_link_assessments": [
                        {
                            "platform": "linkedin",
                            "url": "https://linkedin.com/company/example-as",
                            "identity_score": 0.98,
                            "publishable": publish_handle,
                            "matched_tokens": ["example"] if publish_handle else [],
                            "method": "deterministic_social_handle_identity_v1",
                        },
                        {
                            "platform": "facebook",
                            "url": "https://facebook.com/unrelated-brand",
                            "identity_score": 0.3,
                            "publishable": False,
                            "matched_tokens": [],
                            "method": "deterministic_social_handle_identity_v1",
                        },
                    ],
                },
            },
        },
        "run_metrics": {"requests": 4, "latencies_ms": [10, 20]},
    }


def _envelope(profile: dict) -> dict:
    return {
        "run_id": "h2a-test",
        "organisation_number": profile["organisation_number"],
        "state": "complete",
        "started_at": "2026-09-15T09:00:00Z",
        "completed_at": "2026-09-15T09:00:01Z",
        "profile": profile,
    }


def test_contract_replaces_raw_social_links_with_validated_handle_claims() -> None:
    profile = attach_company_site_social_observations(_profile())
    base = project_terminal_envelope(_envelope(profile))
    assert any(claim["field"] == "social_links" for claim in base["claims"])

    projected = project_profile_handle_observations(base, profile)
    assert validate_contract_object(projected) == []

    handle_claims = [claim for claim in projected["claims"] if claim["field"] == "external.profile_handle"]
    assert len(handle_claims) == 1
    assert handle_claims[0]["platform"] == "linkedin"
    assert handle_claims[0]["value"] == "https://linkedin.com/company/example-as"
    assert "unrelated-brand" not in str(projected["claims"])

    social_claim = next(claim for claim in projected["claims"] if claim["field"] == "social_links")
    assert social_claim["value"] == [
        {"platform": "linkedin", "url": "https://linkedin.com/company/example-as"}
    ]
    assert social_claim["claim_scope"].startswith("Only profile URLs")

    external_evidence = [entry for entry in projected["evidence"] if str(entry["id"]).startswith("ev-external-")]
    assert len(external_evidence) == 1
    assert external_evidence[0]["source_url"] == "https://example.no/"
    assert external_evidence[0]["content_sha256"] == "c" * 64


def test_contract_drops_legacy_raw_social_links_when_no_handle_passes() -> None:
    profile = attach_company_site_social_observations(_profile(publish_handle=False))
    assert profile["external_observations"] == []
    base = project_terminal_envelope(_envelope(profile))
    assert any(claim["field"] == "social_links" for claim in base["claims"])

    projected = project_profile_handle_observations(base, profile)
    assert validate_contract_object(projected) == []
    assert not any(claim["field"] == "social_links" for claim in projected["claims"])
    assert not any(claim["field"] == "external.profile_handle" for claim in projected["claims"])
    assert "unrelated-brand" not in str(projected["claims"])


def test_contract_keeps_company_page_as_evidence_source_not_social_platform() -> None:
    profile = attach_company_site_social_observations(_profile())
    projected = project_profile_handle_observations(project_terminal_envelope(_envelope(profile)), profile)
    claim = next(claim for claim in projected["claims"] if claim["field"] == "external.profile_handle")
    evidence_by_id = {item["id"]: item for item in projected["evidence"]}
    item = evidence_by_id[claim["evidence_ids"][0]]
    assert item["source_url"] == "https://example.no/"
    assert "linkedin.com" not in item["source_url"]
    assert "social-platform page/content was not fetched" in claim["claim_scope"]
