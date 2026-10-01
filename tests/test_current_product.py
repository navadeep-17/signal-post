from __future__ import annotations

import gzip
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from build_current_product import CURRENT_PRODUCT_SCHEMA, build_current_html  # noqa: E402
from norway_company_agent.canonical_projection import project_canonical_profile  # noqa: E402

SOURCE = ROOT / "submission" / "final-release-1000-output.jsonl.gz"


def _two_companies() -> list[dict]:
    rows: list[dict] = []
    with gzip.open(SOURCE, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(project_canonical_profile(json.loads(line)))
            if len(rows) == 2:
                break
    assert len(rows) == 2
    return rows


def test_current_product_exposes_v6_scoring_surfaces() -> None:
    body = build_current_html(_two_companies())

    assert CURRENT_PRODUCT_SCHEMA == "signalpost-product-current-v1"
    assert "Find a company, compare it, verify every claim." in body
    assert "Ask Signalpost" in body
    assert "Recent changes" in body
    assert 'id="evidenceDrawer"' in body
    assert 'id="compareA"' in body
    assert 'id="compareB"' in body
    assert 'id="comparison"' in body
    assert 'data-filter="website"' in body
    assert 'data-filter="workforce"' in body
    assert "Data gaps & unknowns" in body
    assert "Signalpost does not rank companies" in body
    assert "missing values remain unknown" in body
    assert "No web search, hidden lookup, or LLM completion occurs in this UI." in body
    assert "const DATA=" in body
    assert "signalpost-ui-v6" in body


def test_current_product_keeps_all_views_on_one_canonical_payload() -> None:
    rows = _two_companies()
    body = build_current_html(rows)

    for row in rows:
        org = str(row["organisation_number"])
        assert org in body

    assert body.count("const DATA=") == 1
    assert "renderProfile()" in body
    assert "renderCompare()" in body
    assert "renderTimeline()" in body
    assert "answerQuestion(q)" in body
    assert "comparison_is_descriptive_only" not in body


def test_current_product_has_responsive_and_accessible_controls() -> None:
    body = build_current_html(_two_companies())

    assert 'class="skip" href="#main"' in body
    assert 'role="tablist"' in body
    assert 'role="dialog"' in body
    assert 'aria-modal="true"' in body
    assert 'aria-live="polite"' in body
    assert "prefers-reduced-motion" in body
    assert "@media(max-width:700px)" in body
    assert "focus-visible" in body
    assert "if(e.key==='Escape')closeEvidence()" in body


def test_current_product_generated_javascript_parses_with_node(tmp_path: Path) -> None:
    node = shutil.which("node")
    if node is None:
        return

    body = build_current_html(_two_companies())
    script = body.split("<script>", 1)[1].split("</script>", 1)[0]
    script_path = tmp_path / "signalpost-current-product.js"
    script_path.write_text(script, encoding="utf-8")
    completed = subprocess.run(
        [node, "--check", str(script_path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
