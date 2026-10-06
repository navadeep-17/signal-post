from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.canonical_projection import (  # noqa: E402
    project_canonical_profile,
    validate_canonical_projection,
)
from norway_company_agent.hiring_contract import project_hiring_semantics  # noqa: E402
from norway_company_agent.synthesis import (  # noqa: E402
    build_company_synthesis,
    validate_company_synthesis,
)


ORG = "938702675"


def _profile(*, deadline: str = "18.10.2026", employer: str = "AF GRUPPEN ASA") -> dict:
    website_url = "https://www.afgruppen.no/"
    careers_url = "https://www.afgruppen.no/karriere/ledige-stillinger/"
    return {
        "organisation_number": ORG,
        "name": "AF GRUPPEN ASA",
        "evidence": {
            "website": {
                "status": "available",
                "source_type": "registry_linked_company_website",
                "source_url": website_url,
                "retrieved_at": "2026-10-06T06:00:00Z",
                "content_sha256": "a" * 64,
                "value": {
                    "final_url": website_url,
                    "content_sha256": "a" * 64,
                    "main_text_excerpt": "Vi søker dyktige medarbeidere til flere av våre team.",
                    "identity_assessment": {
                        "status": "exact",
                        "score": 1.0,
                        "publishable": True,
                        "method": "fixture",
                    },
                    "careers_links": [
                        {
                            "url": careers_url,
                            "homepage_url": website_url,
                            "homepage_content_sha256": "a" * 64,
                        }
                    ],
                    "job_listing_candidates": [],
                    "pages": [],
                },
            },
            "website_careers_surface": {
                "status": "available",
                "source_type": "verified_company_careers_surface_candidate",
                "source_url": careers_url,
                "retrieved_at": "2026-10-06T06:01:00Z",
                "content_sha256": "b" * 64,
                "value": {
                    "final_url": careers_url,
                    "content_sha256": "b" * 64,
                    "main_text_excerpt": "Ledige stillinger hos AF Gruppen.",
                    "job_listing_candidates": [
                        {
                            "title": "Bedriftslege",
                            "role_url": careers_url + "bedriftslege/",
                            "application_url": "https://candidate.example/apply/bedriftslege",
                            "action_type": "explicit_apply_link",
                            "deadline_raw": deadline,
                            "employer_context": f"{employer} Frist {deadline} Bedriftslege",
                            "hiring_organisation": employer,
                            "method": "dated_role_card",
                        }
                    ],
                    "pages": [],
                },
            },
        },
    }


def _contract() -> dict:
    return {
        "organisation_number": ORG,
        "claims": [
            {
                "field": "external.careers_page",
                "value": {
                    "url": "https://www.afgruppen.no/karriere/ledige-stillinger/",
                    "anchor_text": "Ledige stillinger",
                },
                "availability": "available",
                "confidence": 1.0,
                "evidence_ids": ["ev-careers"],
                "platform": "company_site",
                "signal_type": "careers_page",
                "claim_scope": "Careers surface only; does not assert an active vacancy.",
            }
        ],
        "evidence": [
            {
                "id": "ev-careers",
                "source_url": "https://www.afgruppen.no/",
                "source_class": "company_owned",
                "retrieved_at": "2026-10-06T06:00:00Z",
                "content_sha256": "a" * 64,
                "claim_span": "Homepage link: Ledige stillinger",
            }
        ],
        "changes": [],
        "errors": [],
        "operations": {"requests": 0, "runtime_ms": 0, "third_party_cost_usd": 0.0},
    }


def _fields(contract: dict) -> list[str]:
    return [str(item.get("field") or "") for item in contract.get("claims") or []]


def test_three_hiring_levels_remain_distinct() -> None:
    projected = project_hiring_semantics(_contract(), _profile())
    fields = _fields(projected)
    assert fields.count("external.careers_page") == 1
    assert fields.count("external.hiring_intent") == 1
    assert fields.count("external.job_posting") == 1

    intent = next(x for x in projected["claims"] if x["field"] == "external.hiring_intent")
    job = next(x for x in projected["claims"] if x["field"] == "external.job_posting")
    assert "not a claim that a specific vacancy" in intent["claim_scope"]
    assert job["value"]["title"] == "Bedriftslege"
    assert job["value"]["deadline"] == "2026-10-18"


def test_expired_role_does_not_become_specific_active_job() -> None:
    projected = project_hiring_semantics(_contract(), _profile(deadline="05.10.2026"))
    assert "external.hiring_intent" in _fields(projected)
    assert "external.job_posting" not in _fields(projected)


def test_wrong_employer_role_does_not_become_target_job() -> None:
    projected = project_hiring_semantics(_contract(), _profile(employer="AF ELKRAFT AS"))
    assert "external.hiring_intent" in _fields(projected)
    assert "external.job_posting" not in _fields(projected)


def test_canonical_and_synthesis_keep_intent_separate_from_jobs() -> None:
    projected = project_hiring_semantics(_contract(), _profile(deadline="05.10.2026"))
    canonical = project_canonical_profile(projected)
    assert validate_canonical_projection(canonical) == []

    hiring_types = [
        item["type"]
        for item in canonical["canonical_profile"]["hiring_signals"]
    ]
    assert "careers_page" in hiring_types
    assert "hiring_intent" in hiring_types
    assert canonical["canonical_profile"]["jobs"] == []

    canonical["synthesis"] = build_company_synthesis(canonical)
    assert validate_company_synthesis(canonical) == []
    text = canonical["synthesis"]["decision_brief"]["hiring"]["text"]
    assert "company-authored hiring-intent" in text
    assert "no strict job posting" in text


def test_projection_is_idempotent() -> None:
    first = project_hiring_semantics(_contract(), _profile())
    second = project_hiring_semantics(first, _profile())
    assert _fields(first) == _fields(second)
    assert first["evidence"] == second["evidence"]
