from __future__ import annotations

from copy import deepcopy

from norway_company_agent.company_site_social import (
    attach_company_site_social_observations,
    company_site_social_observations,
)
from norway_company_agent.external_footprint import publishable_observation, validate_observation


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
    profile = _profile()
    profile["evidence"]["website"]["value"]["social_link_assessments"] = [
        {
            "platform": "instagram",
            "url": "https://instagram.com/nummerti/www.instagram.com/webnode_ag",
            "identity_score": 0.98,
            "publishable": True,
            "matched_tokens": ["nummerti"],
            "method": "deterministic_social_handle_identity_v1",
        }
    ]
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
    item = company_site_social_observations(_profile())[0]
    assert item["signal_type"] == "profile_handle"
    assert "followers" not in item.get("metrics", {})
    assert "posts" not in item.get("metrics", {})
    assert "engagement" not in item.get("metrics", {})
    assert item.get("sentiment_label") is None
