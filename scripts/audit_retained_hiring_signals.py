#!/usr/bin/env python3
"""Audit retained exact-site snapshots for explicit current hiring intent.

Research-only, zero-network screen. A candidate is accepted only when:
- the retained website is already exact-entity publishable;
- the hiring statement is in retained company-owned page text;
- language is explicitly recruitment-oriented (e.g. "vi søker", "we are hiring",
  "ledige stillinger", "open positions");
- generic careers/navigation language alone is not enough;
- obvious negative statements such as "ingen ledige stillinger" are rejected.

This screen does not claim a concrete job posting or a dated vacancy. It measures a
narrow company-authored hiring-intent signal that could be projected separately.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable


ACTIVE_PATTERNS: tuple[tuple[str, re.Pattern[str], bool], ...] = (
    ("no_vi_soker", re.compile(r"\bvi\s+s[øo]ker(?:\s+etter)?\b", re.I), True),
    ("no_ledige_stillinger", re.compile(r"\bledige?\s+stillinger?\b", re.I), False),
    ("no_rekrutterer", re.compile(r"\bvi\s+rekrutterer\b", re.I), True),
    ("en_we_are_hiring", re.compile(r"\bwe(?:\s+are|'re|’re)\s+hiring\b", re.I), False),
    ("en_looking_for", re.compile(r"\bwe(?:\s+are|'re|’re)\s+looking\s+for\b", re.I), True),
    ("en_open_positions", re.compile(r"\bopen\s+positions?\b", re.I), False),
    ("en_vacancies", re.compile(r"\bvacanc(?:y|ies)\b", re.I), False),
)

PEOPLE_HINT_RE = re.compile(
    r"\b(?:"
    r"medarbeider(?:e|ne)?|kollega(?:er)?|ansatt(?:e)?|personell|kandidat(?:er)?|"
    r"talent(?:er|fulle)?|team(?:et)?|stilling(?:er)?|jobb(?:er)?|søknad|"
    r"tekniker(?:e)?|mekaniker(?:e)?|ingeniør(?:er)?|utvikler(?:e)?|"
    r"rådgiver(?:e)?|selger(?:e)?|leder(?:e)?|sjåfør(?:er)?|operatør(?:er)?|"
    r"employee(?:s)?|staff|candidate(?:s)?|talent|team|role(?:s)?|job(?:s)?|"
    r"engineer(?:s)?|developer(?:s)?|technician(?:s)?|mechanic(?:s)?|"
    r"manager(?:s)?|consultant(?:s)?|sales|operator(?:s)?"
    r")\b",
    re.I,
)

NEGATIVE_RE = re.compile(
    r"(?:"
    r"ingen\s+ledige?\s+stillinger?|"
    r"har\s+ikke\s+ledige?\s+stillinger?|"
    r"vi\s+s[øo]ker\s+ikke|"
    r"not\s+hiring|"
    r"no\s+open\s+positions?|"
    r"no\s+vacanc(?:y|ies)"
    r")",
    re.I,
)

GENERIC_ONLY_RE = re.compile(
    r"^\s*(?:jobb\s+hos\s+oss|karriere|career(?:s)?|join\s+our\s+team)\s*[.!?]?\s*$",
    re.I,
)


def _org(value: Any) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) != 9:
        raise ValueError(f"invalid organisation number: {value!r}")
    return digits


def iter_profiles(path: Path) -> Iterable[dict[str, Any]]:
    files = sorted(path.rglob("profiles.jsonl"))
    if not files:
        raise ValueError("no profiles.jsonl found")
    seen: set[str] = set()
    for file in files:
        for line in file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            org = _org(row.get("organisation_number"))
            if org in seen:
                raise ValueError(f"duplicate profile org: {org}")
            seen.add(org)
            yield row
    if len(seen) != 1000:
        raise ValueError(f"expected 1000 profiles, got {len(seen)}")


def exact_website(profile: dict[str, Any]) -> dict[str, Any] | None:
    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") if isinstance(website.get("value"), dict) else {}
    assessment = value.get("identity_assessment") if isinstance(value.get("identity_assessment"), dict) else {}
    if website.get("status") != "available" or not assessment.get("publishable"):
        return None
    if len(str(website.get("content_sha256") or "")) != 64:
        return None
    if not str(website.get("retrieved_at") or "").strip():
        return None
    return website


def page_texts(website: dict[str, Any]) -> list[tuple[str, str]]:
    value = website.get("value") or {}
    rows: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add(url: Any, text: Any) -> None:
        clean = str(text or "").strip()
        page_url = str(url or value.get("final_url") or website.get("source_url") or "").strip()
        key = (page_url, clean)
        if clean and key not in seen:
            seen.add(key)
            rows.append(key)

    add(value.get("final_url") or website.get("source_url"), value.get("main_text_excerpt"))
    for page in value.get("pages") or []:
        if isinstance(page, dict):
            add(page.get("url"), page.get("main_text_excerpt"))
    return rows


def hiring_match(text: str) -> dict[str, str] | None:
    if not text or GENERIC_ONLY_RE.fullmatch(text):
        return None
    for kind, pattern, needs_people_hint in ACTIVE_PATTERNS:
        for match in pattern.finditer(text):
            start = max(0, match.start() - 140)
            end = min(len(text), match.end() + 260)
            span = " ".join(text[start:end].split())
            if NEGATIVE_RE.search(span):
                continue
            if needs_people_hint and not PEOPLE_HINT_RE.search(span):
                continue
            return {
                "match_type": kind,
                "evidence_span": span[:500],
            }
    return None


def current_hiring_orgs(path: Path) -> set[str]:
    fields = {
        "external.hiring_signal",
        "external.job_posting",
        "hiring_signal",
        "active_job",
        "job_posting",
    }
    out: set[str] = set()
    seen: set[str] = set()
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            org = _org(row.get("organisation_number"))
            if org in seen:
                raise ValueError(f"duplicate output org: {org}")
            seen.add(org)
            if any(
                isinstance(claim, dict)
                and claim.get("field") in fields
                and claim.get("availability") == "available"
                for claim in row.get("claims") or []
            ):
                out.add(org)
    if len(seen) != 1000:
        raise ValueError(f"expected 1000 output companies, got {len(seen)}")
    return out


def audit(profiles_dir: Path, output_contract_gz: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    existing = current_hiring_orgs(output_contract_gz)
    candidates: list[dict[str, Any]] = []
    exact_sites = 0

    for profile in iter_profiles(profiles_dir):
        website = exact_website(profile)
        if website is None:
            continue
        exact_sites += 1
        org = _org(profile.get("organisation_number"))
        if org in existing:
            continue
        for page_url, text in page_texts(website):
            match = hiring_match(text)
            if not match:
                continue
            span = match["evidence_span"]
            candidates.append(
                {
                    "organisation_number": org,
                    "name": str(profile.get("name") or ""),
                    "match_type": match["match_type"],
                    "source_url": page_url,
                    "retrieved_at": website.get("retrieved_at"),
                    "content_sha256": website.get("content_sha256"),
                    "evidence_span": span,
                    "evidence_span_sha256": hashlib.sha256(span.encode("utf-8")).hexdigest(),
                }
            )
            break

    report = {
        "screen_type": "retained_exact_site_explicit_hiring_intent_audit",
        "companies": 1000,
        "exact_verified_website_companies": exact_sites,
        "existing_hiring_signal_companies": len(existing),
        "net_new_explicit_hiring_intent_companies": len(candidates),
        "net_new_hiring_reach": round(len(candidates) / 1000, 6),
        "logical_network_requests_added": 0,
        "third_party_cost_usd_added": 0.0,
        "search_api_requests_added": 0,
        "production_publication_enabled": False,
        "notes": [
            "Generic careers/navigation text alone is excluded.",
            "This is company-authored hiring intent, not a claim that a specific vacancy is open.",
            "Only retained pages whose website identity gate was already publishable are scanned.",
        ],
    }
    return report, candidates


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles-dir", type=Path, required=True)
    ap.add_argument("--output-contract-gz", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()

    report, candidates = audit(args.profiles_dir, args.output_contract_gz)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (args.output_dir / "candidates.jsonl").open("w", encoding="utf-8") as handle:
        for row in candidates:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
