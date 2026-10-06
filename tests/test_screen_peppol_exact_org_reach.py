from __future__ import annotations

import csv
import gzip
import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "screen_peppol_exact_org_reach.py"
spec = importlib.util.spec_from_file_location("screen_peppol_exact_org_reach", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_participant_org_accepts_only_exact_norwegian_0192() -> None:
    assert module.participant_org("iso6523-actorid-upis::0192:123456789") == "123456789"
    assert module.participant_org("0192:123456789") == "123456789"
    assert module.participant_org("iso6523-actorid-upis%3A%3A0192%3A123456789") == "123456789"
    assert module.participant_org("iso6523-actorid-upis::0192:01234567890") is None
    assert module.participant_org("iso6523-actorid-upis::9908:123456789") is None


def test_has_value_drops_blank_multiline_values() -> None:
    assert module.has_value("https://a.test\n\n")
    assert not module.has_value("\n  \n")


def _write_fixture(path: Path) -> None:
    columns = [
        "Participant ID",
        "Names (per-row)",
        "Country code",
        "Geo info",
        "Identifier schemes",
        "Identifier values",
        "Websites",
        "Contact type",
        "Contact name",
        "Contact phone",
        "Contact email",
        "Additional info",
        "Registration date",
        "Document types",
    ]
    rows = [
        {
            "Participant ID": "iso6523-actorid-upis::0192:123456789",
            "Names (per-row)": "TARGET AS",
            "Country code": "NO",
            "Websites": "https://target.example",
            "Contact email": "personal@example.test",
            "Registration date": "2024-01-01",
        },
        {
            "Participant ID": "iso6523-actorid-upis::0192:987654321",
            "Names (per-row)": "OTHER AS",
            "Country code": "NO",
            "Websites": "",
            "Contact email": "other@example.test",
            "Registration date": "2023-01-01",
        },
        {
            "Participant ID": "iso6523-actorid-upis::9908:123456789",
            "Names (per-row)": "WRONG SCHEME",
            "Country code": "GB",
            "Websites": "https://wrong.example",
            "Contact email": "wrong@example.test",
            "Registration date": "2022-01-01",
        },
    ]
    with gzip.open(path, "wt", encoding="iso-8859-1", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter=";")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def test_scan_returns_aggregate_counts_only(tmp_path: Path) -> None:
    export = tmp_path / "businesscards.csv.gz"
    _write_fixture(export)
    cohorts = {
        "sample": {
            "123456789": {"organisation_number": "123456789", "name": "TARGET AS"},
            "111111111": {"organisation_number": "111111111", "name": "ABSENT AS"},
        }
    }
    result = module.scan(export, cohorts)
    assert result["source_rows"] == 3
    assert result["norwegian_0192_rows"] == 2
    assert result["target_rows"] == 1
    assert result["cohorts"]["sample"]["participant_hits"] == 1
    assert result["cohorts"]["sample"]["website_candidate_companies"] == 1

    # Privacy/data-minimisation gate: no raw source identity/contact values survive.
    encoded = repr(result)
    assert "TARGET AS" not in encoded
    assert "personal@example.test" not in encoded
    assert "https://target.example" not in encoded
    assert "123456789" not in encoded
