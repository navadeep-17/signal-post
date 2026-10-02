from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from build_v6_ui import build_v6_html  # noqa: E402
from norway_company_agent.canonical_projection import project_canonical_profile  # noqa: E402

SOURCE = ROOT / "submission" / "final-release-1000-output.jsonl.gz"


def _rows() -> list[dict]:
    rows: list[dict] = []
    with gzip.open(SOURCE, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(project_canonical_profile(json.loads(line)))
            if len(rows) == 2:
                break
    assert len(rows) == 2
    return rows


def test_v6_polish_supports_find_compare_verify_flow() -> None:
    body = build_v6_html(_rows())

    assert 'id="globalFinderTrigger"' in body
    assert "modal.id='companyFinder'" in body
    assert "Ctrl or Command K" in body
    assert "Search company, organisation number, industry or place" in body
    assert "Verify all evidence" in body
    assert "Compare this company" in body
    assert 'id="compareDiffToggle"' in body
    assert "Differences only" in body
    assert "Evidence coverage by data area" in body
    assert "Copy link" in body


def test_v6_polish_keeps_availability_semantics_visible() -> None:
    body = build_v6_html(_rows())

    assert "function spuxAvailabilityLabel(value)" in body
    assert "f.availability==='available'" in body
    assert "spuxAreaState" in body
    assert "No record" in body
    assert "Not published" in body


def test_v6_polish_has_mobile_first_navigation_and_compare_rules() -> None:
    body = build_v6_html(_rows())

    assert "@media(max-width:700px)" in body
    assert "grid-template-columns:repeat(4,minmax(0,1fr))" in body
    assert ".compare-label{grid-column:1/-1" in body
    assert ".company-finder{padding:0;align-items:flex-end}" in body
    assert ".drawer{top:auto;left:0;right:0;bottom:0" in body
    assert ".hero p{display:none}" in body
    assert ".summary{display:none}" in body


def test_v6_polish_assets_are_bundled_once() -> None:
    body = build_v6_html(_rows())

    assert body.count("function spuxInstallFinder()") == 1
    assert body.count("function spuxInstallCompareTools()") == 1
    assert body.count("const spuxBaseOpenEvidence=openEvidence") == 1
