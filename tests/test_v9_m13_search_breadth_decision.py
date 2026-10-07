from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _load():
    path = ROOT / "scripts" / "decide_v9_m13_search_breadth.py"
    spec = importlib.util.spec_from_file_location("m13_decision", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m13 = _load()
FAMILIES = tuple(m13.FAMILY_FIELDS)


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


def _fixture(*, website_gains: int = 5, control_gain: bool = False, evidence_defect: bool = False):
    orgs = [f"{800000000+i:09d}" for i in range(100)]
    targets = orgs[:20]
    controls = orgs[20:]
    cohort_audit = [
        {
            "organisation_number": org,
            "bucket": "m13_search_holdout" if org in targets else "m13_control_unsearched",
            "previous_search_development": False,
            "m10_positive_canary": False,
            "m12_researched": False,
        }
        for org in orgs
    ]
    baseline = [_row(org) for org in orgs]
    challenger = [_row(org) for org in orgs]

    gain_orgs = targets[:website_gains]
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
            "value": f"https://{org}.example/",
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
    baseline_report = {
        "passed": True,
        "source_policy": {
            "search_api_requests": 0,
            "third_party_cost_usd": 0.0,
        },
        "runtime": {"wall_runtime_seconds": 500},
        "request_budget": {
            "theoretical_challenge_request_charge_ceiling": 2000,
            "observed_conservative_challenge_request_charge": 1350,
        },
    }
    challenger_report = {
        "passed": True,
        "source_policy": {
            "search_api_requests": 20,
            "search_web_tool_calls": 20,
            "third_party_cost_usd": 0.21,
            "openai_web_search_enabled": True,
        },
        "runtime": {"wall_runtime_seconds": 520},
        "request_budget": {
            "provider_search_logical_request_ceiling": 20,
            "theoretical_challenge_request_charge_ceiling": 2000,
            "observed_conservative_challenge_request_charge": 1390,
        },
    }
    return {
        "cohort_report": {
            "selected_companies": 100,
            "search_holdout_companies": 20,
            "control_companies": 80,
            "fresh_companies_used": 0,
        },
        "cohort_audit": cohort_audit,
        "baseline_report": baseline_report,
        "challenger_report": challenger_report,
        "baseline_rows": baseline,
        "challenger_rows": challenger,
        "family_report": family_report,
        "publication_report": publication_report,
        "manual_publications": pubs,
    }


def test_five_clean_holdout_website_gains_reach_manual_audit_only() -> None:
    r = m13.decide(**_fixture(website_gains=5))
    assert r["machine_decision"] == "MANUAL_AUDIT_REQUIRED"
    assert r["holdout_verified_website_gains"] == 5
    assert r["control_new_family_company_edges"] == 0
    assert r["fresh_qualification_authorized"] is False
    assert r["production_promotion_authorized"] is False


def test_four_holdout_website_gains_are_below_predeclared_yield_bar() -> None:
    r = m13.decide(**_fixture(website_gains=4))
    assert r["machine_decision"] == "HOLD_SEARCH_YIELD_BELOW_BAR"
    assert r["errors"] == []


def test_control_gain_blocks_causal_attribution() -> None:
    r = m13.decide(**_fixture(website_gains=5, control_gain=True))
    assert r["machine_decision"] == "BLOCKED"
    assert "zero_control_family_gains" in r["errors"]
    assert "zero_control_publications" in r["errors"]


def test_evidence_defect_blocks_even_with_good_yield() -> None:
    r = m13.decide(**_fixture(website_gains=5, evidence_defect=True))
    assert r["machine_decision"] == "BLOCKED"
    assert "zero_evidence_defects" in r["errors"]
    assert "all_new_publications_have_reopenable_evidence" in r["errors"]
    assert "every_manual_row_machine_check_green" in r["errors"]


def test_search_over_twenty_blocks() -> None:
    q = _fixture(website_gains=5)
    q["challenger_report"]["source_policy"]["search_api_requests"] = 21
    q["challenger_report"]["source_policy"]["search_web_tool_calls"] = 21
    r = m13.decide(**q)
    assert r["machine_decision"] == "BLOCKED"
    assert "challenger_search_calls_1_to_20" in r["errors"]


def test_request_theorem_over_2000_blocks() -> None:
    q = _fixture(website_gains=5)
    q["challenger_report"]["request_budget"]["theoretical_challenge_request_charge_ceiling"] = 2002
    r = m13.decide(**q)
    assert r["machine_decision"] == "BLOCKED"
    assert "challenger_theorem_under_2000" in r["errors"]
