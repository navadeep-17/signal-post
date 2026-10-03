from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_search_discovery as runner  # noqa: E402


def test_conflicting_explicit_org_number_always_quarantines_candidate() -> None:
    assessment = {
        "status": "exact",
        "score": 1.0,
        "publishable": True,
        "reasons": ["target name matched"],
        "method": "fixture",
    }

    result = runner._conflict_quarantine(assessment)

    assert result["status"] == "review"
    assert result["publishable"] is False
    assert result["score"] <= 0.8
    assert result["method"] == "v9_search_candidate_conflicting_org_guard_v1"
    assert any("another entity" in reason for reason in result["reasons"])


def test_conflict_quarantine_is_conservative_without_prior_assessment() -> None:
    result = runner._conflict_quarantine(None)

    assert result["status"] == "review"
    assert result["publishable"] is False
    assert result["score"] <= 0.8


def test_runner_source_persists_only_verified_candidate_pages() -> None:
    source = (ROOT / "scripts" / "run_search_discovery.py").read_text(encoding="utf-8")

    assert 'if verified_website is not None:' in source
    assert 'row["evidence"]["website_search_candidate"] = verified_website' in source
    assert 'quarantined_candidate_pages_persisted": False' in source
    assert 'row["evidence"]["website_search_candidate"] = website' not in source


def test_runner_uses_current_bounded_homepage_fetcher() -> None:
    source = (ROOT / "scripts" / "run_search_discovery.py").read_text(encoding="utf-8")

    assert "fetch_bounded_homepage(" in source
    assert "from norway_company_agent.final_site_discovery import" in source
    assert "fetch_website(" not in source
