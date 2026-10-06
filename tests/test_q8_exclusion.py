from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_q8_exclusion import build_exclusion  # noqa: E402


def _write(path: Path, orgs: list[str]) -> None:
    path.write_text(
        "".join(json.dumps({"organisation_number": org, "name": f"Org {org}"}) + "\n" for org in orgs),
        encoding="utf-8",
    )


def test_build_q8_exclusion_requires_disjoint_exact_union(tmp_path: Path) -> None:
    prior = tmp_path / "prior.jsonl"
    consumed = tmp_path / "consumed.jsonl"
    output = tmp_path / "q8.jsonl"
    report_path = tmp_path / "report.json"
    _write(prior, ["900000001", "900000002"])
    _write(consumed, ["900000003"])

    report = build_exclusion(
        prior,
        consumed,
        output,
        report_path,
        expected_prior=2,
        expected_consumed=1,
        expected_union=3,
    )

    assert report["prior_exclusion_rows"] == 2
    assert report["consumed_fresh_rows"] == 1
    assert report["source_overlap_count"] == 0
    assert report["union_unique_companies"] == 3
    assert output.read_text(encoding="utf-8").count("\n") == 3
    assert json.loads(report_path.read_text(encoding="utf-8"))["exclude_sha256"] == report["exclude_sha256"]


def test_build_q8_exclusion_rejects_overlap(tmp_path: Path) -> None:
    prior = tmp_path / "prior.jsonl"
    consumed = tmp_path / "consumed.jsonl"
    _write(prior, ["900000001"])
    _write(consumed, ["900000001"])

    with pytest.raises(ValueError, match="overlaps prior exclusion"):
        build_exclusion(
            prior,
            consumed,
            tmp_path / "out.jsonl",
            tmp_path / "report.json",
            expected_prior=1,
            expected_consumed=1,
            expected_union=2,
        )


def test_build_q8_exclusion_rejects_bad_count_and_duplicate(tmp_path: Path) -> None:
    prior = tmp_path / "prior.jsonl"
    consumed = tmp_path / "consumed.jsonl"
    _write(prior, ["900000001"])
    _write(consumed, ["900000002"])

    with pytest.raises(ValueError, match="prior exclusion count"):
        build_exclusion(
            prior,
            consumed,
            tmp_path / "out.jsonl",
            tmp_path / "report.json",
            expected_prior=2,
            expected_consumed=1,
            expected_union=3,
        )

    prior.write_text(
        json.dumps({"organisation_number": "900000001"}) + "\n" + json.dumps({"organisation_number": "900000001"}) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate organisation number"):
        build_exclusion(
            prior,
            consumed,
            tmp_path / "out2.jsonl",
            tmp_path / "report2.json",
            expected_prior=2,
            expected_consumed=1,
            expected_union=3,
        )
