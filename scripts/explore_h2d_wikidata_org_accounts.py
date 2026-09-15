#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

"""Explore additional account identifiers only on exact P2333-matched organisation items."""

WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
WIKIDATA_BATCH_SIZE = 100
WIKIDATA_MAX_RESPONSE_BYTES = 1_000_000
WIKIDATA_USER_AGENT = "signal-post/0.1 (+https://github.com/navadeep-17/signal-post)"

ACCOUNT_PROPERTIES = {
    "x": "P2002",
    "instagram": "P2003",
    "facebook": "P2013",
    "youtube": "P2397",
    "tiktok": "P7085",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _normalise_org(value: Any) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) != 9:
        raise ValueError(f"Invalid Norwegian organisation number: {value!r}")
    return digits


def _chunks(values: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]


def _query(orgs: list[str]) -> str:
    organisations = " ".join(json.dumps(org) for org in orgs)
    property_rows = " ".join(
        f"({json.dumps(platform)} wdt:{property_id})"
        for platform, property_id in ACCOUNT_PROPERTIES.items()
    )
    return (
        "SELECT ?org ?item ?platform ?identifier WHERE { "
        f"VALUES ?org {{ {organisations} }} "
        "?item wdt:P2333 ?org . "
        f"VALUES (?platform ?property) {{ {property_rows} }} "
        "?item ?property ?identifier . "
        "}"
    )


def _decode(raw: bytes, encoding: str) -> bytes:
    lowered = str(encoding or "").casefold()
    if "gzip" in lowered:
        return gzip.decompress(raw)
    if "deflate" in lowered:
        try:
            return zlib.decompress(raw)
        except zlib.error:
            return zlib.decompress(raw, -zlib.MAX_WBITS)
    return raw


def _safe_identifier(platform: str, value: str) -> str | None:
    identifier = str(value or "").strip()
    if not identifier or len(identifier) > 200:
        return None
    if any(character.isspace() for character in identifier):
        return None
    if any(character in identifier for character in "/?#\\"):
        return None
    if platform == "youtube":
        return identifier if re.fullmatch(r"UC[A-Za-z0-9_-]{20,30}", identifier) else None
    if platform == "tiktok":
        return identifier if re.fullmatch(r"[A-Za-z0-9_.]{2,40}", identifier) else None
    if platform in {"x", "instagram"}:
        return identifier if re.fullmatch(r"[A-Za-z0-9_.]{1,100}", identifier) else None
    if platform == "facebook":
        return identifier if re.fullmatch(r"[A-Za-z0-9_.-]{1,120}", identifier) else None
    return None


def _profile_url(platform: str, identifier: str) -> str | None:
    safe = _safe_identifier(platform, identifier)
    if safe is None:
        return None
    encoded = urllib.parse.quote(safe, safe="._-")
    if platform == "x":
        return f"https://x.com/{encoded}"
    if platform == "instagram":
        return f"https://www.instagram.com/{encoded}/"
    if platform == "facebook":
        return f"https://www.facebook.com/{encoded}/"
    if platform == "youtube":
        return f"https://www.youtube.com/channel/{encoded}"
    if platform == "tiktok":
        return f"https://www.tiktok.com/@{encoded}"
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Screen exact-P2333 Wikidata organisation items for additional social-account identifiers."
    )
    parser.add_argument("--organisations", required=True, help="Fresh JSONL company cohort")
    parser.add_argument("--report", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--expected-count", type=int, default=300)
    args = parser.parse_args()

    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.expected_count < 1:
        parser.error("--expected-count must be positive")

    rows = read_jsonl(Path(args.organisations))
    if len(rows) != args.expected_count:
        raise SystemExit(f"Expected {args.expected_count} organisations, found {len(rows)}")
    orgs = [_normalise_org(row.get("organisation_number")) for row in rows]
    if len(orgs) != len(set(orgs)):
        raise SystemExit("Duplicate organisation numbers in cohort")
    names = {str(row.get("organisation_number")): str(row.get("name") or "") for row in rows}

    collected: dict[str, dict[str, Any]] = {
        org: {"items": set(), "identifiers": defaultdict(set)} for org in orgs
    }
    metrics: dict[str, Any] = {
        "requests": 0,
        "batches": 0,
        "bytes": 0,
        "latencies_ms": [],
        "errors": [],
    }

    for chunk in _chunks(orgs, WIKIDATA_BATCH_SIZE):
        query = _query(chunk)
        url = WIKIDATA_SPARQL_URL + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": WIKIDATA_USER_AGENT,
                "Accept": "application/sparql-results+json",
                "Accept-Encoding": "gzip,deflate",
            },
        )
        metrics["requests"] += 1
        metrics["batches"] += 1
        started = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=args.timeout) as response:
                raw = response.read(WIKIDATA_MAX_RESPONSE_BYTES + 1)
                headers = getattr(response, "headers", {})
                encoding = headers.get("content-encoding", "") if hasattr(headers, "get") else ""
            metrics["latencies_ms"].append(int((time.monotonic() - started) * 1000))
            metrics["bytes"] += len(raw)
            if len(raw) > WIKIDATA_MAX_RESPONSE_BYTES:
                metrics["errors"].append("Wikidata account response exceeded byte limit")
                continue
            raw_sha256 = hashlib.sha256(raw).hexdigest()
            payload = json.loads(_decode(raw, str(encoding)).decode("utf-8"))
        except urllib.error.HTTPError as exc:
            metrics["latencies_ms"].append(int((time.monotonic() - started) * 1000))
            metrics["errors"].append(f"HTTP {exc.code}")
            continue
        except Exception as exc:
            metrics["latencies_ms"].append(int((time.monotonic() - started) * 1000))
            metrics["errors"].append(f"{type(exc).__name__}: {str(exc)[:180]}")
            continue

        bindings = ((payload.get("results") or {}).get("bindings") or []) if isinstance(payload, dict) else []
        for binding in bindings:
            if not isinstance(binding, dict):
                continue
            org = str(((binding.get("org") or {}).get("value") or "")).strip()
            if org not in collected:
                continue
            item = str(((binding.get("item") or {}).get("value") or "")).strip()
            platform = str(((binding.get("platform") or {}).get("value") or "")).strip()
            identifier = str(((binding.get("identifier") or {}).get("value") or "")).strip()
            if not item or platform not in ACCOUNT_PROPERTIES:
                continue
            collected[org]["items"].add(item)
            if _profile_url(platform, identifier):
                collected[org]["identifiers"][platform].add(identifier)
                collected[org]["response_sha256"] = raw_sha256

    audit_rows: list[dict[str, Any]] = []
    ambiguous_item_orgs = 0
    ambiguous_platform_values = 0
    per_platform: dict[str, int] = defaultdict(int)
    candidate_orgs: set[str] = set()

    for org, values in collected.items():
        items = sorted(values["items"])
        if len(items) > 1:
            ambiguous_item_orgs += 1
            continue
        if len(items) != 1:
            continue
        for platform, identifiers in sorted(values["identifiers"].items()):
            if len(identifiers) > 1:
                ambiguous_platform_values += 1
                continue
            if len(identifiers) != 1:
                continue
            identifier = next(iter(identifiers))
            profile_url = _profile_url(platform, identifier)
            if not profile_url:
                continue
            candidate_orgs.add(org)
            per_platform[platform] += 1
            audit_rows.append(
                {
                    "organisation_number": org,
                    "company_name": names.get(org),
                    "wikidata_item": items[0],
                    "platform": platform,
                    "property_id": ACCOUNT_PROPERTIES[platform],
                    "identifier": identifier,
                    "profile_url": profile_url,
                    "response_sha256": values.get("response_sha256"),
                    "candidate_only": True,
                    "claim_scope": (
                        "Exact P2333-matched Wikidata organisation item declares this account identifier; "
                        "the platform page has not been independently fetched or verified."
                    ),
                }
            )

    report = {
        "experiment": "h2d_wikidata_exact_org_account_screen",
        "expected_count": args.expected_count,
        "properties": ACCOUNT_PROPERTIES,
        "candidate_companies": len(candidate_orgs),
        "candidate_company_rate": round(len(candidate_orgs) / args.expected_count, 6),
        "candidate_identifiers": len(audit_rows),
        "platform_counts": dict(sorted(per_platform.items())),
        "ambiguous_item_organisations": ambiguous_item_orgs,
        "ambiguous_platform_values": ambiguous_platform_values,
        "requests": metrics["requests"],
        "batches": metrics["batches"],
        "bytes": metrics["bytes"],
        "errors": metrics["errors"],
        "third_party_cost_usd": 0.0,
        "prospective_added_production_requests_if_folded_into_existing_h1e_batch": 0,
        "audit_rows": len(audit_rows),
        "passed": not metrics["errors"] and metrics["requests"] <= 3,
        "decision_rule": (
            "This is a recall screen only. Do not publish these candidates without a separate fresh qualification "
            "and manual identity/currentness audit."
        ),
    }

    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_jsonl(Path(args.audit), audit_rows)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
