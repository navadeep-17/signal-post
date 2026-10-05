from __future__ import annotations

import csv
import hashlib
import json
import re
import tempfile
import time
import unicodedata
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SUPPORT_REGISTRY_URL = "https://stotte.brreg.no/nb/oppslag/stoettetildeling/totalbestand/csv"
SUPPORT_REGISTRY_RIGHTS = "NLOD"
MAX_SNAPSHOT_BYTES = 400_000_000
ORG_RE = re.compile(r"(?<!\d)(?:NO\s*)?(\d{3})[\s.\-]?(\d{3})[\s.\-]?(\d{3})(?!\d)", re.I)


def _normalize_header(value: str) -> str:
    value = value.casefold().replace("ø", "o").replace("æ", "ae").replace("å", "a")
    value = "".join(
        char for char in unicodedata.normalize("NFKD", value) if not unicodedata.combining(char)
    )
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def _valid_org_number(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    if len(digits) != 9:
        return False
    nums = [int(ch) for ch in digits]
    weighted = sum(n * w for n, w in zip(nums[:8], (3, 2, 7, 6, 5, 4, 3, 2), strict=True))
    remainder = 11 - (weighted % 11)
    check = 0 if remainder == 11 else remainder
    return check != 10 and check == nums[8]


def _extract_org_numbers(value: Any) -> set[str]:
    found: set[str] = set()
    for match in ORG_RE.finditer(str(value or "")):
        candidate = "".join(match.groups())
        if _valid_org_number(candidate):
            found.add(candidate)
    return found


def _primary_recipient_org_header(headers: list[str]) -> str | None:
    """Return the direct/primary recipient organisation-number column only.

    Støtteregisteret also exposes a ``Spesifisert mottaker`` field.  That field is
    retained as row context but must never independently establish company identity.
    """

    for header in headers:
        normalized = _normalize_header(header)
        if (
            "organisasjonsnummer" in normalized
            and "mottaker" in normalized
            and "giver" not in normalized
            and "spesifisert" not in normalized
        ):
            return header
    return None


def _specified_recipient_org_header(headers: list[str]) -> str | None:
    for header in headers:
        normalized = _normalize_header(header)
        if (
            "organisasjonsnummer" in normalized
            and "mottaker" in normalized
            and "spesifisert" in normalized
            and "giver" not in normalized
        ):
            return header
    return None


def _header(headers: list[str], *markers: str, excluded: tuple[str, ...] = ()) -> str | None:
    for header in headers:
        normalized = _normalize_header(header)
        if all(marker in normalized for marker in markers) and not any(marker in normalized for marker in excluded):
            return header
    return None


def _parse_date(value: Any) -> date | None:
    raw = " ".join(str(value or "").split())
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw[:10], fmt).date()
        except ValueError:
            continue
    return None


def _parse_amount(value: Any) -> Decimal | None:
    raw = "".join(str(value or "").split()).replace("\u00a0", "")
    if not raw:
        return None
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".") if raw.rfind(",") > raw.rfind(".") else raw.replace(",", "")
    elif "," in raw:
        raw = raw.replace(",", ".")
    raw = re.sub(r"[^0-9.\-]", "", raw)
    try:
        return Decimal(raw) if raw else None
    except InvalidOperation:
        return None


def _encoding(path: Path) -> str:
    prefix = path.read_bytes()[:4]
    if prefix.startswith(b"\xff\xfe"):
        return "utf-16"
    if prefix.startswith(b"\xfe\xff"):
        return "utf-16"
    if len(prefix) >= 2 and prefix[1:2] == b"\x00":
        return "utf-16-le"
    return "utf-8-sig"


def _dialect(path: Path, encoding: str) -> csv.Dialect:
    with path.open("r", encoding=encoding, errors="strict", newline="") as handle:
        sample = handle.read(65536)
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        return csv.excel


def _row_hash(row: dict[str, Any]) -> str:
    body = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _observation_id(org: str, row_sha: str, award_date: str) -> str:
    material = f"{org}|{award_date}|{row_sha}"
    return "support-award-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def parse_support_award_snapshot(
    path: Path,
    target_orgs: set[str],
    *,
    snapshot_sha256: str,
    retrieved_at: str,
    as_of: date,
    lookback_days: int = 365,
    max_events_per_company: int = 5,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Parse recent exact-recipient support awards from one official snapshot."""

    if lookback_days < 1 or max_events_per_company < 1:
        raise ValueError("lookback_days and max_events_per_company must be positive")
    cutoff = as_of - timedelta(days=lookback_days)
    encoding = _encoding(path)
    dialect = _dialect(path, encoding)
    candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    rows_scanned = 0

    with path.open("r", encoding=encoding, errors="strict", newline="") as handle:
        reader = csv.DictReader(handle, dialect=dialect)
        headers = [header for header in (reader.fieldnames or []) if header]
        recipient_header = _primary_recipient_org_header(headers)
        specified_recipient_header = _specified_recipient_org_header(headers)
        date_header = _header(headers, "tildelingsdato")
        amount_header = _header(headers, "tildelt", "belop", excluded=("valuta",))
        currency_header = _header(headers, "tildelt", "belop", "valuta")
        interval_from_header = _header(headers, "belopsintervall", "fra", "belop")
        interval_to_header = _header(headers, "belopsintervall", "til", "belop")
        interval_currency_header = _header(headers, "belopsintervall", "valuta")
        status_header = _header(headers, "status")
        measure_header = _header(headers, "stottetiltaksnummer")
        type_header = _header(headers, "stottetiltakstype")
        recipient_name_header = _header(headers, "navn", "stottemottaker", excluded=("spesifisert",))
        giver_org_header = _header(headers, "organisasjonsnummer", "stottegiver")
        giver_name_header = _header(headers, "navn", "stottegiver")
        if not recipient_header or not date_header or not amount_header:
            raise ValueError("Støtteregisteret export is missing required primary-recipient/date/amount columns")

        for row_number, row in enumerate(reader, start=2):
            rows_scanned += 1
            recipient_orgs = _extract_org_numbers(row.get(recipient_header))
            hits = recipient_orgs.intersection(target_orgs)
            if not hits:
                continue
            award_date = _parse_date(row.get(date_header))
            if award_date is None or award_date > as_of or award_date < cutoff:
                continue
            amount = _parse_amount(row.get(amount_header))
            amount_currency = " ".join(str(row.get(currency_header) or "").split()) if currency_header else ""
            interval_from = _parse_amount(row.get(interval_from_header)) if interval_from_header else None
            interval_to = _parse_amount(row.get(interval_to_header)) if interval_to_header else None
            interval_currency = (
                " ".join(str(row.get(interval_currency_header) or "").split())
                if interval_currency_header
                else ""
            )
            row_sha = _row_hash(row)
            status = " ".join(str(row.get(status_header) or "").split()) if status_header else ""
            measure_number = " ".join(str(row.get(measure_header) or "").split()) if measure_header else ""
            recipient_name = " ".join(str(row.get(recipient_name_header) or "").split()) if recipient_name_header else ""
            giver_org = " ".join(str(row.get(giver_org_header) or "").split()) if giver_org_header else ""
            giver_name = " ".join(str(row.get(giver_name_header) or "").split()) if giver_name_header else ""
            support_type = " ".join(str(row.get(type_header) or "").split()) if type_header else ""
            amount_raw = " ".join(str(row.get(amount_header) or "").split())
            interval_from_raw = (
                " ".join(str(row.get(interval_from_header) or "").split())
                if interval_from_header
                else ""
            )
            interval_to_raw = (
                " ".join(str(row.get(interval_to_header) or "").split())
                if interval_to_header
                else ""
            )
            specified_orgs = (
                sorted(_extract_org_numbers(row.get(specified_recipient_header)))
                if specified_recipient_header
                else []
            )
            specified_recipient_org = specified_orgs[0] if len(specified_orgs) == 1 else None
            for org in sorted(hits):
                span = "; ".join(
                    part
                    for part in (
                        f"recipient org: {org}",
                        f"recipient: {recipient_name}" if recipient_name else "",
                        (
                            f"specified recipient org (context only): {specified_recipient_org}"
                            if specified_recipient_org
                            else ""
                        ),
                        f"award date: {row.get(date_header)}",
                        (
                            f"awarded amount: {amount_raw} {amount_currency}".strip()
                            if amount_raw
                            else ""
                        ),
                        (
                            f"awarded amount interval: {interval_from_raw or '?'}..{interval_to_raw or '?'} {interval_currency}".strip()
                            if interval_from_raw or interval_to_raw
                            else ""
                        ),
                        f"support measure: {measure_number}" if measure_number else "",
                        f"support type: {support_type}" if support_type else "",
                        f"granting authority org: {giver_org}" if giver_org else "",
                        f"granting authority: {giver_name}" if giver_name else "",
                        f"status: {status}" if status else "",
                    )
                    if part
                )[:1600]
                candidates[org].append(
                    {
                        "id": _observation_id(org, row_sha, award_date.isoformat()),
                        "organisation_number": org,
                        "platform": "brreg",
                        "signal_type": "official_support_award",
                        "source_class": "official_support_registry",
                        "source_url": SUPPORT_REGISTRY_URL,
                        "retrieved_at": retrieved_at,
                        "content_sha256": row_sha,
                        "source_snapshot_sha256": snapshot_sha256,
                        "source_row_number": row_number,
                        "source_row_key": measure_number or f"row-{row_number}",
                        "exact_entity": True,
                        "identity_proof": f"Støtteregisteret primary recipient organisation number equals target {org}",
                        "acquisition_mode": "official_dataset",
                        "rights_status": "approved",
                        "rights_basis": SUPPORT_REGISTRY_RIGHTS,
                        "evidence_span": span,
                        "effective_at": award_date.isoformat(),
                        "event": {
                            "kind": "support_award",
                            "awarded_at": award_date.isoformat(),
                            "amount": str(amount) if amount is not None else None,
                            "currency": amount_currency or None,
                            "amount_interval_from": str(interval_from) if interval_from is not None else None,
                            "amount_interval_to": str(interval_to) if interval_to is not None else None,
                            "amount_interval_currency": interval_currency or None,
                            "support_measure_number": measure_number or None,
                            "support_measure_type": support_type or None,
                            "recipient_name": recipient_name or None,
                            "specified_recipient_organisation_number": specified_recipient_org,
                            "granting_authority_org": giver_org or None,
                            "granting_authority_name": giver_name or None,
                            "status": status or None,
                        },
                    }
                )

    selected: dict[str, list[dict[str, Any]]] = {}
    for org, rows in candidates.items():
        rows.sort(key=lambda item: (str(item.get("effective_at") or ""), str(item.get("id") or "")), reverse=True)
        selected[org] = rows[:max_events_per_company]
    return selected, {
        "rows_scanned": rows_scanned,
        "companies_with_recent_awards": len(selected),
        "observations": sum(len(rows) for rows in selected.values()),
        "lookback_days": lookback_days,
        "max_events_per_company": max_events_per_company,
        "source_snapshot_sha256": snapshot_sha256,
    }


def attach_support_award_observations(
    profiles: list[dict[str, Any]],
    observations: dict[str, list[dict[str, Any]]],
) -> None:
    for profile in profiles:
        org = str(profile.get("organisation_number") or "")
        current = [item for item in (profile.get("external_observations") or []) if isinstance(item, dict)]
        current = [item for item in current if item.get("signal_type") != "official_support_award"]
        current.extend(observations.get(org, []))
        profile["external_observations"] = current


def fetch_support_award_batch(
    profiles: list[dict[str, Any]],
    *,
    timeout: float = 420.0,
    as_of: date | None = None,
    lookback_days: int = 365,
    max_events_per_company: int = 5,
    opener: Any = None,
) -> dict[str, Any]:
    """Fetch one shared official snapshot and attach exact-recipient recent awards.

    Source failure is non-fatal: the caller receives an auditable error report and profiles
    remain otherwise unchanged, preserving terminal-envelope semantics.
    """

    target_orgs = {str(profile.get("organisation_number") or "") for profile in profiles}
    target_orgs = {org for org in target_orgs if len(org) == 9 and org.isdigit()}
    retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    as_of = as_of or datetime.now(timezone.utc).date()
    request = urllib.request.Request(SUPPORT_REGISTRY_URL, headers={"User-Agent": "Signalpost/1.0"})
    opener = opener or urllib.request.build_opener()
    started = time.monotonic()
    digest = hashlib.sha256()
    bytes_received = 0

    try:
        with tempfile.NamedTemporaryFile(suffix=".csv") as temporary:
            with opener.open(request, timeout=timeout) as response:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    bytes_received += len(chunk)
                    if bytes_received > MAX_SNAPSHOT_BYTES:
                        raise ValueError("Støtteregisteret snapshot exceeds configured byte ceiling")
                    digest.update(chunk)
                    temporary.write(chunk)
            temporary.flush()
            observations, parse_report = parse_support_award_snapshot(
                Path(temporary.name),
                target_orgs,
                snapshot_sha256=digest.hexdigest(),
                retrieved_at=retrieved_at,
                as_of=as_of,
                lookback_days=lookback_days,
                max_events_per_company=max_events_per_company,
            )
        attach_support_award_observations(profiles, observations)
        return {
            "status": "available",
            "requests": 1,
            "bytes": bytes_received,
            "elapsed_ms": round((time.monotonic() - started) * 1000),
            "error": None,
            **parse_report,
        }
    except (OSError, ValueError, csv.Error, urllib.error.URLError) as exc:
        return {
            "status": "source_error",
            "requests": 1,
            "bytes": bytes_received,
            "elapsed_ms": round((time.monotonic() - started) * 1000),
            "error": f"{type(exc).__name__}: {exc}",
            "companies_with_recent_awards": 0,
            "observations": 0,
            "lookback_days": lookback_days,
            "max_events_per_company": max_events_per_company,
        }
