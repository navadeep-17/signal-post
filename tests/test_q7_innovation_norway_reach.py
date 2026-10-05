from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_innovation_norway_screen_exact_org_and_recent_boundary(tmp_path: Path) -> None:
    targets = tmp_path / "targets.jsonl"
    targets.write_text(
        "\n".join(
            json.dumps({"organisation_number": org})
            for org in ("123456789", "987654321", "111111111")
        ) + "\n",
        encoding="utf-8",
    )
    dataset = tmp_path / "Tildelinger.csv"
    dataset.write_text(
        "Kundenavn;Organisasjonsnummer;Tilsagnsdato;Tilsagnsbeløp;Virkemiddel\n"
        "Example AS;123456789;01.02.2026;1 000 000;Tilskudd\n"
        "Other AS;987654321;2020-01-10;250000;Lån\n"
        "Namesake;222222222;2026-01-01;999999;Tilskudd\n",
        encoding="utf-8",
    )
    report = tmp_path / "report.json"

    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "screen_q7_innovation_norway_reach.py"),
            "--targets", str(targets),
            "--dataset", str(dataset),
            "--report", str(report),
            "--as-of", "2026-10-05",
            "--recent-years", "5",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    result = json.loads(report.read_text(encoding="utf-8"))
    assert result["schema"]["organisation_number_column"] == "Organisasjonsnummer"
    assert result["audit"]["rows_scanned"] == 3
    assert result["audit"]["matched_rows"] == 2
    assert result["coverage"]["any_financing_decision"]["companies"] == 2
    assert result["coverage"]["recent_financing_decision"]["companies"] == 1
    assert result["coverage"]["recent_financing_decision"]["organisation_numbers"] == ["123456789"]
    assert "222222222" not in result["matches_by_organisation_number"]
    assert result["source"]["production_rights_qualified"] is False
    assert result["publication_enabled"] is False
