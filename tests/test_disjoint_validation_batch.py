import gzip
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "select_disjoint_validation_batch.py"


def _write_jsonl(path: Path, rows: list[dict]):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def test_disjoint_sampler_is_deterministic_and_excludes_manifest(tmp_path):
    universe = tmp_path / "universe.jsonl.gz"
    exclude = tmp_path / "exclude.jsonl"
    out1 = tmp_path / "validation-1.jsonl"
    out2 = tmp_path / "validation-2.jsonl"
    report1 = tmp_path / "report-1.json"
    report2 = tmp_path / "report-2.json"

    rows = [{"organisation_number": f"{900000000 + index:09d}", "name": f"Company {index}"} for index in range(30)]
    _write_jsonl(universe, rows)
    _write_jsonl(exclude, rows[:10])

    base = [
        sys.executable,
        str(SCRIPT),
        "--universe",
        str(universe),
        "--exclude",
        str(exclude),
        "--count",
        "8",
        "--seed",
        "12345",
    ]
    subprocess.run(base + ["--output", str(out1), "--report", str(report1)], check=True)
    subprocess.run(base + ["--output", str(out2), "--report", str(report2)], check=True)

    assert out1.read_bytes() == out2.read_bytes()
    selected = [json.loads(line) for line in out1.read_text().splitlines() if line.strip()]
    selected_orgs = {row["organisation_number"] for row in selected}
    excluded_orgs = {row["organisation_number"] for row in rows[:10]}
    assert len(selected) == 8
    assert not (selected_orgs & excluded_orgs)
    assert all(row["evaluation_split"] == "zero_overlap_validation" for row in selected)
    assert all(row["sample_slice"] == "external_precision_validation" for row in selected)

    report = json.loads(report1.read_text())
    assert report["overlap_count"] == 0
    assert report["count"] == 8
    assert report["output_sha256"] == json.loads(report2.read_text())["output_sha256"]


def test_disjoint_sampler_rejects_duplicate_exclude_manifest(tmp_path):
    universe = tmp_path / "universe.jsonl"
    exclude = tmp_path / "exclude.jsonl"
    output = tmp_path / "out.jsonl"
    report = tmp_path / "report.json"
    rows = [{"organisation_number": "900000001"}, {"organisation_number": "900000002"}]
    _write_jsonl(universe, rows)
    _write_jsonl(exclude, [rows[0], rows[0]])

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--universe",
            str(universe),
            "--exclude",
            str(exclude),
            "--count",
            "1",
            "--output",
            str(output),
            "--report",
            str(report),
        ],
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "duplicate organisation numbers" in (result.stderr + result.stdout)
