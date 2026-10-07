#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.batch import profiles_from_bulk, read_organisation_inputs  # noqa: E402
from norway_company_agent.v9_m12_late_registry_domain import (  # noqa: E402
    select_late_registry_domain_candidate,
)


# These companies were explicitly researched while choosing M12. They are retained
# for mechanism debugging but MUST NOT count as breadth/holdout evidence.
DEVELOPMENT_RESEARCHED_ORGS = {
    "828829092",  # EMILSEN FISK AS
    "870418892",  # REGNSKAP & KONTORSERVICE NIKOLAISEN
    "896488562",  # SKOGBRUKETS SERVICESENTER AS
    "898321622",  # FAST ENTREPRENØR AS
    "911546221",  # HAGEN UTEROM AS
    "914384729",  # NORD OG NED AS
    "936455298",  # VESTNOR TRANSPORT AS (consumer-domain rejection check)
    "976533194",  # POINT OF VIEW AS
    "979436661",  # BALLSTAD FISK AS
    "988936987",  # ARILD BRÅTEN REGNSKAP AS
    "992784229",  # VIKEDAL FUS BARNEHAGE AS
    "996405524",  # ELEKTRIKERSERVICE VERDAL AS
}

# Existing positive M10 canaries are excluded entirely so repeated prior wins cannot
# satisfy M12 breadth.
M10_POSITIVE_CANARIES = {"927097532", "979943377", "999096298"}


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classify(profile: dict[str, Any]) -> dict[str, Any]:
    org = str(profile.get("organisation_number") or "")
    candidate = select_late_registry_domain_candidate(profile)
    if candidate:
        bucket = (
            "m12_delta_development"
            if org in DEVELOPMENT_RESEARCHED_ORGS
            else "m12_delta_holdout"
        )
    else:
        bucket = "m12_control"
    return {
        "organisation_number": org,
        "bucket": bucket,
        "candidate_domain": (candidate or {}).get("domain"),
        "candidate_strategy": (candidate or {}).get("strategy"),
        "registry_email_domain": (candidate or {}).get("registry_email_domain"),
        "registry_website_present": bool(str(profile.get("website") or "").strip()),
        "development_researched": org in DEVELOPMENT_RESEARCHED_ORGS,
        "m10_positive_canary": org in M10_POSITIVE_CANARIES,
    }


def build(
    profiles: list[dict[str, Any]],
    *,
    target_count: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if target_count < 1:
        raise ValueError("target_count must be positive")

    classified = []
    for profile in profiles:
        org = str(profile.get("organisation_number") or "")
        if len(org) != 9 or not org.isdigit() or org in M10_POSITIVE_CANARIES:
            continue
        # M12 only changes companies without an official registry website.
        if str(profile.get("website") or "").strip():
            continue
        classified.append(classify(profile))

    delta = sorted(
        [row for row in classified if row["bucket"].startswith("m12_delta_")],
        key=lambda row: row["organisation_number"],
    )
    controls = sorted(
        [row for row in classified if row["bucket"] == "m12_control"],
        key=lambda row: row["organisation_number"],
    )
    if len(delta) > target_count:
        raise ValueError(
            f"M12 affected population {len(delta)} exceeds target_count={target_count}; "
            "do not silently omit affected consumed companies"
        )
    selected = [*delta, *controls[: target_count - len(delta)]]
    if len(selected) != target_count:
        raise ValueError(
            f"insufficient consumed profiles: selected={len(selected)}, target={target_count}"
        )

    holdout = [row for row in delta if row["bucket"] == "m12_delta_holdout"]
    development = [row for row in delta if row["bucket"] == "m12_delta_development"]
    if not holdout:
        raise ValueError("M12 has no unresearched affected holdout; experiment cannot test breadth")

    manifest = [
        {
            "organisation_number": row["organisation_number"],
            "evaluation_split": "v9_m12_consumed_request_neutral",
            "sample_slice": row["bucket"],
        }
        for row in selected
    ]
    report = {
        "screen_type": "v9_m12_consumed_request_neutral_target",
        "source_population_companies": len(profiles),
        "selected_companies": len(selected),
        "affected_companies": len(delta),
        "development_researched_affected_companies": len(development),
        "unresearched_holdout_affected_companies": len(holdout),
        "control_companies": sum(row["bucket"] == "m12_control" for row in selected),
        "fresh_companies_used": 0,
        "excluded_m10_positive_canaries": sorted(M10_POSITIVE_CANARIES),
        "development_researched_orgs": sorted(DEVELOPMENT_RESEARCHED_ORGS),
        "selection_rule": [
            "start from frozen already-consumed 1000-company population",
            "exclude the three known M10 positive canaries",
            "exclude registry-website-present companies because M12 does not own their site slot",
            "include every request-allocation-affected late registry-domain company",
            "label externally researched strategy-design companies as development, never holdout",
            "treat remaining affected companies as the unresearched internal breadth holdout",
            "fill to 100 with deterministic controls by organisation number",
        ],
    }
    return manifest, selected, report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source-manifest", type=Path, required=True)
    p.add_argument("--bulk", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--audit", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--target-count", type=int, default=100)
    args = p.parse_args()

    source = read_organisation_inputs(args.source_manifest)
    source_orgs = [row["organisation_number"] for row in source]
    if len(source_orgs) != 1000 or len(set(source_orgs)) != 1000:
        raise ValueError(f"expected frozen consumed 1000, got {len(source_orgs)}")

    profiles, snapshot = profiles_from_bulk(args.bulk, source_orgs)
    manifest, audit, report = build(profiles, target_count=args.target_count)
    _write_jsonl(args.output, manifest)
    _write_jsonl(args.audit, audit)
    report.update(
        {
            "source_manifest_sha256": _sha256(args.source_manifest),
            "target_manifest_sha256": _sha256(args.output),
            "registry_snapshot_sha256": snapshot.get("registry_snapshot_sha256"),
            "registry_snapshot_missing_count": snapshot.get("missing_count"),
        }
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
