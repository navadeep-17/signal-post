from __future__ import annotations

import csv
import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "screen_landbruksdirektoratet_support_reach.py"
spec = importlib.util.spec_from_file_location("screen_landbruksdirektoratet_support_reach", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_find_org_column_handles_norwegian_header() -> None:
    assert module.find_org_column(["Navn", "Organisasjonsnummer", "Sum tilskudd"]) == "Organisasjonsnummer"


def test_parse_number_handles_norwegian_decimal_and_grouping() -> None:
    assert module.parse_number("1 234,50") == 1234.5
    assert module.parse_number("1.234,50") == 1234.5
    assert module.parse_number("") is None


def test_scan_matches_only_org_column_not_free_text(tmp_path: Path) -> None:
    source = tmp_path / "dataset.csv"
    with source.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["Organisasjonsnummer", "Navn", "Beregnet tilskudd"],
            delimiter=";",
        )
        writer.writeheader()
        writer.writerow(
            {
                "Organisasjonsnummer": "123456789",
                "Navn": "TARGET AS",
                "Beregnet tilskudd": "10 000,00",
            }
        )
        writer.writerow(
            {
                "Organisasjonsnummer": "987654321",
                "Navn": "Reference to 111111111 in free text",
                "Beregnet tilskudd": "0",
            }
        )
    cohorts = {
        "sample": {
            "123456789": {"organisation_number": "123456789", "name": "TARGET AS"},
            "111111111": {"organisation_number": "111111111", "name": "ABSENT AS"},
        }
    }
    result = module.scan(source, cohorts)
    assert result["delimiter"] == ";"
    assert result["org_column"] == "Organisasjonsnummer"
    assert result["matches"]["123456789"]["rows"] == 1
    assert result["matches"]["123456789"]["positive_support_cells"] == 1
    assert result["matches"]["111111111"]["rows"] == 0
    assert result["cohorts"]["sample"]["matched_companies"] == 1
    assert result["cohorts"]["sample"]["companies_with_positive_support_cell"] == 1


def test_support_columns_are_diagnostic_only() -> None:
    assert module.support_columns(["Navn", "Tilskudd sau", "Sum beregnet tilskudd", "Areal"]) == [
        "Tilskudd sau",
        "Sum beregnet tilskudd",
    ]
