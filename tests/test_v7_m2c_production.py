from __future__ import annotations

from bs4 import BeautifulSoup

from norway_company_agent.canonical_projection import project_canonical_profile, validate_canonical_projection
from norway_company_agent.homepage_careers_signal import extract_careers_links
from norway_company_agent.output_contract import project_terminal_envelope, validate_contract_object
from norway_company_agent.synthesis import build_company_synthesis, validate_company_synthesis


def _careers_rows(html: str) -> list[dict]:
    return extract_careers_links(
        verified_url="https://example.no/",
        final_url="https://www.example.no/",
        soup=BeautifulSoup(html, "lxml"),
        homepage_content_sha256="a" * 64,
    )


def test_extracts_explicit_same_domain_careers_surface() -> None:
    rows = _careers_rows('<nav><a href="/om-oss/jobb-hos-oss">Jobb hos oss</a></nav>')
    assert len(rows) == 1
    assert rows[0]["url"] == "https://www.example.no/om-oss/jobb-hos-oss"
    assert "does not assert an active vacancy" in rows[0]["claim_scope"]


def test_rejects_external_ats_as_company_owned_careers_surface() -> None:
    rows = _careers_rows('<a href="https://jobs.vendor.test/example">Careers</a>')
    assert rows == []


def test_careers_surface_projects_without_becoming_job_posting() -> None:
    careers = _careers_rows('<a href="/careers">Careers</a>')
    profile = {
        "organisation_number": "123456789",
        "name": "EXAMPLE AS",
        "run_metrics": {"requests": 0, "latencies_ms": []},
        "evidence": {
            "website": {
                "field": "website",
                "status": "available",
                "source_type": "registry_linked_company_website",
                "source_url": "https://www.example.no/",
                "retrieved_at": "2026-10-03T00:00:00+00:00",
                "content_sha256": "a" * 64,
                "value": {
                    "final_url": "https://www.example.no/",
                    "identity_assessment": {"publishable": True, "score": 0.99},
                    "careers_links": careers,
                },
            }
        },
    }
    envelope = {
        "run_id": "m2c-test",
        "organisation_number": "123456789",
        "state": "complete",
        "started_at": "2026-10-03T00:00:00+00:00",
        "completed_at": "2026-10-03T00:00:01+00:00",
        "profile": profile,
    }
    contract = project_terminal_envelope(envelope)
    assert not validate_contract_object(contract)
    careers_claims = [claim for claim in contract["claims"] if claim.get("field") == "external.careers_page"]
    assert len(careers_claims) == 1
    assert careers_claims[0]["signal_type"] == "careers_page"
    assert careers_claims[0]["value"]["url"] == "https://www.example.no/careers"
    assert not [claim for claim in contract["claims"] if claim.get("field") == "external.job_posting"]

    canonical = project_canonical_profile(contract)
    assert not validate_canonical_projection(canonical)
    careers_facts = [fact for fact in canonical["canonical_facts"] if fact.get("type") == "careers_page"]
    assert len(careers_facts) == 1
    assert careers_facts[0]["canonical_field"] == "hiring.careers_page"
    assert canonical["canonical_profile"]["data_areas"]["hiring_and_public_activity"] is True
    assert canonical["canonical_profile"]["jobs"] == []

    canonical["synthesis"] = build_company_synthesis(canonical)
    assert not validate_company_synthesis(canonical)
    hiring = canonical["synthesis"]["decision_brief"]["hiring"]
    assert "careers surface" in hiring["text"].lower()
    assert "no specific active job posting" in hiring["text"].lower()
    assert hiring["evidence"]
