#!/usr/bin/env python3
"""Compare already-produced exact-org research source artifacts.

This is an artifact-only R4 comparator. It performs no source/network access and
never emits Signalpost production claims. Every input match row must carry one
exact 9-digit organisation number produced by an upstream precision screen.
"""

from __future__ import annotations

import argparse
import json
import re
from itertools import combinations
from pathlib import Path
from typing import Any

ORG_RE = re.compile(r"^\d{9}$")


def normalize_org(value: Any) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if not ORG_RE.fullmatch(digits):
        raise ValueError(f"invalid exact organisation number: {value!r}")
    return digits


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"JSONL row is not an object in {path}")
        rows.append(row)
    return rows


def parse_named_paths(values: list[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("expected NAME=PATH")
        name, raw_path = value.split("=", 1)
        name = name.strip()
        if not name or name in result:
            raise ValueError(f"invalid or duplicate source name: {name!r}")
        result[name] = Path(raw_path)
    if not result:
        raise ValueError("at least one source is required")
    return result


def parse_named_ints(values: list[str]) -> dict[str, int]:
    result: dict[str, int] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("expected NAME=INTEGER")
        name, raw = value.split("=", 1)
        parsed = int(raw)
        if parsed < 0:
            raise ValueError("request counts must be non-negative")
        result[name.strip()] = parsed
    return result


def scalar_or_list(row: dict[str, Any], singular: str, plural: str) -> list[str]:
    found: set[str] = set()
    singular_value = row.get(singular)
    if singular_value is not None and str(singular_value).strip():
        found.add(str(singular_value).strip())
    plural_value = row.get(plural)
    if isinstance(plural_value, list):
        found.update(str(value).strip() for value in plural_value if str(value).strip())
    elif plural_value is not None and str(plural_value).strip():
        found.add(str(plural_value).strip())
    return sorted(found)


def load_source(path: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(path):
        org = normalize_org(row.get("organisation_number"))
        if org in result:
            raise ValueError(f"duplicate org {org} in {path}")
        result[org] = row
    return result


def union_rows(sources: dict[str, dict[str, dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    union: dict[str, dict[str, Any]] = {}
    for source_name, rows in sources.items():
        for org, row in rows.items():
            target = union.setdefault(
                org,
                {
                    "organisation_number": org,
                    "sources": [],
                    "websites": [],
                    "emails": [],
                    "phones": [],
                },
            )
            target["sources"].append(source_name)
            target["websites"] = sorted(
                set(target["websites"]) | set(scalar_or_list(row, "website", "websites"))
            )
            target["emails"] = sorted(
                set(target["emails"]) | set(scalar_or_list(row, "email", "emails"))
            )
            target["phones"] = sorted(
                set(target["phones"]) | set(scalar_or_list(row, "phone", "phones"))
            )
    for row in union.values():
        row["sources"] = sorted(set(row["sources"]))
    return union


def load_report(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"report is not an object: {path}")
    return payload


def compare(
    source_paths: dict[str, Path],
    *,
    cohort_size: int,
    consumed_100_path: Path | None,
    source_reports: dict[str, Path],
    original_requests: dict[str, int],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    sources = {name: load_source(path) for name, path in source_paths.items()}
    sets = {name: set(rows) for name, rows in sources.items()}
    union = union_rows(sources)

    if len(union) > cohort_size:
        raise ValueError("union larger than cohort")

    consumed_100: set[str] | None = None
    if consumed_100_path is not None:
        consumed_100 = {
            normalize_org(row.get("organisation_number"))
            for row in read_jsonl(consumed_100_path)
        }
        if len(consumed_100) != 100:
            raise ValueError(f"expected 100-company subset, got {len(consumed_100)}")

    overlaps: list[dict[str, Any]] = []
    for left, right in combinations(sorted(sources), 2):
        overlap = sets[left] & sets[right]
        overlaps.append(
            {
                "left": left,
                "right": right,
                "companies": len(overlap),
                "organisation_numbers": sorted(overlap),
            }
        )

    source_stats: dict[str, Any] = {}
    for name in sorted(sources):
        others: set[str] = set()
        for other_name, other_set in sets.items():
            if other_name != name:
                others |= other_set
        unique = sets[name] - others
        stat: dict[str, Any] = {
            "exact_company_hits": len(sets[name]),
            "unique_contribution": len(unique),
            "unique_organisation_numbers": sorted(unique),
            "original_external_requests": original_requests.get(name),
        }
        report_path = source_reports.get(name)
        if report_path is not None:
            source_report = load_report(report_path)
            stat["reuse_rights_status"] = source_report.get("reuse_rights_status")
            stat["api_access_status"] = source_report.get("api_access_status")
            stat["source"] = source_report.get("source") or source_report.get("source_family")
        source_stats[name] = stat

    union_values = list(union.values())
    request_values = [value for value in original_requests.values()]
    original_request_total = sum(request_values) if request_values else None

    report: dict[str, Any] = {
        "screen_type": "artifact_only_exact_org_source_union",
        "cohort_size": cohort_size,
        "source_count": len(sources),
        "source_stats": source_stats,
        "pairwise_overlaps": overlaps,
        "union_exact_company_hits": len(union),
        "union_reach": round(len(union) / cohort_size, 6),
        "union_website_candidate_companies": sum(bool(row["websites"]) for row in union_values),
        "union_email_candidate_companies": sum(bool(row["emails"]) for row in union_values),
        "union_phone_candidate_companies": sum(bool(row["phones"]) for row in union_values),
        "companies_in_multiple_sources": sum(len(row["sources"]) > 1 for row in union_values),
        "original_external_requests_total": original_request_total,
        "union_hits_per_original_request": (
            round(len(union) / original_request_total, 6)
            if original_request_total and original_request_total > 0
            else None
        ),
        "comparator_external_source_requests": 0,
        "production_publication_enabled": False,
        "notes": [
            "This comparator consumes only frozen research artifacts; it performs no source requests.",
            "Upstream exact-org screens remain responsible for source-specific identity semantics.",
            "A source with unresolved reuse rights cannot be promoted merely because it improves union reach.",
        ],
    }
    if consumed_100 is not None:
        union_100 = set(union) & consumed_100
        report["consumed_100"] = {
            "union_exact_company_hits": len(union_100),
            "union_reach": round(len(union_100) / 100, 6),
            "organisation_numbers": sorted(union_100),
        }

    return report, union


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", action="append", default=[], help="NAME=matched.jsonl")
    parser.add_argument("--source-report", action="append", default=[], help="NAME=report.json")
    parser.add_argument("--original-requests", action="append", default=[], help="NAME=COUNT")
    parser.add_argument("--cohort-size", type=int, required=True)
    parser.add_argument("--consumed-100", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    source_paths = parse_named_paths(args.source)
    source_reports = parse_named_paths(args.source_report) if args.source_report else {}
    original_requests = parse_named_ints(args.original_requests)
    unknown_reports = set(source_reports) - set(source_paths)
    unknown_requests = set(original_requests) - set(source_paths)
    if unknown_reports or unknown_requests:
        raise SystemExit(
            f"source metadata references unknown sources: reports={sorted(unknown_reports)} requests={sorted(unknown_requests)}"
        )

    report, union = compare(
        source_paths,
        cohort_size=args.cohort_size,
        consumed_100_path=args.consumed_100,
        source_reports=source_reports,
        original_requests=original_requests,
    )

    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / "union-companies.jsonl").open("w", encoding="utf-8") as handle:
        for org in sorted(union):
            handle.write(json.dumps(union[org], ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
