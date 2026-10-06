#!/usr/bin/env python3
"""Measure zero-extra-request Wikidata online-account candidate coverage.

Research only. Uses the same exact Norwegian organisation-number property
(P2333) already used by production website discovery, but asks the same batch
lookup for additional organization/account identifiers.

No production claims are emitted and no raw account identifiers are persisted.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "signal-post/0.1 (+https://github.com/navadeep-17/signal-post)"
ORG_RE = re.compile(r"^\d{9}$")
PROPS = {
    "x": "P2002",
    "instagram": "P2003",
    "facebook": "P2013",
    "youtube": "P2397",
    "linkedin": "P4264",
}
MAX_BYTES = 2_000_000


def norm_org(value: Any) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if not ORG_RE.fullmatch(digits):
        raise ValueError(f"invalid organisation number: {value!r}")
    return digits


def read_orgs(path: Path) -> list[str]:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    orgs = [norm_org(row.get("organisation_number")) for row in rows]
    if len(orgs) != len(set(orgs)):
        raise ValueError("duplicate organisation numbers")
    return orgs


def baseline_social_orgs(path: Path) -> set[str]:
    out: set[str] = set()
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            org = norm_org(row.get("organisation_number"))
            facts = row.get("canonical_facts") or []
            if any(
                isinstance(fact, dict)
                and fact.get("type") == "social_profile"
                and fact.get("availability") == "available"
                for fact in facts
            ):
                out.add(org)
    return out


def sparql(orgs: list[str]) -> str:
    values = " ".join(json.dumps(x) for x in orgs)
    optional = " ".join(
        f"OPTIONAL {{ ?item wdt:{prop} ?{name} . }}"
        for name, prop in PROPS.items()
    )
    return (
        "SELECT ?org ?item "
        + " ".join(f"?{name}" for name in PROPS)
        + " WHERE { "
        + f"VALUES ?org {{ {values} }} "
        + "?item wdt:P2333 ?org . "
        + optional
        + " }"
    )


def query_batch(orgs: list[str], timeout: float) -> tuple[list[dict[str, Any]], int]:
    query = sparql(orgs)
    url = ENDPOINT + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/sparql-results+json",
            "Accept-Encoding": "identity",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise RuntimeError("Wikidata batch response exceeded byte limit")
    payload = json.loads(raw.decode("utf-8"))
    bindings = ((payload.get("results") or {}).get("bindings") or [])
    return [x for x in bindings if isinstance(x, dict)], len(raw)


def scan(orgs: list[str], *, batch_size: int = 100, timeout: float = 12.0) -> dict[str, Any]:
    if not 1 <= batch_size <= 100:
        raise ValueError("batch_size must be in [1, 100]")
    state: dict[str, dict[str, Any]] = {
        org: {"items": set(), **{name: set() for name in PROPS}}
        for org in orgs
    }
    requests = 0
    total_bytes = 0
    errors: list[str] = []

    for start in range(0, len(orgs), batch_size):
        chunk = orgs[start : start + batch_size]
        requests += 1
        try:
            rows, nbytes = query_batch(chunk, timeout)
            total_bytes += nbytes
        except urllib.error.HTTPError as exc:
            errors.append(f"batch {start//batch_size}: HTTP {exc.code}")
            continue
        except Exception as exc:
            errors.append(f"batch {start//batch_size}: {type(exc).__name__}: {str(exc)[:160]}")
            continue
        for binding in rows:
            org = str(((binding.get("org") or {}).get("value") or ""))
            if org not in state:
                continue
            item = str(((binding.get("item") or {}).get("value") or ""))
            if item:
                state[org]["items"].add(item)
            for name in PROPS:
                value = str(((binding.get(name) or {}).get("value") or ""))
                if value:
                    state[org][name].add(value)
        time.sleep(0.15)

    exact_item_orgs: set[str] = set()
    ambiguous_orgs: set[str] = set()
    any_social: set[str] = set()
    platform_orgs = {name: set() for name in PROPS}
    multi_value_orgs = {name: set() for name in PROPS}

    for org, row in state.items():
        items = row["items"]
        if len(items) == 1:
            exact_item_orgs.add(org)
        elif items:
            ambiguous_orgs.add(org)
            continue
        else:
            continue
        for name in PROPS:
            values = row[name]
            if values:
                platform_orgs[name].add(org)
                any_social.add(org)
            if len(values) > 1:
                multi_value_orgs[name].add(org)

    return {
        "companies": len(orgs),
        "requests": requests,
        "bytes": total_bytes,
        "errors": errors,
        "exact_single_item_companies": len(exact_item_orgs),
        "ambiguous_item_companies": len(ambiguous_orgs),
        "any_social_candidate_companies": len(any_social),
        "platform_candidate_companies": {
            name: len(values) for name, values in platform_orgs.items()
        },
        "platform_multi_value_companies": {
            name: len(values) for name, values in multi_value_orgs.items()
        },
        "_any_social_orgs": any_social,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--companies", required=True, type=Path)
    ap.add_argument("--baseline-output", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--batch-size", type=int, default=100)
    ap.add_argument("--timeout", type=float, default=12.0)
    args = ap.parse_args()

    orgs = read_orgs(args.companies)
    baseline = baseline_social_orgs(args.baseline_output)
    result = scan(orgs, batch_size=args.batch_size, timeout=args.timeout)
    candidates = result.pop("_any_social_orgs")
    net_new = candidates - baseline

    report = {
        **result,
        "baseline_social_profile_companies": len(baseline),
        "candidate_overlap_baseline_social": len(candidates & baseline),
        "net_new_social_candidate_companies": len(net_new),
        "net_new_social_candidate_reach": round(len(net_new) / len(orgs), 6),
        "theoretical_requests_same_as_existing_wikidata_lookup": math.ceil(len(orgs) / args.batch_size),
        "production_request_delta_if_folded_into_existing_wikidata_query": 0,
        "production_publication_enabled": False,
        "publication_boundary": (
            "candidate coverage only; existing Signalpost first-party social publication "
            "gate is unchanged"
        ),
        "properties": {"organisation_number": "P2333", **PROPS},
        "raw_account_identifiers_retained": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not report["errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
