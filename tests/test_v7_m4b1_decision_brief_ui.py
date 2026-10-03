from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from build_v6_ui import _pool_evidence_payload, build_v6_html  # noqa: E402
from norway_company_agent.canonical_projection import project_canonical_profile  # noqa: E402

SOURCE = ROOT / "submission" / "final-release-1000-output.jsonl.gz"


def _one_company() -> dict:
    with gzip.open(SOURCE, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                return project_canonical_profile(json.loads(line))
    raise AssertionError("certified corpus is empty")


def test_decision_brief_payload_is_compact_and_keeps_temporal_context() -> None:
    company = {
        "areas": {},
        "synthesis": {
            "sections": [],
            "decisionBrief": {
                "how_big_is_it": {
                    "key": "how_big_is_it",
                    "text": "Revenue is published for the latest reporting period.",
                    "evidence": [
                        {
                            "id": "ev-financial",
                            "url": "https://example.test/report",
                            "sourceClass": "official",
                            "retrievedAt": "2026-10-03T06:00:00Z",
                            "reportingPeriod": {"tilDato": "2025-12-31"},
                            "span": "revenue=12500000",
                            "hash": "a" * 64,
                        }
                    ],
                },
                "what_changed": {
                    "key": "what_changed",
                    "text": "A registry change was published.",
                    "evidence": [],
                },
                "what_is_unknown": ["No active job posting is published."],
            },
        },
    }

    payload = _pool_evidence_payload([company])
    decision = payload["companies"][0]["synthesis"]["decisionBrief"]

    assert set(decision) == {"how_big_is_it"}
    item = decision["how_big_is_it"]
    assert item["evidenceRefs"] == ["ev-financial"]
    assert item["dates"] == ["Period ending 2025-12-31"]
    assert "evidence" not in item
    assert payload["evidence"]["ev-financial"]["url"] == "https://example.test/report"
    assert "reportingPeriod" not in payload["evidence"]["ev-financial"]


def test_v6_ui_promotes_v7_decision_brief_as_primary_company_brief() -> None:
    body = build_v6_html([_one_company()])

    assert "function spDecisionBriefCards(synth)" in body
    assert "data-decision-key" in body
    assert "Decision brief" in body
    assert "What it does" in body
    assert "Leadership" in body
    assert "Digital footprint" in body
    assert "sourceButtons(item.evidence||[],'Evidence')" in body
    assert '"decisionBrief":' in body


def test_decision_brief_keeps_existing_legacy_sections_as_fallback() -> None:
    body = build_v6_html([_one_company()])

    assert "if(!cards)return" in body
    assert "spDecisionBaseRenderProfile()" in body
