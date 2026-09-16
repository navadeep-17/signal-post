#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from norway_company_agent.external_footprint import validate_observation  # noqa: E402
from norway_company_agent.workforce_contract import project_workforce_observations  # noqa: E402
from screen_h2g_annual_workforce import (  # noqa: E402
    collect,
    latest_account_year,
    registry_employee_count,
)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def existing_workforce_company(profile: dict) -> bool:
    return any(
        isinstance(row, dict) and row.get("signal_type") == "workforce_snapshot"
        for row in (profile.get("external_observations") or [])
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Fresh-cohort H2g annual-report workforce qualification.")
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--expected-count", type=int, default=300)
    parser.add_argument("--limit", type=int, default=297)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--min-start-interval", type=float, default=2.1)
    parser.add_argument("--ocr-pages", type=int, default=8)
    parser.add_argument("--ocr-dpi", type=int, default=110)
    parser.add_argument("--base-structural-charge", type=int, default=5406)
    parser.add_argument("--max-structural-charge", type=int, default=6000)
    args = parser.parse_args()

    profiles = read_jsonl(Path(args.profiles))
    if len(profiles) != args.expected_count:
        raise SystemExit(f"Expected {args.expected_count} profiles, got {len(profiles)}")

    existing = sum(existing_workforce_company(profile) for profile in profiles)
    eligible = [
        profile
        for profile in profiles
        if registry_employee_count(profile) is None and latest_account_year(profile)
    ]
    selected = eligible[: max(0, min(args.limit, 297))]

    started = time.monotonic()
    results: dict[int, tuple[dict | None, dict]] = {}
    active = {}
    next_index = 0
    last_submit = 0.0
    workers = max(1, args.workers)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        while next_index < len(selected) or active:
            while next_index < len(selected) and len(active) < workers:
                remaining = args.min_start_interval - (time.monotonic() - last_submit)
                if remaining > 0:
                    time.sleep(remaining)
                profile = selected[next_index]
                future = pool.submit(
                    collect,
                    profile,
                    timeout=args.timeout,
                    ocr_pages=args.ocr_pages,
                    ocr_dpi=args.ocr_dpi,
                )
                active[future] = next_index
                next_index += 1
                last_submit = time.monotonic()

            if active:
                done, _ = wait(tuple(active), return_when=FIRST_COMPLETED)
                for future in done:
                    index = active.pop(future)
                    try:
                        results[index] = future.result()
                    except Exception as exc:  # defensive: collect already converts ordinary failures
                        profile = selected[index]
                        results[index] = (
                            None,
                            {
                                "organisation_number": str(profile.get("organisation_number") or ""),
                                "status": "worker_error",
                                "error": f"{type(exc).__name__}: {str(exc)[:180]}",
                                "request_count": 0,
                            },
                        )

    ordered = [results[index] for index in range(len(selected))]
    observations = [observation for observation, _ in ordered if observation]
    audit = [result for _, result in ordered]

    validation_errors = []
    contract_projection_errors = []
    for observation in observations:
        errors = validate_observation(observation)
        validation_errors.extend(
            {"organisation_number": observation.get("organisation_number"), "observation_id": observation.get("id"), "error": error}
            for error in errors
        )
        org = str(observation.get("organisation_number") or "")
        profile = next(row for row in selected if str(row.get("organisation_number") or "") == org)
        projected = project_workforce_observations(
            {"organisation_number": org, "claims": [], "evidence": []},
            {**profile, "external_observations": [observation]},
        )
        claims = [claim for claim in projected.get("claims") or [] if claim.get("field") == "external.workforce_snapshot"]
        if len(claims) != 1 or len(projected.get("evidence") or []) != 1:
            contract_projection_errors.append(
                {"organisation_number": org, "error": "H2g workforce projection did not yield exactly one claim/evidence pair"}
            )

    requests = sum(int(row.get("request_count") or 0) for row in audit)
    added_charge = requests * 2
    structural_charge = args.base_structural_charge + added_charge
    statuses = Counter(str(row.get("status") or "unknown") for row in audit)
    accepted_orgs = {str(row.get("organisation_number") or "") for row in observations}
    existing_orgs = {
        str(profile.get("organisation_number") or "")
        for profile in profiles
        if existing_workforce_company(profile)
    }
    combined = len(existing_orgs | accepted_orgs)

    report = {
        "experiment": "h2g_annual_report_workforce_fresh_qualification_v1",
        "profiles": len(profiles),
        "existing_h2e_workforce_companies": existing,
        "eligible_missing_registry_count_with_account_year": len(eligible),
        "selected_for_h2g": len(selected),
        "requests": requests,
        "accepted": len(observations),
        "accepted_rate_over_selected": round(len(observations) / len(selected), 6) if selected else 0.0,
        "net_new_company_coverage": round(len(accepted_orgs) / len(profiles), 6) if profiles else 0.0,
        "combined_h2e_h2g_workforce_companies": combined,
        "combined_h2e_h2g_company_coverage": round(combined / len(profiles), 6) if profiles else 0.0,
        "added_logical_requests": requests,
        "added_conservative_challenge_request_charge": added_charge,
        "base_structural_challenge_request_charge": args.base_structural_charge,
        "projected_structural_challenge_request_charge": structural_charge,
        "max_structural_challenge_request_charge": args.max_structural_charge,
        "third_party_cost_usd": 0.0,
        "runtime_seconds": round(time.monotonic() - started, 3),
        "workers": workers,
        "min_request_start_interval_seconds": args.min_start_interval,
        "ocr_pages": args.ocr_pages,
        "ocr_dpi": args.ocr_dpi,
        "organisation_number_recovered": sum(bool(row.get("organisation_number_in_combined_text")) for row in audit),
        "status_counts": dict(statuses),
        "validation_errors": validation_errors,
        "contract_projection_errors": contract_projection_errors,
        "claim_boundary": (
            "Latest-year official BRREG annual-account copy only; exact organisation number must be recovered from OCR; "
            "only unambiguous company-scope employee/FTE phrases publish; group/conflicting phrases abstain."
        ),
    }
    report["passed"] = (
        requests <= 297
        and structural_charge <= args.max_structural_charge
        and not validation_errors
        and not contract_projection_errors
        and len(audit) == len(selected)
    )

    Path(args.output).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in observations), encoding="utf-8")
    Path(args.audit).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in audit), encoding="utf-8")
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
