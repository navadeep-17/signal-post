from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.external_footprint import publishable_observation, validate_observation  # noqa: E402
from norway_company_agent.homepage_social_recovery import (  # noqa: E402
    attach_homepage_social_recovery_observations,
    homepage_social_recovery_observations,
)


def _profile() -> dict:
    source_url = "https://amembran.no/"
    digest = "a" * 64
    return {
        "organisation_number": "998823951",
        "name": "A-MEMBRAN AS",
        "evidence": {
            "website": {
                "status": "available",
                "source_type": "deterministic_legal_name_domain_guess",
                "source_url": source_url,
                "retrieved_at": "2026-10-02T00:00:00Z",
                "content_sha256": digest,
                "value": {
                    "final_url": source_url,
                    "content_sha256": digest,
                    "identity_assessment": {
                        "status": "exact",
                        "score": 0.98,
                        "publishable": True,
                        "method": "final_h1c_secondary_identity_guard_v1",
                    },
                    "pages": [
                        {"url": source_url, "content_sha256": digest, "title": "A-Membran"},
                        {
                            "url": "https://amembran.no/kontakt",
                            "content_sha256": "b" * 64,
                            "title": "Kontakt",
                        },
                    ],
                    "secondary_identity_page": {
                        "url": "https://amembran.no/kontakt",
                        "content_sha256": "b" * 64,
                    },
                    "discovered_social_links": [
                        {"platform": "facebook", "url": "https://facebook.com/amembran"}
                    ],
                    "social_link_assessments": [
                        {
                            "platform": "facebook",
                            "url": "https://facebook.com/amembran",
                            "identity_score": 0.95,
                            "publishable": True,
                            "matched_tokens": ["membran"],
                            "method": "deterministic_social_handle_identity_v1",
                        }
                    ],
                    "structured_organisations": [],
                },
            }
        },
        "external_observations": [],
    }


def test_recovers_homepage_handle_even_when_secondary_identity_page_was_appended() -> None:
    observations = homepage_social_recovery_observations(_profile())
    assert len(observations) == 1
    item = observations[0]
    assert item["platform"] == "facebook"
    assert item["profile_url"] == "https://facebook.com/amembran"
    assert item["source_url"] == "https://amembran.no/"
    assert item["content_sha256"] == "a" * 64
    assert item["metrics"]["network_requests_added"] == 0
    assert item["metrics"]["declaration_mode"] == "retained_homepage_html_social_link"
    assert validate_observation(item) == []
    assert publishable_observation(item) is True


def test_recovers_jsonld_same_as_from_retained_exact_homepage() -> None:
    profile = _profile()
    profile["organisation_number"] = "931395726"
    profile["name"] = "MENTI VERDI AS"
    value = profile["evidence"]["website"]["value"]
    value["discovered_social_links"] = []
    value["social_link_assessments"] = []
    value["structured_organisations"] = [
        {
            "@type": "Organization",
            "name": "Menti Verdi AS",
            "sameAs": ["https://www.instagram.com/mentiverdi/"],
        }
    ]

    observations = homepage_social_recovery_observations(profile)
    assert len(observations) == 1
    item = observations[0]
    assert item["platform"] == "instagram"
    assert item["profile_url"] == "https://instagram.com/mentiverdi"
    assert item["metrics"]["declaration_mode"] == "retained_homepage_jsonld_same_as"
    assert item["metrics"]["network_requests_added"] == 0


def test_does_not_promote_social_assessment_not_present_in_retained_homepage_links() -> None:
    profile = _profile()
    value = profile["evidence"]["website"]["value"]
    value["discovered_social_links"] = []
    value["structured_organisations"] = []
    assert homepage_social_recovery_observations(profile) == []


def test_abstains_if_primary_page_url_or_hash_does_not_match_canonical_homepage() -> None:
    wrong_hash = _profile()
    wrong_hash["evidence"]["website"]["value"]["pages"][0]["content_sha256"] = "c" * 64
    assert homepage_social_recovery_observations(wrong_hash) == []

    wrong_url = _profile()
    wrong_url["evidence"]["website"]["value"]["pages"][0]["url"] = "https://amembran.no/other"
    assert homepage_social_recovery_observations(wrong_url) == []


def test_abstains_if_exact_website_identity_is_not_publishable() -> None:
    profile = _profile()
    profile["evidence"]["website"]["value"]["identity_assessment"]["publishable"] = False
    assert homepage_social_recovery_observations(profile) == []


def test_rejects_structured_same_as_that_fails_handle_identity_gate() -> None:
    profile = _profile()
    value = profile["evidence"]["website"]["value"]
    value["discovered_social_links"] = []
    value["social_link_assessments"] = []
    value["structured_organisations"] = [
        {"@type": "Organization", "sameAs": ["https://instagram.com/totallydifferentbrand"]}
    ]
    assert homepage_social_recovery_observations(profile) == []


def test_deduplicates_incumbent_profile_handle_observation() -> None:
    profile = _profile()
    profile["external_observations"] = [
        {
            "id": "incumbent-handle",
            "organisation_number": "998823951",
            "platform": "facebook",
            "signal_type": "profile_handle",
            "profile_url": "https://facebook.com/amembran",
        }
    ]
    assert homepage_social_recovery_observations(profile) == []


def test_attach_is_idempotent_and_preserves_other_observations() -> None:
    profile = _profile()
    profile["external_observations"] = [
        {
            "id": "other-observation",
            "organisation_number": "998823951",
            "platform": "company_site",
            "signal_type": "company_profile",
        }
    ]
    first = attach_homepage_social_recovery_observations(profile)
    second = attach_homepage_social_recovery_observations(deepcopy(first))
    first_ids = [item["id"] for item in first["external_observations"]]
    second_ids = [item["id"] for item in second["external_observations"]]
    assert first_ids == second_ids
    assert "other-observation" in first_ids
    assert sum(item.startswith("homepage-social-recovery-") for item in first_ids) == 1
