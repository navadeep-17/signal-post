from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import time
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

POLICY_SUPPORT_SOURCE_COMMIT = "7c976bdb085b0233451ffcaa2825af07704a0ddb"
POLICY_SUPPORT_SOURCE_URL = (
    "https://raw.githubusercontent.com/innovationnorway/analysis-innovation-policy-data/"
    f"{POLICY_SUPPORT_SOURCE_COMMIT}/InnovationPolicyData.csv"
)
POLICY_SUPPORT_RIGHTS = "NLOD 2.0"
POLICY_SUPPORT_GIT_BLOB = "9bc4349638f75a2296afca6ceac247b567911f9f"
POLICY_SUPPORT_EXPECTED_BYTES = 39_507_381
MAX_SNAPSHOT_BYTES = 50_000_000


def _parse_date(value: Any) -> date | None:
    raw = "".join(str(value or "").split())
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 8:
        try:
            return date(int(digits[:4]), int(digits[4:6]), int(digits[6:8]))
        except ValueError:
            pass
    return None


def _parse_amount(value: Any) -> float | None:
    raw = str(value or "").strip().replace("\u00a0", "").replace(" ", "")
    if not raw:
        return None
    raw = raw.replace(",", ".")
    raw = re.sub(r"[^0-9.\-]", "", raw)
    try:
        return float(raw)
    except ValueError:
        return None


def _row_hash(row: dict[str, Any]) -> str:
    body = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _event_id(org: str, row_sha: str, event_date: str) -> str:
    material = f"{org}|{event_date}|{row_sha}"
    return "policy-support-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def parse_policy_support_snapshot(
    path: Path,
    target_orgs: set[str],
    *,
    snapshot_sha256: str,
    retrieved_at: str,
    max_events_per_company: int = 5,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Parse exact-org historical policy-support rows from the pinned NLOD snapshot."""

    if max_events_per_company < 1:
        raise ValueError("max_events_per_company must be positive")
    raw = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(io.StringIO(raw), delimiter=";")
    expected = {
        "Organisasjonsnummer",
        "Innvilget beløp",
        "Bidragstype",
        "Dato",
        "Virkemiddel",
        "Aktør",
    }
    missing = expected - set(reader.fieldnames or [])
    if missing:
        raise ValueError(f"Policy-support snapshot missing required fields: {sorted(missing)}")

    candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    rows_scanned = 0
    for row_number, row in enumerate(reader, start=2):
        rows_scanned += 1
        org = re.sub(r"\D", "", str(row.get("Organisasjonsnummer") or ""))
        if org not in target_orgs or len(org) != 9:
            continue
        event_date = _parse_date(row.get("Dato"))
        if event_date is None:
            continue
        actor = " ".join(str(row.get("Aktør") or "").split())
        instrument = " ".join(str(row.get("Virkemiddel") or "").split())
        contribution_type = " ".join(str(row.get("Bidragstype") or "").split())
        amount = _parse_amount(row.get("Innvilget beløp"))
        row_sha = _row_hash(row)
        span = "; ".join(
            part
            for part in (
                f"recipient org: {org}",
                f"date: {event_date.isoformat()}",
                f"actor: {actor}" if actor else "",
                f"instrument: {instrument}" if instrument else "",
                f"contribution type: {contribution_type}" if contribution_type else "",
                f"awarded amount: {amount:g} NOK" if amount is not None else "",
            )
            if part
        )[:1600]
        candidates[org].append(
            {
                "id": _event_id(org, row_sha, event_date.isoformat()),
                "organisation_number": org,
                "event_date": event_date.isoformat(),
                "actor": actor or None,
                "instrument": instrument or None,
                "contribution_type": contribution_type or None,
                "awarded_amount": amount,
                "currency": "NOK" if amount is not None else None,
                "source_row_number": row_number,
                "source_row_sha256": row_sha,
                "source_snapshot_sha256": snapshot_sha256,
                "retrieved_at": retrieved_at,
                "evidence_span": span,
            }
        )

    selected: dict[str, list[dict[str, Any]]] = {}
    for org, rows in candidates.items():
        rows.sort(key=lambda item: (str(item["event_date"]), str(item["id"])), reverse=True)
        selected[org] = rows[:max_events_per_company]
    return selected, {
        "rows_scanned": rows_scanned,
        "companies": len(selected),
        "events": sum(len(rows) for rows in selected.values()),
        "max_events_per_company": max_events_per_company,
        "source_snapshot_sha256": snapshot_sha256,
    }


def fetch_policy_support_batch(
    organisation_numbers: list[str],
    *,
    timeout: float = 120.0,
    max_events_per_company: int = 5,
    opener: Any = None,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Fetch exactly one pinned public snapshot and return exact-org historical support events."""

    targets = {
        str(org)
        for org in organisation_numbers
        if len(str(org)) == 9 and str(org).isdigit()
    }
    retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    request = urllib.request.Request(POLICY_SUPPORT_SOURCE_URL, headers={"User-Agent": "Signalpost/1.0"})
    opener = opener or urllib.request.build_opener()
    started = time.monotonic()
    try:
        with opener.open(request, timeout=timeout) as response:
            body = response.read(MAX_SNAPSHOT_BYTES + 1)
        if len(body) > MAX_SNAPSHOT_BYTES:
            raise ValueError("Policy-support snapshot exceeds byte ceiling")
        if len(body) != POLICY_SUPPORT_EXPECTED_BYTES:
            raise ValueError(
                f"Policy-support snapshot byte-size mismatch: {len(body)} != {POLICY_SUPPORT_EXPECTED_BYTES}"
            )
        git_blob = hashlib.sha1(b"blob " + str(len(body)).encode("ascii") + b"\0" + body).hexdigest()
        if git_blob != POLICY_SUPPORT_GIT_BLOB:
            raise ValueError("Policy-support snapshot Git blob mismatch")
        snapshot_sha = hashlib.sha256(body).hexdigest()
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".csv") as temporary:
            temporary.write(body)
            temporary.flush()
            events, parse_report = parse_policy_support_snapshot(
                Path(temporary.name),
                targets,
                snapshot_sha256=snapshot_sha,
                retrieved_at=retrieved_at,
                max_events_per_company=max_events_per_company,
            )
        return events, {
            "status": "ok",
            "requests": 1,
            "bytes": len(body),
            "elapsed_ms": int((time.monotonic() - started) * 1000),
            **parse_report,
        }
    except Exception as exc:
        return {}, {
            "status": "source_error",
            "requests": 1,
            "bytes": 0,
            "elapsed_ms": int((time.monotonic() - started) * 1000),
            "companies": 0,
            "events": 0,
            "max_events_per_company": max_events_per_company,
            "source_snapshot_sha256": None,
            "error": f"{type(exc).__name__}: {str(exc)[:300]}",
        }
