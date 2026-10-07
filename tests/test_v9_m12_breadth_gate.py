from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.v9_measurement import FAMILY_FIELDS



def _script(name: str, filename: str):
    path = ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = _script("m12_builder", "build_v9_m12_consumed_cohort.py")
decision = _script("m12_decision", "decide_v9_m12_breadth.py")


def _profile(org: str, name: str, email: str = "", website: str = ""):
    return {
        "organisation_number": org,
        "name": name,
        "website": website,
        "evidence": {
            "registry": {
                "status": "available",
                "value": {"epostadresse": email},
            }
        },
    }


def test_cohort_labels_researched_development_and_unresearched_holdout():
    profiles = [
        _profile("828829092", "EMILSEN FISK AS", "post@unrelatedbrand.no"),
        _profile("800000001", "OMEGA DELTA AS", "post@anotherbrand.no"),
        _profile("800000002", "CONTROL COMPANY AS"),
        _profile("800000003", "ANOTHER CONTROL AS"),
        _profile("999096298", "DEN GLADE GRIS AS", "post@whatever.no"),
    ]
    manifest, audit, report = builder.build(profiles, target_count=4)
    by_org = {row["organisation_number"]: row for row in audit}
    assert by_org["828829092"]["bucket"] == "m12_delta_development"
    assert by_org["800000001"]["bucket"] == "m12_delta_holdout"
    assert "999096298" not in by_org
    assert report["unresearched_holdout_affected_companies"] == 1
    assert report["development_researched_affected_companies"] == 1
    assert len(manifest) == 4


def _contract(org: str, fields: set[str] | None = None):
    fields = fields or set()
    return {
        "organisation_number": org,
        "claims": [
            {
                "field": field,
                "availability": "available",
                "value": f"value-{field}",
                "evidence_ids": [f"ev-{field}"],
            }
            for field in sorted(fields)
        ],
    }


def _fixture(*, gain_bucket: str | None):
    orgs = [f"{800000000+i:09d}" for i in range(100)]
    holdout_org = orgs[0]
    dev_org = orgs[1]
    audit = []
    for i, org in enumerate(orgs):
        bucket = "m12_control"
        if i == 0:
            bucket = "m12_delta_holdout"
        elif i == 1:
            bucket = "m12_delta_development"
        audit.append({
            "organisation_number": org,
            "bucket": bucket,
            "m10_positive_canary": False,
        })

    baseline = [_contract(org) for org in orgs]
    challenger = [_contract(org) for org in orgs]
    gain_org = None
    if gain_bucket == "holdout":
        gain_org = holdout_org
    elif gain_bucket == "development":
        gain_org = dev_org
    if gain_org:
        idx = orgs.index(gain_org)
        challenger[idx] = _contract(gain_org, {"official_website"})

    family = {
        "companies": 100,
        "same_company_set": True,
        "families": {
            name: {
                "baseline_companies": 0,
                "challenger_companies": int(name == "verified_website" and gain_org is not None),
                "net_new_companies": int(name == "verified_website" and gain_org is not None),
                "lost_companies": 0,
            }
            for name in FAMILY_FIELDS
        },
    }
    manual = []
    if gain_org:
        manual = [{
            "organisation_number": gain_org,
            "field": "official_website",
            "value": "https://example.no/",
            "checks": {"identity": True, "provenance": True},
        }]
    publication = {
        "evidence_defects": 0,
        "all_new_publication_evidence_complete": True,
        "lost_publications": 0,
        "new_publications": len(manual),
        "manual_review_rows": len(manual),
    }
    report = {
        "passed": True,
        "source_policy": {"search_api_requests": 0, "third_party_cost_usd": 0.0},
        "runtime": {"wall_runtime_seconds": 500},
        "request_budget": {
            "theoretical_challenge_request_charge_ceiling": 2000,
            "observed_conservative_challenge_request_charge": 1400,
        },
    }
    return {
        "cohort_report": {
            "selected_companies": 100,
            "fresh_companies_used": 0,
            "unresearched_holdout_affected_companies": 1,
        },
        "cohort_audit": audit,
        "baseline_report": report,
        "challenger_report": {**report, "request_budget": {
            **report["request_budget"],
            "observed_conservative_challenge_request_charge": 1400,
        }},
        "baseline_rows": baseline,
        "challenger_rows": challenger,
        "family_report": family,
        "publication_report": publication,
        "manual_publications": manual,
    }


def test_holdout_lift_can_only_reach_manual_audit_required():
    result = decision.decide(**_fixture(gain_bucket="holdout"))
    assert result["machine_decision"] == "MANUAL_AUDIT_REQUIRED"
    assert result["holdout_new_family_company_edges"] == 1
    assert result["holdout_new_publications"] == 1
    assert result["fresh_qualification_authorized"] is False
    assert result["production_promotion_authorized"] is False


def test_development_only_lift_is_a_hold_not_transfer():
    result = decision.decide(**_fixture(gain_bucket="development"))
    assert result["machine_decision"] == "HOLD_NO_UNRESEARCHED_TRANSFER"
    assert result["development_new_family_company_edges"] == 1
    assert result["holdout_new_family_company_edges"] == 0


def test_zero_lift_is_a_hold():
    result = decision.decide(**_fixture(gain_bucket=None))
    assert result["machine_decision"] == "HOLD_NO_UNRESEARCHED_TRANSFER"


def test_observed_request_increase_blocks_request_neutral_claim():
    q = _fixture(gain_bucket="holdout")
    q["challenger_report"]["request_budget"] = {
        **q["challenger_report"]["request_budget"],
        "observed_conservative_challenge_request_charge": 1402,
    }
    result = decision.decide(**q)
    assert result["machine_decision"] == "BLOCKED"
    assert "observed_request_charge_not_increased" in result["errors"]


def test_any_family_loss_blocks():
    q = _fixture(gain_bucket="holdout")
    q["family_report"]["families"]["social"]["lost_companies"] = 1
    result = decision.decide(**q)
    assert result["machine_decision"] == "BLOCKED"
    assert "no_family_loss:social" in result["errors"]


def test_control_publication_blocks_causal_attribution():
    q = _fixture(gain_bucket="holdout")
    control = q["cohort_audit"][2]["organisation_number"]
    q["manual_publications"].append({
        "organisation_number": control,
        "field": "external.contact_email",
        "value": "x@example.no",
        "checks": {"identity": True, "provenance": True},
    })
    q["publication_report"]["new_publications"] = 2
    q["publication_report"]["manual_review_rows"] = 2
    result = decision.decide(**q)
    assert result["machine_decision"] == "BLOCKED"
    assert "zero_control_publications" in result["errors"]
