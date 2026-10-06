#!/usr/bin/env python3
"""Aggregate inventory of retained profile fields that may be under-projected.

Research-only and zero-network. Reads archived retained profiles plus the frozen
1000-company output contract. It persists only path names, types, and counts;
raw company values, URLs, names, emails, free text, and org lists are never
written to the report.
"""

from __future__ import annotations

import argparse
import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


IGNORED_PREFIXES = (
    "run_metrics",
)

# These branches are intentionally excluded from the retained-field opportunity
# inventory because they are already projection products rather than source
# material, or are dominated by raw text/provenance rather than reusable facts.
EXCLUDED_BRANCHES = (
    "external_observations",
)

RAWISH_KEYS = {
    "main_text_excerpt",
    "identity_text_excerpt",
    "description",
    "evidence_span",
    "note",
    "content_sha256",
    "retrieved_at",
    "source_url",
    "requested_url",
    "final_url",
    "url",
    "crawl_errors",
}


def _nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _typename(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int) and not isinstance(value, bool):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    return type(value).__name__


def _walk(value: Any, path: str, out: dict[str, set[str]], types: dict[str, Counter[str]]) -> None:
    if path and any(path == p or path.startswith(p + ".") for p in EXCLUDED_BRANCHES):
        return
    if path and any(path == p or path.startswith(p + ".") for p in IGNORED_PREFIXES):
        return

    if isinstance(value, dict):
        for key, child in value.items():
            key_s = str(key)
            child_path = f"{path}.{key_s}" if path else key_s
            if any(
                child_path == prefix or child_path.startswith(prefix + ".")
                for prefix in EXCLUDED_BRANCHES
            ):
                continue
            if any(
                child_path == prefix or child_path.startswith(prefix + ".")
                for prefix in IGNORED_PREFIXES
            ):
                continue
            # Keep structural/container presence, but do not descend into rawish
            # free-text/provenance payloads.
            if _nonempty(child):
                out[child_path].add("present")
                types[child_path][_typename(child)] += 1
            if key_s in RAWISH_KEYS:
                continue
            _walk(child, child_path, out, types)
        return

    if isinstance(value, list):
        item_path = path + "[]"
        if value:
            out[item_path].add("present")
            types[item_path]["list_items"] += len(value)
        # Walk only object/list structure. Scalar list values are deliberately
        # not inspected; their path presence is already counted above.
        for child in value[:50]:
            if isinstance(child, (dict, list)):
                _walk(child, item_path, out, types)
        return


def read_profiles(profiles_dir: Path) -> list[dict[str, Any]]:
    paths = sorted(profiles_dir.rglob("profiles.jsonl"))
    if not paths:
        raise ValueError("no profiles.jsonl found")
    rows: list[dict[str, Any]] = []
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if isinstance(row, dict):
                    rows.append(row)
    return rows


def output_coverage(path: Path) -> tuple[dict[str, int], dict[str, int], dict[str, int], int]:
    claim_orgs: dict[str, set[str]] = defaultdict(set)
    fact_orgs: dict[str, set[str]] = defaultdict(set)
    area_orgs: dict[str, set[str]] = defaultdict(set)
    count = 0
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            org = str(row.get("organisation_number") or "")
            count += 1
            for claim in row.get("claims") or []:
                if (
                    isinstance(claim, dict)
                    and claim.get("availability") == "available"
                    and claim.get("field")
                ):
                    claim_orgs[str(claim["field"])].add(org)
            for fact in row.get("canonical_facts") or []:
                if (
                    isinstance(fact, dict)
                    and fact.get("availability") == "available"
                    and fact.get("type")
                ):
                    fact_orgs[str(fact["type"])].add(org)
            for area, present in ((row.get("canonical_profile") or {}).get("data_areas") or {}).items():
                if present:
                    area_orgs[str(area)].add(org)
    return (
        {k: len(v) for k, v in claim_orgs.items()},
        {k: len(v) for k, v in fact_orgs.items()},
        {k: len(v) for k, v in area_orgs.items()},
        count,
    )


def audit(
    profiles: list[dict[str, Any]],
    output_gz: Path,
    *,
    min_companies: int,
) -> dict[str, Any]:
    path_orgs: dict[str, set[str]] = defaultdict(set)
    path_types: dict[str, Counter[str]] = defaultdict(Counter)

    seen_orgs: set[str] = set()
    for profile in profiles:
        org = str(profile.get("organisation_number") or "")
        if not org or org in seen_orgs:
            raise ValueError("duplicate or missing retained profile organisation number")
        seen_orgs.add(org)

        presence: dict[str, set[str]] = defaultdict(set)
        types: dict[str, Counter[str]] = defaultdict(Counter)
        _walk(profile, "", presence, types)
        for path in presence:
            path_orgs[path].add(org)
        for path, counter in types.items():
            path_types[path].update(counter)

    claims, facts, areas, output_count = output_coverage(output_gz)
    if output_count != len(profiles):
        raise ValueError(f"profile/output count mismatch: {len(profiles)} vs {output_count}")

    paths = []
    for path, orgs in path_orgs.items():
        n = len(orgs)
        if n < min_companies:
            continue
        paths.append(
            {
                "path": path,
                "companies": n,
                "coverage_pct": round(100 * n / len(profiles), 2),
                "types": dict(sorted(path_types[path].items())),
            }
        )
    paths.sort(key=lambda x: (-x["companies"], x["path"]))

    return {
        "screen_type": "retained_profile_field_inventory_zero_network",
        "companies": len(profiles),
        "network_requests": 0,
        "minimum_companies": min_companies,
        "retained_paths_meeting_threshold": len(paths),
        "retained_paths": paths,
        "current_available_claim_field_coverage": dict(sorted(claims.items())),
        "current_available_canonical_fact_coverage": dict(sorted(facts.items())),
        "current_canonical_data_area_coverage": dict(sorted(areas.items())),
        "privacy_boundary": {
            "raw_values_retained": False,
            "organisation_number_lists_retained": False,
            "urls_retained": False,
            "emails_retained": False,
            "free_text_retained": False,
            "aggregate_path_counts_only": True,
        },
        "notes": [
            "This is a discovery inventory, not authorization to publish any retained field.",
            "High coverage alone is insufficient; each candidate needs exact source semantics and projection validation.",
            "external_observations and run_metrics are excluded because they are already derived/projection/runtime branches.",
            "Raw text, URLs, hashes, descriptions and provenance values are not traversed or retained.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profiles-dir", type=Path, required=True)
    parser.add_argument("--output-contract-gz", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--min-companies", type=int, default=20)
    args = parser.parse_args()

    profiles = read_profiles(args.profiles_dir)
    if len(profiles) != 1000:
        raise SystemExit(f"expected 1000 retained profiles, got {len(profiles)}")
    report = audit(
        profiles,
        args.output_contract_gz,
        min_companies=max(1, args.min_companies),
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
