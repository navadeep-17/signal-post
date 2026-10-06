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
from norway_company_agent.canonical_projection import (  # noqa: E402
    project_canonical_profile,
    validate_canonical_projection,
)
from norway_company_agent.company_site_contact import (  # noqa: E402
    attach_company_site_contact_email_observations,
)
from norway_company_agent.company_site_phone import (  # noqa: E402
    attach_company_site_contact_phone_observations,
)
from norway_company_agent.external_contract import (  # noqa: E402
    project_contact_email_observations,
    project_contact_phone_observations,
)
from norway_company_agent.output_contract import validate_contract_object  # noqa: E402
from norway_company_agent.synthesis import (  # noqa: E402
    build_company_synthesis,
    validate_company_synthesis,
)

V8_RUNNER = ROOT / "scripts" / "run_signalpost_v8.py"
V6_BUILDER = ROOT / "scripts" / "build_v6_ui.py"


def _arg_value(argv: list[str], flag: str) -> str | None:
    prefix = flag + "="
    for index, arg in enumerate(argv):
        if arg.startswith(prefix):
            return arg[len(prefix) :]
        if arg == flag:
            if index + 1 >= len(argv):
                raise ValueError(f"V9 wrapper requires a value after {flag}")
            return argv[index + 1]
    return None


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    temporary.replace(path)


def _available_claim_count(row: dict[str, Any], field: str) -> int:
    return sum(
        1
        for claim in row.get("claims") or []
        if isinstance(claim, dict)
        and claim.get("field") == field
        and claim.get("availability") == "available"
        and claim.get("value") not in (None, "")
    )


def _project_m4_zero_request_contacts(
    *,
    output_path: Path,
    report_path: Path,
    work_dir: Path,
    product_output: Path,
) -> bool:
    rows = read_jsonl(output_path)
    profiles = read_jsonl(work_dir / "profiles.jsonl")
    profiles_by_org = {
        str(profile.get("organisation_number") or ""): profile
        for profile in profiles
    }
    if len(profiles_by_org) != len(profiles):
        raise ValueError("V9 retained profiles contain missing or duplicate organisation numbers")

    before_email_claims = sum(_available_claim_count(row, "external.contact_email") for row in rows)
    before_phone_claims = sum(_available_claim_count(row, "external.contact_phone") for row in rows)

    projected: list[dict[str, Any]] = []
    contract_errors: list[dict[str, str]] = []
    canonical_errors: list[dict[str, str]] = []
    synthesis_errors: list[dict[str, str]] = []

    for row in rows:
        org = str(row.get("organisation_number") or "")
        profile = profiles_by_org.get(org)
        if profile is None:
            raise ValueError(f"V9 retained profile missing for {org}")

        # M4 is extraction/projection only over the already-retained exact website snapshot.
        # These helpers perform no network access.
        attach_company_site_contact_email_observations(profile)
        attach_company_site_contact_phone_observations(profile)

        item = project_contact_email_observations(row, profile)
        item = project_contact_phone_observations(item, profile)
        item = project_canonical_profile(item)
        item["synthesis"] = build_company_synthesis(item)

        for error in validate_contract_object(item):
            contract_errors.append({"organisation_number": org, "error": error})
        for error in validate_canonical_projection(item):
            canonical_errors.append({"organisation_number": org, "error": error})
        for error in validate_company_synthesis(item):
            synthesis_errors.append({"organisation_number": org, "error": error})
        projected.append(item)

    after_email_claims = sum(_available_claim_count(row, "external.contact_email") for row in projected)
    after_phone_claims = sum(_available_claim_count(row, "external.contact_phone") for row in projected)
    email_observations = [
        observation
        for profile in profiles
        for observation in (profile.get("external_observations") or [])
        if isinstance(observation, dict) and observation.get("contact_email")
    ]
    phone_observations = [
        observation
        for profile in profiles
        for observation in (profile.get("external_observations") or [])
        if isinstance(observation, dict) and observation.get("contact_phone")
    ]

    _write_jsonl(work_dir / "profiles.jsonl", profiles)
    _write_jsonl(output_path, projected)

    report = json.loads(report_path.read_text(encoding="utf-8"))
    expected_count = int(report.get("expected_count") or len(projected))
    workspace_returncode = subprocess.run(
        [
            sys.executable,
            str(V6_BUILDER),
            "--input",
            str(output_path),
            "--output",
            str(product_output),
            "--expect-count",
            str(expected_count),
        ],
        cwd=ROOT,
        check=False,
    ).returncode

    source_policy = dict(report.get("source_policy") or {})
    source_policy.update(
        {
            "company_page_structured_contact_email_recovery_enabled": True,
            "company_page_structured_contact_phone_recovery_enabled": True,
            "contact_email_network_requests": 0,
            "contact_phone_network_requests": 0,
        }
    )
    report["source_policy"] = source_policy

    external_signals = dict(report.get("external_signals") or {})
    external_signals.update(
        {
            "contact_email_observations": len(email_observations),
            "companies_with_contact_emails": len(
                {str(item.get("organisation_number") or "") for item in email_observations}
            ),
            "contact_email_network_requests": 0,
            "contact_phone_observations": len(phone_observations),
            "companies_with_contact_phones": len(
                {str(item.get("organisation_number") or "") for item in phone_observations}
            ),
            "contact_phone_network_requests": 0,
        }
    )
    report["external_signals"] = external_signals

    report["v9_m4_zero_request_contacts"] = {
        "network_requests_added": 0,
        "third_party_cost_usd_added": 0.0,
        "search_api_requests_added": 0,
        "before_contact_email_claims": before_email_claims,
        "after_contact_email_claims": after_email_claims,
        "added_contact_email_claims": max(0, after_email_claims - before_email_claims),
        "before_contact_phone_claims": before_phone_claims,
        "after_contact_phone_claims": after_phone_claims,
        "added_contact_phone_claims": max(0, after_phone_claims - before_phone_claims),
        "contract_validation_errors": contract_errors,
        "canonical_validation_errors": canonical_errors,
        "synthesis_validation_errors": synthesis_errors,
        "workspace_rebuild_returncode": workspace_returncode,
    }
    report["claims"] = sum(len(row.get("claims") or []) for row in projected)
    report["evidence_items"] = sum(len(row.get("evidence") or []) for row in projected)

    checks = report.setdefault("checks", {})
    checks["v9_m4_contact_projection_contract_valid"] = not contract_errors
    checks["v9_m4_contact_projection_canonical_valid"] = not canonical_errors
    checks["v9_m4_contact_projection_synthesis_valid"] = not synthesis_errors
    checks["v9_m4_contact_workspace_rebuild_valid"] = workspace_returncode == 0
    report["passed"] = (
        bool(report.get("passed"))
        and not contract_errors
        and not canonical_errors
        and not synthesis_errors
        and workspace_returncode == 0
    )
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return bool(report["passed"])


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        output_raw = _arg_value(args, "--output")
        report_raw = _arg_value(args, "--report")
        work_raw = _arg_value(args, "--work-dir")
        product_raw = _arg_value(args, "--product-output")
        if not all((output_raw, report_raw, work_raw, product_raw)):
            raise ValueError(
                "V9 M4 wrapper requires --output, --report, --work-dir and --product-output"
            )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    completed = subprocess.run(
        [sys.executable, str(V8_RUNNER), *args],
        cwd=ROOT,
        check=False,
    )
    if completed.returncode != 0:
        return int(completed.returncode)

    try:
        passed = _project_m4_zero_request_contacts(
            output_path=Path(str(output_raw)),
            report_path=Path(str(report_raw)),
            work_dir=Path(str(work_raw)),
            product_output=Path(str(product_raw)),
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"V9 M4 zero-request contact projection failed: {exc}", file=sys.stderr)
        return 1
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
