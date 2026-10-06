from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_retained_website_recovery.py"
spec = importlib.util.spec_from_file_location("audit_retained_website_recovery", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def profile(org="111111111"):
    return {
        "organisation_number": org,
        "evidence": {
            "website": {
                "status": "available",
                "source_url": "https://example.no",
                "value": {
                    "final_url": "https://www.example.no/",
                    "identity_assessment": {"publishable": True},
                    "identity_text_excerpt": "Kontakt old@example.no",
                    "pages": [
                        {"main_text_excerpt": "Kontakt sales@example.no og group@other.no"}
                    ],
                    "structured_organisations": [
                        {
                            "@type": "Organization",
                            "description": "Example develops industrial software for Norwegian customers.",
                            "email": "info@example.no",
                        }
                    ],
                },
            }
        },
    }


def test_recovers_only_net_new_same_domain_and_structured_description():
    p = profile()
    outputs = {
        "111111111": {
            "organisation_number": "111111111",
            "claims": [
                {
                    "field": "external.contact_email",
                    "availability": "available",
                    "value": "old@example.no",
                }
            ],
        }
    }
    report, rows = module.audit([p], outputs)
    assert report["verified_site_companies"] == 1
    assert report["net_new_same_domain_email_candidate_companies"] == 1
    assert report["net_new_same_domain_email_candidates"] == 2
    assert report["structured_description_candidate_companies"] == 1
    assert rows[0]["net_new_email_candidate_count"] == 2
    encoded = repr((report, rows))
    assert "sales@example.no" not in encoded
    assert "info@example.no" not in encoded
    assert "industrial software" not in encoded


def test_rejects_unverified_site():
    p = profile()
    p["evidence"]["website"]["value"]["identity_assessment"]["publishable"] = False
    report, rows = module.audit([p], {"111111111":{"organisation_number":"111111111","claims":[]}})
    assert report["verified_site_companies"] == 0
    assert report["net_new_same_domain_email_candidate_companies"] == 0
    assert rows == []
