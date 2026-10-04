from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.company_site_social import (  # noqa: E402
    attach_company_site_social_observations,
    company_site_social_observations,
)
from norway_company_agent.external_contract import project_profile_handle_observations  # noqa: E402
from norway_company_agent.external_footprint import publishable_observation, validate_observation  # noqa: E402


def _profile() -> dict:
    digest = "a" * 64
    source_url = "https://example.no/"
    return {
        "organisation_number": "912345678",
        "name": "EXAMPLE AS",
        "evidence": {
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
                    "pages": [
                        {
                            "url": source_url,
                            "content_sha256": digest,
                            "title": "Example AS",
                        }
                    ],
                    "social_link_assessments": [
                        {
                            "platform": "linkedin",
                            "url": "https://linkedin.com/company/example-as",
                            "identity_score": 0.98,
                            "publishable": True,
                            "matched_tokens": ["example"],
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
            }
        },
    }


def _c12_mtm_profile() -> dict:
    """Regression shape for Builderr C12 example organisation 811730912.

    The social handle is intentionally abbreviated so the old legal-name/handle heuristic
    rejects it. The exact company homepage declaration is the evidence being tested; this
    fixture does not hard-code a claim into production behavior.
    """
    digest = "c" * 64
    source_url = "https://www.mtm-skogservice.no/"
    return {
        "organisation_number": "811730912",
        "name": "MTM SKOGSERVICE AS",
        "evidence": {
            "website": {
                "status": "available",
                "source_type": "registry_linked_company_website",
                "source_url": source_url,
                "retrieved_at": "2026-10-04T05:00:00Z",
                "content_sha256": digest,
                "value": {
                    "final_url": source_url,
                    "content_sha256": digest,
                    "identity_assessment": {
                        "status": "exact",
                        "score": 1.0,
                        "publishable": True,
                        "method": "deterministic_name_org_evidence_v3",
                    },
                    "pages": [
                        {
                            "url": source_url,
                            "content_sha256": digest,
                            "title": "MTM Skogservice AS",
                        }
                    ],
                    "discovered_social_links": [
                        {"platform": "facebook", "url": "https://facebook.com/mtmbutikk"}
                    ],
                    "social_link_assessments": [
                        {
                            "platform": "facebook",
                            "url": "https://facebook.com/mtmbutikk",
                            "identity_score": 0.3,
                            "publishable": False,
                            "matched_tokens": [],
                            "method": "deterministic_social_handle_identity_v1",
                        }
                    ],
                    "structured_organisations": [],
                },
            }
        },
    }


def test_emits_only_publishable_handle_with_exact_company_page_provenance() -> None:
    observations = company_site_social_observations(_profile())
    assert len(observations) == 1
    item = observations[0]
    assert item["signal_type"] == "profile_handle"
    assert item["platform"] == "linkedin"
    assert item["profile_url"] == "https://linkedin.com/company/example-as"
    assert item["source_url"] == "https://example.no/"
    assert item["content_sha256"] == "a" * 64
    assert item["acquisition_mode"] == "permitted_public_page"
    assert item["rights_status"] == "approved"
    assert item["exact_entity"] is True
    assert "social-platform page/content was not fetched" in item["metrics"]["claim_scope"]
    assert validate_observation(item) == []
    assert publishable_observation(item) is True


def test_c12_exact_homepage_declaration_survives_weak_handle_name_match() -> None:
    observations = company_site_social_observations(_c12_mtm_profile())
    assert len(observations) == 1
    item = observations[0]
    assert item["organisation_number"] == "811730912"
    assert item["platform"] == "facebook"
    assert item["profile_url"] == "https://facebook.com/mtmbutikk"
    assert item["source_url"] == "https://www.mtm-skogservice.no/"
    assert item["strategy"] == "verified_company_homepage_declaration_c12_v1"
    assert item["metrics"]["network_requests_added"] == 0
    assert item["metrics"]["social_handle_name_match_required"] is False
    assert validate_observation(item) == []
    assert publishable_observation(item) is True


def test_c12_direct_declaration_becomes_material_external_profile_handle_claim() -> None:
    profile = attach_company_site_social_observations(_c12_mtm_profile())
    contract = {
        "organisation_number": "811730912",
        "claims": [],
        "evidence": [],
        "changes": [],
        "errors": [],
    }
    projected = project_profile_handle_observations(contract, profile)
    claims = [row for row in projected["claims"] if row.get("field") == "external.profile_handle"]
    assert len(claims) == 1
    assert claims[0]["value"] == "https://facebook.com/mtmbutikk"
    assert claims[0]["platform"] == "facebook"
    assert claims[0]["availability"] == "available"
    evidence = {row["id"]: row for row in projected["evidence"]}
    ev = evidence[claims[0]["evidence_ids"][0]]
    assert ev["source_url"] == "https://www.mtm-skogservice.no/"
    assert ev["content_sha256"] == "c" * 64


def test_direct_declaration_does_not_relax_non_exact_website_identity() -> None:
    profile = _c12_mtm_profile()
    profile["evidence"]["website"]["value"]["identity_assessment"]["publishable"] = False
    assert company_site_social_observations(profile) == []


def test_relaxed_declaration_rule_abstains_on_legacy_multi_page_snapshot() -> None:
    profile = _c12_mtm_profile()
    profile["evidence"]["website"]["value"]["pages"].append(
        {
            "url": "https://www.mtm-skogservice.no/kontakt",
            "content_sha256": "d" * 64,
            "title": "Kontakt",
        }
    )
    assert company_site_social_observations(profile) == []


def test_abstains_when_website_identity_is_not_publishable() -> None:
    profile = _profile()
    profile["evidence"]["website"]["value"]["identity_assessment"]["publishable"] = False
    assert company_site_social_observations(profile) == []


def test_abstains_when_snapshot_has_multiple_pages_without_per_link_provenance() -> None:
    profile = _profile()
    profile["evidence"]["website"]["value"]["pages"].append(
        {
            "url": "https://example.no/contact",
            "content_sha256": "b" * 64,
            "title": "Contact",
        }
    )
    assert company_site_social_observations(profile) == []


def test_abstains_when_source_hash_or_timestamp_is_missing_or_mismatched() -> None:
    missing_time = _profile()
    missing_time["evidence"]["website"]["retrieved_at"] = None
    assert company_site_social_observations(missing_time) == []

    invalid_hash = _profile()
    invalid_hash["evidence"]["website"]["value"]["content_sha256"] = "short"
    assert company_site_social_observations(invalid_hash) == []

    page_hash_mismatch = _profile()
    page_hash_mismatch["evidence"]["website"]["value"]["pages"][0]["content_sha256"] = "b" * 64
    assert company_site_social_observations(page_hash_mismatch) == []


def test_rejects_nested_social_hostname_artifact() -> None:
    profile = _c12_mtm_profile()
    profile["evidence"]["website"]["value"]["discovered_social_links"] = [
        {
            "platform": "instagram",
            "url": "https://instagram.com/nummerti/www.instagram.com/webnode_ag",
        }
    ]
    profile["evidence"]["website"]["value"]["social_link_assessments"] = []
    assert company_site_social_observations(profile) == []


def test_accepts_canonical_facebook_p_page_shape() -> None:
    profile = _profile()
    profile["evidence"]["website"]["value"]["social_link_assessments"] = [
        {
            "platform": "facebook",
            "url": "https://facebook.com/p/Example-AS-61555049420983",
            "identity_score": 0.98,
            "publishable": True,
            "matched_tokens": ["example"],
            "method": "deterministic_social_handle_identity_v1",
        }
    ]
    observations = company_site_social_observations(profile)
    assert len(observations) == 1
    assert observations[0]["profile_url"] == "https://facebook.com/p/Example-AS-61555049420983"


def test_attach_preserves_other_external_observations_and_is_idempotent() -> None:
    profile = _profile()
    profile["external_observations"] = [
        {
            "id": "future-other-observation",
            "organisation_number": "912345678",
            "platform": "company_site",
            "signal_type": "company_profile",
        }
    ]
    first = attach_company_site_social_observations(profile)
    second = attach_company_site_social_observations(deepcopy(first))
    ids_first = [item["id"] for item in first["external_observations"]]
    ids_second = [item["id"] for item in second["external_observations"]]
    assert ids_first == ids_second
    assert "future-other-observation" in ids_first
    assert sum(item.startswith("company-site-handle-") for item in ids_first) == 1


def test_does_not_treat_declared_profile_as_platform_activity_or_metrics() -> None:
    item = company_site_social_observations(_c12_mtm_profile())[0]
    assert item["signal_type"] == "profile_handle"
    assert "followers" not in item.get("metrics", {})
    assert "posts" not in item.get("metrics", {})
    assert "engagement" not in item.get("metrics", {})
    assert item.get("sentiment_label") is None
