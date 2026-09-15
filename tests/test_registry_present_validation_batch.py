from __future__ import annotations

import gzip
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "select_registry_present_validation_batch.py"


def _write_universe(path: Path, orgs: list[str]) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for index, org in enumerate(orgs):
            handle.write(json.dumps({"organisation_number": org, "name": f"Company {index}"}) + "\n")


def _write_registry(path: Path, orgs: list[str]) -> None:
    header = "organisasjonsnummer;navn;organisasjonsform.kode;antallAnsatte;konkurs;underAvvikling;forretningsadresse.kommune;forretningsadresse.kommunenummer;naeringskode1.kode;naeringskode1.beskrivelse;hjemmeside;sisteInnsendteAarsregnskap\n"
    with gzip.open(path, "wt", encoding="utf-8-sig", newline="") as handle:
        handle.write(header)
        for index, org in enumerate(orgs):
            handle.write(f"{org};Registry {index};AS;1;false;false;OSLO;0301;62.010;IT;;2025\n")


def test_registry_present_selector_excludes_stale_and_prior_rows(tmp_path: Path):
    universe = tmp_path / "universe.jsonl.gz"
    registry = tmp_path / "registry.csv"
    exclude = tmp_path / "exclude.jsonl"
    output = tmp_path / "selected.jsonl"
    report = tmp_path / "report.json"

    _write_universe(universe, ["900000001", "900000002", "900000003", "900000004", "900000005"])
    _write_registry(registry, ["900000001", "900000002", "900000004", "900000005"])
    exclude.write_text(json.dumps({"organisation_number": "900000001"}) + "\n", encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--universe", str(universe),
            "--exclude", str(exclude),
            "--registry-bulk", str(registry),
            "--count", "3",
            "--seed", "42",
            "--output", str(output),
            "--report", str(report),
        ],
        check=True,
        cwd=ROOT,
    )

    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    selected = {row["organisation_number"] for row in rows}
    assert selected == {"900000002", "900000004", "900000005"}
    assert "900000003" not in selected
    metadata = json.loads(report.read_text(encoding="utf-8"))
    assert metadata["count"] == 3
    assert metadata["excluded_rows"] == 1
    assert metadata["missing_registry_count"] == 0
    assert metadata["overlap_count"] == 0
    assert metadata["eligible_rows"] == 3
