from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_zero_request_recovery.py"
spec = importlib.util.spec_from_file_location("audit_zero_request_recovery", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def row(org, fields, *, activity=False):
    claims=[
        {"field": field, "availability": "available", "value": {"x":1}}
        for field in fields
    ]
    return {
        "organisation_number": org,
        "claims": claims,
        "canonical_facts": [],
        "canonical_profile": {
            "data_areas": {
                "company_record": True,
                "financials": False,
                "people_and_locations": False,
                "company_website": "official_website" in fields,
                "hiring_and_public_activity": activity,
            }
        },
    }


def test_detects_zero_request_surface_upper_bound():
    rows=[
        row("111111111", {"external.workforce_snapshot"}),
        row("222222222", {"official_registry_change"}),
        row("333333333", {"official.support_award"}, activity=True),
        row("444444444", {"official_website","social_links","registered_contact_email"}),
    ]
    report=module.audit(rows)
    assert report["network_requests"] == 0
    assert report["opportunities"]["workforce_snapshot_but_hiring_activity_area_false"]["companies"] == 1
    assert report["opportunities"]["registry_change_but_hiring_activity_area_false"]["companies"] == 1
    assert report["opportunities"]["social_links_without_external_profile_handle"]["companies"] == 1
    assert report["typed_activity_surface_upper_bound"]["current_hiring_and_public_activity_companies"] == 1
    assert report["typed_activity_surface_upper_bound"]["union_if_typed_facts_are_surfaced_without_relabeling"] == 3
    assert report["typed_activity_surface_upper_bound"]["net_new_area_companies_upper_bound"] == 2
