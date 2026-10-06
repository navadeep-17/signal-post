from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "screen_forskningsradet_project_reach.py"
spec = importlib.util.spec_from_file_location("screen_forskningsradet_project_reach", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def row(
    org: str,
    *,
    awarded: str = "1000000",
    start: str = "2025",
    end: str = "2027",
    phase: str = "Aktivt",
    number: str = "P1",
) -> dict[str, str]:
    return {
        "organisasjonsnummer": org,
        "prosjektnummer": number,
        "prosjekttittel": "Test project",
        "prosjektfase": phase,
        "prosjektstart": start,
        "prosjektslutt": end,
        "prosjektansvarlig_navn": "EXAMPLE AS",
        "prosjekttype": "Innovasjonsprosjekt",
        "soknadstype": "Innovasjonsprosjekt",
        "virkemiddel": "Test",
        "hovedaktivitet": "Test",
        "aktivitet": "Digitalisering",
        "fagomraade": "Teknologi",
        "fag": "IKT",
        "fagdisiplin": "Programvare",
        "sokt_belop": "2000000",
        "tildelt_belop": awarded,
    }


def test_exact_org_only() -> None:
    report, matches = module.screen(
        [row("999999999"), row("888888888", number="P2")],
        {"999999999"},
        current_year=2026,
    )
    assert report["exact_target_company_hits"] == 1
    assert matches[0]["organisation_number"] == "999999999"


def test_funded_metrics_require_positive_award() -> None:
    report, matches = module.screen(
        [row("999999999", awarded="0")],
        {"999999999"},
        current_year=2026,
    )
    assert report["exact_target_company_hits"] == 1
    assert report["companies_with_funded_project"] == 0
    assert matches[0]["funded_project_rows"] == 0


def test_current_window_and_nonterminal_phase_are_separate() -> None:
    rows = [
        row("999999999", start="2024", end="2027", phase="Avsluttet", number="P1"),
        row("999999999", start="2025", end="2027", phase="Aktivt", number="P2"),
    ]
    report, matches = module.screen(rows, {"999999999"}, current_year=2026)
    assert report["companies_with_funded_project_spanning_current_year"] == 1
    assert report["companies_with_nonterminal_funded_project_spanning_current_year"] == 1
    assert matches[0]["current_year_funded_project_rows"] == 2
    assert matches[0]["current_year_nonterminal_funded_project_rows"] == 1


def test_project_leader_is_not_emitted() -> None:
    source = row("999999999")
    source["prosjektleder"] = "PERSON NAME"
    _report, matches = module.screen([source], {"999999999"}, current_year=2026)
    project = matches[0]["sample_projects"][0]
    assert "prosjektleder" not in project
    assert "project_leader" not in project
    assert "PERSON NAME" not in str(project)
