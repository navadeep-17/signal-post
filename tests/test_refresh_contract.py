from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.output_contract import project_terminal_envelope  # noqa: E402
from norway_company_agent.refresh_contract import (  # noqa: E402
    group_refresh_events,
    normalize_refresh_event,
    validate_refresh_change,
)


OLD_HASH = "a" * 64
NEW_HASH = "b" * 64


def raw_change(**overrides):
    value = {
        "organisation_number": "923609016",
        "field": "registry.employees",
        "old_value": 2,
        "new_value": 3,
        "source_url": "https://data.brreg.no/enhetsregisteret/api/enheter/923609016",
        "retrieved_at": "2026-08-02T00:00:00Z",
        "effective_at": "2026-08-01T23:59:59Z",
        "source_class": "official_registry_live",
        "old_content_sha256": OLD_HASH,
        "new_content_sha256": NEW_HASH,
        "status": "available",
    }
    value.update(overrides)
    return value


def minimal_envelope():
    return {
        "run_id": "refresh-test",
        "organisation_number": "923609016",
        "state": "complete",
        "started_at": "2026-08-02T00:00:00Z",
        "completed_at": "2026-08-02T00:00:01Z",
        "modules": {},
        "profile": {
            "organisation_number": "923609016",
            "run_metrics": {"requests": 0, "latencies_ms": []},
            "evidence": {},
        },
    }


def test_refresh_event_normalizes_to_stable_public_shape():
    first = normalize_refresh_event(raw_change())
    second = normalize_refresh_event(raw_change())
    assert first == second
    assert first["id"].startswith("chg-")
    assert first["previous_value"] == 2
    assert first["current_value"] == 3
    assert first["previous_content_sha256"] == OLD_HASH
    assert first["current_content_sha256"] == NEW_HASH
    assert validate_refresh_change(first, expected_org="923609016") == []


def test_refresh_change_is_attached_to_matching_contract_object():
    change = normalize_refresh_event(raw_change())
    item = project_terminal_envelope(minimal_envelope(), changes=[change])
    assert item["organisation_number"] == "923609016"
    assert item["changes"] == [change]
    assert validate_refresh_change(item["changes"][0], expected_org=item["organisation_number"]) == []


def test_grouping_rejects_wrong_company_event():
    with pytest.raises(ValueError, match="outside output batch"):
        group_refresh_events(
            [raw_change(organisation_number="987654321")],
            expected_organisation_numbers={"923609016"},
        )


def test_grouping_rejects_duplicate_field_event():
    with pytest.raises(ValueError, match="Duplicate refresh field event"):
        group_refresh_events(
            [raw_change(), raw_change(new_value=4, new_content_sha256="c" * 64)],
            expected_organisation_numbers={"923609016"},
        )


def test_unchanged_value_is_not_a_valid_change():
    with pytest.raises(ValueError, match="does not change the value"):
        normalize_refresh_event(raw_change(new_value=2))


def test_invalid_provenance_hash_is_rejected():
    normalized = normalize_refresh_event(raw_change(new_content_sha256="short"))
    assert "invalid current_content_sha256" in validate_refresh_change(normalized, expected_org="923609016")
    with pytest.raises(ValueError, match="invalid current_content_sha256"):
        group_refresh_events(
            [raw_change(new_content_sha256="short")],
            expected_organisation_numbers={"923609016"},
        )


def test_zero_values_remain_real_refresh_values():
    normalized = normalize_refresh_event(raw_change(old_value=0, new_value=1))
    assert normalized["previous_value"] == 0
    assert normalized["current_value"] == 1


def test_empty_refresh_event_set_is_idempotent_for_contract_projection():
    grouped = group_refresh_events([], expected_organisation_numbers={"923609016"})
    item = project_terminal_envelope(minimal_envelope(), changes=grouped["923609016"])
    assert item["changes"] == []
