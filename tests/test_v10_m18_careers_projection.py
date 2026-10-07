from __future__ import annotations

import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import run_signalpost_v8 as v8  # noqa: E402
from norway_company_agent.output_contract import project_terminal_envelope  # noqa: E402


def _fixture() -> tuple[dict, dict]:
    homepage_hash = "a" * 64
    profile = {
        "organisation_number": "123456789",
        "name": "EXAMPLE AS",
        "municipality": "OSLO",
        "run_metrics": {"requests": 1, "latencies_ms": [10]},
        "evidence": {
            "website": {
                "field": "website",
                "status": "available",
                "source_type": "registry_linked_company_website",
                "source_url": "https://www.example.no/",
                "retrieved_at": "2026-10-07T00:00:00+00:00",
                "content_sha256": homepage_hash,
                "value": {
                    "final_url": "https://www.example.no/",
                    "description": "Example builds industrial software.",
                    "identity_assessment": {
                        "status": "exact",
                        "publishable": True,
                        "score": 0.99,
                    },
                    "careers_links": [
                        {
                            "url": "https://www.example.no/careers",
                            "anchor_text": "Careers",
                            "homepage_url": "https://www.example.no/",
                            "homepage_content_sha256": homepage_hash,
                            "evidence_span": "Homepage link: Careers",
                            "claim_scope": (
                                "Exact verified company homepage explicitly links to a same-company-host careers surface. "
                                "This is hiring presence only and does not assert an active vacancy."
                            ),
                        }
                    ],
                },
            }
        },
    }
    envelope = {
        "run_id": "m18-test",
        "organisation_number": "123456789",
        "state": "complete",
        "started_at": "2026-10-07T00:00:00+00:00",
        "completed_at": "2026-10-07T00:00:01+00:00",
        "profile": profile,
    }
    return project_terminal_envelope(envelope), profile


def test_v8_postprocess_materializes_careers_presence_without_job_claim(
    tmp_path: Path,
    monkeypatch,
) -> None:
    row, profile = _fixture()
    output = tmp_path / "output.jsonl"
    report = tmp_path / "report.json"
    work = tmp_path / "work"
    product = tmp_path / "product.html"
    work.mkdir()
    output.write_text(json.dumps(row) + "\n", encoding="utf-8")
    (work / "profiles.jsonl").write_text(json.dumps(profile) + "\n", encoding="utf-8")
    report.write_text(
        json.dumps({
            "passed": True,
            "canonical_projection": {},
            "synthesis": {},
            "checks": {},
        }),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        v8.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0),
    )

    assert v8._project_q4_feed_activity(
        output_path=output,
        report_path=report,
        work_dir=work,
        product_output=product,
        expected_count=1,
    ) is True

    result = json.loads(output.read_text(encoding="utf-8").strip())
    careers = [
        claim for claim in result["claims"]
        if claim.get("field") == "external.careers_page"
    ]
    jobs = [
        claim for claim in result["claims"]
        if claim.get("field") == "external.job_posting"
    ]
    assert len(careers) == 1
    assert jobs == []
    assert careers[0]["signal_type"] == "careers_page"
    assert "does not assert an active vacancy" in careers[0]["claim_scope"]

    hiring_facts = result["canonical_profile"]["hiring_signals"]
    assert len(hiring_facts) == 1
    assert hiring_facts[0]["canonical_field"] == "hiring.careers_page"

    hiring = result["synthesis"]["decision_brief"]["hiring"]
    assert "hiring-presence signal only" in hiring["text"]
    assert "no active vacancy is established" in hiring["text"]
    assert len(hiring["evidence"]) == 1
    assert hiring["evidence"][0]["source_url"] == "https://www.example.no/"

    saved_report = json.loads(report.read_text(encoding="utf-8"))
    projection = saved_report["canonical_projection"]["careers_presence_projection"]
    assert projection["published_claims"] == 1
    assert projection["companies_with_published_claims"] == 1
    assert projection["network_requests_added_by_projection"] == 0
