from __future__ import annotations

from pathlib import Path
import sys

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.canonical_projection import project_canonical_profile, validate_canonical_projection  # noqa: E402
from norway_company_agent.external_contract import project_profile_handle_observations  # noqa: E402
from norway_company_agent.homepage_careers_signal import extract_careers_links  # noqa: E402
from norway_company_agent.output_contract import project_terminal_envelope, validate_contract_object  # noqa: E402


def _careers_rows(html: str) -> list[dict]:
    return extract_careers_links(
        verified_url="https://example.no/",
        final_url="https://www.example.no/",
        soup=BeautifulSoup(html, "lxml"),
        homepage_content_sha256="a" * 64,
    )


def _profile_with_careers(careers: list[dict]) -> dict:
    return {
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


def _base_contract(profile: dict) -> dict:
    envelope = {
        "run_id": "m2c-test",
        "organisation_number": "123456789",
        "state": "complete",
        "started_at": "2026-10-03T00:00:00+00:00",
        "completed_at": "2026-10-03T00:00:01+00:00",
        "profile": profile,
    }
    return project_terminal_envelope(envelope)


def test_extracts_explicit_same_domain_careers_surface() -> None:
    rows = _careers_rows('<nav><a href="/om-oss/jobb-hos-oss">Jobb hos oss</a></nav>')
    assert len(rows) == 1
    assert rows[0]["url"] == "https://www.example.no/om-oss/jobb-hos-oss"
    assert "does not assert an active vacancy" in rows[0]["claim_scope"]


def test_rejects_external_ats_as_company_owned_careers_surface() -> None:
    rows = _careers_rows('<a href="https://jobs.vendor.test/example">Careers</a>')
    assert rows == []


def test_careers_surface_projects_to_contract_and_canonical_without_job_posting() -> None:
    careers = _careers_rows('<a href="/careers">Careers</a>')
    profile = _profile_with_careers(careers)
    contract = project_profile_handle_observations(_base_contract(profile), profile)

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


def test_careers_projection_is_idempotent() -> None:
    careers = _careers_rows('<a href="/careers">Careers</a>')
    profile = _profile_with_careers(careers)
    once = project_profile_handle_observations(_base_contract(profile), profile)
    twice = project_profile_handle_observations(once, profile)

    assert [c for c in twice["claims"] if c.get("field") == "external.careers_page"] == [
        c for c in once["claims"] if c.get("field") == "external.careers_page"
    ]
    assert len([e for e in twice["evidence"] if str(e.get("id") or "").startswith("ev-careers-")]) == 1


def test_careers_projection_rejects_mismatched_homepage_snapshot() -> None:
    careers = _careers_rows('<a href="/careers">Careers</a>')
    careers[0]["homepage_content_sha256"] = "b" * 64
    profile = _profile_with_careers(careers)
    contract = project_profile_handle_observations(_base_contract(profile), profile)

    assert not [claim for claim in contract["claims"] if claim.get("field") == "external.careers_page"]
