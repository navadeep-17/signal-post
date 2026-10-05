#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_v2_product import read_jsonl  # noqa: E402
from norway_company_agent.canonical_projection import (  # noqa: E402
    CANONICAL_SCHEMA_VERSION,
    project_canonical_profile,
    validate_canonical_projection,
)
from norway_company_agent.output_contract import validate_contract_object  # noqa: E402
from norway_company_agent.support_contract import project_support_award_observations  # noqa: E402
from norway_company_agent.support_registry import fetch_support_award_batch  # noqa: E402
from norway_company_agent.synthesis import (  # noqa: E402
    SYNTHESIS_SCHEMA_VERSION,
    build_company_synthesis,
    validate_company_synthesis,
)

LEGACY_RUNNER = ROOT / "scripts" / "run_signalpost_v2.py"
V6_BUILDER = ROOT / "scripts" / "build_v6_ui.py"
DEFAULT_MAX_CHALLENGE_REQUESTS = 2000
DEFAULT_MAX_WALL_RUNTIME_SECONDS = 2400
SHARED_REQUEST_CHARGE_MULTIPLIER = 2
SUPPORT_REGISTRY_SHARED_REQUEST_CEILING = 1
DEFAULT_SUPPORT_REGISTRY_TIMEOUT = 420.0
DEFAULT_SUPPORT_LOOKBACK_DAYS = 365
DEFAULT_SUPPORT_EVENTS_PER_COMPANY = 5


def _arg_value(argv: list[str], flag: str) -> str | None:
    prefix = flag + "="
    for index, arg in enumerate(argv):
        if arg.startswith(prefix):
            return arg[len(prefix) :]
        if arg == flag:
            if index + 1 >= len(argv):
                raise ValueError(f"V7 wrapper requires a value after {flag}")
            return argv[index + 1]
    return None


def _set_arg(argv: list[str], flag: str, value: str) -> list[str]:
    args = list(argv)
    prefix = flag + "="
    for index, arg in enumerate(args):
        if arg.startswith(prefix):
            args[index] = prefix + value
            return args
        if arg == flag:
            if index + 1 >= len(args):
                raise ValueError(f"V7 wrapper requires a value after {flag}")
            args[index + 1] = value
            return args
    return [*args, flag, value]


def _remove_arg(argv: list[str], flag: str) -> list[str]:
    args = list(argv)
    prefix = flag + "="
    for index, arg in enumerate(args):
        if arg.startswith(prefix):
            del args[index]
            return args
        if arg == flag:
            if index + 1 >= len(args):
                raise ValueError(f"V7 wrapper requires a value after {flag}")
            del args[index : index + 2]
            return args
    return args


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


def prepare_legacy_args(argv: list[str]) -> tuple[list[str], dict[str, Any]]:
    output = _arg_value(argv, "--output")
    report = _arg_value(argv, "--report")
    product_output = _arg_value(argv, "--product-output")
    if not output:
        raise ValueError("V7 wrapper requires --output so support awards can be projected into the final JSONL.")
    if not report:
        raise ValueError("V7 wrapper requires --report so shared-source accounting remains auditable.")
    if not product_output:
        raise ValueError("V7 wrapper requires --product-output for the evaluator-facing V6 workspace.")

    try:
        max_challenge_requests = int(
            _arg_value(argv, "--max-challenge-requests") or str(DEFAULT_MAX_CHALLENGE_REQUESTS)
        )
        max_wall_runtime_seconds = int(
            _arg_value(argv, "--max-wall-runtime-seconds") or str(DEFAULT_MAX_WALL_RUNTIME_SECONDS)
        )
        support_timeout = float(
            _arg_value(argv, "--support-registry-timeout") or str(DEFAULT_SUPPORT_REGISTRY_TIMEOUT)
        )
        support_lookback_days = int(
            _arg_value(argv, "--support-lookback-days") or str(DEFAULT_SUPPORT_LOOKBACK_DAYS)
        )
        support_events_per_company = int(
            _arg_value(argv, "--support-events-per-company") or str(DEFAULT_SUPPORT_EVENTS_PER_COMPANY)
        )
    except ValueError as exc:
        raise ValueError("V7 wrapper resource/support settings must be numeric") from exc

    if max_challenge_requests < 1:
        raise ValueError("--max-challenge-requests must be positive")
    if max_wall_runtime_seconds < 1:
        raise ValueError("--max-wall-runtime-seconds must be positive")
    if support_timeout <= 0:
        raise ValueError("--support-registry-timeout must be positive")
    if support_lookback_days < 1:
        raise ValueError("--support-lookback-days must be positive")
    if support_events_per_company < 1:
        raise ValueError("--support-events-per-company must be positive")

    support_charge_ceiling = SUPPORT_REGISTRY_SHARED_REQUEST_CEILING * SHARED_REQUEST_CHARGE_MULTIPLIER
    legacy_max_challenge_requests = max_challenge_requests - support_charge_ceiling
    if legacy_max_challenge_requests < 1:
        raise ValueError(
            "Configured challenge request budget is too small after reserving the bounded Støtteregisteret request ceiling"
        )

    prepared = list(argv)
    for flag in (
        "--support-registry-timeout",
        "--support-lookback-days",
        "--support-events-per-company",
    ):
        prepared = _remove_arg(prepared, flag)
    prepared = _set_arg(prepared, "--max-challenge-requests", str(legacy_max_challenge_requests))

    return prepared, {
        "output": output,
        "report": report,
        "product_output": product_output,
        "expected_count_arg": _arg_value(argv, "--expected-count"),
        "max_challenge_requests": max_challenge_requests,
        "legacy_max_challenge_requests": legacy_max_challenge_requests,
        "max_wall_runtime_seconds": max_wall_runtime_seconds,
        "support_registry_timeout": support_timeout,
        "support_lookback_days": support_lookback_days,
        "support_events_per_company": support_events_per_company,
        "support_request_charge_ceiling": support_charge_ceiling,
    }


def _commands(prepared: list[str], settings: dict[str, Any]) -> tuple[list[str], list[str]]:
    legacy = [sys.executable, str(LEGACY_RUNNER), *prepared]
    workspace = [
        sys.executable,
        str(V6_BUILDER),
        "--input",
        str(settings["output"]),
        "--output",
        str(settings["product_output"]),
    ]
    if settings.get("expected_count_arg"):
        workspace.extend(["--expect-count", str(settings["expected_count_arg"])])
    return legacy, workspace


def build_commands(argv: list[str]) -> tuple[list[str], list[str]]:
    prepared, settings = prepare_legacy_args(argv)
    return _commands(prepared, settings)


def _apply_support_awards(settings: dict[str, Any], wall_start: float) -> bool:
    output_path = Path(str(settings["output"]))
    report_path = Path(str(settings["report"]))
    rows = read_jsonl(output_path)

    profiles = [
        {
            "organisation_number": str(row.get("organisation_number") or ""),
            "external_observations": [],
        }
        for row in rows
    ]
    support_report = fetch_support_award_batch(
        profiles,
        timeout=float(settings["support_registry_timeout"]),
        lookback_days=int(settings["support_lookback_days"]),
        max_events_per_company=int(settings["support_events_per_company"]),
    )
    observed_support_requests = int(support_report.get("requests") or 0)
    support_bounded = observed_support_requests <= SUPPORT_REGISTRY_SHARED_REQUEST_CEILING

    profiles_by_org = {
        str(profile.get("organisation_number") or ""): profile
        for profile in profiles
        if profile.get("organisation_number")
    }
    projected: list[dict[str, Any]] = []
    contract_errors: list[dict[str, str]] = []
    canonical_errors: list[dict[str, str]] = []
    synthesis_errors: list[dict[str, str]] = []

    for row in rows:
        org = str(row.get("organisation_number") or "")
        profile = profiles_by_org.get(org)
        if profile is None:
            contract_errors.append(
                {"organisation_number": org, "error": "support projection profile missing for output organisation"}
            )
            projected.append(row)
            continue
        with_support = project_support_award_observations(row, profile)
        item = project_canonical_profile(with_support)
        item["synthesis"] = build_company_synthesis(item)
        for error in validate_contract_object(item):
            contract_errors.append({"organisation_number": org, "error": error})
        for error in validate_canonical_projection(item):
            canonical_errors.append({"organisation_number": org, "error": error})
        for error in validate_company_synthesis(item):
            synthesis_errors.append({"organisation_number": org, "error": error})
        projected.append(item)

    _write_jsonl(output_path, projected)

    report = json.loads(report_path.read_text(encoding="utf-8"))
    request_budget = report.setdefault("request_budget", {})
    base_observed_logical = int(request_budget.get("observed_logical_requests") or 0)
    base_observed_charge = int(request_budget.get("observed_conservative_challenge_request_charge") or 0)
    base_theoretical_logical = int(request_budget.get("theoretical_logical_request_ceiling") or 0)
    base_theoretical_charge = int(request_budget.get("theoretical_challenge_request_charge_ceiling") or 0)
    support_observed_charge = observed_support_requests * SHARED_REQUEST_CHARGE_MULTIPLIER
    combined_observed_logical = base_observed_logical + observed_support_requests
    combined_observed_charge = base_observed_charge + support_observed_charge
    combined_theoretical_logical = base_theoretical_logical + SUPPORT_REGISTRY_SHARED_REQUEST_CEILING
    combined_theoretical_charge = base_theoretical_charge + int(settings["support_request_charge_ceiling"])
    max_challenge_requests = int(settings["max_challenge_requests"])
    combined_budget_valid = (
        bool((report.get("checks") or {}).get("budget_valid"))
        and combined_observed_charge <= max_challenge_requests
        and combined_theoretical_charge <= max_challenge_requests
    )

    request_budget.update(
        {
            "v2_max_challenge_requests_after_support_reservation": int(settings["legacy_max_challenge_requests"]),
            "support_registry_logical_request_ceiling": SUPPORT_REGISTRY_SHARED_REQUEST_CEILING,
            "support_registry_conservative_charge_ceiling": int(settings["support_request_charge_ceiling"]),
            "support_registry_observed_logical_requests": observed_support_requests,
            "support_registry_observed_conservative_charge": support_observed_charge,
            "observed_logical_requests": combined_observed_logical,
            "observed_conservative_challenge_request_charge": combined_observed_charge,
            "theoretical_logical_request_ceiling": combined_theoretical_logical,
            "theoretical_challenge_request_charge_ceiling": combined_theoretical_charge,
            "max_challenge_requests": max_challenge_requests,
        }
    )

    support_claims = [
        claim
        for row in projected
        for claim in (row.get("claims") or [])
        if isinstance(claim, dict) and claim.get("field") == "official.support_award"
    ]
    support_companies = sum(
        any(
            isinstance(claim, dict) and claim.get("field") == "official.support_award"
            for claim in (row.get("claims") or [])
        )
        for row in projected
    )
    support_canonical_facts = sum(
        1
        for row in projected
        for fact in (row.get("canonical_facts") or [])
        if isinstance(fact, dict) and fact.get("type") == "public.official_support_award"
    )

    canonical_report = dict(report.get("canonical_projection") or {})
    canonical_report.update(_canonical_metrics(projected))
    canonical_report["validation_errors"] = canonical_errors
    canonical_report["support_award_projection"] = {
        "claim_field": "official.support_award",
        "canonical_type": "public.official_support_award",
        "published_claims": len(support_claims),
        "published_canonical_facts": support_canonical_facts,
        "companies_with_published_claims": support_companies,
        "identity_authority": "primary recipient organisation number only",
    }
    report["canonical_projection"] = canonical_report

    synthesis_report = dict(report.get("synthesis") or {})
    synthesis_report.update(
        {
            "schema_version": SYNTHESIS_SCHEMA_VERSION,
            "companies": len(projected),
            "support_award_context_enabled": True,
            "validation_errors": synthesis_errors,
        }
    )
    report["synthesis"] = synthesis_report

    source_policy = report.setdefault("source_policy", {})
    source_policy.update(
        {
            "support_registry_enabled": True,
            "support_registry_rights_basis": "NLOD",
            "support_registry_mode": "official_dataset_exact_primary_recipient_org",
            "support_registry_network_requests": observed_support_requests,
            "support_registry_lookback_days": int(settings["support_lookback_days"]),
            "support_registry_max_events_per_company": int(settings["support_events_per_company"]),
            "support_registry_third_party_cost_usd": 0.0,
        }
    )

    external_signals = report.setdefault("external_signals", {})
    external_signals.update(
        {
            "support_award_observations": len(support_claims),
            "companies_with_support_awards": support_companies,
            "support_registry_network_requests": observed_support_requests,
        }
    )

    report["support_registry"] = {
        "status": support_report.get("status"),
        "requests": observed_support_requests,
        "bytes": int(support_report.get("bytes") or 0),
        "elapsed_ms": int(support_report.get("elapsed_ms") or 0),
        "companies_with_recent_awards": int(support_report.get("companies_with_recent_awards") or 0),
        "observations": int(support_report.get("observations") or 0),
        "lookback_days": int(support_report.get("lookback_days") or settings["support_lookback_days"]),
        "max_events_per_company": int(
            support_report.get("max_events_per_company") or settings["support_events_per_company"]
        ),
        "source_snapshot_sha256": support_report.get("source_snapshot_sha256"),
        "error": support_report.get("error"),
        "source_failure_nonfatal": True,
    }

    report["claims"] = sum(len(row.get("claims") or []) for row in projected)
    report["evidence_items"] = sum(len(row.get("evidence") or []) for row in projected)
    report.setdefault("runtime", {})["wall_runtime_seconds"] = round(time.monotonic() - wall_start, 3)
    report["runtime"]["max_wall_runtime_seconds"] = int(settings["max_wall_runtime_seconds"])

    checks = report.setdefault("checks", {})
    checks["support_registry_request_bounded"] = support_bounded
    checks["support_projection_contract_valid"] = not contract_errors
    checks["canonical_projection_valid"] = not canonical_errors
    checks["synthesis_valid"] = not synthesis_errors
    checks["combined_request_budget_valid"] = combined_budget_valid
    checks["budget_valid"] = combined_budget_valid

    report["support_projection_errors"] = {
        "contract": contract_errors,
        "canonical": canonical_errors,
        "synthesis": synthesis_errors,
    }
    report["passed"] = (
        bool(report.get("passed"))
        and support_bounded
        and not contract_errors
        and not canonical_errors
        and not synthesis_errors
        and combined_budget_valid
    )
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return bool(report["passed"])


def _finalize_report(settings: dict[str, Any], wall_start: float, workspace_returncode: int) -> bool:
    report_path = Path(str(settings["report"]))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    elapsed = time.monotonic() - wall_start
    runtime = report.setdefault("runtime", {})
    runtime["wall_runtime_seconds"] = round(elapsed, 3)
    runtime["max_wall_runtime_seconds"] = int(settings["max_wall_runtime_seconds"])

    checks = report.setdefault("checks", {})
    checks["v6_workspace_built"] = workspace_returncode == 0
    checks["wrapper_wall_runtime_within_limit"] = elapsed <= int(settings["max_wall_runtime_seconds"])
    report["passed"] = bool(report.get("passed")) and all(
        [checks["v6_workspace_built"], checks["wrapper_wall_runtime_within_limit"]]
    )
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return bool(report["passed"])


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    wall_start = time.monotonic()
    try:
        prepared, settings = prepare_legacy_args(args)
        legacy, workspace = _commands(prepared, settings)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    first = subprocess.run(legacy, cwd=ROOT, check=False)
    if first.returncode != 0:
        return int(first.returncode)

    try:
        support_ok = _apply_support_awards(settings, wall_start)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"V7 support projection failed: {exc}", file=sys.stderr)
        return 1
    if not support_ok:
        return 1

    second = subprocess.run(workspace, cwd=ROOT, check=False)
    final_ok = _finalize_report(settings, wall_start, int(second.returncode))
    if second.returncode != 0:
        return int(second.returncode)
    return 0 if final_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
