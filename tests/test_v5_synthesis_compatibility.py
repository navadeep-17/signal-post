from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.synthesis import build_company_synthesis  # noqa: E402


def test_no_registry_change_keeps_pre_v5_what_changed_shape() -> None:
    contract = {
        "organisation_number": "123456789",
        "canonical_facts": [],
        "canonical_profile": {
            "data_areas": {
                "company_record": False,
                "financials": False,
                "people_and_locations": False,
                "company_website": False,
                "hiring_and_public_activity": False,
            }
        },
        "changes": [],
        "evidence": [],
    }

    synthesis = build_company_synthesis(contract)

    assert synthesis["what_changed"] == {
        "text": "No material change is published for this run; this does not imply that nothing changed outside checked sources.",
        "change_count": 0,
        "changes": [],
    }
    assert "registry_changes" not in synthesis["what_changed"]
    assert "evidence_ids" not in synthesis["what_changed"]
    assert "source_boundary" not in synthesis["what_changed"]
