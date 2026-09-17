#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELECTOR = ROOT / "scripts" / "select_disjoint_validation_batch.py"
ENTRY_SELECTOR = ROOT / "select_entry_batch.py"

COHORTS = [
    (20260915, "zero_overlap_validation", "external_precision_validation", None),
    (20260916, "h1c_secondary_confirmation", "fresh_external_precision_validation", "7c0d1ae4355edf1e2b282ebc386b7874eb6c3cbc36e5b01f0685069cbcd38d83"),
    (20260917, "h1d_recall_recovery", "fresh_zero_cost_site_recall_validation", "a05a38c86526babcf90c013230e406888d9e00a942e8fef40653e03b0c53aa7a"),
    (20260918, "h1d_zero_overlap_confirmation", "fresh_transfer_validation", "15741f32379a6db226ecff10de8cacf0c40bc34f40d511ae060bf13daeafaf3e"),
    (20260919, "h1d_final_zero_overlap", "fresh_final_recall_validation", "b20dec131e3ad6ac7938757ddd79bef6f7a97f6961d64cdbd0bf1395238dd661"),
    (20260920, "h1e_wikidata_candidate", "fresh_zero_cost_external_candidate_validation", "e07629ef1bc7cf593cdeb5a187c15db772c36ea17d758df71b34f2b49894186f"),
]
POST_H1E = [
    (20260922, "h2a_company_social", "fresh_profile_handle_validation", "1d1da002538c0a493303934de53925984c36f641bef2e7623df48897b2e4a88f"),
    (20260923, "h2b_company_activity", "fresh_dated_company_activity_validation", "0bff58af0b8535e71c677dbe44c873a7dfe63805839eb72044896577e1c968dc"),
    (20260924, "h2c_company_contact_email", "fresh_same_domain_contact_email_validation", "eee5765bcdfed57aa81489c2f3ef613bf612fcde92f73e5dc641df97905812bf"),
    (20260925, "h1f_zero_cost_tld_recall", "fresh_compact_com_fallback_validation", "da9584073e526207d2bfe52c525509c2852daaa8fb85f26fd9c586a5e4ee4a6e"),
    (20260926, "h1g_zero_cost_hyphenated_no_recall", "fresh_hyphenated_no_fallback_validation", "62c70f68049a73ae0d4eac60478bee3478e3894be5dd7039bfa28519db7e4dea"),
    (20260927, "h2d_wikidata_linkedin", "fresh_exact_org_linkedin_validation", "73ffeb9a5010c6bc86a5b7ab2ed07e6d18e206b6db2f016a4ba4fe4e7d56e55c"),
]
H1E_RECOVERED_SHA = "5b4c4ae41a01c8b29aefa703bfd754da3e7448b33cbbbcb831d705032ef030b7"
H2E_SHA = "edccd719c765469323f72314f6b1fe65dbf1c6e2f6b4acdf9ce77ad8cfc38015"
H2G1_SHA = "85eea94589af258745ce5398eb382b9d2c41ea8b95a3448b14dbd2c0c6e0b62a"
H2G2_SHA = "abaa68d267355ee7f24e59c82408aabb513b8e146706aa6b380b6dc3e0946404"
H2H_SHA = "08ff94cd39a07b4cb24f8ed0479e2a94c758cd47ca550f0af63cc94382ed98ef"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_sha(path: Path, expected: str) -> None:
    actual = sha(path)
    if actual != expected:
        raise SystemExit(f"SHA mismatch for {path}: {actual} != {expected}")


def cat(paths: list[Path], output: Path) -> None:
    with output.open("wb") as handle:
        for path in paths:
            handle.write(path.read_bytes())


def count_unique(path: Path) -> tuple[int, int]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    orgs = [str(row["organisation_number"]) for row in rows]
    return len(rows), len(set(orgs))


def select(universe: Path, exclude: Path, output: Path, seed: int, split: str, slice_name: str, count: int = 300) -> None:
    report = output.with_suffix(".report.json")
    subprocess.run([
        sys.executable, str(SELECTOR), "--universe", str(universe), "--exclude", str(exclude),
        "--count", str(count), "--seed", str(seed), "--evaluation-split", split,
        "--sample-slice", slice_name, "--output", str(output), "--report", str(report),
    ], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Recreate all touched cohorts and freeze a new disjoint Signalpost release 1000.")
    parser.add_argument("--universe", required=True)
    parser.add_argument("--h1e-recovered", required=True)
    parser.add_argument("--h2e", required=True)
    parser.add_argument("--h2g1", required=True)
    parser.add_argument("--h2g2", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--release-seed", type=int, default=20261002)
    args = parser.parse_args()

    universe = Path(args.universe)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    entry = out / "entry-1000.jsonl"
    subprocess.run([sys.executable, str(ENTRY_SELECTOR), "--universe", str(universe), "--count", "1000", "--seed", "20260823", "--output", str(entry)], check=True)

    exclude = entry
    for index, (seed, split, slice_name, expected) in enumerate(COHORTS, start=1):
        cohort = out / f"cohort-{index}-{seed}.jsonl"
        select(universe, exclude, cohort, seed, split, slice_name)
        if expected:
            assert_sha(cohort, expected)
        merged = out / f"exclude-{1000 + index * 300}.jsonl"
        cat([exclude, cohort], merged)
        exclude = merged

    recovered = Path(args.h1e_recovered)
    assert_sha(recovered, H1E_RECOVERED_SHA)
    merged = out / "exclude-3100.jsonl"
    cat([exclude, recovered], merged)
    exclude = merged

    for offset, (seed, split, slice_name, expected) in enumerate(POST_H1E, start=1):
        cohort = out / f"post-{offset}-{seed}.jsonl"
        select(universe, exclude, cohort, seed, split, slice_name)
        assert_sha(cohort, expected)
        total = 3100 + offset * 300
        merged = out / f"exclude-{total}.jsonl"
        cat([exclude, cohort], merged)
        exclude = merged

    external = [
        (Path(args.h2e), H2E_SHA, 5200),
        (Path(args.h2g1), H2G1_SHA, 5500),
        (Path(args.h2g2), H2G2_SHA, 5800),
    ]
    for cohort, expected, total in external:
        assert_sha(cohort, expected)
        merged = out / f"exclude-{total}.jsonl"
        cat([exclude, cohort], merged)
        exclude = merged

    h2h = out / "prior-h2h-100.jsonl"
    select(universe, exclude, h2h, 20261001, "h2h_fagfolkguiden_review_coverage", "fresh_rights_review_source_coverage_screen", count=100)
    assert_sha(h2h, H2H_SHA)
    exclude5900 = out / "exclude-5900.jsonl"
    cat([exclude, h2h], exclude5900)
    rows, unique = count_unique(exclude5900)
    if (rows, unique) != (5900, 5900):
        raise SystemExit(f"Historical exclusion integrity failed: rows={rows}, unique={unique}")

    release = out / "final-release-1000.jsonl"
    select(universe, exclude5900, release, args.release_seed, "final_release_1000_post_h2g", "frozen_submission_release", count=1000)
    rows, unique = count_unique(release)
    if (rows, unique) != (1000, 1000):
        raise SystemExit(f"Release integrity failed: rows={rows}, unique={unique}")

    selection_report = json.loads(release.with_suffix(".report.json").read_text(encoding="utf-8"))
    if selection_report.get("excluded_rows") != 5900 or selection_report.get("overlap_count") != 0:
        raise SystemExit(f"Release disjointness failed: {selection_report}")

    (out / "final-release-1000.sha256").write_text(sha(release) + "\n", encoding="utf-8")
    summary = {
        "release_seed": args.release_seed,
        "historical_exclusions": 5900,
        "release_companies": 1000,
        "overlap_count": 0,
        "release_manifest_sha256": sha(release),
        "universe_sha256": sha(universe),
        "selection_report": selection_report,
    }
    (out / "final-release-freeze-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
