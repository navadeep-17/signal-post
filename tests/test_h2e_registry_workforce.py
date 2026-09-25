from __future__ import annotations

import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.external_footprint import validate_observation
from norway_company_agent.registry_workforce import (
    attach_registry_workforce_observations,
    registry_workforce_observations,
)
from norway_company_agent.workforce_contract import project_workforce_observations


def _profile(*, org: str = "912345678", employees=17) -> dict:
    return {
        "organisation_number": org,
        "external_observations": [],
        "evidence": {
            "registry_live": {
                "status": "available",
                "source_type": "official_registry_live",
                "source_url": f"https://data.brreg.no/enhetsregisteret/api/enheter/{org}",
                "retrieved_at": "2026-09-16T00:00:00Z",
                "content_sha256": "a" * 64,
                "value": {
                    "organisation_number": org,
                    "employees": employees,
                },
            }
        },
    }


def test_registry_employee_count_becomes_publishable_workforce_observation():
    observations = registry_workforce_observations(_profile(employees=17))
    assert len(observations) == 1
    row = observations[0]
    assert row["platform"] == "brreg"
    assert row["signal_type"] == "workforce_snapshot"
    assert row["metrics"]["employees"] == 17
    assert row["metrics"]["measure"] == "employees"
    assert validate_observation(row) == []


def test_missing_registry_employee_count_abstains():
    assert registry_workforce_observations(_profile(employees=None)) == []


def test_mismatched_registry_entity_abstains():
    profile = _profile()
    profile["evidence"]["registry_live"]["value"]["organisation_number"] = "998877665"
    assert registry_workforce_observations(profile) == []


def test_attach_is_idempotent_and_preserves_other_observations():
    profile = _profile()
    profile["external_observations"] = [{"id": "other", "signal_type": "company_profile"}]
    attach_registry_workforce_observations(profile)
    attach_registry_workforce_observations(profile)
    ids = [row["id"] for row in profile["external_observations"]]
    assert ids.count("other") == 1
    assert len([value for value in ids if value.startswith("brreg-workforce-")]) == 1


def test_workforce_projection_is_idempotent():
    profile = _profile(employees=23)
    attach_registry_workforce_observations(profile)
    contract = {
        "organisation_number": profile["organisation_number"],
        "claims": [],
        "evidence": [],
    }
    first = project_workforce_observations(deepcopy(contract), profile)
    second = project_workforce_observations(deepcopy(first), profile)
    claims = [claim for claim in second["claims"] if claim.get("field") == "external.workforce_snapshot"]
    assert len(claims) == 1
    assert claims[0]["value"] == {"measure": "employees", "value": 23, "scope": "registry_entity"}

    first_ids = [entry["id"] for entry in first["evidence"]]
    second_ids = [entry["id"] for entry in second["evidence"]]
    assert second_ids == first_ids
    assert len(second_ids) == len(set(second_ids))
    assert len([value for value in second_ids if value.startswith("ev-workforce-")]) == 1
    assert len([value for value in second_ids if value.startswith("ev-registry-live-")]) == 1
