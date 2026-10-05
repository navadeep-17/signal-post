from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "compare_bulk_exact_org_union.py"
spec = importlib.util.spec_from_file_location("compare_bulk_exact_org_union", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_union_comparator_counts_unique_contribution_and_overlap(tmp_path: Path) -> None:
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    consumed = tmp_path / "consumed.jsonl"
    _write_jsonl(
        a,
        [
            {"organisation_number": "111111111", "website": "https://a.example"},
            {"organisation_number": "222222222"},
        ],
    )
    _write_jsonl(
        b,
        [
            {"organisation_number": "222222222", "emails": ["post@b.example"]},
            {"organisation_number": "333333333", "phone": "12345678"},
        ],
    )
    _write_jsonl(
        consumed,
        [{"organisation_number": f"{i:09d}"} for i in range(1, 98)]
        + [
            {"organisation_number": "111111111"},
            {"organisation_number": "222222222"},
            {"organisation_number": "333333333"},
        ],
    )
    report, union = module.compare(
        {"a": a, "b": b},
        cohort_size=1000,
        consumed_100_path=consumed,
        source_reports={},
        original_requests={"a": 1, "b": 2},
    )
    assert report["union_exact_company_hits"] == 3
    assert report["companies_in_multiple_sources"] == 1
    assert report["source_stats"]["a"]["unique_contribution"] == 1
    assert report["source_stats"]["b"]["unique_contribution"] == 1
    assert report["pairwise_overlaps"][0]["companies"] == 1
    assert report["union_website_candidate_companies"] == 1
    assert report["union_email_candidate_companies"] == 1
    assert report["union_phone_candidate_companies"] == 1
    assert report["original_external_requests_total"] == 3
    assert report["union_hits_per_original_request"] == 1.0
    assert report["consumed_100"]["union_exact_company_hits"] == 3
    assert set(union) == {"111111111", "222222222", "333333333"}


def test_union_merges_candidate_fields_without_reassigning_identity(tmp_path: Path) -> None:
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    _write_jsonl(a, [{"organisation_number": "111111111", "websites": ["https://a.example"]}])
    _write_jsonl(
        b,
        [{"organisation_number": "111111111", "website": "https://b.example", "email": "x@example.test"}],
    )
    report, union = module.compare(
        {"a": a, "b": b},
        cohort_size=1000,
        consumed_100_path=None,
        source_reports={},
        original_requests={},
    )
    row = union["111111111"]
    assert row["sources"] == ["a", "b"]
    assert row["websites"] == ["https://a.example", "https://b.example"]
    assert row["emails"] == ["x@example.test"]
    assert report["companies_in_multiple_sources"] == 1


def test_duplicate_org_in_one_upstream_artifact_fails_closed(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    _write_jsonl(
        source,
        [
            {"organisation_number": "111111111"},
            {"organisation_number": "111111111"},
        ],
    )
    try:
        module.load_source(source)
    except ValueError as exc:
        assert "duplicate org" in str(exc)
    else:
        raise AssertionError("expected duplicate source identity to fail")
