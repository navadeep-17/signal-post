#!/usr/bin/env python3
"""Research-only BRREG public announcement exact-org reach screen.

Parses server-rendered Brønnøysund public announcement search HTML. Exact
nine-digit organisation numbers are the only company join. A date header row
sets the effective announcement date for following company rows.

This script performs no network access and emits aggregate/target-level research
evidence only; it does not publish production claims.
"""

from __future__ import annotations

import argparse
import gzip
import html as html_lib
import json
import re
from pathlib import Path
from typing import Any

TR_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.I | re.S)
TD_RE = re.compile(r"<td\b[^>]*>(.*?)</td>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
ORG_RE = re.compile(r"(?<!\d)(\d{3}[ .]?\d{3}[ .]?\d{3}|\d{9})(?!\d)")
DATE_RE = re.compile(r"\b(\d{2}\.\d{2}\.\d{4})\b")


def _clean(fragment: str) -> str:
    value = html_lib.unescape(TAG_RE.sub(" ", fragment))
    return re.sub(r"\s+", " ", value).strip()


def norm_org(value: Any) -> str | None:
    digits = re.sub(r"\D", "", str(value or ""))
    return digits if len(digits) == 9 else None


def read_targets(path: Path) -> set[str]:
    out: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        org = norm_org(row.get("organisation_number"))
        if not org:
            raise ValueError(f"invalid target row: {row!r}")
        if org in out:
            raise ValueError(f"duplicate target org {org}")
        out.add(org)
    if not out:
        raise ValueError("empty target cohort")
    return out


def current_registry_change_orgs(path: Path, targets: set[str]) -> set[str]:
    seen: set[str] = set()
    covered: set[str] = set()
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            org = norm_org(row.get("organisation_number"))
            if not org or org not in targets:
                continue
            seen.add(org)
            for claim in row.get("claims") or []:
                if (
                    isinstance(claim, dict)
                    and claim.get("field") == "official_registry_change"
                    and claim.get("availability") == "available"
                ):
                    covered.add(org)
                    break
    if seen != targets:
        raise ValueError(f"production output target mismatch: seen={len(seen)} targets={len(targets)}")
    return covered


def parse_announcement_html(path: Path) -> list[dict[str, Any]]:
    raw = path.read_bytes()
    text = None
    for enc in ("utf-8", "iso-8859-1", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise ValueError("could not decode announcement HTML")

    current_date: str | None = None
    rows: list[dict[str, Any]] = []

    for tr in TR_RE.findall(text):
        cells = [_clean(cell) for cell in TD_RE.findall(tr)]
        if not cells:
            continue
        joined = " | ".join(cells)

        dates = DATE_RE.findall(joined)
        orgs = sorted(
            {
                digits
                for match in ORG_RE.findall(joined)
                if (digits := re.sub(r"\D", "", match)) and len(digits) == 9
            }
        )

        # BRREG date headers contain a date but no organisation number.
        if dates and not orgs:
            current_date = dates[0]
            continue

        if not orgs:
            continue

        # Data rows currently carry one org number. Multiple orgs are rejected
        # rather than ambiguously attributing one announcement row.
        if len(orgs) != 1:
            rows.append(
                {
                    "organisation_number": None,
                    "announcement_date": current_date,
                    "ambiguous_org_count": len(orgs),
                    "cell_count": len(cells),
                }
            )
            continue

        # Do not persist company names. The likely announcement-type text is
        # retained only as a normalized short label candidate for aggregate
        # classification; identity is never derived from it.
        nonempty = [x for x in cells if x]
        org_display = next((x for x in nonempty if norm_org(x) == orgs[0]), None)
        other = [x for x in nonempty if x != org_display]
        type_candidate = other[-1][:160] if other else ""

        rows.append(
            {
                "organisation_number": orgs[0],
                "announcement_date": current_date,
                "type_candidate": type_candidate,
                "ambiguous_org_count": 0,
                "cell_count": len(cells),
            }
        )
    return rows


def screen(
    html_paths: list[Path],
    targets: set[str],
    current_changes: set[str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    all_rows: list[dict[str, Any]] = []
    for path in html_paths:
        all_rows.extend(parse_announcement_html(path))

    matched: dict[str, dict[str, Any]] = {}
    ambiguous_rows = 0
    undated_rows = 0
    for row in all_rows:
        if row.get("ambiguous_org_count"):
            ambiguous_rows += 1
            continue
        org = row.get("organisation_number")
        if not org:
            continue
        if not row.get("announcement_date"):
            undated_rows += 1
        if org not in targets:
            continue
        entry = matched.setdefault(
            org,
            {
                "organisation_number": org,
                "announcement_rows": 0,
                "dates": set(),
                "type_candidates": set(),
            },
        )
        entry["announcement_rows"] += 1
        if row.get("announcement_date"):
            entry["dates"].add(row["announcement_date"])
        if row.get("type_candidate"):
            entry["type_candidates"].add(row["type_candidate"])

    audit: list[dict[str, Any]] = []
    for org in sorted(matched):
        entry = matched[org]
        audit.append(
            {
                "organisation_number": org,
                "announcement_rows": entry["announcement_rows"],
                "dates": sorted(entry["dates"]),
                # No business names; announcement type only.
                "type_candidates": sorted(entry["type_candidates"]),
                "already_has_production_registry_change": org in current_changes,
            }
        )

    matched_orgs = set(matched)
    net_new = matched_orgs - current_changes
    report = {
        "screen_type": "brreg_public_announcements_shared_range_exact_org",
        "target_companies": len(targets),
        "source_html_files": len(html_paths),
        "parsed_announcement_rows": len(all_rows),
        "ambiguous_org_rows_excluded": ambiguous_rows,
        "undated_org_rows": undated_rows,
        "exact_target_companies": len(matched_orgs),
        "exact_target_reach": round(len(matched_orgs) / len(targets), 6) if targets else 0.0,
        "current_production_registry_change_companies": len(current_changes),
        "overlap_current_registry_change": len(matched_orgs & current_changes),
        "net_new_vs_current_registry_change": len(net_new),
        "net_new_vs_current_registry_change_reach": round(len(net_new) / len(targets), 6) if targets else 0.0,
        "external_requests": len(html_paths),
        "production_publication_enabled": False,
        "reuse_rights_status": "REQUIRES_EXPLICIT_PUBLIC_HTML_REUSE_MAPPING",
        "notes": [
            "Only an exact 9-digit organisation number in a BRREG announcement row establishes company identity.",
            "Announcement dates are inherited from BRREG date-header rows in the same response.",
            "Rows with multiple 9-digit organisation numbers are excluded.",
            "These are official registry/legal events and must never be relabelled as company-authored news.",
            "The paid XML subscription is not used.",
            "Production promotion requires explicit reuse-rights mapping for the public HTML announcement surface.",
        ],
    }
    return report, audit


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", action="append", type=Path, required=True)
    ap.add_argument("--companies", type=Path, required=True)
    ap.add_argument("--production-output-gz", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()

    targets = read_targets(args.companies)
    current = current_registry_change_orgs(args.production_output_gz, targets)
    report, audit = screen(args.html, targets, current)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "matched-companies.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in audit),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
