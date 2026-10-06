from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "screen_mattilsynet_smilefjes_reach.py"
spec = importlib.util.spec_from_file_location("screen_mattilsynet_smilefjes_reach", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def row(
    org: str,
    inspection_date: str,
    *,
    establishment: str = "E1",
    inspection: str = "T1",
    name: str = "EXAMPLE",
    grade: str = "1",
) -> dict[str, str]:
    parsed = module.parse_source_date(inspection_date)
    return {
        "orgnummer": org,
        "tilsynsobjektid": establishment,
        "tilsynid": inspection,
        "navn": name,
        "dato": inspection_date,
        "_parsed_date": parsed.isoformat() if parsed else "",
        "status": "0",
        "total_karakter": grade,
        "tilsynsbesoektype": "0",
        "adrlinje1": "Gate 1",
        "adrlinje2": "",
        "postnr": "0001",
        "poststed": "Oslo",
    }


def test_only_exact_org_number_counts() -> None:
    rows = [
        row("999999999", "01102026"),
        row("888888888", "02102026"),
    ]
    report, matches = module.screen(rows, {"999999999"}, today=date(2026, 10, 6))
    assert report["exact_target_company_hits"] == 1
    assert matches[0]["organisation_number"] == "999999999"


def test_no_parent_or_subunit_inheritance() -> None:
    rows = [row("888888888", "01102026")]
    report, matches = module.screen(rows, {"999999999"}, today=date(2026, 10, 6))
    assert report["exact_target_company_hits"] == 0
    assert matches == []


def test_latest_inspection_recency_and_scope_are_preserved() -> None:
    rows = [
        row("999999999", "01102024", establishment="E1", inspection="T-old", grade="2"),
        row("999999999", "01102026", establishment="E2", inspection="T-new", grade="0"),
    ]
    report, matches = module.screen(rows, {"999999999"}, today=date(2026, 10, 6))
    match = matches[0]
    assert report["companies_with_latest_inspection_within_365_days"] == 1
    assert report["companies_with_latest_inspection_within_730_days"] == 1
    assert match["scope"] == "establishment_inspection_only"
    assert match["latest_inspection_date"] == "2026-10-01"
    assert match["establishment_ids"] == ["E1", "E2"]
    assert match["latest_inspections"][0]["inspection_id"] == "T-new"


def test_invalid_date_is_not_treated_as_recent() -> None:
    rows = [row("999999999", "32132026")]
    report, matches = module.screen(rows, {"999999999"}, today=date(2026, 10, 6))
    assert report["exact_target_company_hits"] == 1
    assert report["companies_with_parseable_inspection_date"] == 0
    assert report["companies_with_latest_inspection_within_365_days"] == 0
    assert matches[0]["latest_inspection_date"] is None
