from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "m10_gate_b_breadth", ROOT / "scripts" / "audit_v9_m10_gate_b_breadth.py"
)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

CANARIES = ("927097532", "979943377", "999096298")
FAMILIES = mod.FAMILIES


def fixture():
    a_orgs = [*CANARIES, *(f"{800000000+i}" for i in range(17))]
    b_orgs = [*a_orgs, *(f"{850000000+i}" for i in range(80))]
    a_manifest = [{"organisation_number": x} for x in a_orgs]
    b_manifest = [{"organisation_number": x} for x in b_orgs]
    row = {
        "organisation_number": CANARIES[0],
        "field": "external.contact_email",
        "value": "frank@entalpy.no",
        "manual_exact_entity_review_required": True,
        "manual_semantic_scope_review_required": True,
        "checks": {"identity": True, "provenance": True},
        "evidence": [{
            "source_url": "https://entalpy.no/",
            "content_sha256": "a" * 64,
            "claim_span": "Frank contact email",
            "extraction_method": "structured_organisation",
        }],
    }
    fam_a = {
        "families": {
            name: {"net_new_companies": int(name == "external_contact"), "lost_companies": 0}
            for name in FAMILIES
        }
    }
    fam_b = {"families": {k: dict(v) for k, v in fam_a["families"].items()}}
    machine = {
        "machine_decision": "MANUAL_AUDIT_REQUIRED",
        "errors": [], "companies": 100, "lost_external_publications": 0,
        "lost_family_company_edges": 0, "new_external_publications": 1,
        "manual_audit_rows": 1,
    }
    approval = {
        "manual_review_finalized": True,
        "human_signoff_claimed": False,
        "gate_b_consumed_eval_authorized": True,
        "gate_b_production_promotion_authorized": False,
        "approved_publications": [{**{
            k: row[k] for k in ("organisation_number", "field", "value")
        }, "verdict": "APPROVED_AS_SCOPED"}],
    }
    return {
        "gate_a_manifest": a_manifest,
        "gate_b_manifest": b_manifest,
        "gate_a_manual": [row],
        "gate_b_manual": [dict(row)],
        "gate_a_family": fam_a,
        "gate_b_family": fam_b,
        "gate_b_machine": machine,
        "gate_a_approval": approval,
    }


def test_identical_positive_canary_claims_do_not_prove_holdout_transfer():
    result = mod.evaluate(**fixture())
    assert result["decision"] == "HOLD_BREADTH_CANARY_ONLY"
    assert result["additional_gate_b_companies"] == 80
    assert result["additional_80_new_publication_tuples"] == 0
    assert result["gate_b_only_new_publication_tuples"] == 0
    assert result["gate_b_scoped_manual_review_completed_for_reused_publications"]
    assert not result["production_promotion_authorized"]
    assert not result["fresh_qualification_authorized"]


def test_new_holdout_claim_is_detected_but_not_automatically_approved():
    q = fixture()
    another = {**q["gate_a_manual"][0], "organisation_number": "850000000"}
    q["gate_b_manual"].append(another)
    q["gate_b_machine"]["new_external_publications"] = 2
    q["gate_b_machine"]["manual_audit_rows"] = 2
    q["gate_b_family"]["families"]["external_contact"]["net_new_companies"] = 2
    report = mod.evaluate(**q)
    assert report["decision"] == "REVIEW_B_ONLY_TRANSFER_AND_FAMILY_DELTAS"
    assert report["additional_80_new_publication_tuples"] == 1
    assert not report["gate_b_scoped_manual_review_completed_for_reused_publications"]
    assert len(report["gate_b_publication_signatures_requiring_new_manual_approval"]) == 1


def test_changed_evidence_hash_from_gate_a_fails_closed():
    q = fixture()
    q["gate_b_manual"][0] = {
        **q["gate_b_manual"][0],
        "evidence": [{**q["gate_b_manual"][0]["evidence"][0], "content_sha256": "b" * 64}],
    }
    with pytest.raises(ValueError, match="source/hash/claim span changed"):
        mod.evaluate(**q)


def test_missing_earlier_publication_fails_closed():
    q = fixture()
    q["gate_b_manual"] = []
    q["gate_b_machine"]["new_external_publications"] = 0
    q["gate_b_machine"]["manual_audit_rows"] = 0
    with pytest.raises(ValueError, match="disappeared"):
        mod.evaluate(**q)


def test_non_exact_publication_evidence_fails_closed():
    q = fixture()
    q["gate_b_manual"][0] = {
        **q["gate_b_manual"][0],
        "checks": {"identity": False, "provenance": True},
    }
    with pytest.raises(ValueError, match="incomplete identity/evidence checks"):
        mod.evaluate(**q)


def test_unapproved_a_review_fails_closed():
    q = fixture()
    q["gate_a_approval"]["approved_publications"][0]["verdict"] = "PENDING"
    with pytest.raises(ValueError, match="unresolved publication"):
        mod.evaluate(**q)


def test_added_company_not_in_reserved_100_fails_closed():
    q = fixture()
    q["gate_b_manual"][0] = {**q["gate_b_manual"][0], "organisation_number": "700000001"}
    with pytest.raises(ValueError, match="outside selected cohort"):
        mod.evaluate(**q)
