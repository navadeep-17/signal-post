#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

USER_AGENT = "signalpost-source-screen/1.0"


def _org(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("organisation_number")
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(digits) != 9:
        raise ValueError(f"Invalid Norwegian organisation number: {value!r}")
    return digits


def _read_companies(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"Expected JSON object rows in {path}")
        org = _org(row)
        if org in seen:
            raise ValueError(f"Duplicate organisation number in cohort: {org}")
        seen.add(org)
        rows.append(row)
    if not rows:
        raise ValueError("Screen cohort is empty")
    return rows


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def exact_org_pattern(organisation_number: str) -> re.Pattern[bytes]:
    org = _org(organisation_number)
    a, b, c = org[:3], org[3:6], org[6:]
    return re.compile(
        rb"(?<!\d)"
        + a.encode("ascii")
        + rb"(?:[^0-9]{0,3})"
        + b.encode("ascii")
        + rb"(?:[^0-9]{0,3})"
        + c.encode("ascii")
        + rb"(?!\d)"
    )


def analyse_payload(payload: bytes, organisation_number: str, *, context_bytes: int = 240) -> dict[str, Any]:
    pattern = exact_org_pattern(organisation_number)
    matches = list(pattern.finditer(payload))
    context: str | None = None
    if matches:
        match = matches[0]
        left = max(0, match.start() - context_bytes)
        right = min(len(payload), match.end() + context_bytes)
        context = payload[left:right].decode("utf-8", errors="replace")
    return {
        "matched": bool(matches),
        "exact_org_occurrences": len(matches),
        "first_context": context,
        "response_bytes": len(payload),
        "response_sha256": _sha256_bytes(payload),
    }


def build_request(
    endpoint_template: str,
    organisation_number: str,
    *,
    api_key: str,
    api_key_header: str,
    accept: str,
) -> urllib.request.Request:
    if "{organisation_number}" not in endpoint_template:
        raise ValueError("endpoint template must contain {organisation_number}")
    endpoint = endpoint_template.format(organisation_number=_org(organisation_number))
    if not endpoint.startswith("https://"):
        raise ValueError("screen endpoint must use https://")
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": accept,
        api_key_header: api_key,
    }
    return urllib.request.Request(endpoint, headers=headers, method="GET")


def fetch_payload(
    endpoint_template: str,
    organisation_number: str,
    *,
    api_key: str,
    api_key_header: str,
    accept: str,
    timeout: float,
    max_bytes: int,
) -> tuple[int, str, bytes]:
    request = build_request(
        endpoint_template,
        organisation_number,
        api_key=api_key,
        api_key_header=api_key_header,
        accept=accept,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read(max_bytes + 1)
            if len(payload) > max_bytes:
                raise RuntimeError(f"response exceeded max_bytes={max_bytes}")
            return int(response.status), response.geturl(), payload
    except urllib.error.HTTPError as exc:
        payload = exc.read(max_bytes + 1)
        if len(payload) > max_bytes:
            payload = payload[:max_bytes]
        return int(exc.code), exc.geturl(), payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Credential-gated reach screen for official APIs. The screen only measures whether "
            "the exact target organisation number appears in the response. It does not publish facts."
        )
    )
    parser.add_argument("--companies", required=True)
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--endpoint-template", required=True, help="HTTPS GET URL containing {organisation_number}")
    parser.add_argument("--api-key-env", default="SIGNALPOST_SOURCE_API_KEY")
    parser.add_argument("--api-key-header", default="Ocp-Apim-Subscription-Key")
    parser.add_argument("--accept", default="application/json, application/xml, text/xml;q=0.9, */*;q=0.1")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--max-bytes", type=int, default=5_000_000)
    parser.add_argument("--responses-dir", required=True)
    parser.add_argument("--rows-output", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    api_key = os.environ.get(args.api_key_env, "").strip()
    if not api_key:
        raise SystemExit(f"Missing API key in environment variable {args.api_key_env}")
    if args.max_bytes < 1024:
        raise SystemExit("--max-bytes must be at least 1024")

    companies_path = Path(args.companies)
    companies = _read_companies(companies_path)
    responses_dir = Path(args.responses_dir)
    rows_path = Path(args.rows_output)
    report_path = Path(args.report)
    responses_dir.mkdir(parents=True, exist_ok=True)
    rows_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    total_bytes = 0
    for company in companies:
        org = _org(company)
        status, final_url, payload = fetch_payload(
            args.endpoint_template,
            org,
            api_key=api_key,
            api_key_header=args.api_key_header,
            accept=args.accept,
            timeout=args.timeout,
            max_bytes=args.max_bytes,
        )
        total_bytes += len(payload)
        response_path = responses_dir / f"{org}.response"
        response_path.write_bytes(payload)
        analysis = analyse_payload(payload, org)
        rows.append(
            {
                "organisation_number": org,
                "name": company.get("name"),
                "http_status": status,
                "final_url": final_url,
                **analysis,
            }
        )

    matched = [row for row in rows if row["matched"] and 200 <= int(row["http_status"]) < 300]
    successful = [row for row in rows if 200 <= int(row["http_status"]) < 300]
    report = {
        "source": args.source_name,
        "screen_type": "credential_gated_exact_org_response_presence",
        "companies": len(rows),
        "successful_responses": len(successful),
        "matched_companies": len(matched),
        "reach_rate": round(len(matched) / len(rows), 6),
        "total_response_bytes": total_bytes,
        "cohort_sha256": _sha256_file(companies_path),
        "production_connector_implemented": False,
        "api_key_header": args.api_key_header,
        "notes": [
            "This is a reach/access screen only; it does not publish company facts.",
            "A match only means the exact target organisation number appears in the returned official payload.",
            "Promotion requires source-specific schema parsing and role validation (for example owner/applicant/supplier), not mere identifier presence.",
            "API key values are never persisted in artifacts or reports.",
        ],
    }

    with rows_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
