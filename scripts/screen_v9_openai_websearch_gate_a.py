#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from norway_company_agent.v9_openai_gate_a import (
    GateAProviderConfig,
    preflight_gate_a_provider,
    run_gate_a_provider_screen,
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _bool(value: str) -> bool:
    return str(value or "").strip().casefold() in {"1", "true", "yes", "on"}


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Fail-closed consumed Gate-A screen for the experimental OpenAI web-search "
            "nomination provider. Provider output never authorizes publication."
        )
    )
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--gate-a", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--enable-live-provider", default="false")
    parser.add_argument("--evaluator-reproducible", default="false")
    parser.add_argument("--rights-status", default="unknown")
    parser.add_argument("--challenge-cost-budget-usd", type=float, default=0.0)
    parser.add_argument("--project-third-party-budget-usd", type=float, default=0.0)
    parser.add_argument("--site-timeout", type=float, default=8.0)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()

    gate_a_rows = read_jsonl(Path(args.gate_a))
    if len(gate_a_rows) != 20:
        raise SystemExit(f"frozen Gate-A must contain exactly 20 rows, got {len(gate_a_rows)}")

    profile_map = {
        str(row.get("organisation_number") or ""): row
        for row in read_jsonl(Path(args.profiles))
    }
    target_orgs = [str(row.get("organisation_number") or "") for row in gate_a_rows]
    missing = [org for org in target_orgs if org not in profile_map]
    if missing:
        raise SystemExit(f"Gate-A organisations missing from profiles: {missing[:5]}")
    profiles = [profile_map[org] for org in target_orgs]

    config = GateAProviderConfig(
        enable_live_provider=_bool(args.enable_live_provider),
        evaluator_reproducible=_bool(args.evaluator_reproducible),
        rights_status=args.rights_status,
        challenge_cost_budget_usd=args.challenge_cost_budget_usd,
        project_third_party_budget_usd=args.project_third_party_budget_usd,
    )
    api_key = str(os.environ.get("OPENAI_API_KEY") or "").strip()
    started = time.monotonic()

    if args.preflight_only:
        report = {
            "schema_version": "signalpost-v9-openai-websearch-gate-a-preflight-v1",
            "status": "preflight_only",
            "cohort": "consumed_gate_a_20",
            "fresh_qualification_credit": False,
            "publication_enabled": False,
            "production_publications": 0,
            "provider_preflight": preflight_gate_a_provider(
                config,
                company_count=len(profiles),
                api_key_available=bool(api_key),
            ),
            "runtime_seconds": round(time.monotonic() - started, 3),
        }
    else:
        report = run_gate_a_provider_screen(
            profiles,
            api_key=api_key,
            config=config,
            site_timeout=args.site_timeout,
        )
        report["runtime_seconds"] = round(time.monotonic() - started, 3)

    write_json(Path(args.report), report)
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "company_results"},
            ensure_ascii=False,
            indent=2,
        )
    )

    if not args.preflight_only and report.get("status") == "provider_gate_blocked":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
