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
    hiring_intent_match,
    project_company_authored_hiring_intent,
)
from norway_company_agent.output_contract import validate_contract_object
from norway_company_agent.synthesis import (
    build_company_synthesis,
    validate_company_synthesis,
)


ORG = "927097532"
URL = "https://entalpy.no/"


def _profile(text: str, *, publishable: bool = True) -> dict:
    return {
        "organisation_number": ORG,
        "name": "ENTALPY AS",
        "evidence": {
            "website": {
                "status": "available",
                "source_type": "registry_linked_company_website",
                "source_url": URL,
                "retrieved_at": "2026-09-17T16:33:12.152602Z",
                "content_sha256": "a" * 64,
                "value": {
                    "final_url": URL,
                    "main_text_excerpt": text,
                    "identity_assessment": {
                        "status": "exact" if publishable else "review",
                        "score": 0.99 if publishable else 0.7,
                        "publishable": publishable,
                        "method": "fixture",
                    },
                    "careers_links": [],
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
                "value": {"url": "https://entalpy.no/karriere/"},
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
                "retrieved_at": "2026-09-17T16:33:12.152602Z",
                "content_sha256": "a" * 64,
                "claim_span": "Homepage careers link",
            }
        )
    return {
        "organisation_number": ORG,
        "run": {
            "run_id": "fixture",
            "started_at": "2026-09-17T16:33:12Z",
            "completed_at": "2026-09-17T16:33:13Z",
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


def test_measured_norwegian_recruitment_language_becomes_intent_only() -> None:
    text = (
        "Ser du etter nye utfordringer? Bli med i teamet vårt. "
        "Vi søker etter talentfulle kuldeteknikere og mekanikere, "
        "så vel som administrativt- og logistikkpersonell."
    )
    row = project_company_authored_hiring_intent(_contract(), _profile(text))
    assert _fields(row).count("external.careers_page") == 1
    assert _fields(row).count("external.hiring_intent") == 1
    assert "external.job_posting" not in _fields(row)

    claim = next(x for x in row["claims"] if x["field"] == "external.hiring_intent")
    assert claim["value"]["match_type"] == "no_vi_soker"
    assert "not proof that a specific vacancy is currently open" in claim["claim_scope"]

    evidence = next(x for x in row["evidence"] if x["id"] in claim["evidence_ids"])
    assert evidence["source_url"] == URL
    assert evidence["content_sha256"] == "a" * 64
    assert "Vi søker etter talentfulle kuldeteknikere" in evidence["claim_span"]
    assert evidence["extraction_method"].startswith(
        "explicit_company_authored_recruitment_language:"
    )


def test_generic_careers_surface_is_not_hiring_intent() -> None:
    row = project_company_authored_hiring_intent(
        _contract(),
        _profile("Karriere Jobb hos oss Join our team"),
    )
    assert "external.careers_page" in _fields(row)
    assert "external.hiring_intent" not in _fields(row)
    assert "external.job_posting" not in _fields(row)


def test_vi_soker_requires_people_or_role_context() -> None:
    assert hiring_intent_match("Vi søker etter bedre løsninger for kundene våre.") is None
    assert hiring_intent_match("Vi søker etter nye leverandører av reservedeler.") is None


def test_negative_hiring_language_abstains() -> None:
    assert hiring_intent_match("Vi har ingen ledige stillinger akkurat nå.") is None
    assert hiring_intent_match("We are not hiring at this time.") is None


def test_unverified_site_never_publishes_intent() -> None:
    row = project_company_authored_hiring_intent(
        _contract(),
        _profile("Vi søker dyktige medarbeidere til teamet.", publishable=False),
    )
    assert "external.hiring_intent" not in _fields(row)


def test_projection_is_zero_network_and_idempotent() -> None:
    profile = _profile("We are hiring engineers to join our product team.")
    baseline = _contract()
    first = project_company_authored_hiring_intent(baseline, profile)
    second = project_company_authored_hiring_intent(first, profile)
    assert first["operations"] == baseline["operations"]
    assert second == first


def test_canonical_and_synthesis_preserve_three_level_boundary() -> None:
    profile = _profile("Vi søker dyktige medarbeidere til teamet vårt.")
    projected = project_company_authored_hiring_intent(_contract(), profile)
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


def test_evaluator_wiring_uses_v8_wrapper_and_preserves_pinned_v2() -> None:
    v8 = (ROOT / "scripts" / "run_signalpost_v8.py").read_text(encoding="utf-8")
    v2 = (ROOT / "scripts" / "run_signalpost_v2.py").read_text(encoding="utf-8")
    assert "from norway_company_agent.hiring_intent_contract import project_company_authored_hiring_intent" in v8
    assert v8.count("project_company_authored_hiring_intent(with_phone, profile)") == 1
    assert '"hiring_semantics_network_requests": 0' in v8
    assert "hiring_intent_contract" not in v2
    assert "project_company_authored_hiring_intent" not in v2


def test_synthesis_is_backward_compatible_when_m5_adds_no_intent() -> None:
    baseline = project_canonical_profile(_contract(careers=False))
    baseline["synthesis"] = build_company_synthesis(baseline)
    assert baseline["synthesis"]["decision_brief"]["hiring"]["text"] == (
        "No strict job posting is published for this run."
    )
    assert "No company-authored hiring-intent signal is published." not in baseline["synthesis"]["unknowns"]
