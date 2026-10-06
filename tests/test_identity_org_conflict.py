from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.evidence import evidence  # noqa: E402
from norway_company_agent.identity import apply_website_identity_gate  # noqa: E402


def _profile(org: str, name: str) -> dict:
    return {
        "organisation_number": org,
        "name": name,
        "evidence": {},
    }


def _website(url: str, *, title: str, identity_text: str, main_text: str = "") -> dict:
    return evidence(
        "website",
        "available",
        "test_company_site",
        url,
        value={
            "final_url": url,
            "title": title,
            "description": "",
            "identity_text_excerpt": identity_text,
            "main_text_excerpt": main_text,
            "structured_organisations": [],
            "social_links": [],
            "pages": [
                {
                    "url": url,
                    "title": title,
                    "identity_text_excerpt": identity_text,
                    "main_text_excerpt": main_text,
                }
            ],
        },
        content_sha256="a" * 64,
        retrieved_at="2026-09-15T00:00:00Z",
    )


def test_registry_linked_parent_org_number_vetoes_local_entity_publication():
    profile = _profile("983928323", "ST. HANSHAUGEN VENSTRE")
    website = _website(
        "https://www.venstre.no/lokal/oslo/st-hanshaugen/",
        title="St. Hanshaugen Venstre",
        identity_text=(
            "St. Hanshaugen Venstre. Venstres Hovedorganisasjon. "
            "Adresse: Møllergata 16, 0179 Oslo. Organisasjonsnummer: 971 278 390."
        ),
        main_text="St. Hanshaugen Venstre lokalpolitikk. " * 10,
    )

    gated = apply_website_identity_gate(profile, website)
    assessment = gated["assessment"]

    assert assessment["publishable"] is False
    assert assessment["status"] == "related_or_uncertain"
    assert assessment["score"] == 0.1
    assert assessment["observed_organisation_numbers"] == ["971278390"]
    assert "different legal-entity organisation number" in " ".join(assessment["reasons"])


def test_target_explicit_org_number_wins_when_page_also_mentions_another_entity():
    profile = _profile("983928323", "ST. HANSHAUGEN VENSTRE")
    website = _website(
        "https://example.test/st-hanshaugen/",
        title="St. Hanshaugen Venstre",
        identity_text=(
            "ST. HANSHAUGEN VENSTRE Org.nr 983 928 323. "
            "Samarbeidspartner Organisasjonsnummer: 971 278 390."
        ),
        main_text="St. Hanshaugen Venstre lokalpolitikk. " * 10,
    )

    gated = apply_website_identity_gate(profile, website)
    assessment = gated["assessment"]

    assert assessment["publishable"] is True
    assert assessment["score"] == 1.0
    assert assessment["observed_organisation_numbers"] == ["971278390", "983928323"]
    assert "exact organisation number is explicitly labelled" in " ".join(assessment["reasons"])


def test_no_mva_format_is_treated_as_explicit_target_organisation_number():
    profile = _profile("917910146", "EVENTI AS")
    website = _website(
        "https://www.eventi.no/",
        title="Eventi AS",
        identity_text="Eventi AS, Arabergvegen 3, 4050 Sola - NO 917 910 146 MVA",
        main_text="Teknisk totalleverandør innen festival og event. " * 8,
    )

    gated = apply_website_identity_gate(profile, website)
    assessment = gated["assessment"]

    assert assessment["publishable"] is True
    assert assessment["score"] == 1.0
    assert assessment["observed_organisation_numbers"] == ["917910146"]


def test_name_only_identity_behavior_is_preserved_when_no_org_number_is_labelled():
    profile = _profile("984531257", "LAFINTO AS")
    website = _website(
        "https://www.lafinto.no/",
        title="Lafinto AS",
        identity_text="Lafinto AS, Habornveien 53, 1630 Gamle Fredrikstad",
        main_text="Bilinnredning og spesialprosjekter for kjøretøy. " * 8,
    )

    gated = apply_website_identity_gate(profile, website)
    assessment = gated["assessment"]

    assert assessment["publishable"] is True
    assert assessment["score"] == 0.95
    assert assessment["observed_organisation_numbers"] == []


def test_explicit_current_domain_owner_vetoes_name_matching_wrong_entity():
    profile = _profile("825188592", "INTERIØRKUPP AS")
    website = _website(
        "https://interiorkupp.no/",
        title="Interiørkupp",
        identity_text=(
            "Interiorkupp.no eies av Rolf Sletvold Interiørsenter AS, "
            "og tilbyr kvalitetsprodukter til hjemmet."
        ),
        main_text="Parkett, gulv, tapet og andre interiørvarer. Trygg levering i hele Norge. " * 8,
    )

    gated = apply_website_identity_gate(profile, website)
    assessment = gated["assessment"]

    assert assessment["publishable"] is False
    assert assessment["status"] == "related_or_uncertain"
    assert assessment["score"] == 0.1
    assert assessment["observed_site_owners"] == ["Rolf Sletvold Interiørsenter AS"]
    assert "website is owned by a different named legal entity" in " ".join(assessment["reasons"])


def test_explicit_current_domain_owner_does_not_veto_same_target_entity():
    profile = _profile("825188592", "INTERIØRKUPP AS")
    website = _website(
        "https://interiorkupp.no/",
        title="Interiørkupp AS",
        identity_text="Interiorkupp.no eies av Interiørkupp AS.",
        main_text="Parkett, gulv, tapet og andre interiørvarer. Trygg levering i hele Norge. " * 8,
    )

    gated = apply_website_identity_gate(profile, website)
    assessment = gated["assessment"]

    assert assessment["publishable"] is True
    assert assessment["score"] == 0.95
    assert assessment["observed_site_owners"] == ["Interiørkupp AS"]


def test_generic_website_owner_phrase_does_not_veto_same_target_entity():
    profile = _profile("825188592", "INTERIØRKUPP AS")
    website = _website(
        "https://interiorkupp.no/",
        title="Interiørkupp AS",
        identity_text="Denne nettsiden eies av INTERIØRKUPP AS.",
        main_text="Parkett, gulv, tapet og andre interiørvarer. Trygg levering i hele Norge. " * 8,
    )

    gated = apply_website_identity_gate(profile, website)
    assessment = gated["assessment"]

    assert assessment["publishable"] is True
    assert assessment["observed_site_owners"] == ["INTERIØRKUPP AS"]


def test_neuter_generic_website_owner_phrase_vetoes_different_entity():
    profile = _profile("825188592", "INTERIØRKUPP AS")
    website = _website(
        "https://interiorkupp.no/",
        title="Interiørkupp",
        identity_text="Dette nettstedet eies av Annen Butikk AS.",
        main_text="Parkett, gulv, tapet og andre interiørvarer. Trygg levering i hele Norge. " * 8,
    )

    gated = apply_website_identity_gate(profile, website)
    assessment = gated["assessment"]

    assert assessment["publishable"] is False
    assert assessment["observed_site_owners"] == ["Annen Butikk AS"]
    assert "website is owned by a different named legal entity" in " ".join(assessment["reasons"])


def test_other_domain_owner_statement_is_not_treated_as_current_site_identity():
    profile = _profile("825188592", "INTERIØRKUPP AS")
    website = _website(
        "https://interiorkupp.no/",
        title="Interiørkupp AS",
        identity_text="Partnernettstedet example.no eies av Annen Butikk AS.",
        main_text="Parkett, gulv, tapet og andre interiørvarer. Trygg levering i hele Norge. " * 8,
    )

    gated = apply_website_identity_gate(profile, website)
    assessment = gated["assessment"]

    assert assessment["publishable"] is True
    assert assessment["observed_site_owners"] == []



def test_plain_bil_car_company_is_not_misclassified_as_business_sports_club():
    profile = _profile("935038308", "BRANDSRUD BIL AS")
    website = _website(
        "https://www.brandsrudbil.no/",
        title="Brandsrud Bil AS",
        identity_text="Brandsrud Bil AS, Myrveien 5, 1815 Askim.",
        main_text="Bilverksted, service og reparasjon av biler. " * 8,
    )

    gated = apply_website_identity_gate(profile, website)
    assessment = gated["assessment"]

    assert assessment["publishable"] is True
    assert assessment["status"] == "exact"
    assert "sports-club" not in " ".join(assessment["reasons"])


def test_explicit_dotted_bil_abbreviation_keeps_sports_club_guard():
    profile = _profile("999999999", "ACME B.I.L.")
    website = _website(
        "https://www.acme.no/",
        title="ACME",
        identity_text="ACME, Oslo.",
        main_text="ACME driver virksomhet og arrangementer. " * 8,
    )

    gated = apply_website_identity_gate(profile, website)
    assessment = gated["assessment"]

    assert assessment["publishable"] is False
    assert assessment["status"] == "related_or_uncertain"
    assert "sports-club" in " ".join(assessment["reasons"])


def test_plain_bil_with_registry_idrett_context_keeps_sports_club_guard():
    profile = _profile("999999998", "ACME BIL")
    profile["evidence"] = {
        "registry": {
            "value": {
                "aktivitet": "Bedriftsidrettslag for ansatte og familie.",
                "vedtektsfestetFormaal": "Drive bedriftsidrett og sosiale aktiviteter.",
            }
        }
    }
    website = _website(
        "https://www.acme.no/",
        title="ACME",
        identity_text="ACME, Oslo.",
        main_text="ACME driver virksomhet og arrangementer. " * 8,
    )

    gated = apply_website_identity_gate(profile, website)
    assessment = gated["assessment"]

    assert assessment["publishable"] is False
    assert "sports-club" in " ".join(assessment["reasons"])
