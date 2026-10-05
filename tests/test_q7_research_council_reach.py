from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_research_council_screen_uses_exact_org_and_typed_award_semantics(tmp_path: Path) -> None:
    targets = tmp_path / "targets.jsonl"
    targets.write_text(
        '\n'.join(
            [
                json.dumps({"organisation_number": "123456789"}),
                json.dumps({"organisation_number": "987654321"}),
                json.dumps({"organisation_number": "111111111"}),
            ]
        )
        + '\n',
        encoding="utf-8",
    )

    dataset = tmp_path / "dataset.csv"
    dataset.write_text(
        "prosjektnummer,prosjekttittel,soknadsdato,prosjektfase,prosjektansvarlig_navn,organisasjonsnummer,sektor,sokt_belop,tildelt_belop\n"
        "1,Recent award,2025-01-10 00:00:00,Bevilgning,Example AS,123456789,Næringsliv,1000000,500000\n"
        "2,Old award,2018-02-01 00:00:00,Avsluttet,Other AS,987654321,Næringsliv,800000,400000\n"
        "3,Recent rejection,2026-01-01 00:00:00,Avslag,Other AS,987654321,Næringsliv,300000,0\n"
        "4,Namesake wrong org,2025-05-01 00:00:00,Bevilgning,Example AS,222222222,Næringsliv,100,100\n",
        encoding="utf-8",
    )
    report = tmp_path / "report.json"

    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "screen_q7_research_council_reach.py"),
            "--targets",
            str(targets),
            "--dataset",
            str(dataset),
            "--report",
            str(report),
            "--as-of",
            "2026-10-05",
            "--recent-years",
            "5",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    result = json.loads(report.read_text(encoding="utf-8"))
    coverage = result["coverage"]

    assert result["audit"]["target_companies"] == 3
    assert result["audit"]["rows_scanned"] == 4
    assert result["audit"]["matched_rows"] == 3
    assert coverage["any_application"]["companies"] == 2
    assert coverage["recent_application"]["companies"] == 2
    assert coverage["any_awarded_project"]["companies"] == 2
    assert coverage["recent_awarded_project"]["companies"] == 1
    assert coverage["active_awarded_project"]["companies"] == 1
    assert coverage["recent_awarded_project"]["organisation_numbers"] == ["123456789"]
    assert "222222222" not in result["matches_by_organisation_number"]
    assert result["publication_enabled"] is False
    assert result["fresh_cohort_consumed"] is False
