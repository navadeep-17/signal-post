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

from build_v2_product import compact_company  # noqa: E402
from build_v6_ui import V6_UI_SCHEMA, build_v6_html  # noqa: E402
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


def _company_with_industry() -> dict:
    with gzip.open(SOURCE, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = project_canonical_profile(json.loads(line))
            compact = compact_company(row)
            if any(
                fact.get("type") == "industry" and fact.get("availability") == "available"
                for fact in compact["areas"]["company_record"]
            ):
                return row
    raise AssertionError("certified corpus contains no compact available industry fact")


def _company_with_unavailable_canonical_fact() -> tuple[dict, str]:
    with gzip.open(SOURCE, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = project_canonical_profile(json.loads(line))
            for fact in row.get("canonical_facts") or []:
                state = fact.get("availability")
                if state in {"not_available", "blocked", "not_applicable", "ambiguous", "failed"}:
                    return row, str(state)
    raise AssertionError("certified corpus contains no unavailable canonical fact")


def test_v6_ui_exposes_scoring_surfaces() -> None:
    body = build_v6_html(_two_companies())

    assert V6_UI_SCHEMA == "signalpost-ui-v6"
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


def test_v6_ui_keeps_views_on_one_canonical_payload() -> None:
    rows = _two_companies()
    body = build_v6_html(rows)

    for row in rows:
        org = str(row["organisation_number"])
        assert org in body

    assert body.count("const DATA=") == 1
    assert "renderProfile()" in body
    assert "renderCompare()" in body
    assert "renderTimeline()" in body
    assert "answerQuestion(q)" in body


def test_v6_ui_search_indexes_existing_compact_industry_fact() -> None:
    row = _company_with_industry()
    compact = compact_company(row)
    industry = next(
        fact
        for fact in compact["areas"]["company_record"]
        if fact.get("type") == "industry" and fact.get("availability") == "available"
    )
    body = build_v6_html([row])

    assert industry.get("value") is not None
    assert "function industrySearchText(x)" in body
    assert "firstFact(x,'industry')" in body
    assert "norm(searchText(x)).includes(q)" in body
    assert 'placeholder="Search name, org no., municipality, industry"' in body


def test_v6_ui_compare_preserves_existing_canonical_availability_state() -> None:
    row, state = _company_with_unavailable_canonical_fact()
    body = build_v6_html([row])

    assert f'"availability":"{state}"' in body
    assert "function availabilityLabel(state)" in body
    assert "function availabilityCompareCell(rows)" in body
    assert "Canonical availability state" in body
    assert "No value is substituted." in body
    assert "No canonical fact exists for this comparison field." in body
    assert "never substitutes zero or a generic missing value" in body


def test_v6_ui_has_responsive_and_accessible_controls() -> None:
    body = build_v6_html(_two_companies())

    assert 'class="skip" href="#main"' in body
    assert 'role="tablist"' in body
    assert 'role="dialog"' in body
    assert 'aria-modal="true"' in body
    assert 'aria-live="polite"' in body
    assert "prefers-reduced-motion" in body
    assert "@media(max-width:700px)" in body
    assert "focus-visible" in body
    assert "if(e.key==='Escape')closeEvidence()" in body


def test_v6_ui_generated_javascript_parses_with_node(tmp_path: Path) -> None:
    node = shutil.which("node")
    if node is None:
        return

    body = build_v6_html(_two_companies())
    script = body.split("<script>", 1)[1].split("</script>", 1)[0]
    script_path = tmp_path / "signalpost-v6-ui.js"
    script_path.write_text(script, encoding="utf-8")
    completed = subprocess.run(
        [node, "--check", str(script_path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
