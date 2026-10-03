from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from build_v6_ui import build_v6_html  # noqa: E402
from norway_company_agent.external_contract import project_profile_handle_observations  # noqa: E402
from norway_company_agent.output_contract import project_terminal_envelope  # noqa: E402


def _contract_with_careers() -> dict:
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
        "run_id": "m4b2-test",
        "organisation_number": "123456789",
        "state": "complete",
        "started_at": "2026-10-03T00:00:00+00:00",
        "completed_at": "2026-10-03T00:00:01+00:00",
        "profile": profile,
    }
    base = project_terminal_envelope(envelope)
    return project_profile_handle_observations(base, profile)


def test_careers_signal_ui_exposes_filter_badge_and_boundary() -> None:
    body = build_v6_html([_contract_with_careers()])

    assert "spCareersInstallFilter" in body
    assert "b.dataset.filter='careers'" in body
    assert "careers-badge" in body
    assert "Careers surface found." in body
    assert "This does not establish an active vacancy." in body
    assert "https://www.example.no/careers" in body
    assert "Careers evidence" in body


def test_grounded_hiring_answer_distinguishes_careers_page_from_job_posting() -> None:
    body = build_v6_html([_contract_with_careers()])

    assert "Are they hiring?" in body
    assert "Hiring evidence" in body
    assert "spJobFacts(x)" in body
    assert "spCareersFacts(x)" in body
    assert "A verified company-owned careers page is published, but the current evidence does not establish an active vacancy." in body
    assert "No qualified job posting or verified company-owned careers page is published in the current evidence." in body
