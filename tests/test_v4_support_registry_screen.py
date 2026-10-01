from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "screen_support_registry_reach.py"
spec = importlib.util.spec_from_file_location("screen_support_registry_reach", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_scan_bulk_payload_matches_compact_and_grouped_org_numbers(tmp_path: Path) -> None:
    payload = tmp_path / "support.json"
    payload.write_text(
        json.dumps(
            [
                {"recipient": {"organisationNumber": "123456789"}, "amount": 1000},
                {"recipientText": "987 654 321", "amount": 2000},
                {"recipient": {"organisationNumber": "1112223330"}, "amount": 3000},
            ]
        ),
        encoding="utf-8",
    )
    companies = [
        {"organisation_number": "123456789", "name": "COMPACT AS"},
        {"organisation_number": "987654321", "name": "GROUPED AS"},
        {"organisation_number": "111222333", "name": "BOUNDARY AS"},
        {"organisation_number": "555666777", "name": "ABSENT AS"},
    ]

    rows = module.scan_bulk_payload(payload, companies, chunk_bytes=1024, overlap_bytes=64)
    by_org = {row["organisation_number"]: row for row in rows}

    assert by_org["123456789"]["matched"] is True
    assert by_org["123456789"]["raw_identifier_occurrences"] == 1
    assert by_org["987654321"]["matched"] is True
    assert by_org["987654321"]["raw_identifier_occurrences"] == 1
    assert by_org["111222333"]["matched"] is False
    assert by_org["555666777"]["matched"] is False


def test_scan_bulk_payload_deduplicates_overlap_window_matches(tmp_path: Path) -> None:
    payload = tmp_path / "support.json"
    payload.write_bytes(b"x" * 1000 + b'"123456789"' + b"y" * 1500)
    companies = [{"organisation_number": "123456789", "name": "ONE AS"}]

    rows = module.scan_bulk_payload(payload, companies, chunk_bytes=1024, overlap_bytes=128)

    assert rows[0]["matched"] is True
    assert rows[0]["raw_identifier_occurrences"] == 1
