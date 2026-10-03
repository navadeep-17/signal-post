from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from build_v6_ui import V6_PAYLOAD_FORMAT, _pool_evidence_payload, build_v6_html  # noqa: E402
from norway_company_agent.canonical_projection import project_canonical_profile  # noqa: E402
from v6_payload_adapter import compact_company_v6  # noqa: E402

SOURCE = ROOT / "submission" / "final-release-1000-output.jsonl.gz"
V2_HTML = ROOT / "submission" / "signalpost-v2.html"


def _rows(limit: int | None = None) -> list[dict]:
    rows: list[dict] = []
    with gzip.open(SOURCE, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            rows.append(project_canonical_profile(json.loads(line)))
            if limit is not None and len(rows) >= limit:
                break
    return rows


def test_v6_pools_evidence_without_changing_runtime_contract() -> None:
    companies = [compact_company_v6(row) for row in _rows(4)]
    assert all("decisionBrief" in company["synthesis"] for company in companies)

    raw_bytes = len(json.dumps(companies, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    pooled = _pool_evidence_payload(companies)
    pooled_bytes = len(json.dumps(pooled, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))

    assert pooled["format"] == V6_PAYLOAD_FORMAT
    assert pooled["evidence"]
    assert pooled_bytes < raw_bytes
    for company in pooled["companies"]:
        for facts in company["areas"].values():
            for fact in facts:
                assert "evidence" not in fact
                assert "evidenceRefs" in fact
        for section in company["synthesis"]["sections"]:
            assert "sources" not in section
            assert "sourceRefs" in section
        decision = company["synthesis"]["decisionBrief"]
        assert set(decision).issubset(
            {
                "what_is_this_company",
                "what_does_it_do",
                "how_big_is_it",
                "who_runs_it",
                "hiring",
                "digital_footprint",
            }
        )
        for item in decision.values():
            assert "key" not in item
            assert "evidence" not in item
            for evidence_id in item.get("evidenceRefs", []):
                assert evidence_id in pooled["evidence"]


def test_v6_full_certified_workspace_is_materially_smaller_than_v2() -> None:
    rows = _rows()
    assert len(rows) == 1000
    body = build_v6_html(rows)
    v6_bytes = len(body.encode("utf-8"))
    v2_bytes = V2_HTML.stat().st_size

    # This remains a hard UX guard while adding the compact decision brief.
    assert v6_bytes < v2_bytes * 0.80, (
        f"V6 HTML is {v6_bytes:,} bytes vs V2 {v2_bytes:,}; expected at least 20% reduction"
    )
