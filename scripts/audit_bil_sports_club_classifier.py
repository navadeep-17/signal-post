#!/usr/bin/env python3
"""Zero-network impact audit for the BIL/B.I.L. sports-club classifier fix.

The historical classifier treated contiguous "BIL" (Norwegian: car) as if it were
the abbreviation B.I.L. (bedriftsidrettslag). This audit measures the frozen
1000-company impact without retaining names or organisation-number lists.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.identity import _is_business_sports_club  # noqa: E402

OLD_RE = re.compile(r"(?:^|\s)B\.?\s*I\.?\s*L\.?(?:\s|$)", re.I)


def read_profiles(profiles_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in sorted(profiles_dir.rglob("profiles.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            org = re.sub(r"\D", "", str(row.get("organisation_number") or ""))
            if len(org) != 9 or org in seen:
                raise ValueError(f"invalid or duplicate org: {org!r}")
            seen.add(org)
            rows.append(row)
    if len(rows) != 1000:
        raise ValueError(f"expected 1000 archived profiles, got {len(rows)}")
    return rows


def audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    old_true = 0
    new_true = 0
    old_only = 0
    new_only = 0
    old_only_plain_bil = 0
    old_only_with_as_suffix = 0
    explicit_separator_names = 0
    registry_context_rescues = 0

    for row in rows:
        name = str(row.get("name") or "")
        old = bool(OLD_RE.search(name))
        new = bool(_is_business_sports_club(row))
        if old:
            old_true += 1
        if new:
            new_true += 1
        if old and not new:
            old_only += 1
            if re.search(r"(?i)(?:^|\s)BIL(?:\s|$)", name):
                old_only_plain_bil += 1
            if re.search(r"(?i)\bBIL\s+AS\b", name):
                old_only_with_as_suffix += 1
        if new and not old:
            new_only += 1
            # Plain BIL can still be a true sports club when BRREG says so.
            if re.search(r"(?i)(?:^|\s)BIL(?:\s|$)", name):
                registry_context_rescues += 1
        if re.search(
            r"(?i)(?<![A-ZÆØÅ0-9])B(?:\s*\.\s*|\s+)I(?:\s*\.\s*|\s+)L\.?(?![A-ZÆØÅ0-9])",
            name,
        ):
            explicit_separator_names += 1

    return {
        "screen_type": "zero_network_bil_sports_club_classifier_impact",
        "companies": len(rows),
        "old_classifier_positive_companies": old_true,
        "corrected_classifier_positive_companies": new_true,
        "old_only_false_positive_risk_companies": old_only,
        "old_only_plain_bil_companies": old_only_plain_bil,
        "old_only_bil_as_companies": old_only_with_as_suffix,
        "corrected_only_registry_context_companies": new_only,
        "corrected_only_plain_bil_registry_context_companies": registry_context_rescues,
        "explicit_b_i_l_separator_name_companies": explicit_separator_names,
        "network_requests": 0,
        "company_values_retained": False,
        "organisation_lists_retained": False,
        "notes": [
            "The old regex allowed zero separators, so ordinary BIL could be interpreted as B.I.L.",
            "The corrected classifier requires B/I/L separators unless exact BRREG activity/purpose text independently indicates bedriftsidrett/idrett.",
            "This audit measures classifier impact only; it does not publish websites.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profiles-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    report = audit(read_profiles(args.profiles_dir))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
