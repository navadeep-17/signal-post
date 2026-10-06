from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.canonical_projection import (
    project_canonical_profile,
    validate_canonical_projection,
)
from norway_company_agent.hiring_intent_contract import (
    project_company_authored_hiring_intent,
)
from norway_company_agent.output_contract import validate_contract_object
from norway_company_agent.synthesis import (
    build_company_synthesis,
    validate_company_synthesis,
)


ORG = "938702675"
URL = "https://www.afgruppen.no/"


def _profile(*, count: int = 10, publishable: bool = True, method: str = "explicit_homepage_vacancy_count") -> dict:
    return {
        "organisation_number": ORG,
        "name": "AF GRUPPEN ASA",
        "evidence": {
            "website": {
                "status": "available",
                "source_type": "registry_linked_company_website",
                "source_url": URL,
                "retrieved_at": "2026-10-06T06:00:00Z",
                "content_sha256": "a" * 64,
                "value": {
                    "final_url": URL,
                    "identity_assessment": {
                        "status": "exact" if publishable else "review",
                        "score": 1.0 if publishable else 0.7,
                        "publishable": publishable,
                        "method": "fixture",
                    },
                    "active_hiring_signal": {
                        "active_vacancy_count": count,
                        "active_vacancies": count > 0,
                        "method": method if count > 0 else "none",
                        "homepage_url": URL,
                        "evidence_span": f"{count} Antall ledige stillinger" if count > 0 else "",
                    },
                    "careers_links": [
                        {
                            "url": "https://www.afgruppen.no/karriere/",
                            "homepage_url": URL,
                            "homepage_content_sha256": "a" * 64,
                        }
                    ],
                    "pages": [],
                },
            }
        },
    }


def _contract(*, careers: bool = True) -> dict:
    claims = []
    evidence = []
    if careers:
        claims.append(
            {
                "field": "external.careers_page",
                "value": {"url": "https://www.afgruppen.no/karriere/"},
                "availability": "available",
                "confidence": 1.0,
                "evidence_ids": ["ev-careers"],
                "platform": "company_site",
                "signal_type": "careers_page",
                "claim_scope": "Careers surface only; does not assert active hiring.",
            }
        )
        evidence.append(
            {
                "id": "ev-careers",
                "source_url": URL,
                "source_class": "company_owned",
                "retrieved_at": "2026-10-06T06:00:00Z",
                "content_sha256": "a" * 64,
                "claim_span": "Homepage careers link",
            }
        )
    return {
        "organisation_number": ORG,
        "run": {
            "run_id": "fixture",
            "started_at": "2026-10-06T06:00:00Z",
            "completed_at": "2026-10-06T06:00:01Z",
            "terminal_status": "completed",
        },
        "claims": claims,
        "evidence": evidence,
        "changes": [],
        "errors": [],
        "operations": {"requests": 17, "runtime_ms": 1000, "third_party_cost_usd": 0.0},
    }


def _fields(row: dict) -> list[str]:
    return [str(claim.get("field") or "") for claim in row.get("claims") or []]


def test_explicit_positive_homepage_count_becomes_intent_only() -> None:
    row = project_company_authored_hiring_intent(_contract(), _profile())
    assert _fields(row).count("external.careers_page") == 1
    assert _fields(row).count("external.hiring_intent") == 1
    assert "external.job_posting" not in _fields(row)

    claim = next(x for x in row["claims"] if x["field"] == "external.hiring_intent")
    assert claim["value"]["active_vacancy_count"] == 10
    assert "not proof of any specific vacancy" in claim["claim_scope"]

    evidence = next(x for x in row["evidence"] if x["id"] in claim["evidence_ids"])
    assert evidence["source_url"] == URL
    assert evidence["content_sha256"] == "a" * 64
    assert evidence["claim_span"] == "10 Antall ledige stillinger"
    assert evidence["extraction_method"] == "explicit_homepage_vacancy_count"


def test_careers_surface_without_positive_count_is_not_intent() -> None:
    row = project_company_authored_hiring_intent(_contract(), _profile(count=0))
    assert "external.careers_page" in _fields(row)
    assert "external.hiring_intent" not in _fields(row)
    assert "external.job_posting" not in _fields(row)


def test_wrong_method_or_unverified_site_abstains() -> None:
    assert "external.hiring_intent" not in _fields(
        project_company_authored_hiring_intent(
            _contract(),
            _profile(method="broad_numeric_proximity"),
        )
    )
    assert "external.hiring_intent" not in _fields(
        project_company_authored_hiring_intent(
            _contract(),
            _profile(publishable=False),
        )
    )


def test_projection_is_zero_network_and_idempotent() -> None:
    baseline = _contract()
    first = project_company_authored_hiring_intent(baseline, _profile())
    second = project_company_authored_hiring_intent(first, _profile())
    assert first["operations"] == baseline["operations"]
    assert second == first


def test_canonical_and_synthesis_preserve_three_level_boundary() -> None:
    projected = project_company_authored_hiring_intent(_contract(), _profile())
    canonical = project_canonical_profile(projected)
    assert validate_contract_object(canonical) == []
    assert validate_canonical_projection(canonical) == []

    hiring_signals = canonical["canonical_profile"]["hiring_signals"]
    assert [fact["type"] for fact in hiring_signals] == ["careers_page", "hiring_intent"]
    intent = next(fact for fact in hiring_signals if fact["type"] == "hiring_intent")
    assert intent["canonical_field"] == "hiring.company_authored_intent"
    assert canonical["canonical_profile"]["jobs"] == []

    canonical["synthesis"] = build_company_synthesis(canonical)
    assert validate_company_synthesis(canonical) == []
    text = canonical["synthesis"]["decision_brief"]["hiring"]["text"]
    assert "Company-authored hiring intent is published" in text
    assert "no strict specific job posting" in text


def test_workspace_copy_distinguishes_intent_from_specific_job() -> None:
    source = (ROOT / "scripts" / "ui_v6" / "app_careers_signal.js").read_text(encoding="utf-8")
    assert "spHiringIntentFacts" in source
    assert "Company-authored hiring intent is published" in source
    assert "no qualified specific job posting is published" in source
    assert "does not establish company-authored hiring intent or a specific active vacancy" in source
