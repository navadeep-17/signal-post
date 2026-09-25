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
from build_v2_product import build_v2_html, read_jsonl  # noqa: E402


def _flag_value(argv: list[str], flag: str) -> str:
    try:
        index = argv.index(flag)
    except ValueError as exc:
        raise SystemExit(f"V2 runner requires {flag}") from exc
    if index + 1 >= len(argv):
        raise SystemExit(f"V2 runner requires a value after {flag}")
    return argv[index + 1]


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

    base_output = output_path.with_name(output_path.stem + ".v1-base" + output_path.suffix)
    base_report = report_path.with_name(report_path.stem + ".v1-base" + report_path.suffix)
    base_args = _replace_flag(forwarded, "--output", str(base_output))
    base_args = _replace_flag(base_args, "--report", str(base_report))

    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_signalpost_final.py"), *base_args],
        cwd=ROOT,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)

    base_rows = read_jsonl(base_output)
    profiles_by_org = _profile_index(work_dir)
    projected: list[dict[str, Any]] = []
    for row in base_rows:
        org = str(row.get("organisation_number") or "")
        profile = profiles_by_org.get(org)
        if profile is None:
            raise SystemExit(f"V2 retained profile missing for {org}")
        with_registry = project_v2_registry_claims(row, profile)
        with_activity = project_first_party_activity_claims(with_registry, profile)
        item = project_canonical_profile(with_activity)
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
    report["canonical_projection"] = _canonical_metrics(projected)
    report["canonical_projection"]["validation_errors"] = errors
    report["canonical_projection"]["v2_registry_projection"] = {
        "network_requests_added": 0,
        "fields": ["industry", "municipality_number", "bankrupt", "liquidating"],
        "source": "exact-org BRREG registry profile retained by the unchanged base collector",
    }
    report["canonical_projection"]["first_party_activity_projection"] = {
        "network_requests_added": 0,
        "generic_careers_page_counts_as_hiring": False,
        "job_requirement": "specific retained company-owned role page + job detail marker + explicit apply action",
        "company_update_requirement": "specific retained company-owned news/update page + explicit publication date",
    }
    report["synthesis"] = {
        "schema_version": SYNTHESIS_SCHEMA_VERSION,
        "companies": len(projected),
        "network_requests_added": 0,
        "llm_used": False,
        "new_facts_created": False,
        "validation_errors": synthesis_errors,
    }
    report.setdefault("checks", {})["canonical_projection_valid"] = not errors
    report["checks"]["synthesis_valid"] = not synthesis_errors
    report["passed"] = bool(report.get("passed")) and not errors and not synthesis_errors

    if product_output:
        product_path = Path(product_output)
        product_path.parent.mkdir(parents=True, exist_ok=True)
        product_path.write_text(
            build_v2_html(projected, title="Signalpost V2 — evidence-backed company intelligence"),
            encoding="utf-8",
        )
        report["product_surface"] = {
            "path": str(product_path),
            "data_linked": True,
            "source_output": str(output_path),
            "companies": len(projected),
            "deterministic_synthesis": True,
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
