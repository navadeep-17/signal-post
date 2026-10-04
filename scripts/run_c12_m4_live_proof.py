#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.final_site_discovery import (  # noqa: E402
    MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE,
    discover_final_website,
)
from norway_company_agent.first_party_activity import project_first_party_activity_claims  # noqa: E402

CASES = (
    {
        "key": "granne_negative",
        "organisation_number": "838797172",
        "name": "GRANNE FORSIKRING",
        "website": "https://www.granne.no/",
        "expect_jobs": False,
    },
    {
        "key": "af_positive",
        "organisation_number": "938702675",
        "name": "AF GRUPPEN ASA",
        "website": "https://www.afgruppen.no/",
        "expect_jobs": True,
    },
)


def _contract(org: str) -> dict:
    return {
        "organisation_number": org,
        "claims": [],
        "evidence": [],
        "changes": [],
        "errors": [],
    }


def _summarize(case: dict) -> dict:
    profile = {
        "organisation_number": case["organisation_number"],
        "name": case["name"],
        "website": case["website"],
        "evidence": {},
        "external_observations": [],
    }
    enriched, metrics = discover_final_website(profile, timeout=8.0)
    evidence_map = enriched.get("evidence") or {}
    website = evidence_map.get("website") or {}
    value = website.get("value") or {}
    identity = value.get("identity_assessment") or {}
    hiring = value.get("active_hiring_signal") or {}
    careers = evidence_map.get("website_careers_surface") or {}
    careers_value = careers.get("value") or {}
    contract = project_first_party_activity_claims(_contract(case["organisation_number"]), enriched)
    jobs = [
        claim
        for claim in (contract.get("claims") or [])
        if claim.get("field") == "external.job_posting" and claim.get("availability") == "available"
    ]
    return {
        "key": case["key"],
        "organisation_number": case["organisation_number"],
        "legal_name": case["name"],
        "website_identity": {
            "status": identity.get("status"),
            "score": identity.get("score"),
            "publishable": identity.get("publishable"),
            "method": identity.get("method"),
            "reasons": identity.get("reasons"),
        },
        "logical_site_requests": int(metrics.get("requests") or 0),
        "site_request_ceiling": MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE,
        "homepage_active_hiring_signal": hiring,
        "homepage_careers_links": [
            {"url": item.get("url"), "anchor_text": item.get("anchor_text"), "marker": item.get("marker")}
            for item in (value.get("careers_links") or [])
            if isinstance(item, dict)
        ],
        "homepage_job_candidate_count": len(value.get("job_listing_candidates") or []),
        "careers_surface_attempted": bool(metrics.get("careers_surface_attempted")),
        "careers_surface_retained": bool(metrics.get("careers_surface_retained")),
        "careers_surface_candidate_url": metrics.get("careers_surface_candidate_url"),
        "careers_surface_final_url": careers_value.get("final_url"),
        "careers_surface_job_candidate_count": len(careers_value.get("job_listing_candidates") or []),
        "material_jobs": [
            {
                "value": claim.get("value"),
                "confidence": claim.get("confidence"),
                "evidence_ids": claim.get("evidence_ids"),
                "claim_scope": claim.get("claim_scope"),
            }
            for claim in jobs
        ],
        "third_party_api_cost_usd": 0.0,
        "raw_page_body_persisted": False,
    }


def main() -> None:
    rows = [_summarize(case) for case in CASES]
    report = {
        "schema": "signalpost-c12-m4-live-proof-v1",
        "cases": rows,
        "third_party_api_cost_usd": 0.0,
    }
    output = ROOT / "out" / "c12-m4-live-proof.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    by_key = {row["key"]: row for row in rows}
    granne = by_key["granne_negative"]
    af = by_key["af_positive"]

    assert granne["website_identity"]["publishable"] is True, "Granne exact-site identity did not publish"
    assert granne["logical_site_requests"] <= MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE
    assert granne["material_jobs"] == [], "Granne generic/no-vacancy surface became a job"

    assert af["website_identity"]["publishable"] is True, "AF exact-site identity did not publish"
    assert af["logical_site_requests"] <= MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE
    assert af["homepage_active_hiring_signal"].get("active_vacancies") is True, "AF homepage did not expose active hiring signal"
    assert af["careers_surface_attempted"] is True, "AF active hiring did not trigger bounded careers follow-up"
    assert af["careers_surface_retained"] is True, "AF careers surface was not retained"
    assert af["material_jobs"], "AF exact first-party current role did not become a job claim"
    assert any((job.get("value") or {}).get("deadline") for job in af["material_jobs"]), "AF job claim lacks current deadline"


if __name__ == "__main__":
    main()
