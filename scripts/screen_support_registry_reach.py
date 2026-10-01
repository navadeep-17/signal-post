#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


def _org(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("organisation_number")
    digits = "".join(character for character in str(value or "") if character.isdigit())
    if len(digits) != 9:
        raise ValueError(f"Invalid Norwegian organisation number: {value!r}")
    return digits


def _read_companies(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"Expected JSON object rows in {path}")
        organisation_number = _org(row)
        if organisation_number in seen:
            raise ValueError(f"Duplicate organisation number in screen cohort: {organisation_number}")
        seen.add(organisation_number)
        rows.append(row)
    if not rows:
        raise ValueError("Screen cohort is empty")
    return rows


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pattern_for_org(organisation_number: str) -> re.Pattern[bytes]:
    # The public registry UI renders organisation numbers both compactly and in
    # 3-3-3 groups. This reach screen is deliberately schema-agnostic: it asks
    # only whether the exact 9-digit identifier occurs in the official bulk
    # payload. Production extraction must parse structured fields instead.
    a, b, c = organisation_number[:3], organisation_number[3:6], organisation_number[6:]
    expr = (
        rb"(?<!\d)"
        + a.encode("ascii")
        + rb"(?:[^0-9]{0,3})"
        + b.encode("ascii")
        + rb"(?:[^0-9]{0,3})"
        + c.encode("ascii")
        + rb"(?!\d)"
    )
    return re.compile(expr)


def scan_bulk_payload(
    payload_path: Path,
    companies: list[dict[str, Any]],
    *,
    chunk_bytes: int = 8 * 1024 * 1024,
    overlap_bytes: int = 256,
    context_bytes: int = 220,
) -> list[dict[str, Any]]:
    if chunk_bytes < 1024:
        raise ValueError("chunk_bytes must be at least 1024")
    if overlap_bytes < 32:
        raise ValueError("overlap_bytes must be at least 32")

    patterns = {_org(row): _pattern_for_org(_org(row)) for row in companies}
    positions: dict[str, set[int]] = {org: set() for org in patterns}
    first_context: dict[str, str] = {}

    tail = b""
    consumed = 0
    with payload_path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_bytes)
            if not chunk:
                break
            window = tail + chunk
            window_start = consumed - len(tail)
            for org, pattern in patterns.items():
                for match in pattern.finditer(window):
                    absolute_position = window_start + match.start()
                    if absolute_position < 0 or absolute_position in positions[org]:
                        continue
                    positions[org].add(absolute_position)
                    if org not in first_context:
                        left = max(0, match.start() - context_bytes)
                        right = min(len(window), match.end() + context_bytes)
                        first_context[org] = window[left:right].decode("utf-8", errors="replace")
            consumed += len(chunk)
            tail = window[-overlap_bytes:]

    results: list[dict[str, Any]] = []
    for row in companies:
        organisation_number = _org(row)
        matches = sorted(positions[organisation_number])
        results.append(
            {
                "organisation_number": organisation_number,
                "name": row.get("name"),
                "matched": bool(matches),
                "raw_identifier_occurrences": len(matches),
                "first_byte_offset": matches[0] if matches else None,
                "first_context": first_context.get(organisation_number),
            }
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Measure exact-organisation-number reach in the official BRREG "
            "Støtteregisteret bulk JSON without implementing a production connector."
        )
    )
    parser.add_argument("--companies", required=True, help="JSONL cohort with organisation_number")
    parser.add_argument("--support-json", required=True, help="Official Støtteregisteret totalbestand JSON")
    parser.add_argument("--report", required=True)
    parser.add_argument("--rows-output", required=True)
    args = parser.parse_args()

    companies_path = Path(args.companies)
    support_path = Path(args.support_json)
    report_path = Path(args.report)
    rows_path = Path(args.rows_output)

    companies = _read_companies(companies_path)
    if not support_path.is_file() or support_path.stat().st_size == 0:
        raise SystemExit(f"Support-registry payload is missing or empty: {support_path}")

    rows = scan_bulk_payload(support_path, companies)
    matched = [row for row in rows if row["matched"]]
    report = {
        "source": "brreg_stotteregisteret_totalbestand_json",
        "source_url": "https://stotte.brreg.no/nb/oppslag/stoettetildeling/totalbestand/json",
        "screen_type": "exact_identifier_presence_only",
        "companies": len(rows),
        "matched_companies": len(matched),
        "reach_rate": round(len(matched) / len(rows), 6),
        "total_raw_identifier_occurrences": sum(int(row["raw_identifier_occurrences"]) for row in rows),
        "payload_bytes": support_path.stat().st_size,
        "payload_sha256": _sha256(support_path),
        "cohort_sha256": _sha256(companies_path),
        "production_connector_implemented": False,
        "notes": [
            "This is a reach screen, not a production extractor.",
            "A match means the exact organisation number occurs in the official bulk payload.",
            "Any promoted connector must parse structured recipient fields and preserve source evidence.",
        ],
    }

    rows_path.parent.mkdir(parents=True, exist_ok=True)
    with rows_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
