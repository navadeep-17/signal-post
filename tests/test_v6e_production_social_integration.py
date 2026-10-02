from __future__ import annotations

from norway_company_agent.company_site_social import attach_company_site_social_observations


def test_production_attachment_recovers_primary_homepage_jsonld_sameas() -> None:
    digest = "a" * 64
    profile = {
        "organisation_number": "932097567",
        "name": "SØRØ TAKSERING AS",
        "evidence": {
            "website": {
                "status": "available",
                "source_url": "https://sorotaksering.no/",
                "retrieved_at": "2026-10-02T10:34:29Z",
                "content_sha256": digest,
                "value": {
                    "final_url": "https://sorotaksering.no/",
                    "content_sha256": digest,
                    "identity_assessment": {
                        "status": "exact",
                        "score": 0.95,
                        "publishable": True,
                        "method": "deterministic_domain_page_identity_guard_v3",
                    },
                    "pages": [
                        {
                            "url": "https://sorotaksering.no/",
                            "content_sha256": digest,
                            "title": "Sørø Taksering",
                        }
                    ],
                    "social_link_assessments": [],
                    "structured_organisations": [
                        {
                            "@type": "Organization",
                            "name": "Sørø Taksering As",
                            "sameAs": ["https://www.facebook.com/sorotaksering"],
                        }
                    ],
                },
            }
        },
        "external_observations": [],
    }

    attach_company_site_social_observations(profile)
    handles = [item for item in profile["external_observations"] if item.get("signal_type") == "profile_handle"]
    assert len(handles) == 1
    assert handles[0]["profile_url"] == "https://facebook.com/sorotaksering"
    assert handles[0]["strategy"] == "verified_company_homepage_social_recovery_v1"
    assert handles[0]["metrics"]["network_requests_added"] == 0
