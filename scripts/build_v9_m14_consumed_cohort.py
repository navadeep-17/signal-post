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
from norway_company_agent.h1g_hyphenated_no_recall import hyphenated_no_candidate  # noqa: E402
from norway_company_agent.h1h_single_token_compact_com import single_token_compact_com_candidate  # noqa: E402
from norway_company_agent.v9_email_domain import select_registry_email_domain_candidate  # noqa: E402

PR137_GATE_A_SHA256 = "f2177abd0bd0d6202f9fe47fd00b8def06b21c01fdf4c864c1f3b68f80b160d5"

M10_POSITIVE_CANARIES = {"927097532", "979943377", "999096298"}
M12_RESEARCHED_ORGS = {
    "828829092", "870418892", "896488562", "898321622",
    "911546221", "914384729", "936455298", "976533194",
    "979436661", "988936987", "992784229", "996405524",
}
BUILDERR_PUBLIC_PRACTICE_ORGS = {
    "811413682",  # ELOPAK ASA website example
    "811730912",  # MTM SKOGSERVICE AS social example
    "923609016",  # EQUINOR ASA careers example
    "883971752",  # SUNNAAS SYKEHUS HF dated-news example
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _orgs(rows: list[dict[str, Any]]) -> set[str]:
    values = {str(row.get("organisation_number") or "") for row in rows}
    if any(len(org) != 9 or not org.isdigit() for org in values):
        raise ValueError("all organisation numbers must be nine digits")
    return values


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def build(
    profiles: list[dict[str, Any]],
    *,
    prior_search_orgs: set[str],
    treated_count: int = 20,
    control_count: int = 80,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if treated_count < 1 or control_count < 1:
        raise ValueError("treated_count and control_count must be positive")

    excluded = (
        set(prior_search_orgs)
        | M10_POSITIVE_CANARIES
        | M12_RESEARCHED_ORGS
        | BUILDERR_PUBLIC_PRACTICE_ORGS
    )

    treated_candidates: list[dict[str, Any]] = []
    control_candidates: list[dict[str, Any]] = []

    for profile in profiles:
        org = str(profile.get("organisation_number") or "")
        if len(org) != 9 or not org.isdigit() or org in excluded:
            continue
        if str(profile.get("website") or "").strip():
            continue
        # If M2 would spend the first site slot on a BRREG email-domain candidate,
        # H1c then consumes the remaining two requests and H1h has no idle slot.
        if select_registry_email_domain_candidate(profile) is not None:
            continue

        h1h = single_token_compact_com_candidate(profile)
        h1g = hyphenated_no_candidate(profile)
        row = {
            "organisation_number": org,
            "name": str(profile.get("name") or ""),
            "municipality": str(profile.get("municipality") or ""),
            "registry_website_present": False,
            "registry_email_candidate_present": False,
            "h1g_candidate_available": h1g is not None,
            "h1h_candidate_available": h1h is not None,
            "h1h_candidate_domain": h1h.get("domain") if h1h else None,
        }

        if h1h is not None and h1g is None:
            treated_candidates.append(row)
        elif h1g is not None and h1h is None:
            control_candidates.append(row)

    treated_candidates.sort(key=lambda row: row["organisation_number"])
    control_candidates.sort(key=lambda row: row["organisation_number"])

    if len(treated_candidates) < treated_count:
        raise ValueError(
            f"only {len(treated_candidates)} clean single-token H1h candidates remain; "
            f"need {treated_count}"
        )
    if len(control_candidates) < control_count:
        raise ValueError(
            f"only {len(control_candidates)} clean multi-token controls remain; "
            f"need {control_count}"
        )

    treated = treated_candidates[:treated_count]
    controls = control_candidates[:control_count]
    selected = [*treated, *controls]

    manifest = [
        {
            "organisation_number": row["organisation_number"],
            "evaluation_split": "v9_m14_consumed_compact_com",
            "sample_slice": (
                "m14_single_token_compact_com"
                if index < treated_count
                else "m14_multi_token_control"
            ),
        }
        for index, row in enumerate(selected)
    ]
    audit = [
        {
            **row,
            "bucket": (
                "m14_single_token_compact_com"
                if index < treated_count
                else "m14_multi_token_control"
            ),
            "previous_search_development": row["organisation_number"] in prior_search_orgs,
            "m10_positive_canary": row["organisation_number"] in M10_POSITIVE_CANARIES,
            "m12_researched": row["organisation_number"] in M12_RESEARCHED_ORGS,
            "builderr_public_practice": row["organisation_number"] in BUILDERR_PUBLIC_PRACTICE_ORGS,
        }
        for index, row in enumerate(selected)
    ]

    if any(
        row["previous_search_development"]
        or row["m10_positive_canary"]
        or row["m12_researched"]
        or row["builderr_public_practice"]
        for row in audit
    ):
        raise AssertionError("researched/practice organisation leaked into M14 cohort")

    report = {
        "screen_type": "v9_m14_consumed_single_token_compact_com",
        "source_population_companies": len(profiles),
        "selected_companies": len(selected),
        "treated_companies": len(treated),
        "control_companies": len(controls),
        "eligible_treated_population": len(treated_candidates),
        "eligible_control_population": len(control_candidates),
        "fresh_companies_used": 0,
        "prior_search_development_excluded": len(prior_search_orgs),
        "m10_positive_canaries_excluded": sorted(M10_POSITIVE_CANARIES),
        "m12_researched_orgs_excluded": sorted(M12_RESEARCHED_ORGS),
        "builderr_public_practice_orgs_excluded": sorted(BUILDERR_PUBLIC_PRACTICE_ORGS),
        "treated_organisation_numbers": [row["organisation_number"] for row in treated],
        "selection_rule": [
            "start with frozen already-consumed 1000-company population",
            "exclude all PR #137 search-development companies",
            "exclude M10 positive canaries",
            "exclude all M12 externally researched companies",
            "exclude all Builderr public practice examples",
            "require no BRREG website in frozen shared snapshot",
            "require no admissible BRREG email-domain candidate",
            "treated: H1h single-token compact .com candidate exists and H1g does not",
            "controls: H1g multi-token hyphenated .no candidate exists and H1h does not",
            "sort each pool by organisation number before fixed selection",
            "candidate page outcome never influences cohort membership",
        ],
    }
    return manifest, audit, report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source-manifest", type=Path, required=True)
    p.add_argument("--bulk", type=Path, required=True)
    p.add_argument("--prior-search-manifest", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--audit", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--treated-count", type=int, default=20)
    p.add_argument("--control-count", type=int, default=80)
    args = p.parse_args()

    if sha256(args.prior_search_manifest) != PR137_GATE_A_SHA256:
        raise ValueError("PR #137 prior-search Gate-A manifest SHA-256 mismatch")

    source = read_organisation_inputs(args.source_manifest)
    source_orgs = [row["organisation_number"] for row in source]
    if len(source_orgs) != 1000 or len(set(source_orgs)) != 1000:
        raise ValueError(f"expected frozen consumed 1000, got {len(source_orgs)}")

    prior_search = read_organisation_inputs(args.prior_search_manifest)
    if len(prior_search) != 20 or len(_orgs(prior_search)) != 20:
        raise ValueError("expected exact prior PR #137 Gate-A 20-company manifest")

    profiles, snapshot = profiles_from_bulk(args.bulk, source_orgs)
    manifest, audit, report = build(
        profiles,
        prior_search_orgs=_orgs(prior_search),
        treated_count=args.treated_count,
        control_count=args.control_count,
    )
    write_jsonl(args.output, manifest)
    write_jsonl(args.audit, audit)
    report.update({
        "source_manifest_sha256": sha256(args.source_manifest),
        "prior_search_manifest_sha256": sha256(args.prior_search_manifest),
        "target_manifest_sha256": sha256(args.output),
        "registry_snapshot_sha256": snapshot.get("registry_snapshot_sha256"),
        "registry_snapshot_missing_count": snapshot.get("missing_count"),
    })
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
