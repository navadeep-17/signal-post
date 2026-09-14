from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.domain_discovery import (  # noqa: E402
    corroborate_registry_email_domain_identity,
    qualify_registry_email_domain_identity,
    registry_email_addresses,
    registry_email_domain_candidates,
)
from norway_company_agent.identity import assess_website_identity  # noqa: E402


def profile(*, website: str = "", email: str = "") -> dict:
    return {
        "organisation_number": "123456789",
        "name": "EXAMPLE BEDRIFT AS",
        "website": website,
        "evidence": {"registry": {"value": {"epostadresse": email}}},
    }


def website_record(
    *,
    title: str = "",
    text: str = "",
    pages: list[dict] | None = None,
    final_url: str = "https://candidate.example/",
) -> dict:
    return {
        "status": "available",
        "source_url": final_url,
        "value": {
            "final_url": final_url,
            "title": title,
            "description": "",
            "main_text_excerpt": text,
            "structured_organisations": [],
            "pages": pages or [],
        },
    }


def exact_assessment() -> dict:
    return {
        "status": "exact",
        "score": 0.95,
        "publishable": True,
        "reasons": ["all normalized legal-name tokens appear together in homepage identity evidence"],
        "method": "deterministic_name_org_evidence_v2",
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
        {"domain": "arkjv.no", "url": "arkjv.no", "source": "brreg_public_registry_email_domain"}
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


def test_exact_legal_name_email_domain_can_corroborate_review() -> None:
    row = {"name": "MASTER SURGERY SYSTEMS AS"}
    review = {
        "status": "review",
        "score": 0.85,
        "publishable": False,
        "reasons": ["most legal-name tokens appear, but exact identity is incomplete"],
        "method": "deterministic_name_org_evidence_v2",
    }
    result = corroborate_registry_email_domain_identity(row, "mastersurgerysystems.no", review)
    assert result["publishable"] is True
    assert result["status"] == "exact"
    assert result["score"] == 0.97


def test_manager_domain_cannot_corroborate_customer_review() -> None:
    row = {"name": "BONDELIA I BORETTSLAG"}
    review = {
        "status": "review",
        "score": 0.85,
        "publishable": False,
        "reasons": ["most legal-name tokens appear, but exact identity is incomplete"],
        "method": "deterministic_name_org_evidence_v2",
    }
    result = corroborate_registry_email_domain_identity(row, "gobb.no", review)
    assert result == review


def test_subdomain_manager_cannot_corroborate_customer_review() -> None:
    row = {"name": "NORDLIEN OG HEDDAL BOLIGSTIFTELSE"}
    review = {
        "status": "review",
        "score": 0.85,
        "publishable": False,
        "reasons": ["most legal-name tokens appear, but exact identity is incomplete"],
        "method": "deterministic_name_org_evidence_v2",
    }
    result = corroborate_registry_email_domain_identity(row, "notodden.bbl.no", review)
    assert result == review


def test_corroboration_never_upgrades_related_or_uncertain() -> None:
    row = {"name": "MARINOR AS"}
    weak = {
        "status": "related_or_uncertain",
        "score": 0.3,
        "publishable": False,
        "reasons": ["insufficient page evidence"],
        "method": "deterministic_name_org_evidence_v2",
    }
    assert corroborate_registry_email_domain_identity(row, "marinor.as", weak) == weak


def test_h1_rejects_hostname_only_multitoken_identity() -> None:
    row = {"organisation_number": "123456789", "name": "EXAMPLE BEDRIFT AS"}
    site = website_record(title="Provider Hosting", text="Provider Hosting customer portal")
    result = qualify_registry_email_domain_identity(row, "example-bedrift.provider.no", site, exact_assessment())
    assert result["publishable"] is False
    assert result["status"] == "review"
    assert result["method"] == "registry_email_domain_page_identity_guard_v2"


def test_h1_rejects_single_token_client_subdomain_even_when_page_mentions_name() -> None:
    row = {"organisation_number": "123456789", "name": "MESCO AS"}
    site = website_record(title="MESCO", text=("MESCO customer portal. " * 20), final_url="https://mesco.provider.no/")
    result = qualify_registry_email_domain_identity(row, "mesco.provider.no", site, exact_assessment())
    assert result["publishable"] is False
    assert result["status"] == "review"


def test_h1_rejects_parent_domain_that_lists_subsidiary_full_legal_name() -> None:
    row = {"organisation_number": "123456789", "name": "CHILD OPERATIONS AS"}
    site = website_record(
        title="Parent Group",
        text="Our subsidiaries include CHILD OPERATIONS AS and several other legal entities.",
        final_url="https://parentgroup.no/",
    )
    result = qualify_registry_email_domain_identity(row, "parentgroup.no", site, exact_assessment())
    assert result["publishable"] is False
    assert "domain ownership" in result["reasons"][-1]


def test_h1_rejects_franchise_brand_domain_without_location_or_org_proof() -> None:
    row = {"organisation_number": "123456789", "name": "ACME OSLO AS"}
    site = website_record(
        title="ACME",
        text="ACME OSLO AS is one of many independently operated ACME locations.",
        final_url="https://acme.no/",
    )
    result = qualify_registry_email_domain_identity(row, "acme.no", site, exact_assessment())
    assert result["publishable"] is False


def test_h1_rejects_namesake_domain_without_location_or_org_proof() -> None:
    row = {"organisation_number": "123456789", "name": "NORDLYS BYGG AS"}
    site = website_record(
        title="Nordlys",
        text="Reference project delivered for NORDLYS BYGG AS. Contact Nordlys media for details.",
        final_url="https://nordlys.no/",
    )
    result = qualify_registry_email_domain_identity(row, "nordlys.no", site, exact_assessment())
    assert result["publishable"] is False


def test_h1_keeps_legitimate_multitoken_company_page_on_acronym_domain() -> None:
    row = {"organisation_number": "985589003", "name": "ARKITEKTFIRMA JON VIKØREN AS"}
    site = website_record(
        title="Arkitektfirma Jon Vikøren AS",
        text="Arkitektfirma Jon Vikøren AS er et arkitektkontor i Norge.",
        final_url="https://arkjv.no/",
    )
    result = qualify_registry_email_domain_identity(row, "arkjv.no", site, exact_assessment())
    assert result["publishable"] is True


def test_h1_keeps_exact_domain_with_legal_suffix_in_label() -> None:
    row = {"organisation_number": "919863609", "name": "OVS AS"}
    site = website_record(title="OVS AS", text="OVS AS leverer VVS-tjenester.", final_url="http://ovs-as.no/")
    result = qualify_registry_email_domain_identity(row, "ovs-as.no", site, exact_assessment())
    assert result["publishable"] is True


def test_h1_keeps_legitimate_rebrand_when_final_domain_matches_current_legal_name() -> None:
    row = {"organisation_number": "975363090", "name": "EMMTO AS"}
    site = website_record(
        title="Emmto",
        text="EMMTO AS er byggentreprenør i Kongsvinger.",
        final_url="https://emmto.no/",
    )
    result = qualify_registry_email_domain_identity(row, "hedmur.no", site, exact_assessment())
    assert result["publishable"] is True


def test_h1_allows_partial_domain_only_with_registry_location_corroboration() -> None:
    row = {
        "organisation_number": "979448759",
        "name": "NORDANGER GULV AS",
        "municipality": "OSLO",
        "evidence": {
            "registry": {
                "value": {
                    "forretningsadresse.adresse": "Professor Birkelands vei 36",
                    "forretningsadresse.postnummer": "1081",
                    "forretningsadresse.poststed": "OSLO",
                }
            }
        },
    }
    site = website_record(
        title="Nordanger Gulv AS",
        text="Nordanger Gulv AS. Besøksadresse Professor Birkelands vei 36, 1081 Oslo.",
        final_url="https://nordanger.no/",
    )
    result = qualify_registry_email_domain_identity(row, "nordanger.no", site, exact_assessment())
    assert result["publishable"] is True


def test_h1_keeps_exact_org_number_as_strongest_page_identity() -> None:
    row = {"organisation_number": "993550116", "name": "MASTER SURGERY SYSTEMS AS"}
    base_exact = {
        "status": "exact",
        "score": 1.0,
        "publishable": True,
        "reasons": ["exact organisation number appears in homepage identity evidence"],
        "method": "deterministic_name_org_evidence_v2",
    }
    site = website_record(title="MSS", text="Org nr 993 550 116", final_url="https://unusual-brand.no/")
    result = qualify_registry_email_domain_identity(row, "legacy-provider.no", site, base_exact)
    assert result["publishable"] is True
    assert result["score"] == 1.0
