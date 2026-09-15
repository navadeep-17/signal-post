from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.evidence import evidence
from norway_company_agent.wikidata_discovery import (
    fetch_wikidata_website_candidates,
    discover_final_website_with_wikidata,
    qualify_wikidata_candidate_identity,
    theoretical_wikidata_lookup_requests,
)


class _Response:
    def __init__(self, payload: dict):
        self._raw = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, amount: int = -1):
        return self._raw if amount < 0 else self._raw[:amount]


def _available_site(*, org: str, url: str = "https://example.no/") -> dict:
    return evidence(
        "website",
        "available",
        "wikidata_official_website_candidate",
        url,
        value={
            "final_url": url,
            "registered_domain": "example.no",
            "title": "EXAMPLE AS",
            "description": "",
            "identity_text_excerpt": f"EXAMPLE AS Organisasjonsnummer {org}",
            "main_text_excerpt": f"EXAMPLE AS Organisasjonsnummer {org}",
            "structured_organisations": [],
            "pages": [{
                "url": url,
                "title": "EXAMPLE AS",
                "identity_text_excerpt": f"EXAMPLE AS Organisasjonsnummer {org}",
                "main_text_excerpt": f"EXAMPLE AS Organisasjonsnummer {org}",
            }],
        },
    )


def test_theoretical_wikidata_lookup_requests_are_batched_per_100():
    assert theoretical_wikidata_lookup_requests(0) == 0
    assert theoretical_wikidata_lookup_requests(100) == 1
    assert theoretical_wikidata_lookup_requests(101) == 2
    assert theoretical_wikidata_lookup_requests(300) == 3


def test_exact_p2333_p856_mapping_yields_one_candidate():
    payload = {
        "results": {
            "bindings": [{
                "org": {"value": "912345678"},
                "item": {"value": "http://www.wikidata.org/entity/Q123"},
                "website": {"value": "https://example.no"},
            }]
        }
    }
    with patch("urllib.request.urlopen", return_value=_Response(payload)) as mocked:
        candidates, metrics = fetch_wikidata_website_candidates(["912345678"])

    assert candidates["912345678"]["url"] == "https://example.no/"
    assert candidates["912345678"]["wikidata_item"].endswith("Q123")
    assert metrics["requests"] == 1
    assert metrics["candidate_count"] == 1
    request = mocked.call_args.args[0]
    assert "P2333" in request.full_url
    assert "P856" in request.full_url
    assert request.headers.get("User-agent")


def test_ambiguous_wikidata_mapping_abstains():
    payload = {
        "results": {
            "bindings": [
                {
                    "org": {"value": "912345678"},
                    "item": {"value": "http://www.wikidata.org/entity/Q123"},
                    "website": {"value": "https://one.no"},
                },
                {
                    "org": {"value": "912345678"},
                    "item": {"value": "http://www.wikidata.org/entity/Q123"},
                    "website": {"value": "https://two.no"},
                },
            ]
        }
    }
    with patch("urllib.request.urlopen", return_value=_Response(payload)):
        candidates, metrics = fetch_wikidata_website_candidates(["912345678"])

    assert candidates == {}
    assert metrics["ambiguous_count"] == 1


def test_candidate_requires_independent_page_identity_not_wikidata_alone():
    profile = {
        "organisation_number": "912345678",
        "name": "EXAMPLE AS",
        "municipality": "OSLO",
        "evidence": {},
    }
    strong = _available_site(org="912345678")
    strong_assessment = {
        "status": "exact",
        "score": 0.95,
        "publishable": True,
        "reasons": ["name match"],
    }
    qualified = qualify_wikidata_candidate_identity(profile, strong, strong_assessment)
    assert qualified is not None
    assert qualified["publishable"] is True
    assert qualified["score"] == 1.0

    weak = evidence(
        "website",
        "available",
        "wikidata_official_website_candidate",
        "https://example.no/",
        value={
            "final_url": "https://example.no/",
            "title": "EXAMPLE AS",
            "main_text_excerpt": "EXAMPLE AS sells products worldwide.",
            "identity_text_excerpt": "",
            "structured_organisations": [],
            "pages": [],
        },
    )
    quarantined = qualify_wikidata_candidate_identity(profile, weak, strong_assessment)
    assert quarantined is not None
    assert quarantined["publishable"] is False


def test_wikidata_fallback_never_steals_consumed_h1d_budget():
    profile = {"organisation_number": "912345678", "name": "EXAMPLE AS", "evidence": {}}
    base_total = {"requests": 4, "bytes": 0, "latencies_ms": [], "promoted": False, "selected_source": None}
    candidate = {
        "organisation_number": "912345678",
        "wikidata_item": "http://www.wikidata.org/entity/Q123",
        "url": "https://example.no/",
    }
    with patch(
        "norway_company_agent.wikidata_discovery.discover_final_website",
        return_value=(profile, base_total),
    ), patch(
        "norway_company_agent.wikidata_discovery.fetch_bounded_homepage"
    ) as fetch_site:
        row, metrics = discover_final_website_with_wikidata(
            profile,
            wikidata_candidate=candidate,
        )

    assert row is profile
    assert metrics["wikidata_attempted"] is False
    assert metrics["wikidata_skipped_reason"] == "site_request_budget_consumed"
    fetch_site.assert_not_called()


def test_wikidata_fallback_can_promote_exact_org_number_with_remaining_slot():
    profile = {
        "organisation_number": "912345678",
        "name": "EXAMPLE AS",
        "municipality": "OSLO",
        "evidence": {},
    }
    base_total = {"requests": 2, "bytes": 0, "latencies_ms": [], "promoted": False, "selected_source": None}
    candidate = {
        "organisation_number": "912345678",
        "wikidata_item": "http://www.wikidata.org/entity/Q123",
        "url": "https://example.no/",
    }
    candidate_record = _available_site(org="912345678")
    ops = {"requests": 2, "bytes": 100, "latencies_ms": [5]}

    with patch(
        "norway_company_agent.wikidata_discovery.discover_final_website",
        return_value=(profile, base_total),
    ), patch(
        "norway_company_agent.wikidata_discovery.fetch_bounded_homepage",
        return_value=(candidate_record, ops),
    ), patch(
        "norway_company_agent.wikidata_discovery.apply_registry_risk_guard",
        side_effect=lambda row: (row, []),
    ):
        row, metrics = discover_final_website_with_wikidata(
            profile,
            wikidata_candidate=candidate,
        )

    website = row["evidence"]["website"]
    assert website["status"] == "available"
    assert website["value"]["identity_assessment"]["publishable"] is True
    assert metrics["requests"] == 4
    assert metrics["wikidata_attempted"] is True
    assert metrics["wikidata_verified"] is True
    assert metrics["selected_source"] == "wikidata_candidate"
