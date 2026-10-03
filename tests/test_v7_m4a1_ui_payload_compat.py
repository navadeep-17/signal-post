from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.external_contract import project_profile_handle_observations  # noqa: E402
from norway_company_agent.output_contract import project_terminal_envelope  # noqa: E402
from v6_payload_adapter import compact_company_v6  # noqa: E402


def _contract() -> dict:
    homepage_hash = "a" * 64
    profile = {
        "organisation_number": "123456789",
        "run_metrics": {"requests": 1, "latencies_ms": [10]},
        "evidence": {
            "website": {
                "field": "website",
                "status": "available",
                "source_type": "registry_linked_company_website",
                "source_url": "https://www.example.no/",
                "retrieved_at": "2026-10-03T00:00:00+00:00",
                "content_sha256": homepage_hash,
                "value": {
                    "final_url": "https://www.example.no/",
                    "description": "Example builds industrial software.",
                    "identity_assessment": {"publishable": True, "score": 0.99},
                    "careers_links": [
                        {
                            "url": "https://www.example.no/careers",
                            "anchor_text": "Careers",
                            "homepage_url": "https://www.example.no/",
                            "homepage_content_sha256": homepage_hash,
                            "evidence_span": "Careers → https://www.example.no/careers",
                            "claim_scope": "Verified company-owned careers page; does not assert an active vacancy.",
                        }
                    ],
                },
            }
        },
    }
    envelope = {
        "run_id": "m4a1-test",
        "organisation_number": "123456789",
        "state": "complete",
        "started_at": "2026-10-03T00:00:00+00:00",
        "completed_at": "2026-10-03T00:00:01+00:00",
        "profile": profile,
    }
    base = project_terminal_envelope(envelope)
    return project_profile_handle_observations(base, profile)


def test_v6_adapter_exposes_current_careers_canonical_fact() -> None:
    compact = compact_company_v6(_contract())

    hiring = compact["areas"]["hiring_and_public_activity"]
    careers = [fact for fact in hiring if fact.get("type") == "careers_page"]

    assert len(careers) == 1
    assert careers[0]["field"] == "hiring.careers_page"
    assert careers[0]["value"]["url"] == "https://www.example.no/careers"
    assert careers[0]["availability"] == "available"
    assert careers[0]["evidence"][0]["url"] == "https://www.example.no/"


def test_v6_adapter_preserves_current_decision_brief_evidence_trace() -> None:
    compact = compact_company_v6(_contract())

    brief = compact["synthesis"]["decisionBrief"]
    description = brief["what_does_it_do"]

    assert "industrial software" in description["text"]
    assert description["evidence"]
    trace = description["evidence"][0]
    assert trace["url"] == "https://www.example.no/"
    assert trace["retrievedAt"] == "2026-10-03T00:00:00+00:00"
    assert trace["span"] == "Example builds industrial software."
    assert trace["hash"] == "a" * 64


def test_v6_adapter_does_not_turn_careers_page_into_job_posting() -> None:
    compact = compact_company_v6(_contract())
    hiring = compact["areas"]["hiring_and_public_activity"]

    assert any(fact.get("type") == "careers_page" for fact in hiring)
    assert not any(fact.get("type") == "job_posting" for fact in hiring)
