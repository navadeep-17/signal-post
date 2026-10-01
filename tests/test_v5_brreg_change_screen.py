from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "screen_brreg_change_feed_reach.py"
spec = importlib.util.spec_from_file_location("screen_brreg_change_feed_reach", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _companies() -> list[dict]:
    return [
        {"organisation_number": "123456789", "name": "A AS"},
        {"organisation_number": "987654321", "name": "B AS"},
    ]


def test_build_url_batches_exact_orgs_and_enables_changes() -> None:
    url = module.build_url(["123456789", "987654321"])
    assert url.startswith(module.ENDPOINT + "?")
    assert "123456789%2C987654321" in url
    assert "includeChanges=true" in url
    assert "size=10000" in url
    assert "sort=id%2CDESC" in url


def test_analyse_payload_measures_history_recency_and_paths() -> None:
    payload = {
        "_embedded": {
            "oppdaterteEnheter": [
                {
                    "oppdateringsid": 3,
                    "dato": "2026-09-01T12:00:00Z",
                    "organisasjonsnummer": "123456789",
                    "endringstype": "Endring",
                    "endringer": [
                        {"op": "replace", "path": "/navn", "value": "A AS"},
                        {"op": "replace", "path": "/forretningsadresse/postnummer", "value": "0001"},
                    ],
                },
                {
                    "oppdateringsid": 2,
                    "dato": "2025-04-01T12:00:00Z",
                    "organisasjonsnummer": "123456789",
                    "endringstype": "Endring",
                    "endringer": [{"op": "replace", "path": "/naeringskode1", "value": "62.100"}],
                },
                {
                    "oppdateringsid": 1,
                    "dato": "2020-01-01T00:00:00Z",
                    "organisasjonsnummer": "987654321",
                    "endringstype": "Nyregistrering",
                    "endringer": [],
                },
            ]
        },
        "page": {"totalElements": 3},
    }

    rows, report = module.analyse_payload(
        payload,
        _companies(),
        as_of=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )
    by_org = {row["organisation_number"]: row for row in rows}

    assert by_org["123456789"]["events"] == 2
    assert by_org["123456789"]["events_last_365_days"] == 1
    assert by_org["123456789"]["events_last_730_days"] == 2
    assert by_org["123456789"]["latest_update_at"] == "2026-09-01T12:00:00Z"
    assert by_org["987654321"]["events_last_730_days"] == 0
    assert report["companies_with_history"] == 2
    assert report["companies_with_update_last_365_days"] == 1
    assert report["companies_with_update_last_730_days"] == 1
    assert report["top_change_paths"]["/navn"] == 1
    assert report["unexpected_organisation_numbers"] == []


def test_analyse_payload_does_not_attribute_unexpected_org() -> None:
    payload = {
        "_embedded": {
            "oppdaterteEnheter": [
                {
                    "oppdateringsid": 1,
                    "dato": "2026-09-01T00:00:00Z",
                    "organisasjonsnummer": "111222333",
                    "endringstype": "Endring",
                    "endringer": [],
                }
            ]
        }
    }
    rows, report = module.analyse_payload(
        payload,
        _companies(),
        as_of=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )
    assert all(row["events"] == 0 for row in rows)
    assert report["unexpected_organisation_numbers"] == ["111222333"]


def test_extract_events_rejects_wrong_embedded_shape() -> None:
    with pytest.raises(ValueError, match="oppdaterteEnheter"):
        module.extract_events({"_embedded": {"oppdaterteEnheter": {"not": "a list"}}})
