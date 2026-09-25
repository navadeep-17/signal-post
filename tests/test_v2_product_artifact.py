from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_v2_product import build_v2_html  # noqa: E402
from norway_company_agent.canonical_projection import project_canonical_profile, validate_canonical_projection  # noqa: E402
from norway_company_agent.output_contract import validate_contract_object  # noqa: E402

SOURCE = ROOT / "submission" / "final-release-1000-output.jsonl.gz"
PRODUCT = ROOT / "submission" / "signalpost-v2.html"
TITLE = "Signalpost V2 — evidence-backed company intelligence"


def _source_rows() -> list[dict]:
    rows = []
    with gzip.open(SOURCE, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def test_embedded_v2_product_is_exactly_rebuilt_from_certified_evidence() -> None:
    rows = _source_rows()
    assert len(rows) == 1000
    projected = []
    for row in rows:
        assert validate_contract_object(row) == []
        item = project_canonical_profile(row)
        assert validate_canonical_projection(item) == []
        projected.append(item)

    expected = build_v2_html(projected, title=TITLE)
    actual = PRODUCT.read_text(encoding="utf-8")
    assert actual == expected
    assert len(actual.encode("utf-8")) > 1_000_000
    assert "Signalpost V2" in actual
    assert "Builderr canonical view" in actual
    assert "Company record" in actual
    assert "Financials" in actual
    assert "People & locations" in actual
    assert "Company website" in actual
    assert "Hiring & public activity" in actual
    assert "A generic careers page is not a hiring fact." in actual
    assert "What the company does" in actual
    assert "Financial snapshot" in actual
    assert "People & footprint" in actual
    assert "Website & public activity" in actual
    assert "What changed" in actual
    assert "What remains unknown" in actual
    assert "Deterministic zero-network synthesis" in actual
    assert "Latest financials" in actual
    assert "Who runs it?" in actual
    assert "const DATA=" in actual
