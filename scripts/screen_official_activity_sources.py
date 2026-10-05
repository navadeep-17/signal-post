#!/usr/bin/env python3
"""Isolated source-screen harness for Patentstyret and Doffin.

This module is intentionally NOT imported by any production runner. It exists to
measure source suitability on already-consumed cohorts before any production
wiring is considered.

Live mode is opt-in and requires explicit environment configuration:
- PATENTSTYRET_API_URL: full URL template containing ``{orgnr}``
- PATENTSTYRET_API_KEY: Azure APIM subscription key
- DOFFIN_API_KEY: Doffin public API subscription key

The parsers are conservative: an external record is accepted only when an exact
9-digit Norwegian organisation number equal to the target can be found in the
record (or, for Patentstyret portfolio responses, when the endpoint response is
queried directly by that exact organisation number and no conflicting orgnr is
present).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

ORG_RE = re.compile(r"(?<!\d)(\d{9})(?!\d)")


def normalize_orgnr(value: str) -> str:
    digits = re.sub(r"\D", "", str(value))
    if len(digits) != 9:
        raise ValueError(f"expected 9-digit organisation number, got {value!r}")
    return digits


def _iter_scalars(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for child in value.values():
            yield from _iter_scalars(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_scalars(child)
    elif value is not None:
        yield str(value)


def organisation_numbers_in_json(value: Any) -> set[str]:
    found: set[str] = set()
    for scalar in _iter_scalars(value):
        found.update(ORG_RE.findall(scalar))
    return found


def _case_like_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        keys = {str(k).lower() for k in value}
        if {"applicationnumber", "caseurl", "registrationnumber"} & keys:
            yield value
        for child in value.values():
            yield from _case_like_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _case_like_dicts(child)


def extract_patentstyret_cases(payload: Any, target_orgnr: str) -> list[dict[str, Any]]:
    """Return conservative portfolio case summaries for one exact target orgnr."""
    target = normalize_orgnr(target_orgnr)
    response_orgs = organisation_numbers_in_json(payload)
    conflicting = bool(response_orgs and target not in response_orgs)
    if conflicting:
        return []

    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for case in _case_like_dicts(payload):
        case_orgs = organisation_numbers_in_json(case)
        if case_orgs and target not in case_orgs:
            continue
        app = case.get("applicationNumber") or case.get("ApplicationNumber")
        reg = case.get("registrationNumber") or case.get("RegistrationNumber")
        url = case.get("caseUrl") or case.get("CaseUrl")
        category = (
            case.get("ipRightType")
            or case.get("caseType")
            or case.get("category")
            or case.get("type")
        )
        status = case.get("status") or case.get("currentStatus")
        date = (
            case.get("applicationDate")
            or case.get("registrationDate")
            or case.get("statusDate")
            or case.get("publicationDate")
        )
        key = json.dumps([app, reg, url, category, date], ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "organisation_number": target,
                "application_number": app,
                "registration_number": reg,
                "case_url": url,
                "category": category,
                "status": status,
                "event_date": date,
            }
        )
    return out


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text_orgs(element: ET.Element) -> set[str]:
    found: set[str] = set()
    for node in element.iter():
        if node.text:
            found.update(ORG_RE.findall(node.text))
        for value in node.attrib.values():
            found.update(ORG_RE.findall(value))
    return found


def extract_doffin_exact_supplier_hits(xml_bytes: bytes, target_orgnr: str) -> list[dict[str, Any]]:
    """Find exact-org supplier/tenderer appearances in one eForms UBL notice.

    This is a source-screen parser only. It deliberately does not infer that a
    generic Party node is a winning supplier. Only supplier/tenderer/contractor
    scoped elements are considered.
    """
    target = normalize_orgnr(target_orgnr)
    root = ET.fromstring(xml_bytes)
    supplier_scopes = {
        "TendererParty",
        "TenderingParty",
        "ContractorParty",
        "EconomicOperatorParty",
        "Winner",
        "WinningParty",
    }
    hits: list[dict[str, Any]] = []
    seen_paths: set[tuple[str, str]] = set()

    notice_id = None
    issue_date = None
    for node in root.iter():
        name = _local(node.tag)
        if notice_id is None and name in {"ID", "NoticeID"} and node.text:
            notice_id = node.text.strip()
        if issue_date is None and name in {"IssueDate", "PublicationDate"} and node.text:
            issue_date = node.text.strip()

    for node in root.iter():
        scope = _local(node.tag)
        if scope not in supplier_scopes:
            continue
        orgs = _text_orgs(node)
        if target not in orgs:
            continue
        key = (scope, notice_id or "")
        if key in seen_paths:
            continue
        seen_paths.add(key)
        hits.append(
            {
                "organisation_number": target,
                "scope": scope,
                "notice_id": notice_id,
                "publication_date": issue_date,
            }
        )
    return hits


@dataclass
class ScreenResult:
    source: str
    organisation_number: str
    exact_identity: bool
    records: int
    response_sha256: str
    error: str | None = None


def _get(url: str, api_key: str, timeout: float = 20.0) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json, application/xml, text/xml;q=0.9, */*;q=0.1",
            "User-Agent": "Signalpost-source-screen/1.0",
            "Ocp-Apim-Subscription-Key": api_key,
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def live_patentstyret(orgnr: str) -> ScreenResult:
    target = normalize_orgnr(orgnr)
    template = os.environ.get("PATENTSTYRET_API_URL")
    key = os.environ.get("PATENTSTYRET_API_KEY")
    if not template or "{orgnr}" not in template:
        raise RuntimeError("PATENTSTYRET_API_URL must be set and contain {orgnr}")
    if not key:
        raise RuntimeError("PATENTSTYRET_API_KEY is not set")
    url = template.format(orgnr=urllib.parse.quote(target))
    body = _get(url, key)
    payload = json.loads(body)
    cases = extract_patentstyret_cases(payload, target)
    return ScreenResult(
        source="patentstyret",
        organisation_number=target,
        exact_identity=bool(cases),
        records=len(cases),
        response_sha256=hashlib.sha256(body).hexdigest(),
    )


def fixture_mode(source: str, orgnr: str, path: Path) -> ScreenResult:
    target = normalize_orgnr(orgnr)
    body = path.read_bytes()
    if source == "patentstyret":
        records = extract_patentstyret_cases(json.loads(body), target)
    elif source == "doffin":
        records = extract_doffin_exact_supplier_hits(body, target)
    else:
        raise ValueError(source)
    return ScreenResult(
        source=source,
        organisation_number=target,
        exact_identity=bool(records),
        records=len(records),
        response_sha256=hashlib.sha256(body).hexdigest(),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", choices=["patentstyret", "doffin"])
    parser.add_argument("orgnr")
    parser.add_argument("--fixture", type=Path)
    args = parser.parse_args(argv)

    try:
        if args.fixture:
            result = fixture_mode(args.source, args.orgnr, args.fixture)
        elif args.source == "patentstyret":
            result = live_patentstyret(args.orgnr)
        else:
            raise RuntimeError(
                "Doffin live screen is intentionally not enabled yet: its search API is notice-oriented, "
                "not an exact supplier-org lookup. Enabling it before proving a bounded query plan would risk "
                "the production request budget. Use downloaded eForms XML fixtures for exact-supplier screening."
            )
    except Exception as exc:
        print(json.dumps({"source": args.source, "organisation_number": args.orgnr, "error": str(exc)}))
        return 2

    print(json.dumps(asdict(result), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
