from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "screen_dsb_elvirksomhet_reach.py"
spec = importlib.util.spec_from_file_location("screen_dsb_elvirksomhet_reach", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def row(
    company_org: str,
    subunit_org: str,
    *,
    status: str = "Aktiv",
    name: str = "EXAMPLE AS AVD OSLO",
    email: str = "branch@example.no",
    phone: str = "12345678",
    tasks: str = "Prosjektering;Kontroll",
    scope: str = "Bygning;Elektrisk utstyr",
) -> dict[str, str]:
    return {
        "Status": status,
        "Foretaks-/bedriftsnavn": name,
        "Foretaksnr": company_org,
        "Bedriftsnr": subunit_org,
        "E-post": email,
        "Telefon": phone,
        "Ansvarlig DLE": "DLE AS",
        "Antall elektrofagarbeidere": "1-5",
        "Arbeidsoppgaver": tasks,
        "Anlegg- og utstyrstyper": scope,
    }


def test_only_foretaksnr_establishes_target_identity() -> None:
    rows = [
        row("999999999", "888888888"),
        row("777777777", "999999999"),
    ]
    report, matches = module.screen(rows, {"999999999"})
    assert report["exact_target_company_hits"] == 1
    assert matches[0]["organisation_number"] == "999999999"
    assert matches[0]["subunit_organisation_numbers"] == ["888888888"]


def test_subunit_contacts_are_observations_not_company_contact_candidates() -> None:
    rows = [
        row("999999999", "888888888", email="one@example.no", phone="111"),
        row("999999999", "777777777", email="two@example.no", phone="222"),
    ]
    report, matches = module.screen(rows, {"999999999"})
    match = matches[0]
    assert report["companies_with_subunit_email_observations"] == 1
    assert report["companies_with_subunit_phone_observations"] == 1
    assert match["subunit_email_observations"] == ["one@example.no", "two@example.no"]
    assert "emails" not in match
    assert "email" not in match
    assert "phones" not in match
    assert "phone" not in match


def test_rows_for_same_legal_entity_collapse_without_losing_scope() -> None:
    rows = [
        row(
            "999999999",
            "888888888",
            tasks="Prosjektering;Kontroll",
            scope="Bygning;Industri",
        ),
        row(
            "999999999",
            "777777777",
            status="Inaktiv",
            tasks="Reparasjon;Kontroll",
            scope="Industri;Maskiner",
        ),
    ]
    report, matches = module.screen(rows, {"999999999"})
    match = matches[0]
    assert report["active_registration_companies"] == 1
    assert match["dsb_registry_rows"] == 2
    assert match["statuses"] == ["Aktiv", "Inaktiv"]
    assert match["work_tasks"] == ["Kontroll", "Prosjektering", "Reparasjon"]
    assert match["facility_equipment_types"] == ["Bygning", "Industri", "Maskiner"]


def test_malformed_foretaksnr_never_matches() -> None:
    rows = [row("99999999X", "888888888")]
    report, matches = module.screen(rows, {"999999999"})
    assert report["malformed_foretaksnr_values"] == 1
    assert report["exact_target_company_hits"] == 0
    assert matches == []
