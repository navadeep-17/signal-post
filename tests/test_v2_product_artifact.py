from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_submission_prototype import build_html  # noqa: E402
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

    expected = build_html(projected, title=TITLE)
    actual = PRODUCT.read_text(encoding="utf-8")
    assert actual == expected
    assert len(actual.encode("utf-8")) == 17544893
    assert "Signalpost evidence workspace" in actual
    assert "Company intelligence you can trace back to evidence." in actual
    assert "Claim boundary:" in actual
    assert 'const DATA=' in actual
