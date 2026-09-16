#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

PATH = Path("scripts/run_signalpost_final.py")
text = PATH.read_text(encoding="utf-8")


def replace_once(old: str, new: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one runner match, got {count}: {old[:100]!r}")
    text = text.replace(old, new, 1)


replace_once(
    "from norway_company_agent.registry_workforce import attach_registry_workforce_observations  # noqa: E402\n",
    "from norway_company_agent.registry_workforce import attach_registry_workforce_observations  # noqa: E402\n"
    "from norway_company_agent.annual_report_workforce import attach_annual_report_workforce_batch  # noqa: E402\n",
)

replace_once(
    '    parser.add_argument("--refresh-report", help="Optional refresh report with events[]")\n',
    '    parser.add_argument("--refresh-report", help="Optional refresh report with events[]")\n'
    '    parser.add_argument("--annual-workforce-workers", type=int, default=4)\n'
    '    parser.add_argument("--annual-workforce-timeout", type=float, default=60.0)\n'
    '    parser.add_argument("--annual-workforce-min-start-interval", type=float, default=2.1)\n'
    '    parser.add_argument("--annual-workforce-ocr-pages", type=int, default=8)\n'
    '    parser.add_argument("--annual-workforce-ocr-dpi", type=int, default=110)\n',
)

replace_once(
    '    if args.max_wall_runtime_seconds < 1:\n        parser.error("--max-wall-runtime-seconds must be positive")\n',
    '    if args.max_wall_runtime_seconds < 1:\n        parser.error("--max-wall-runtime-seconds must be positive")\n'
    '    if args.annual_workforce_workers < 1:\n        parser.error("--annual-workforce-workers must be positive")\n'
    '    if args.annual_workforce_timeout <= 0:\n        parser.error("--annual-workforce-timeout must be positive")\n'
    '    if args.annual_workforce_min_start_interval < 0:\n        parser.error("--annual-workforce-min-start-interval cannot be negative")\n'
    '    if args.annual_workforce_ocr_pages < 0:\n        parser.error("--annual-workforce-ocr-pages cannot be negative")\n'
    '    if args.annual_workforce_ocr_dpi < 50:\n        parser.error("--annual-workforce-ocr-dpi must be at least 50")\n',
)

replace_once(
    "    per_profile_logical_ceiling = OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE + MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE\n"
    "    theoretical_shared_wikidata_requests = theoretical_wikidata_lookup_requests(args.expected_count)\n"
    "    theoretical_logical_ceiling = (\n"
    "        args.expected_count * per_profile_logical_ceiling\n"
    "        + theoretical_shared_wikidata_requests\n"
    "    )\n"
    "    theoretical_charge_ceiling = budget.charge_requests(theoretical_logical_ceiling)\n"
    "    if theoretical_charge_ceiling > args.max_challenge_requests:\n"
    "        raise SystemExit(\n"
    "            f\"Configured pipeline cannot prove request safety: theoretical charge \"\n"
    "            f\"{theoretical_charge_ceiling}>{args.max_challenge_requests}. \"\n"
    "            \"Reduce expected count or raise the explicit budget only within the challenge's request cap.\"\n"
    "        )\n",
    "    per_profile_logical_ceiling = OFFICIAL_LOGICAL_REQUESTS_PER_PROFILE + MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE\n"
    "    theoretical_shared_wikidata_requests = theoretical_wikidata_lookup_requests(args.expected_count)\n"
    "    base_theoretical_logical_ceiling = (\n"
    "        args.expected_count * per_profile_logical_ceiling\n"
    "        + theoretical_shared_wikidata_requests\n"
    "    )\n"
    "    base_theoretical_charge_ceiling = budget.charge_requests(base_theoretical_logical_ceiling)\n"
    "    if base_theoretical_charge_ceiling > args.max_challenge_requests:\n"
    "        raise SystemExit(\n"
    "            f\"Configured base pipeline cannot prove request safety: theoretical charge \"\n"
    "            f\"{base_theoretical_charge_ceiling}>{args.max_challenge_requests}. \"\n"
    "            \"Reduce expected count or raise the explicit budget only within the challenge's request cap.\"\n"
    "        )\n"
    "    remaining_structural_charge = args.max_challenge_requests - base_theoretical_charge_ceiling\n"
    "    annual_workforce_logical_request_ceiling = min(\n"
    "        args.expected_count,\n"
    "        max(0, remaining_structural_charge // budget.request_charge_multiplier),\n"
    "    )\n"
    "    theoretical_logical_ceiling = base_theoretical_logical_ceiling + annual_workforce_logical_request_ceiling\n"
    "    theoretical_charge_ceiling = budget.charge_requests(theoretical_logical_ceiling)\n",
)

replace_once(
    "    completed_at = utc_now()\n"
    "    ordered_profiles = [state[org] for org in orgs]\n"
    "    external_observation_errors, profile_handle_observations, contact_email_observations = _external_observation_audit(\n"
    "        ordered_profiles\n"
    "    )\n",
    "    ordered_profiles = [state[org] for org in orgs]\n"
    "    annual_workforce_report = attach_annual_report_workforce_batch(\n"
    "        ordered_profiles,\n"
    "        max_requests=annual_workforce_logical_request_ceiling,\n"
    "        workers=args.annual_workforce_workers,\n"
    "        min_start_interval=args.annual_workforce_min_start_interval,\n"
    "        timeout=args.annual_workforce_timeout,\n"
    "        ocr_pages=args.annual_workforce_ocr_pages,\n"
    "        ocr_dpi=args.annual_workforce_ocr_dpi,\n"
    "        request_charge_multiplier=budget.request_charge_multiplier,\n"
    "    )\n"
    "    completed_at = utc_now()\n"
    "    external_observation_errors, profile_handle_observations, contact_email_observations = _external_observation_audit(\n"
    "        ordered_profiles\n"
    "    )\n"
    "    workforce_observations = [\n"
    "        observation\n"
    "        for profile in ordered_profiles\n"
    "        for observation in (profile.get(\"external_observations\") or [])\n"
    "        if isinstance(observation, dict) and observation.get(\"signal_type\") == \"workforce_snapshot\"\n"
    "    ]\n",
)

replace_once(
    "    companies_with_contact_emails = len(\n"
    "        {str(item.get(\"organisation_number\") or \"\") for item in contact_email_observations}\n"
    "    )\n",
    "    companies_with_contact_emails = len(\n"
    "        {str(item.get(\"organisation_number\") or \"\") for item in contact_email_observations}\n"
    "    )\n"
    "    companies_with_workforce = len(\n"
    "        {str(item.get(\"organisation_number\") or \"\") for item in workforce_observations}\n"
    "    )\n"
    "    annual_workforce_observations = [\n"
    "        item for item in workforce_observations if item.get(\"source_class\") == \"official_annual_account_copy\"\n"
    "    ]\n",
)

replace_once(
    '        "site_source_accounting_consistent": sum(selected_sources.values()) == len(ordered_profiles),\n',
    '        "site_source_accounting_consistent": sum(selected_sources.values()) == len(ordered_profiles),\n'
    '        "annual_workforce_request_bounded": int(annual_workforce_report.get("requests") or 0) <= annual_workforce_logical_request_ceiling,\n'
    '        "annual_workforce_execution_clean": not (annual_workforce_report.get("execution_errors") or []),\n',
)

replace_once(
    '            "registry_workforce_network_requests": 0,\n',
    '            "registry_workforce_network_requests": 0,\n'
    '            "annual_report_workforce_enabled": annual_workforce_logical_request_ceiling > 0,\n'
    '            "annual_report_workforce_ocr_runtime_available": bool(annual_workforce_report.get("runtime_available")),\n'
    '            "annual_report_workforce_network_requests": int(annual_workforce_report.get("requests") or 0),\n',
)

replace_once(
    '            "theoretical_logical_request_ceiling": theoretical_logical_ceiling,\n',
    '            "base_theoretical_logical_request_ceiling": base_theoretical_logical_ceiling,\n'
    '            "base_theoretical_challenge_request_charge_ceiling": base_theoretical_charge_ceiling,\n'
    '            "annual_report_workforce_logical_request_ceiling": annual_workforce_logical_request_ceiling,\n'
    '            "theoretical_logical_request_ceiling": theoretical_logical_ceiling,\n',
)

replace_once(
    '            "contact_email_network_requests": 0,\n'
    '            "validation_errors": external_observation_errors,\n',
    '            "contact_email_network_requests": 0,\n'
    '            "workforce_observations": len(workforce_observations),\n'
    '            "companies_with_workforce": companies_with_workforce,\n'
    '            "annual_report_workforce_observations": len(annual_workforce_observations),\n'
    '            "annual_report_workforce_network_requests": int(annual_workforce_report.get("requests") or 0),\n'
    '            "validation_errors": external_observation_errors,\n',
)

replace_once(
    '        "refresh_events": len(refresh_events),\n',
    '        "annual_report_workforce": {\n'
    '            "runtime_available": bool(annual_workforce_report.get("runtime_available")),\n'
    '            "eligible": int(annual_workforce_report.get("eligible") or 0),\n'
    '            "selected": int(annual_workforce_report.get("selected") or 0),\n'
    '            "requests": int(annual_workforce_report.get("requests") or 0),\n'
    '            "accepted": int(annual_workforce_report.get("accepted") or 0),\n'
    '            "added_conservative_challenge_request_charge": int(annual_workforce_report.get("added_conservative_challenge_request_charge") or 0),\n'
    '            "status_counts": dict(annual_workforce_report.get("status_counts") or {}),\n'
    '            "runtime_seconds": float(annual_workforce_report.get("runtime_seconds") or 0.0),\n'
    '            "execution_errors": list(annual_workforce_report.get("execution_errors") or []),\n'
    '        },\n'
    '        "refresh_events": len(refresh_events),\n',
)

PATH.write_text(text, encoding="utf-8")
print(f"Patched {PATH}")
