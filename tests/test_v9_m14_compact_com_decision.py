from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _load():
    path = ROOT / "scripts" / "decide_v9_m14_compact_com.py"
    spec = importlib.util.spec_from_file_location("m14_decision", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m14 = _load()
FAMILIES = tuple(m14.FAMILY_FIELDS)


def _row(org: str, fields: set[str] | None = None) -> dict:
    return {
        "organisation_number": org,
        "claims": [
            {
                "field": field,
                "availability": "available",
                "value": f"value-{field}",
                "evidence_ids": [f"ev-{field}"],
            }
            for field in sorted(fields or set())
        ],
    }


def _fixture(*, website_gains: int = 2, control_gain: bool = False, evidence_defect: bool = False):
    orgs = [f"{800000000+i:09d}" for i in range(100)]
    treated = orgs[:20]
    controls = orgs[20:]
    cohort_audit = [
        {
            "organisation_number": org,
            "bucket": "m14_single_token_compact_com" if org in treated else "m14_multi_token_control",
            "previous_search_development": False,
            "m10_positive_canary": False,
            "m12_researched": False,
            "builderr_public_practice": False,
        }
        for org in orgs
    ]
    baseline = [_row(org) for org in orgs]
    challenger = [_row(org) for org in orgs]

    gain_orgs = treated[:website_gains]
    for org in gain_orgs:
        challenger[orgs.index(org)] = _row(org, {"official_website"})
    if control_gain:
        challenger[orgs.index(controls[0])] = _row(controls[0], {"official_website"})

    all_gain_count = website_gains + int(control_gain)
    family_report = {
        "companies": 100,
        "same_company_set": True,
        "families": {
            family: {
                "baseline_companies": 0,
                "challenger_companies": all_gain_count if family == "verified_website" else 0,
                "net_new_companies": all_gain_count if family == "verified_website" else 0,
                "lost_companies": 0,
            }
            for family in FAMILIES
        },
    }

    pubs = []
    for org in gain_orgs:
        pubs.append({
            "organisation_number": org,
            "field": "official_website",
            "value": f"https://{org}.com/",
            "checks": {
                "identity": not evidence_defect,
                "provenance": True,
                "field_specific_identity_scope_proof": True,
            },
        })
    if control_gain:
        pubs.append({
            "organisation_number": controls[0],
            "field": "official_website",
            "value": "https://control.example/",
            "checks": {
                "identity": True,
                "provenance": True,
                "field_specific_identity_scope_proof": True,
            },
        })

    publication_report = {
        "evidence_defects": int(evidence_defect),
        "all_new_publication_evidence_complete": not evidence_defect,
        "lost_publications": 0,
        "new_publications": len(pubs),
        "manual_review_rows": len(pubs),
    }
    common_report = {
        "passed": True,
        "source_policy": {"third_party_cost_usd": 0.0},
        "runtime": {"wall_runtime_seconds": 500},
        "request_budget": {
            "theoretical_challenge_request_charge_ceiling": 2000,
            "observed_conservative_challenge_request_charge": 1350,
        },
    }
    return {
        "cohort_report": {
            "selected_companies": 100,
            "treated_companies": 20,
            "control_companies": 80,
            "fresh_companies_used": 0,
        },
        "cohort_audit": cohort_audit,
        "baseline_report": common_report,
        "challenger_report": {
            **common_report,
            "request_budget": {
                "theoretical_challenge_request_charge_ceiling": 2000,
                "observed_conservative_challenge_request_charge": 1390,
            },
        },
        "baseline_rows": baseline,
        "challenger_rows": challenger,
        "family_report": family_report,
        "publication_report": publication_report,
        "manual_publications": pubs,
    }


def test_two_clean_treated_website_gains_reach_manual_audit_only() -> None:
    r = m14.decide(**_fixture(website_gains=2))
    assert r["machine_decision"] == "MANUAL_AUDIT_REQUIRED"
    assert r["treated_verified_website_gains"] == 2
    assert r["control_new_family_company_edges"] == 0
    assert r["production_promotion_authorized"] is False


def test_one_treated_gain_is_below_predeclared_bar() -> None:
    r = m14.decide(**_fixture(website_gains=1))
    assert r["machine_decision"] == "HOLD_COMPACT_COM_YIELD_BELOW_BAR"
    assert r["errors"] == []


def test_control_gain_blocks() -> None:
    r = m14.decide(**_fixture(website_gains=2, control_gain=True))
    assert r["machine_decision"] == "BLOCKED"
    assert "zero_control_family_gains" in r["errors"]
    assert "zero_control_publications" in r["errors"]


def test_evidence_defect_blocks() -> None:
    r = m14.decide(**_fixture(website_gains=2, evidence_defect=True))
    assert r["machine_decision"] == "BLOCKED"
    assert "zero_evidence_defects" in r["errors"]
    assert "every_manual_row_machine_check_green" in r["errors"]


def test_request_theorem_increase_blocks() -> None:
    q = _fixture(website_gains=2)
    q["challenger_report"]["request_budget"]["theoretical_challenge_request_charge_ceiling"] = 2002
    r = m14.decide(**q)
    assert r["machine_decision"] == "BLOCKED"
    assert "challenger_theorem_under_2000" in r["errors"]
