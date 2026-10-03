from __future__ import annotations

from copy import deepcopy

from norway_company_agent.canonical_projection import project_canonical_profile, validate_canonical_projection
from norway_company_agent.first_party_activity import extract_careers_signals, project_first_party_activity_claims
from norway_company_agent.output_contract import validate_contract_object


def _profile(*pages: dict, publishable: bool = True) -> dict:
    return {
        "organisation_number": "123456789",
        "evidence": {
            "website": {
                "status": "available",
                "source_url": "https://example.no/",
                "retrieved_at": "2026-10-03T06:00:00Z",
                "value": {
                    "final_url": "https://example.no/",
                    "identity_assessment": {"publishable": publishable},
                    "pages": list(pages),
                },
            }
        },
    }


def _page(url: str, title: str, text: str, digest: str = "abc123") -> dict:
    return {
        "url": url,
        "title": title,
        "main_text_excerpt": text,
        "identity_text_excerpt": "",
        "content_sha256": digest,
    }


def _contract() -> dict:
    return {
        "organisation_number": "123456789",
        "run": {
            "run_id": "v7-m2-test",
            "started_at": "2026-10-03T06:00:00Z",
            "completed_at": "2026-10-03T06:00:01Z",
            "terminal_status": "completed",
        },
        "claims": [],
        "evidence": [],
        "changes": [],
        "errors": [],
        "operations": {"requests": 0, "runtime_ms": 1000, "third_party_cost_usd": 0.0},
    }


def test_verified_generic_careers_page_is_a_hiring_signal_but_not_a_job_posting() -> None:
    profile = _profile(
        _page(
            "https://example.no/careers",
            "Careers — Example AS",
            "Join our team and explore career opportunities with Example AS.",
            "careershash",
        )
    )

    signals = extract_careers_signals(profile)
    assert len(signals) == 1
    assert signals[0]["url"] == "https://example.no/careers"

    projected = project_first_party_activity_claims(_contract(), profile)
    fields = [claim["field"] for claim in projected["claims"]]
    assert fields.count("external.careers_signal") == 1
    assert fields.count("external.job_posting") == 0
    assert validate_contract_object(projected) == []

    canonical = project_canonical_profile(projected)
    assert validate_canonical_projection(canonical) == []
    careers = [fact for fact in canonical["canonical_facts"] if fact["type"] == "careers_signal"]
    assert len(careers) == 1
    assert careers[0]["canonical_field"] == "hiring.careers_signal"
    assert canonical["canonical_profile"]["data_areas"]["hiring_and_public_activity"] is True


def test_careers_signal_never_publishes_from_unverified_site() -> None:
    profile = _profile(
        _page(
            "https://example.no/",
            "Example AS",
            "Careers · Join our team",
        ),
        publishable=False,
    )
    assert extract_careers_signals(profile) == []
    projected = project_first_party_activity_claims(_contract(), profile)
    assert all(claim["field"] != "external.careers_signal" for claim in projected["claims"])


def test_careers_signal_is_idempotent_and_evidence_backed() -> None:
    profile = _profile(
        _page(
            "https://example.no/",
            "Example AS",
            "About us. Careers. Contact.",
            "homepagehash",
        )
    )
    once = project_first_party_activity_claims(_contract(), profile)
    twice = project_first_party_activity_claims(deepcopy(once), profile)
    assert once == twice

    claim = next(item for item in twice["claims"] if item["field"] == "external.careers_signal")
    evidence_id = claim["evidence_ids"][0]
    ev = next(item for item in twice["evidence"] if item["id"] == evidence_id)
    assert ev["source_url"] == "https://example.no/"
    assert ev["retrieved_at"] == "2026-10-03T06:00:00Z"
    assert "Careers" in ev["claim_span"]
    assert claim["signal_type"] == "careers_signal"
    assert "does not assert any active vacancy" in claim["claim_scope"]
