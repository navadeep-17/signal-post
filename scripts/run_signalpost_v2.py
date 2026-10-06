#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from norway_company_agent.brreg_changes import (  # noqa: E402
    fetch_registry_change_events,
    project_registry_change_claims,
    theoretical_change_feed_requests,
)
from norway_company_agent.canonical_projection import (  # noqa: E402
    CANONICAL_SCHEMA_VERSION,
    project_canonical_profile,
    validate_canonical_projection,
)
from norway_company_agent.first_party_activity import project_first_party_activity_claims  # noqa: E402
from norway_company_agent.output_contract import validate_contract_object  # noqa: E402
from norway_company_agent.synthesis import (  # noqa: E402
    SYNTHESIS_SCHEMA_VERSION,
    build_company_synthesis,
    validate_company_synthesis,
)
from norway_company_agent.v2_registry_projection import project_v2_registry_claims  # noqa: E402
from build_current_product import CURRENT_PRODUCT_SCHEMA, build_current_html  # noqa: E402
from build_v2_product import read_jsonl  # noqa: E402

DEFAULT_EXPECTED_COUNT = 100
DEFAULT_MAX_CHALLENGE_REQUESTS = 2000
SHARED_REQUEST_CHARGE_MULTIPLIER = 2


def _flag_value(argv: list[str], flag: str) -> str:
    try:
        index = argv.index(flag)
    except ValueError as exc:
        raise SystemExit(f"V2 runner requires {flag}") from exc
    if index + 1 >= len(argv):
        raise SystemExit(f"V2 runner requires a value after {flag}")
    return argv[index + 1]


def _flag_value_or_default(argv: list[str], flag: str, default: str) -> str:
    if flag not in argv:
        return default
    return _flag_value(argv, flag)


def _pop_optional_flag(argv: list[str], flag: str) -> tuple[list[str], str | None]:
    args = list(argv)
    if flag not in args:
        return args, None
    index = args.index(flag)
    if index + 1 >= len(args):
        raise SystemExit(f"V2 runner requires a value after {flag}")
    value = args[index + 1]
    del args[index:index + 2]
    return args, value


def _replace_flag(argv: list[str], flag: str, value: str) -> list[str]:
    args = list(argv)
    index = args.index(flag)
    args[index + 1] = value
    return args


def _set_flag(argv: list[str], flag: str, value: str) -> list[str]:
    args = list(argv)
    if flag in args:
        return _replace_flag(args, flag, value)
    return [*args, flag, value]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    temporary.replace(path)


def _canonical_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    fact_count = sum(len(row.get("canonical_facts") or []) for row in rows)
    area_counts = {
        "company_record": 0,
        "financials": 0,
        "people_and_locations": 0,
        "company_website": 0,
        "hiring_and_public_activity": 0,
    }
    fact_type_counts: dict[str, int] = {}
    for row in rows:
        profile = row.get("canonical_profile") or {}
        areas = profile.get("data_areas") or {}
        for key in area_counts:
            area_counts[key] += int(bool(areas.get(key)))
        for fact in row.get("canonical_facts") or []:
            name = str(fact.get("type") or "unknown")
            fact_type_counts[name] = fact_type_counts.get(name, 0) + 1
    return {
        "schema_version": CANONICAL_SCHEMA_VERSION,
        "companies": len(rows),
        "facts": fact_count,
        "companies_by_data_area": area_counts,
        "fact_type_counts": dict(sorted(fact_type_counts.items())),
    }


def _profile_index(work_dir: Path) -> dict[str, dict[str, Any]]:
    path = work_dir / "profiles.jsonl"
    if not path.is_file():
        raise SystemExit(f"V2 runner expected retained internal profiles at {path}")
    profiles = read_jsonl(path)
    index = {
        str(profile.get("organisation_number") or ""): profile
        for profile in profiles
        if profile.get("organisation_number")
    }
    if len(index) != len(profiles):
        raise SystemExit("V2 retained profiles contain missing or duplicate organisation numbers")
    return index


def main() -> None:
    forwarded, product_output = _pop_optional_flag(sys.argv[1:], "--product-output")
    output_path = Path(_flag_value(forwarded, "--output"))
    report_path = Path(_flag_value(forwarded, "--report"))
    work_dir = Path(_flag_value(forwarded, "--work-dir"))

    expected_count = int(_flag_value_or_default(forwarded, "--expected-count", str(DEFAULT_EXPECTED_COUNT)))
    max_challenge_requests = int(
        _flag_value_or_default(forwarded, "--max-challenge-requests", str(DEFAULT_MAX_CHALLENGE_REQUESTS))
    )
    if expected_count < 1:
        raise SystemExit("--expected-count must be positive")
    if max_challenge_requests < 1:
        raise SystemExit("--max-challenge-requests must be positive")

    # The base runner deliberately fills its conservative structural request budget with
    # annual-report workforce attempts. Reserve the small shared BRREG change-feed budget
    # before invoking it so the combined V5 path still proves the original challenge cap.
    change_request_ceiling = theoretical_change_feed_requests(expected_count)
    change_charge_ceiling = change_request_ceiling * SHARED_REQUEST_CHARGE_MULTIPLIER
    base_max_challenge_requests = max_challenge_requests - change_charge_ceiling
    if base_max_challenge_requests < 1:
        raise SystemExit(
            "Configured challenge request budget is too small after reserving the bounded BRREG change-feed request ceiling"
        )

    base_output = output_path.with_name(output_path.stem + ".v1-base" + output_path.suffix)
    base_report = report_path.with_name(report_path.stem + ".v1-base" + report_path.suffix)
    base_args = _replace_flag(forwarded, "--output", str(base_output))
    base_args = _replace_flag(base_args, "--report", str(base_report))
    base_args = _set_flag(base_args, "--max-challenge-requests", str(base_max_challenge_requests))

    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_signalpost_final.py"), *base_args],
        cwd=ROOT,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)

    base_rows = read_jsonl(base_output)
    profiles_by_org = _profile_index(work_dir)
    orgs = [str(row.get("organisation_number") or "") for row in base_rows]
    change_events_by_org, change_metrics = fetch_registry_change_events(orgs)
    integrity_errors = [str(error) for error in (change_metrics.get("integrity_errors") or [])]

    projected: list[dict[str, Any]] = []
    for row in base_rows:
        org = str(row.get("organisation_number") or "")
        profile = profiles_by_org.get(org)
        if profile is None:
            raise SystemExit(f"V2 retained profile missing for {org}")
        with_registry = project_v2_registry_claims(row, profile)
        with_activity = project_first_party_activity_claims(with_registry, profile)
        with_registry_changes = project_registry_change_claims(
            with_activity,
            change_events_by_org.get(org, []),
        )
        item = project_canonical_profile(with_registry_changes)
        item["synthesis"] = build_company_synthesis(item)
        projected.append(item)

    errors: list[dict[str, Any]] = []
    synthesis_errors: list[dict[str, Any]] = []
    for row in projected:
        org = str(row.get("organisation_number") or "")
        for error in validate_contract_object(row):
            errors.append({"organisation_number": org, "layer": "output_contract", "error": error})
        for error in validate_canonical_projection(row):
            errors.append({"organisation_number": org, "layer": "canonical_projection", "error": error})
        for error in validate_company_synthesis(row):
            synthesis_errors.append({"organisation_number": org, "layer": "synthesis", "error": error})

    _write_jsonl(output_path, projected)

    report = json.loads(base_report.read_text(encoding="utf-8"))
    request_budget = report.setdefault("request_budget", {})
    base_observed_logical = int(request_budget.get("observed_logical_requests") or 0)
    base_observed_charge = int(request_budget.get("observed_conservative_challenge_request_charge") or 0)
    base_theoretical_logical = int(request_budget.get("theoretical_logical_request_ceiling") or 0)
    base_theoretical_charge = int(request_budget.get("theoretical_challenge_request_charge_ceiling") or 0)
    observed_change_requests = int(change_metrics.get("requests") or 0)
    observed_change_charge = observed_change_requests * SHARED_REQUEST_CHARGE_MULTIPLIER
    combined_observed_logical = base_observed_logical + observed_change_requests
    combined_observed_charge = base_observed_charge + observed_change_charge
    combined_theoretical_logical = base_theoretical_logical + change_request_ceiling
    combined_theoretical_charge = base_theoretical_charge + change_charge_ceiling

    request_budget.update(
        {
            "base_runner_max_challenge_requests_after_v5_reservation": base_max_challenge_requests,
            "brreg_change_feed_logical_request_ceiling": change_request_ceiling,
            "brreg_change_feed_conservative_charge_ceiling": change_charge_ceiling,
            "brreg_change_feed_observed_logical_requests": observed_change_requests,
            "brreg_change_feed_observed_conservative_charge": observed_change_charge,
            "observed_logical_requests": combined_observed_logical,
            "observed_conservative_challenge_request_charge": combined_observed_charge,
            "theoretical_logical_request_ceiling": combined_theoretical_logical,
            "theoretical_challenge_request_charge_ceiling": combined_theoretical_charge,
            "max_challenge_requests": max_challenge_requests,
        }
    )

    registry_change_claims = sum(
        1
        for row in projected
        for claim in (row.get("claims") or [])
        if isinstance(claim, dict) and claim.get("field") == "official_registry_change"
    )
    registry_change_companies = sum(
        any(
            isinstance(claim, dict) and claim.get("field") == "official_registry_change"
            for claim in (row.get("claims") or [])
        )
        for row in projected
    )

    report["canonical_projection"] = _canonical_metrics(projected)
    report["canonical_projection"]["validation_errors"] = errors
    report["canonical_projection"]["v2_registry_projection"] = {
        "network_requests_added": 0,
        "fields": ["industry", "municipality_number", "bankrupt", "liquidating", "company_description", "registered_purpose"],
        "source": "exact-org BRREG registry profile retained by the unchanged base collector",
    }
    report["canonical_projection"]["first_party_activity_projection"] = {
        "network_requests_added": 0,
        "generic_careers_page_counts_as_hiring": False,
        "job_requirement": "specific retained company-owned role page + job detail marker + explicit apply action",
        "company_update_requirement": "specific retained company-owned news/update page + explicit publication date",
    }
    report["registry_change_feed"] = {
        **change_metrics,
        "network_requests_added": observed_change_requests,
        "third_party_cost_usd": 0.0,
        "claim_field": "official_registry_change",
        "canonical_type": "registry_change",
        "companies_with_published_claims": registry_change_companies,
        "published_claims": registry_change_claims,
        "source_boundary": "official BRREG registry changes; never labelled as company-authored news, hiring or social activity",
    }
    report["synthesis"] = {
        "schema_version": SYNTHESIS_SCHEMA_VERSION,
        "companies": len(projected),
        "network_requests_added": 0,
        "llm_used": False,
        "new_facts_created": False,
        "registry_change_context_enabled": True,
        "validation_errors": synthesis_errors,
    }
    report.setdefault("source_policy", {})["brreg_registry_change_feed_enabled"] = True
    report["source_policy"]["brreg_registry_change_feed_mode"] = "official_api_exact_org_batched"
    report["source_policy"]["brreg_registry_change_feed_third_party_cost_usd"] = 0.0

    checks = report.setdefault("checks", {})
    base_budget_valid = bool(checks.get("budget_valid"))
    checks["canonical_projection_valid"] = not errors
    checks["synthesis_valid"] = not synthesis_errors
    checks["brreg_change_feed_integrity_valid"] = not integrity_errors
    checks["brreg_change_feed_request_bounded"] = observed_change_requests <= change_request_ceiling
    checks["combined_request_budget_valid"] = (
        base_budget_valid
        and combined_observed_charge <= max_challenge_requests
        and combined_theoretical_charge <= max_challenge_requests
    )
    checks["budget_valid"] = checks["combined_request_budget_valid"]
    report["passed"] = (
        bool(report.get("passed"))
        and not errors
        and not synthesis_errors
        and not integrity_errors
        and checks["brreg_change_feed_request_bounded"]
        and checks["combined_request_budget_valid"]
    )

    if product_output:
        product_path = Path(product_output)
        product_path.parent.mkdir(parents=True, exist_ok=True)
        product_path.write_text(
            build_current_html(projected, title="Signalpost — evidence-backed company intelligence"),
            encoding="utf-8",
        )
        report["product_surface"] = {
            "schema_version": CURRENT_PRODUCT_SCHEMA,
            "path": str(product_path),
            "data_linked": True,
            "source_output": str(output_path),
            "companies": len(projected),
            "deterministic_synthesis": True,
            "comparison_enabled": True,
            "comparison_semantics": "side-by-side descriptive facts only; no company ranking",
            "evidence_links_in_compare": True,
            "canonical_areas": [
                "company_record",
                "financials",
                "people_and_locations",
                "company_website",
                "hiring_and_public_activity",
            ],
        }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
