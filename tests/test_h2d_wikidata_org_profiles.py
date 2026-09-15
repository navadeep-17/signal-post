from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.external_footprint import validate_observation
from norway_company_agent.wikidata_org_profiles import (
    candidate_observation,
    fetch_wikidata_linkedin_candidates,
    linkedin_company_url,
)


class _Response:
    def __init__(self, payload: dict):
        self._raw = json.dumps(payload).encode("utf-8")
        self.headers = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, amount: int = -1):
        return self._raw if amount < 0 else self._raw[:amount]


def test_linkedin_company_url_accepts_org_slug_and_rejects_path_injection():
    assert linkedin_company_url("example-company") == "https://www.linkedin.com/company/example-company/"
    assert linkedin_company_url("example/company") is None
    assert linkedin_company_url(" example company ") is None
    assert linkedin_company_url("-bad") is None


def test_exact_p2333_p4264_mapping_yields_one_candidate_in_one_request():
    payload = {
        "results": {
            "bindings": [
                {
                    "org": {"value": "912345678"},
                    "item": {"value": "http://www.wikidata.org/entity/Q123"},
                    "linkedin": {"value": "example-company"},
                }
            ]
        }
    }
    with patch("urllib.request.urlopen", return_value=_Response(payload)) as mocked:
        candidates, metrics = fetch_wikidata_linkedin_candidates(["912345678"])

    candidate = candidates["912345678"]
    assert candidate["wikidata_item"].endswith("Q123")
    assert candidate["property_id"] == "P4264"
    assert candidate["profile_url"] == "https://www.linkedin.com/company/example-company/"
    assert metrics["requests"] == 1
    assert metrics["candidate_companies"] == 1
    request = mocked.call_args.args[0]
    assert "P2333" in request.full_url
    assert "P4264" in request.full_url
    assert request.headers.get("User-agent")


def test_duplicate_wikidata_items_for_same_org_abstain():
    payload = {
        "results": {
            "bindings": [
                {
                    "org": {"value": "912345678"},
                    "item": {"value": "http://www.wikidata.org/entity/Q123"},
                    "linkedin": {"value": "example-company"},
                },
                {
                    "org": {"value": "912345678"},
                    "item": {"value": "http://www.wikidata.org/entity/Q456"},
                    "linkedin": {"value": "example-company"},
                },
            ]
        }
    }
    with patch("urllib.request.urlopen", return_value=_Response(payload)):
        candidates, metrics = fetch_wikidata_linkedin_candidates(["912345678"])

    assert candidates == {}
    assert metrics["ambiguous_item_organisations"] == 1


def test_duplicate_linkedin_values_for_same_item_abstain():
    payload = {
        "results": {
            "bindings": [
                {
                    "org": {"value": "912345678"},
                    "item": {"value": "http://www.wikidata.org/entity/Q123"},
                    "linkedin": {"value": "example-company"},
                },
                {
                    "org": {"value": "912345678"},
                    "item": {"value": "http://www.wikidata.org/entity/Q123"},
                    "linkedin": {"value": "example-company-old"},
                },
            ]
        }
    }
    with patch("urllib.request.urlopen", return_value=_Response(payload)):
        candidates, metrics = fetch_wikidata_linkedin_candidates(["912345678"])

    assert candidates == {}
    assert metrics["ambiguous_linkedin_identifiers"] == 1


def test_candidate_observation_is_publishable_and_narrowly_scoped():
    profile = {"organisation_number": "912345678", "name": "EXAMPLE AS"}
    candidate = {
        "organisation_number": "912345678",
        "wikidata_item": "http://www.wikidata.org/entity/Q123",
        "property_id": "P4264",
        "linkedin_identifier": "example-company",
        "profile_url": "https://www.linkedin.com/company/example-company/",
        "source_url": "https://query.wikidata.org/sparql?query=test",
        "content_sha256": "a" * 64,
        "retrieved_at": "2026-09-16T00:00:00Z",
    }
    observation = candidate_observation(profile, candidate)

    assert observation is not None
    assert observation["platform"] == "linkedin"
    assert observation["signal_type"] == "profile_handle"
    assert observation["source_class"] == "wikidata"
    assert observation["acquisition_mode"] == "official_api"
    assert validate_observation(observation) == []
    assert "LinkedIn page itself was not fetched" in observation["metrics"]["claim_scope"]


def test_candidate_observation_rejects_org_mismatch():
    profile = {"organisation_number": "912345678"}
    candidate = {
        "organisation_number": "987654321",
        "profile_url": "https://www.linkedin.com/company/example-company/",
    }
    assert candidate_observation(profile, candidate) is None
