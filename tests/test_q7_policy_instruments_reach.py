from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_policy_support_screen_measures_net_new_exact_org_coverage(tmp_path: Path) -> None:
    profiles = tmp_path / "profiles.jsonl"
    profiles.write_text(
        "\n".join(
            json.dumps({"organisation_number": org})
            for org in ("123456789", "987654321", "111111111", "333333333")
        ) + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "output.jsonl"
    output.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "organisation_number": "123456789",
                        "claims": [{"field": "official.support_award", "availability": "available"}],
                    }
                ),
                json.dumps({"organisation_number": "987654321", "claims": []}),
                json.dumps({"organisation_number": "111111111", "claims": []}),
                json.dumps({"organisation_number": "333333333", "claims": []}),
            ]
        ) + "\n",
        encoding="utf-8",
    )
    dataset = tmp_path / "InnovationPolicyData.csv"
    dataset.write_text(
        "orgnr,aktoer,virkemiddel,bidragstype,dato,Innvilget_beloep\n"
        "123456789,Actor A,Grant A,Tilskudd,20230101,100000\n"
        "987654321,Actor B,Grant B,Tilskudd,20220501,250000\n"
        "111111111,Actor B,Grant C,Lån,20200101,500000\n"
        "222222222,Actor C,Wrong org,Tilskudd,20240101,1\n",
        encoding="utf-8",
    )
    report = tmp_path / "report.json"

    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "screen_q7_policy_instruments_reach.py"),
            "--profiles", str(profiles),
            "--output-contract", str(output),
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
    coverage = result["coverage"]
    assert result["audit"]["target_companies"] == 4
    assert result["audit"]["incumbent_support_award_companies"] == 1
    assert result["audit"]["matched_rows"] == 3
    assert coverage["any_policy_support"]["companies"] == 3
    assert coverage["recent_policy_support"]["companies"] == 2
    assert coverage["overlap_with_existing_support_award"]["organisation_numbers"] == ["123456789"]
    assert coverage["net_new_over_existing_support_award"]["organisation_numbers"] == ["111111111", "987654321"]
    assert coverage["recent_net_new_over_existing_support_award"]["organisation_numbers"] == ["987654321"]
    assert "222222222" not in result["matches_by_organisation_number"]
    assert result["publication_enabled"] is False
    assert result["fresh_cohort_consumed"] is False
