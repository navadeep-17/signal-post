#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.first_party_activity import project_first_party_activity_claims  # noqa: E402
from norway_company_agent.final_site_discovery import (  # noqa: E402
    MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE,
    discover_final_website,
)

ORG = "813396092"
NAME = "SAMEIE JESSHEIM PARK DRIFT"
WEBSITE = "https://www.bori.no/"


def main() -> None:
    profile = {
        "organisation_number": ORG,
        "name": NAME,
        "website": WEBSITE,
        "municipality": "LILLESTRØM",
        "evidence": {},
        "external_observations": [],
    }
    enriched, metrics = discover_final_website(profile, timeout=8.0)
    website = ((enriched.get("evidence") or {}).get("website") or {})
    value = website.get("value") or {}
    identity = value.get("identity_assessment") or {}
    detail = ((enriched.get("evidence") or {}).get("website_news_detail") or {})
    detail_value = detail.get("value") or {}

    projected = project_first_party_activity_claims(
        {
            "organisation_number": ORG,
            "claims": [],
            "evidence": [],
            "changes": [],
            "errors": [],
        },
        enriched,
    )
    updates = [
        {
            "field": claim.get("field"),
            "value": claim.get("value"),
            "availability": claim.get("availability"),
            "evidence_ids": claim.get("evidence_ids"),
        }
        for claim in (projected.get("claims") or [])
        if claim.get("field") == "external.company_update"
    ]
    report = {
        "schema": "signalpost-c12-m3-bori-probe-v1",
        "organisation_number": ORG,
        "legal_name": NAME,
        "registry_listed_website": WEBSITE,
        "website_status": website.get("status"),
        "website_final_url": value.get("final_url"),
        "website_identity": {
            "status": identity.get("status"),
            "score": identity.get("score"),
            "publishable": identity.get("publishable"),
            "method": identity.get("method"),
            "reasons": identity.get("reasons"),
            "observed_organisation_numbers": identity.get("observed_organisation_numbers"),
        },
        "logical_site_requests": int(metrics.get("requests") or 0),
        "site_request_ceiling": MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE,
        "selected_source": metrics.get("selected_source"),
        "news_detail_attempted": bool(metrics.get("news_detail_attempted")),
        "news_detail_retained": bool(metrics.get("news_detail_retained")),
        "news_detail_candidate_url": metrics.get("news_detail_candidate_url"),
        "homepage_news_nominations": [
            {
                "url": item.get("url"),
                "anchor_text": item.get("anchor_text"),
                "marker": item.get("marker"),
            }
            for item in (value.get("news_detail_links") or [])
            if isinstance(item, dict)
        ],
        "detail_status": detail.get("status"),
        "detail_source_type": detail.get("source_type"),
        "detail_final_url": detail_value.get("final_url"),
        "detail_content_sha256": detail.get("content_sha256") or detail_value.get("content_sha256"),
        "material_company_updates": updates,
        "third_party_api_cost_usd": 0.0,
        "raw_page_body_persisted": False,
    }
    output = ROOT / "out" / "c12-m3-bori-probe.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if report["logical_site_requests"] > MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE:
        raise SystemExit("C12-M3 exceeded the production site request ceiling")


if __name__ == "__main__":
    main()
