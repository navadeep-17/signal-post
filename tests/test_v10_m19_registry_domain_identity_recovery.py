from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.registry_domain_identity_recovery import (
    METHOD,
    assess_registry_domain_composite_identity,
    project_registry_domain_composite_website,
)


def _base_profile(
    *,
    org: str,
    name: str,
    registry_website: str,
    registry_email: str,
    final_url: str,
    legal_tokens: list[str],
    matched_tokens: list[str],
    observed_orgs: list[str] | None = None,
    observed_owners: list[str] | None = None,
) -> dict:
    site_hash = "a" * 64
    reg_hash = "b" * 64
    return {
        "organisation_number": org,
        "name": name,
        "evidence": {
            "registry_live": {
                "status": "available",
                "source_type": "official_registry_live",
                "source_url": f"https://data.brreg.no/enhetsregisteret/api/enheter/{org}",
                "retrieved_at": "2026-10-07T00:00:00+00:00",
                "content_sha256": reg_hash,
                "value": {
                    "organisation_number": org,
                    "name": name,
                    "website": registry_website,
                    "contact_email": registry_email,
                },
            },
            "website": {
                "status": "available",
                "source_type": "registry_linked_company_website",
                "source_url": final_url,
                "retrieved_at": "2026-10-07T00:00:01+00:00",
                "content_sha256": site_hash,
                "value": {
                    "final_url": final_url,
                    "content_sha256": site_hash,
                    "identity_assessment": {
                        "status": "review",
                        "score": 0.65,
                        "publishable": False,
                        "legal_name_tokens": legal_tokens,
                        "matched_tokens": matched_tokens,
                        "observed_organisation_numbers": observed_orgs or [],
                        "observed_site_owners": observed_owners or [],
                        "reasons": ["fixture prior gate abstained"],
                        "method": "deterministic_name_org_evidence_v4",
                    },
                },
            },
        },
    }


def _ambiguous_contract(profile: dict) -> dict:
    org = profile["organisation_number"]
    website = profile["evidence"]["website"]
    return {
        "organisation_number": org,
        "claims": [
            {
                "field": "official_website",
                "value": None,
                "availability": "ambiguous",
                "confidence": 1.0,
                "evidence_ids": ["ev-site"],
            }
        ],
        "evidence": [
            {
                "id": "ev-site",
                "source_url": website["source_url"],
                "source_class": "company_owned",
                "retrieved_at": website["retrieved_at"],
                "content_sha256": website["content_sha256"],
                "claim_span": "Bounded single-page final evaluator evidence",
                "identity_proof": deepcopy(website["value"]["identity_assessment"]),
                "extraction_method": "deterministic_name_org_evidence_v4",
            }
        ],
    }


def test_ra_style_registry_domain_email_and_name_recovers_exact_site() -> None:
    profile = _base_profile(
        org="927041057",
        name="RÅ! KOMPETANSE AS",
        registry_website="raakompetanse.no",
        registry_email="randi.eriksen@raakompetanse.no",
        final_url="https://raakompetanse.no/",
        legal_tokens=["ra", "kompetanse"],
        matched_tokens=["kompetanse", "ra"],
    )
    assessment = assess_registry_domain_composite_identity(profile)
    assert assessment is not None
    assert assessment["publishable"] is True
    assert assessment["method"] == METHOD
    assert assessment["substantive_legal_name_tokens"] == ["kompetanse"]

    result = project_registry_domain_composite_website(_ambiguous_contract(profile), profile)
    claim = result["claims"][0]
    assert claim["availability"] == "available"
    assert claim["value"] == "https://raakompetanse.no/"
    assert len(claim["evidence_ids"]) == 2
    assert claim["signal_type"] == "registry_domain_composite_identity_recovery"

    site_evidence = next(x for x in result["evidence"] if x["id"] == "ev-site")
    assert site_evidence["identity_proof"]["publishable"] is True
    assert site_evidence["prior_identity_proof"]["publishable"] is False


def test_np_style_short_initial_can_be_ignored_when_substantive_tokens_and_domains_agree() -> None:
    profile = _base_profile(
        org="981405900",
        name="NP NORDIC PROTECTION AS",
        registry_website="www.nordic-protection.no",
        registry_email="post@nordic-protection.no",
        final_url="https://nordic-protection.no/",
        legal_tokens=["np", "nordic", "protection"],
        matched_tokens=["nordic", "protection"],
    )
    assessment = assess_registry_domain_composite_identity(profile)
    assert assessment is not None
    assert assessment["substantive_legal_name_tokens"] == ["nordic", "protection"]
    assert assessment["publishable"] is True


def test_service_manager_site_is_rejected_when_registry_email_domain_differs_and_name_missing() -> None:
    profile = _base_profile(
        org="955225198",
        name="BØLER GARASJELAG SA",
        registry_website="www.norian.no/eiendomsforvaltning/",
        registry_email="bolergarasjelag@styremail.no",
        final_url="https://ecitnorian.com/no/",
        legal_tokens=["boler", "garasjelag"],
        matched_tokens=[],
    )
    assert assess_registry_domain_composite_identity(profile) is None


def test_housing_manager_site_is_rejected_when_legal_name_tokens_are_absent() -> None:
    profile = _base_profile(
        org="984182104",
        name="BORETTSLAGET RÅDHUSGATA 6",
        registry_website="www.helgelandbbl.no",
        registry_email="post@helgelandbbl.no",
        final_url="https://helgelandbbl.no/",
        legal_tokens=["borettslaget", "radhusgata"],
        matched_tokens=[],
    )
    assert assess_registry_domain_composite_identity(profile) is None


def test_mismatched_registered_email_domain_fails_closed() -> None:
    profile = _base_profile(
        org="927041057",
        name="RÅ! KOMPETANSE AS",
        registry_website="raakompetanse.no",
        registry_email="randi@example.org",
        final_url="https://raakompetanse.no/",
        legal_tokens=["ra", "kompetanse"],
        matched_tokens=["ra", "kompetanse"],
    )
    assert assess_registry_domain_composite_identity(profile) is None


def test_conflicting_observed_org_number_fails_closed() -> None:
    profile = _base_profile(
        org="981405900",
        name="NP NORDIC PROTECTION AS",
        registry_website="nordic-protection.no",
        registry_email="post@nordic-protection.no",
        final_url="https://nordic-protection.no/",
        legal_tokens=["np", "nordic", "protection"],
        matched_tokens=["nordic", "protection"],
        observed_orgs=["999999999"],
    )
    assert assess_registry_domain_composite_identity(profile) is None


def test_explicit_site_owner_name_fails_closed() -> None:
    profile = _base_profile(
        org="981405900",
        name="NP NORDIC PROTECTION AS",
        registry_website="nordic-protection.no",
        registry_email="post@nordic-protection.no",
        final_url="https://nordic-protection.no/",
        legal_tokens=["np", "nordic", "protection"],
        matched_tokens=["nordic", "protection"],
        observed_owners=["OTHER COMPANY AS"],
    )
    assert assess_registry_domain_composite_identity(profile) is None
