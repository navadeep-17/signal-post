from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.zero_cost_registry_guard import (  # noqa: E402
    apply_registry_risk_guard,
    registry_risk_reasons,
)


def profile(name="OUT OF BOUNDS AS", org="927210657"):
    return {
        "organisation_number": org,
        "name": name,
        "municipality": "BÆRUM",
        "evidence": {
            "registry": {
                "status": "available",
                "value": {
                    "naeringskode1.kode": "00.000",
                    "aktivitet": "Erverve, eie og forvalte aksjer og andeler i andre selskaper.",
                    "vedtektsfestetFormaal": "Erverve, eie og forvalte aksjer og andeler i andre selskaper.",
                    "forretningsadresse.adresse": "Bjerkeholtet 12",
                    "forretningsadresse.postnummer": "1344",
                    "forretningsadresse.poststed": "HASLUM",
                    "forretningsadresse.kommune": "BÆRUM",
                },
            },
            "website_discovery_zero_cost": {
                "status": "available",
                "value": {"candidate_domain": "out-of-bounds.no"},
            },
            "website": {
                "status": "available",
                "source_url": "https://www.out-of-bounds.no/",
                "value": {
                    "final_url": "https://www.out-of-bounds.no/",
                    "title": "Billige Golfballer | Out of Bounds",
                    "description": "",
                    "main_text_excerpt": "Out of Bounds Sweden AB, Bergfotsgatan 3A, Mölndal, Sweden. Golfbutikk siden 2007.",
                    "structured_organisations": [],
                    "pages": [],
                    "identity_assessment": {
                        "status": "exact",
                        "score": 0.95,
                        "publishable": True,
                        "reasons": ["name/domain matched"],
                        "method": "deterministic_domain_page_identity_guard_v3",
                    },
                },
            },
        },
    }


def test_foreign_same_core_legal_entity_is_quarantined():
    item = profile()
    reasons = registry_risk_reasons(item, item["evidence"]["website"])
    assert any("foreign legal entity" in reason for reason in reasons)
    guarded, reasons = apply_registry_risk_guard(item)
    assessment = guarded["evidence"]["website"]["value"]["identity_assessment"]
    assert assessment["publishable"] is False
    assert assessment["status"] == "review"
    assert assessment["method"] == "h1c_registry_risk_guard_v1"
    assert reasons


def test_holding_or_unspecified_registry_entity_needs_location_without_org_number():
    item = profile(name="EXAMPLE HOLDING AS", org="999999999")
    website = item["evidence"]["website"]
    website["value"]["title"] = "Example Holding AS"
    website["value"]["main_text_excerpt"] = "Example Holding AS invests in companies across Norway."
    website["value"]["final_url"] = "https://exampleholding.no/"
    website["source_url"] = "https://exampleholding.no/"
    reasons = registry_risk_reasons(item, website)
    assert any("holding-oriented" in reason for reason in reasons)


def test_exact_org_number_overrides_registry_risk():
    item = profile(name="EXAMPLE HOLDING AS", org="999999999")
    website = item["evidence"]["website"]
    website["value"]["title"] = "Example Holding AS"
    website["value"]["main_text_excerpt"] = "Example Holding AS. Organisasjonsnummer 999 999 999."
    website["value"]["final_url"] = "https://exampleholding.no/"
    website["source_url"] = "https://exampleholding.no/"
    assert registry_risk_reasons(item, website) == []


def test_registry_location_allows_unspecified_entity_when_no_conflicting_legal_entity():
    item = profile(name="EXAMPLE HOLDING AS", org="999999999")
    website = item["evidence"]["website"]
    website["value"]["title"] = "Example Holding AS"
    website["value"]["main_text_excerpt"] = "Example Holding AS, Bjerkeholtet 12, 1344 Haslum."
    website["value"]["final_url"] = "https://exampleholding.no/"
    website["source_url"] = "https://exampleholding.no/"
    assert registry_risk_reasons(item, website) == []


def test_conflicting_foreign_entity_stays_blocked_even_if_target_location_is_elsewhere_on_page():
    item = profile()
    website = item["evidence"]["website"]
    website["value"]["main_text_excerpt"] = (
        "Out of Bounds Sweden AB operates the shop. Bjerkeholtet 12, 1344 Haslum."
    )
    reasons = registry_risk_reasons(item, website)
    assert any("foreign legal entity" in reason for reason in reasons)
