from __future__ import annotations

from norway_company_agent.company_site_social import company_site_social_observations


def _profile(*, name: str, source_url: str, platform: str, profile_url: str, publishable: bool = False) -> dict:
    digest = "7" * 64
    return {
        "organisation_number": "976332888",
        "name": name,
        "evidence": {
            "website": {
                "status": "available",
                "source_type": "registry_linked_company_website",
                "source_url": source_url,
                "retrieved_at": "2026-10-05T17:00:00Z",
                "content_sha256": digest,
                "value": {
                    "final_url": source_url,
                    "content_sha256": digest,
                    "identity_assessment": {
                        "status": "exact",
                        "score": 0.95,
                        "publishable": True,
                        "method": "deterministic_name_org_evidence_v4",
                    },
                    "pages": [
                        {
                            "url": source_url,
                            "content_sha256": digest,
                            "title": name,
                        }
                    ],
                    "discovered_social_links": [
                        {"platform": platform, "url": profile_url},
                    ],
                    "social_link_assessments": [
                        {
                            "platform": platform,
                            "url": profile_url,
                            "identity_score": 0.3 if not publishable else 0.98,
                            "publishable": publishable,
                            "matched_tokens": [] if not publishable else ["company"],
                            "method": "deterministic_social_handle_identity_v1",
                        }
                    ],
                },
            }
        },
    }


def test_rejects_human_readable_theme_vendor_profile_from_exact_homepage() -> None:
    profile = _profile(
        name="CLINIC COMPANY AS",
        source_url="https://cliniccompany.no/",
        platform="facebook",
        profile_url="https://facebook.com/unrelatedthemevendor",
        publishable=False,
    )
    assert company_site_social_observations(profile) == []


def test_preserves_readable_handle_that_matches_verified_site_brand() -> None:
    profile = _profile(
        name="OPERATING COMPANY AS",
        source_url="https://northstarstudio.no/",
        platform="instagram",
        profile_url="https://instagram.com/northstarstudio",
        publishable=False,
    )
    observations = company_site_social_observations(profile)
    assert len(observations) == 1
    assert observations[0]["profile_url"] == "https://instagram.com/northstarstudio"
    assert observations[0]["strategy"] == "verified_company_homepage_declaration_c12_v1"
    proof = observations[0]["identity_proof"]
    declaration = next(item for item in proof if item.get("type") == "company_homepage_declared_social_link")
    guard = next(item for item in proof if item.get("type") == "direct_company_homepage_declaration_guard")
    assert declaration["source_url"] == "https://northstarstudio.no/"
    assert guard["profile_url"] == "https://instagram.com/northstarstudio"
    assert guard["match_basis"] == "verified_site_brand"
    assert guard["method"] == "deterministic_social_declaration_identity_v1"
    assert guard["score"] >= 0.95


def test_preserves_readable_handle_that_matches_meaningful_legal_name_tokens() -> None:
    profile = _profile(
        name="ALPINE DESIGN STUDIO AS",
        source_url="https://example.no/",
        platform="facebook",
        profile_url="https://facebook.com/alpinedesignstudio",
        publishable=False,
    )
    observations = company_site_social_observations(profile)
    assert len(observations) == 1
    assert observations[0]["profile_url"] == "https://facebook.com/alpinedesignstudio"
    guard = next(
        item
        for item in observations[0]["identity_proof"]
        if item.get("type") == "direct_company_homepage_declaration_guard"
    )
    assert guard["match_basis"] == "legal_name_tokens"
    assert set(guard["matched_tokens"]) >= {"alpine", "design", "studio"}


def test_existing_publishable_handle_assessment_remains_authoritative() -> None:
    profile = _profile(
        name="EXAMPLE COMPANY AS",
        source_url="https://example.no/",
        platform="facebook",
        profile_url="https://facebook.com/brandalias",
        publishable=True,
    )
    observations = company_site_social_observations(profile)
    assert len(observations) == 1
    proof = observations[0]["identity_proof"]
    assert any(item.get("type") == "social_handle_identity_gate" for item in proof)


def test_opaque_youtube_channel_id_keeps_exact_homepage_declaration_rule() -> None:
    profile = _profile(
        name="FOREST SERVICES AS",
        source_url="https://forestservices.no/",
        platform="youtube",
        profile_url="https://youtube.com/channel/UCWQ6axV2SNSqhA0JVoTZk-w",
        publishable=False,
    )
    observations = company_site_social_observations(profile)
    assert len(observations) == 1
    assert observations[0]["platform"] == "youtube"
    guard = next(
        item
        for item in observations[0]["identity_proof"]
        if item.get("type") == "direct_company_homepage_declaration_guard"
    )
    assert guard["match_basis"] == "opaque_platform_identifier"
    assert guard["method"] == "opaque_profile_identifier_on_exact_homepage_v1"
