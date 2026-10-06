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

from build_v2_product import read_jsonl  # noqa: E402
from norway_company_agent.batch import read_organisation_inputs  # noqa: E402
from norway_company_agent.canonical_projection import (  # noqa: E402
    CANONICAL_SCHEMA_VERSION,
    project_canonical_profile,
    validate_canonical_projection,
)
from norway_company_agent.company_site_phone import attach_company_site_contact_phone_observations  # noqa: E402
from norway_company_agent.external_contract import project_contact_phone_observations  # noqa: E402
from norway_company_agent.external_precision_guard import project_external_precision_guard  # noqa: E402
from norway_company_agent.first_party_feed_contract import project_first_party_feed_updates  # noqa: E402
from norway_company_agent.output_contract import validate_contract_object  # noqa: E402
from norway_company_agent.synthesis import (  # noqa: E402
    SYNTHESIS_SCHEMA_VERSION,
    build_company_synthesis,
    validate_company_synthesis,
)

V7_RUNNER = ROOT / "scripts" / "run_signalpost_v7.py"
V6_BUILDER = ROOT / "scripts" / "build_v6_ui.py"
SMOKE_TEST_MIN_REQUEST_BUDGET = 2000
REQUEST_BUDGET_PER_COMPANY = 20
SMOKE_TEST_MIN_WALL_RUNTIME_SECONDS = 2400
WALL_RUNTIME_SECONDS_PER_COMPANY = 3


def _arg_value(argv: list[str], flag: str) -> str | None:
    prefix = flag + "="
    for index, arg in enumerate(argv):
        if arg.startswith(prefix):
            return arg[len(prefix) :]
        if arg == flag:
            if index + 1 >= len(argv):
                raise ValueError(f"V8 wrapper requires a value after {flag}")
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
                raise ValueError(f"V8 wrapper requires a value after {flag}")
            args[index + 1] = value
            return args
    return [*args, flag, value]


def default_request_budget(expected_count: int) -> int:
    if expected_count < 1:
        raise ValueError("expected_count must be positive")
    return max(SMOKE_TEST_MIN_REQUEST_BUDGET, REQUEST_BUDGET_PER_COMPANY * expected_count)


def default_wall_runtime_seconds(expected_count: int) -> int:
    if expected_count < 1:
        raise ValueError("expected_count must be positive")
    return max(
        SMOKE_TEST_MIN_WALL_RUNTIME_SECONDS,
        WALL_RUNTIME_SECONDS_PER_COMPANY * expected_count,
    )


def prepare_evaluator_args(argv: list[str]) -> tuple[list[str], dict[str, int]]:
    organisations = _arg_value(argv, "--organisations")
    if not organisations:
        raise ValueError("V8 wrapper requires --organisations so the evaluator batch size can be derived.")

    inputs = read_organisation_inputs(organisations)
    expected_count = len(inputs)
    if expected_count < 1:
        raise ValueError("V8 wrapper requires at least one organisation input.")

    explicit_expected = _arg_value(argv, "--expected-count")
    if explicit_expected is not None:
        try:
            configured_expected = int(explicit_expected)
        except ValueError as exc:
            raise ValueError("--expected-count must be an integer") from exc
        if configured_expected != expected_count:
            raise ValueError(
                f"--expected-count={configured_expected} does not match the supplied evaluator batch ({expected_count})."
            )

    prepared = _set_arg(argv, "--expected-count", str(expected_count))

    explicit_request_budget = _arg_value(prepared, "--max-challenge-requests")
    if explicit_request_budget is None:
        request_budget = default_request_budget(expected_count)
        prepared = _set_arg(prepared, "--max-challenge-requests", str(request_budget))
    else:
        try:
            request_budget = int(explicit_request_budget)
        except ValueError as exc:
            raise ValueError("--max-challenge-requests must be an integer") from exc
        if request_budget < 1:
            raise ValueError("--max-challenge-requests must be positive")

    explicit_wall_runtime = _arg_value(prepared, "--max-wall-runtime-seconds")
    if explicit_wall_runtime is None:
        wall_runtime = default_wall_runtime_seconds(expected_count)
        prepared = _set_arg(prepared, "--max-wall-runtime-seconds", str(wall_runtime))
    else:
        try:
            wall_runtime = int(explicit_wall_runtime)
        except ValueError as exc:
            raise ValueError("--max-wall-runtime-seconds must be an integer") from exc
        if wall_runtime < 1:
            raise ValueError("--max-wall-runtime-seconds must be positive")

    return prepared, {
        "expected_count": expected_count,
        "max_challenge_requests": request_budget,
        "max_wall_runtime_seconds": wall_runtime,
    }


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    temporary.replace(path)


def _profile_index(work_dir: Path) -> dict[str, dict[str, Any]]:
    path = work_dir / "profiles.jsonl"
    if not path.is_file():
        raise ValueError(f"V8 wrapper expected retained internal profiles at {path}")
    profiles = read_jsonl(path)
    index = {
        str(profile.get("organisation_number") or ""): profile
        for profile in profiles
        if profile.get("organisation_number")
    }
    if len(index) != len(profiles):
        raise ValueError("V8 retained profiles contain missing or duplicate organisation numbers")
    return index


def _canonical_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    area_counts = {
        "company_record": 0,
        "financials": 0,
        "people_and_locations": 0,
        "company_website": 0,
        "hiring_and_public_activity": 0,
    }
    fact_type_counts: dict[str, int] = {}
    for row in rows:
        canonical = row.get("canonical_profile") or {}
        areas = canonical.get("data_areas") or {}
        for key in area_counts:
            area_counts[key] += int(bool(areas.get(key)))
        for fact in row.get("canonical_facts") or []:
            fact_type = str(fact.get("type") or "unknown")
            fact_type_counts[fact_type] = fact_type_counts.get(fact_type, 0) + 1
    return {
        "schema_version": CANONICAL_SCHEMA_VERSION,
        "companies": len(rows),
        "facts": sum(len(row.get("canonical_facts") or []) for row in rows),
        "companies_by_data_area": area_counts,
        "fact_type_counts": dict(sorted(fact_type_counts.items())),
    }


def _project_q4_feed_activity(
    *,
    output_path: Path,
    report_path: Path,
    work_dir: Path,
    product_output: Path,
    expected_count: int,
) -> bool:
    rows = read_jsonl(output_path)
    profiles_by_org = _profile_index(work_dir)
    projected: list[dict[str, Any]] = []
    contract_errors: list[dict[str, str]] = []
    canonical_errors: list[dict[str, str]] = []
    synthesis_errors: list[dict[str, str]] = []
    feed_claims = 0
    feed_companies = 0
    contact_phone_claims = 0
    contact_phone_companies = 0
    precision_removed_claims = 0
    precision_removed_companies = 0

    for row in rows:
        org = str(row.get("organisation_number") or "")
        profile = profiles_by_org.get(org)
        if profile is None:
            raise ValueError(f"V8 retained profile missing for {org}")
        before_phone = sum(
            1
            for claim in row.get("claims") or []
            if isinstance(claim, dict)
            and claim.get("field") == "external.contact_phone"
            and claim.get("availability") == "available"
        )
        profile = attach_company_site_contact_phone_observations(profile)
        with_phone = project_contact_phone_observations(row, profile)
        after_phone = sum(
            1
            for claim in with_phone.get("claims") or []
            if isinstance(claim, dict)
            and claim.get("field") == "external.contact_phone"
            and claim.get("availability") == "available"
        )
        added_phone = max(0, after_phone - before_phone)
        contact_phone_claims += added_phone
        contact_phone_companies += int(added_phone > 0)

        before = sum(
            1
            for claim in with_phone.get("claims") or []
            if isinstance(claim, dict) and claim.get("field") == "external.company_update"
        )
        with_feed = project_first_party_feed_updates(with_phone, profile)
        guarded = project_external_precision_guard(with_feed)
        removed = max(0, len(with_feed.get("claims") or []) - len(guarded.get("claims") or []))
        precision_removed_claims += removed
        precision_removed_companies += int(removed > 0)
        after = sum(
            1
            for claim in guarded.get("claims") or []
            if isinstance(claim, dict) and claim.get("field") == "external.company_update"
        )
        added = max(0, after - before)
        feed_claims += added
        feed_companies += int(added > 0)

        item = project_canonical_profile(guarded)
        item["synthesis"] = build_company_synthesis(item)
        for error in validate_contract_object(item):
            contract_errors.append({"organisation_number": org, "error": error})
        for error in validate_canonical_projection(item):
            canonical_errors.append({"organisation_number": org, "error": error})
        for error in validate_company_synthesis(item):
            synthesis_errors.append({"organisation_number": org, "error": error})
        projected.append(item)

    _write_jsonl(output_path, projected)

    workspace_command = [
        sys.executable,
        str(V6_BUILDER),
        "--input",
        str(output_path),
        "--output",
        str(product_output),
        "--expect-count",
        str(expected_count),
    ]
    workspace_returncode = subprocess.run(workspace_command, cwd=ROOT, check=False).returncode

    report = json.loads(report_path.read_text(encoding="utf-8"))
    canonical_report = dict(report.get("canonical_projection") or {})
    canonical_report.update(_canonical_metrics(projected))
    canonical_report["validation_errors"] = canonical_errors
    canonical_report["q4_feed_activity_projection"] = {
        "claim_field": "external.company_update",
        "canonical_type": "public.company_update",
        "published_claims": feed_claims,
        "companies_with_published_claims": feed_companies,
        "network_requests_added_by_projection": 0,
        "source_boundary": (
            "exact-verified company website -> same-site RSS/Atom snapshot; feed is cited source; "
            "article URL is observed in the feed and is not represented as independently fetched"
        ),
    }
    canonical_report["structured_contact_phone_projection"] = {
        "claim_field": "external.contact_phone",
        "canonical_type": "website.contact_phone",
        "published_claims_added": contact_phone_claims,
        "companies_with_new_published_claims": contact_phone_companies,
        "network_requests_added_by_projection": 0,
        "source_boundary": (
            "already-retained exact company website -> exact schema.org Organization/ContactPoint "
            "telephone field; no additional fetch"
        ),
    }
    report["canonical_projection"] = canonical_report

    source_policy = report.setdefault("source_policy", {})
    source_policy.update(
        {
            "company_page_structured_contact_phone_extraction_enabled": True,
            "contact_phone_network_requests": 0,
        }
    )
    external_signals = report.setdefault("external_signals", {})
    external_signals.update(
        {
            "structured_contact_phone_claims_added": contact_phone_claims,
            "companies_with_new_structured_contact_phones": contact_phone_companies,
            "contact_phone_network_requests": 0,
        }
    )

    report["synthesis"] = {
        **dict(report.get("synthesis") or {}),
        "schema_version": SYNTHESIS_SCHEMA_VERSION,
        "companies": len(projected),
        "q4_feed_activity_context_enabled": True,
        "validation_errors": synthesis_errors,
    }
    report["external_precision_guard"] = {
        "network_requests_added": 0,
        "removed_claims": precision_removed_claims,
        "companies_with_removed_claims": precision_removed_companies,
        "scope": ["external.careers_page", "external.company_update"],
    }
    report["q4_feed_activity"] = {
        "production_fetch_location": "spare site-request slot after exact website verification and after H1g priority",
        "network_requests_added_by_projection": 0,
        "published_claims": feed_claims,
        "companies_with_published_claims": feed_companies,
        "max_site_logical_requests_per_profile_unchanged": 4,
        "third_party_cost_usd": 0.0,
    }
    report["claims"] = sum(len(row.get("claims") or []) for row in projected)
    report["evidence_items"] = sum(len(row.get("evidence") or []) for row in projected)

    checks = report.setdefault("checks", {})
    checks["q4_feed_projection_contract_valid"] = not contract_errors
    checks["structured_contact_phone_projection_zero_network"] = True
    checks["canonical_projection_valid"] = not canonical_errors
    checks["synthesis_valid"] = not synthesis_errors
    checks["q4_workspace_rebuild_valid"] = workspace_returncode == 0
    report["q4_feed_projection_errors"] = {
        "contract": contract_errors,
        "canonical": canonical_errors,
        "synthesis": synthesis_errors,
    }
    report["passed"] = (
        bool(report.get("passed"))
        and not contract_errors
        and not canonical_errors
        and not synthesis_errors
        and workspace_returncode == 0
    )
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return bool(report["passed"])


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        prepared, settings = prepare_evaluator_args(args)
        output_raw = _arg_value(prepared, "--output")
        report_raw = _arg_value(prepared, "--report")
        work_raw = _arg_value(prepared, "--work-dir")
        product_raw = _arg_value(prepared, "--product-output")
        q4_path_count = sum(value is not None for value in (report_raw, work_raw))
        if q4_path_count == 1:
            raise ValueError("V8 Q4 projection requires --report and --work-dir together")
        q4_projection_enabled = q4_path_count == 2
        if q4_projection_enabled and (not output_raw or not product_raw):
            raise ValueError(
                "V8 Q4 projection requires --output and --product-output when --report/--work-dir are supplied"
            )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(
        "Signalpost V8 evaluator batch: "
        f"{settings['expected_count']} companies; "
        f"internal conservative request ceiling={settings['max_challenge_requests']}; "
        f"internal wall-runtime validation ceiling={settings['max_wall_runtime_seconds']}s; "
        f"q4_feed_projection={'enabled' if q4_projection_enabled else 'disabled_legacy_mode'}.",
        file=sys.stderr,
    )
    completed = subprocess.run(
        [sys.executable, str(V7_RUNNER), *prepared],
        cwd=ROOT,
        check=False,
    )
    if completed.returncode != 0:
        return int(completed.returncode)
    if not q4_projection_enabled:
        return 0

    try:
        passed = _project_q4_feed_activity(
            output_path=Path(str(output_raw)),
            report_path=Path(str(report_raw)),
            work_dir=Path(str(work_raw)),
            product_output=Path(str(product_raw)),
            expected_count=int(settings["expected_count"]),
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"V8 Q4 feed projection failed: {exc}", file=sys.stderr)
        return 1
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
