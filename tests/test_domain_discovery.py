from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.domain_discovery import registry_email_addresses, registry_email_domain_candidates  # noqa: E402
from norway_company_agent.identity import assess_website_identity  # noqa: E402


def profile(*, website: str = "", email: str = "") -> dict:
    return {
        "organisation_number": "123456789",
        "name": "EXAMPLE BEDRIFT AS",
        "website": website,
        "evidence": {
            "registry": {
                "value": {
                    "epostadresse": email,
                }
            }
        },
    }


def test_registry_email_addresses_normalises_and_deduplicates() -> None:
    row = profile(email="POST@Example.NO; post@example.no")
    assert registry_email_addresses(row) == ["POST@example.no", "post@example.no"]


def test_existing_registry_website_is_not_eligible() -> None:
    result = registry_email_domain_candidates(profile(website="https://example.no", email="post@example.no"))
    assert result["eligible"] is False
    assert result["reason"] == "registry_website_present"


def test_missing_registry_email_is_not_eligible() -> None:
    result = registry_email_domain_candidates(profile())
    assert result["eligible"] is False
    assert result["reason"] == "registry_email_missing_or_invalid"


def test_generic_consumer_mail_domain_is_rejected() -> None:
    result = registry_email_domain_candidates(profile(email="owner@gmail.com"))
    assert result["eligible"] is False
    assert result["reason"] == "only_generic_email_domains"
    assert result["generic_domains"] == ["gmail.com"]


def test_norwegian_isp_mail_domain_is_rejected() -> None:
    result = registry_email_domain_candidates(profile(email="owner@online.no"))
    assert result["eligible"] is False
    assert result["reason"] == "only_generic_email_domains"


def test_corporate_email_domain_becomes_candidate_without_scheme() -> None:
    result = registry_email_domain_candidates(profile(email="post@arkjv.no"))
    assert result["eligible"] is True
    assert result["reason"] == "candidate_domains_from_registry_email"
    assert result["candidates"] == [
        {
            "domain": "arkjv.no",
            "url": "arkjv.no",
            "source": "brreg_public_registry_email_domain",
        }
    ]


def test_subdomain_is_preserved_for_independent_verification() -> None:
    result = registry_email_domain_candidates(profile(email="post@notodden.bbl.no"))
    assert result["eligible"] is True
    assert result["candidates"][0]["domain"] == "notodden.bbl.no"


def test_invalid_email_does_not_create_candidate() -> None:
    result = registry_email_domain_candidates(profile(email="not-an-email"))
    assert result["eligible"] is False
    assert result["reason"] == "registry_email_missing_or_invalid"


def test_norwegian_webhotel_placeholder_cannot_be_exact_company_identity() -> None:
    row = {
        "organisation_number": "980165493",
        "name": "MESCO AS",
        "evidence": {
            "website": {
                "status": "available",
                "source_url": "https://mesco.no/",
                "value": {
                    "final_url": "https://mesco.no/",
                    "title": "ADATA.NO REGISTRERT DOMENE",
                    "description": "",
                    "main_text_excerpt": (
                        "ADATA.NO REGISTRERT DOMENE. Dette domenet er registrert av en kunde. "
                        "Har du bestilt webhotell mottar du informasjon om din webkonto. "
                        "Du kan oppgradere til Webhotell for fri webside og mail."
                    ),
                    "structured_organisations": [],
                    "pages": [],
                },
            }
        },
    }

    assessment = assess_website_identity(row)

    assert assessment["publishable"] is False
    assert assessment["status"] == "related_or_uncertain"
    assert assessment["score"] == 0.1
    assert "hosting placeholder" in assessment["reasons"][0]
