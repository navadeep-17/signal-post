from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, filename: str):
    path = ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


audit_module = _load("audit_v9_m10_publications", "audit_v9_m10_publications.py")
builder_module = _load("build_v9_m10_consumed_gates", "build_v9_m10_consumed_gates.py")


def _contract(org: str, claims=None, evidence=None):
    return {
        "organisation_number": org,
        "claims": claims or [],
        "evidence": evidence or [],
    }


def _hiring_claim(eid: str):
    return {
        "field": "external.hiring_intent",
        "availability": "available",
        "value": {"match_type": "no_vi_soker", "source_url": "https://example.no/"},
        "confidence": 1.0,
        "evidence_ids": [eid],
        "platform": "company_site",
        "signal_type": "hiring_intent",
        "claim_scope": "Exact company-authored recruitment intent; no specific vacancy asserted.",
    }


def _evidence(eid: str, *, content_hash: str = "a" * 64):
    return {
        "id": eid,
        "source_url": "https://example.no/",
        "source_class": "company_owned",
        "retrieved_at": "2026-10-06T10:00:00Z",
        "content_sha256": content_hash,
        "claim_span": "Vi søker dyktige medarbeidere.",
        "identity_proof": {
            "status": "exact",
            "score": 1.0,
            "publishable": True,
            "method": "fixture",
        },
    }


def test_m10_publication_audit_accepts_complete_exact_evidence() -> None:
    baseline = [_contract("927097532")]
    challenger = [
        _contract(
            "927097532",
            claims=[_hiring_claim("ev1")],
            evidence=[_evidence("ev1")],
        )
    ]
    report, manual = audit_module.audit_new_publications(baseline, challenger)
    assert report["new_publications"] == 1
    assert report["evidence_defects"] == 0
    assert report["all_new_publication_evidence_complete"] is True
    assert len(manual) == 1
    assert manual[0]["manual_exact_entity_review_required"] is True


def test_m10_publication_audit_rejects_missing_page_hash() -> None:
    baseline = [_contract("927097532")]
    challenger = [
        _contract(
            "927097532",
            claims=[_hiring_claim("ev1")],
            evidence=[_evidence("ev1", content_hash="")],
        )
    ]
    report, manual = audit_module.audit_new_publications(baseline, challenger)
    assert report["evidence_defects"] == 1
    assert report["all_new_publication_evidence_complete"] is False
    assert manual[0]["checks"]["all_content_hashes_present"] is False


def test_gate_a_contains_all_canaries_and_is_deterministic() -> None:
    canaries = ["999096298", "979943377", "927097532"]
    rows = [
        {"organisation_number": org, "bucket": "m2_delta"}
        for org in [
            "800000001",
            "800000002",
            "800000003",
            "800000004",
            "800000005",
            "800000006",
            "800000007",
            "800000008",
            "800000009",
            "800000010",
            "800000011",
            "800000012",
            "800000013",
            "800000014",
            "800000015",
            "800000016",
            "800000017",
            "800000018",
            "800000019",
            "800000020",
        ]
    ] + [
        {"organisation_number": org, "bucket": "forced_canary"}
        for org in canaries
    ]
    selected = builder_module.build_gate_a(rows, canaries=canaries, target_count=20)
    assert [row["organisation_number"] for row in selected[:3]] == canaries
    assert len(selected) == 20
    assert len({row["organisation_number"] for row in selected}) == 20
