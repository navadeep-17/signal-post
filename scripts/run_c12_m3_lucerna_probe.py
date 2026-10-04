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

ORG = "982897327"
NAME = "LUCERNA AS"
WEBSITE = "https://www.lucerna.no/"
EXPECTED_ARTICLE = "https://www.lucerna.no/elbilladere-i-fokus-hos-det-lokale-eltilsyn-dle"
EXPECTED_DATE = "2026-06-03"


def main() -> None:
    profile = {
        "organisation_number": ORG,
        "name": NAME,
        "website": WEBSITE,
        "municipality": "HAMMERFEST",
        "evidence": {},
        "external_observations": [],
    }
    enriched, metrics = discover_final_website(profile, timeout=8.0)
    evidence = enriched.get("evidence") or {}
    website = evidence.get("website") or {}
    website_value = website.get("value") or {}
    identity = website_value.get("identity_assessment") or {}
    detail = evidence.get("website_news_detail") or {}
    detail_value = detail.get("value") or {}
    detail_pages = [item for item in (detail_value.get("pages") or []) if isinstance(item, dict)]
    detail_page = detail_pages[0] if detail_pages else {}

    contract = project_first_party_activity_claims(
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
        claim
        for claim in (contract.get("claims") or [])
        if claim.get("field") == "external.company_update"
    ]

    report = {
        "schema": "signalpost-c12-m3-lucerna-live-proof-v1",
        "organisation_number": ORG,
        "legal_name": NAME,
        "website_identity": {
            "status": identity.get("status"),
            "score": identity.get("score"),
            "publishable": identity.get("publishable"),
            "method": identity.get("method"),
            "reasons": identity.get("reasons"),
        },
        "logical_site_requests": int(metrics.get("requests") or 0),
        "site_request_ceiling": MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE,
        "news_detail_attempted": bool(metrics.get("news_detail_attempted")),
        "news_detail_retained": bool(metrics.get("news_detail_retained")),
        "news_detail_candidate_url": metrics.get("news_detail_candidate_url"),
        "detail_status": detail.get("status"),
        "detail_source_type": detail.get("source_type"),
        "detail_final_url": detail_value.get("final_url"),
        "detail_content_sha256": detail.get("content_sha256") or detail_value.get("content_sha256"),
        "detail_title": detail_page.get("title"),
        "detail_published_date_candidates": detail_page.get("published_date_candidates") or [],
        "material_company_updates": [
            {
                "value": item.get("value"),
                "availability": item.get("availability"),
                "evidence_ids": item.get("evidence_ids"),
            }
            for item in updates
        ],
        "third_party_api_cost_usd": 0.0,
        "raw_page_body_persisted": False,
    }

    output = ROOT / "out" / "c12-m3-lucerna-live-proof.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    assert identity.get("publishable") is True, "Lucerna exact-site identity gate did not publish"
    assert report["logical_site_requests"] <= MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE
    assert report["news_detail_attempted"] is True
    assert report["news_detail_retained"] is True
    assert str(report["detail_final_url"] or "").rstrip("/") == EXPECTED_ARTICLE.rstrip("/")
    assert report["detail_published_date_candidates"], "Detail page retained no page-local date evidence"
    assert len(updates) == 1, f"Expected one material update, got {len(updates)}"
    value = updates[0].get("value") or {}
    assert str(value.get("url") or "").rstrip("/") == EXPECTED_ARTICLE.rstrip("/")
    assert value.get("published_date") == EXPECTED_DATE


if __name__ == "__main__":
    main()
