from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

ENDPOINT = "https://data.brreg.no/enhetsregisteret/api/enheter/{org}"
FIELDS = {
    "registration_date": "registreringsdatoEnhetsregisteret",
    "registered_address": "forretningsadresse",
    "activity": "aktivitet",
    "registered_purpose": "vedtektsfestetFormaal",
    "contact_email": "epostadresse",
    "contact_phone": "telefon",
    "contact_mobile": "mobil",
    "website": "hjemmeside",
}


def _org(value: Any) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _fetch(org: str, timeout: float, retries: int) -> dict[str, Any]:
    url = ENDPOINT.format(org=org)
    last_error = ""
    for attempt in range(retries + 1):
        started = time.monotonic()
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "Signalpost-Phase1-Coverage/1.0",
                },
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
                status = int(getattr(response, "status", 200))
            body = json.loads(raw.decode("utf-8"))
            return {
                "organisation_number": org,
                "status": status,
                "url": url,
                "content_sha256": hashlib.sha256(raw).hexdigest(),
                "elapsed_ms": round((time.monotonic() - started) * 1000, 3),
                "fields": {
                    name: _present(body.get(source_key))
                    for name, source_key in FIELDS.items()
                },
            }
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code}"
            if exc.code not in {429, 500, 502, 503, 504}:
                break
        except Exception as exc:  # measurement must report failure, not hide it
            last_error = f"{type(exc).__name__}: {exc}"
        if attempt < retries:
            time.sleep(min(2.0 * (attempt + 1), 5.0))
    return {
        "organisation_number": org,
        "status": None,
        "url": url,
        "error": last_error or "unknown fetch error",
        "fields": {name: False for name in FIELDS},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure exact-live BRREG field coverage on a fixed cohort.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--audit", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--retries", type=int, default=2)
    args = parser.parse_args()

    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    orgs = [_org(row.get("organisation_number")) for row in rows]
    if any(len(org) != 9 for org in orgs):
        raise SystemExit("input contains invalid organisation number")
    if len(set(orgs)) != len(orgs):
        raise SystemExit("input contains duplicate organisation numbers")

    started = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        results = list(pool.map(lambda org: _fetch(org, args.timeout, args.retries), orgs))
    runtime = time.monotonic() - started

    status_counts = Counter(str(row.get("status")) for row in results)
    field_counts = {
        field: sum(1 for row in results if (row.get("fields") or {}).get(field) is True)
        for field in FIELDS
    }
    failures = [
        {
            "organisation_number": row["organisation_number"],
            "status": row.get("status"),
            "error": row.get("error"),
        }
        for row in results
        if row.get("status") != 200
    ]
    summary = {
        "schema_version": "signalpost-phase1-registry-live-coverage-v1",
        "companies": len(orgs),
        "unique_companies": len(set(orgs)),
        "exact_live_successes": sum(1 for row in results if row.get("status") == 200),
        "status_counts": dict(sorted(status_counts.items())),
        "field_company_coverage": field_counts,
        "requests": len(results),
        "requests_per_company": round(len(results) / len(orgs), 4) if orgs else 0.0,
        "runtime_seconds": round(runtime, 3),
        "third_party_cost_usd": 0.0,
        "failures": failures,
    }

    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.audit.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in results),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(f"{len(failures)} exact-live BRREG requests failed")


if __name__ == "__main__":
    main()
