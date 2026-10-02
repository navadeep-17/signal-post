from __future__ import annotations

from copy import deepcopy

from norway_company_agent.external_footprint import publishable_observation, validate_observation
from norway_company_agent.zero_network_social_recovery import (
    attach_zero_network_social_recovery,
    recover_company_site_social_observations,
)


def profile(*, pages: int = 1) -> dict:
    digest = "a" * 64
    page_rows = [{"url": "https://mentiverdi.no/", "content_sha256": digest, "title": "Menti Verdi"}]
    if pages > 1:
        page_rows.append({"url": "https://mentiverdi.no/personvern", "content_sha256": "b" * 64, "title": "Personvern"})
    return {
        "organisation_number": "931395726",
        "name": "MENTI VERDI AS",
        "evidence": {
            "website": {
                "status": "available",
                "source_type": "deterministic_legal_name_domain_guess",
                "source_url": "https://mentiverdi.no/",
                "retrieved_at": "2026-10-02T00:00:00Z",
                "content_sha256": digest,
                "value": {
                    "final_url": "https://mentiverdi.no/",
                    "content_sha256": digest,
                    "identity_assessment": {
                        "status": "exact",
                        "score": 1.0,
                        "publishable": True,
                        "method": "deterministic_name_org_evidence_v3",
                    },
                    "pages": page_rows,
                    "social_link_assessments": [],
                    "structured_organisations": [
                        {
                            "@type": "Organization",
                            "name": "Menti Verdi",
                            "sameAs": ["https://www.instagram.com/mentiverdi/"],
                        }
                    ],
                },
            }
        },
        "external_observations": [],
    }


def test_recovers_jsonld_sameas_from_exact_retained_homepage_without_network() -> None:
    rows = recover_company_site_social_observations(profile())
    assert len(rows) == 1
    item = rows[0]
    assert item["platform"] == "instagram"
    assert item["profile_url"] == "https://instagram.com/mentiverdi"
    assert item["source_url"] == "https://mentiverdi.no/"
    assert item["content_sha256"] == "a" * 64
    assert item["metrics"]["network_requests_added"] == 0
    assert validate_observation(item) == []
    assert publishable_observation(item) is True


def test_multi_page_identity_snapshot_can_reuse_primary_homepage_assessment() -> None:
    row = profile(pages=2)
    row["evidence"]["website"]["value"]["structured_organisations"] = []
    row["evidence"]["website"]["value"]["social_link_assessments"] = [
        {
            "platform": "facebook",
            "url": "https://facebook.com/mentiverdi",
            "identity_score": 0.98,
            "publishable": True,
            "matched_tokens": ["menti", "verdi"],
            "method": "deterministic_social_handle_identity_v1",
        }
    ]
    rows = recover_company_site_social_observations(row)
    assert len(rows) == 1
    assert rows[0]["source_url"] == "https://mentiverdi.no/"
    assert rows[0]["content_sha256"] == "a" * 64


def test_secondary_page_cannot_nominate_a_social_candidate() -> None:
    row = profile(pages=2)
    row["evidence"]["website"]["value"]["structured_organisations"] = []
    row["evidence"]["website"]["value"]["social_link_assessments"] = []
    row["evidence"]["website"]["value"]["pages"][1]["social_links"] = [
        {"platform": "facebook", "url": "https://facebook.com/mentiverdi"}
    ]
    assert recover_company_site_social_observations(row) == []


def test_non_exact_website_cannot_recover_socials() -> None:
    row = profile()
    row["evidence"]["website"]["value"]["identity_assessment"] = {
        "status": "related_or_uncertain",
        "score": 0.3,
        "publishable": False,
    }
    assert recover_company_site_social_observations(row) == []


def test_weak_handle_sameas_still_abstains() -> None:
    row = profile()
    row["evidence"]["website"]["value"]["structured_organisations"][0]["sameAs"] = [
        "https://instagram.com/unrelatedbrand"
    ]
    assert recover_company_site_social_observations(row) == []


def test_primary_page_url_or_hash_must_match_top_level_provenance() -> None:
    wrong_url = profile()
    wrong_url["evidence"]["website"]["value"]["pages"][0]["url"] = "https://other.example/"
    assert recover_company_site_social_observations(wrong_url) == []

    wrong_hash = profile()
    wrong_hash["evidence"]["website"]["value"]["pages"][0]["content_sha256"] = "c" * 64
    assert recover_company_site_social_observations(wrong_hash) == []


def test_existing_social_observation_is_not_duplicated_and_attach_is_idempotent() -> None:
    row = profile()
    first = attach_zero_network_social_recovery(row)
    second = attach_zero_network_social_recovery(deepcopy(first))
    first_rows = [x for x in first["external_observations"] if x.get("signal_type") == "profile_handle"]
    second_rows = [x for x in second["external_observations"] if x.get("signal_type") == "profile_handle"]
    assert len(first_rows) == 1
    assert [x["id"] for x in first_rows] == [x["id"] for x in second_rows]
    assert recover_company_site_social_observations(second) == []
