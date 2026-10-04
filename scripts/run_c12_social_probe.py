#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.company_site_social import attach_company_site_social_observations  # noqa: E402
from norway_company_agent.external_contract import project_profile_handle_observations  # noqa: E402
from norway_company_agent.final_site_discovery import fetch_bounded_homepage  # noqa: E402
from norway_company_agent.identity import apply_website_identity_gate  # noqa: E402

ORG = "811730912"
NAME = "MTM SKOGSERVICE AS"
WEBSITE = "https://www.mtm-skogservice.no/"


def main() -> None:
    profile = {
        "organisation_number": ORG,
        "name": NAME,
        "website": WEBSITE,
        "evidence": {},
        "external_observations": [],
    }
    record, metrics = fetch_bounded_homepage(
        WEBSITE,
        source_type="registry_linked_company_website",
        timeout=8.0,
    )
    gated = apply_website_identity_gate(profile, record)
    website = gated["website"]
    profile["evidence"]["website"] = website
    attach_company_site_social_observations(profile)

    projected = project_profile_handle_observations(
        {
            "organisation_number": ORG,
            "claims": [],
            "evidence": [],
            "changes": [],
            "errors": [],
        },
        profile,
    )

    value = website.get("value") or {}
    observations = [
        {
            "platform": item.get("platform"),
            "profile_url": item.get("profile_url"),
            "strategy": item.get("strategy"),
            "source_url": item.get("source_url"),
        }
        for item in profile.get("external_observations") or []
        if item.get("signal_type") == "profile_handle"
    ]
    claims = [
        {
            "field": item.get("field"),
            "value": item.get("value"),
            "platform": item.get("platform"),
            "availability": item.get("availability"),
        }
        for item in projected.get("claims") or []
        if item.get("field") == "external.profile_handle"
    ]
    report = {
        "schema": "signalpost-c12-social-probe-v1",
        "organisation_number": ORG,
        "website": WEBSITE,
        "website_status": website.get("status"),
        "identity_assessment": value.get("identity_assessment"),
        "logical_site_requests": int(metrics.get("requests") or 0),
        "bytes_received": int(metrics.get("bytes") or 0),
        "discovered_social_links": value.get("discovered_social_links") or [],
        "social_link_assessments": [
            {
                "platform": item.get("platform"),
                "url": item.get("url"),
                "identity_score": item.get("identity_score"),
                "publishable": item.get("publishable"),
            }
            for item in value.get("social_link_assessments") or []
            if isinstance(item, dict)
        ],
        "material_social_observations": observations,
        "material_social_claims": claims,
        "third_party_api_cost_usd": 0.0,
        "raw_page_body_persisted": False,
    }
    output = ROOT / "out" / "c12-social-probe.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if website.get("status") != "available" or not (value.get("identity_assessment") or {}).get("publishable"):
        raise SystemExit("C12 probe could not independently verify the exact company homepage")


if __name__ == "__main__":
    main()
