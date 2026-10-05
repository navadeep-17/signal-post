#!/usr/bin/env python3
"""Research-only OpenStreetMap exact-org reach screen.

Only the standardized Norwegian `ref:NO:orgnr` tag can establish identity.
Website/contact fields are candidate observations only and are never production
publication proof. Multiple conflicting website domains for one exact org are
reported as ambiguous and produce no website candidate.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ORG_RE = re.compile(r"^\d{9}$")
WEBSITE_KEYS = ("website", "contact:website", "url", "contact:url")
EMAIL_KEYS = ("email", "contact:email")
SOCIAL_KEYS = ("contact:facebook", "contact:instagram", "facebook", "instagram")


def normalize_org(value: Any) -> str | None:
    text = str(value or "").strip()
    return text if ORG_RE.fullmatch(text) else None


def normalize_url(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text or any(ch.isspace() for ch in text):
        return None
    if text.startswith("//"):
        text = "https:" + text
    elif "://" not in text:
        text = "https://" + text
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    host = parsed.hostname.lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    if not host or "." not in host:
        return None
    return parsed._replace(scheme="https", netloc=host + ((f":{parsed.port}") if parsed.port else "")).geturl()


def domain_of(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


def load_targets(path: Path) -> set[str]:
    result: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        org = normalize_org(row.get("organisation_number"))
        if org:
            result.add(org)
    return result


def screen(payload: dict[str, Any], targets: set[str]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    elements = payload.get("elements") or []
    if not isinstance(elements, list):
        raise ValueError("Overpass payload must contain an elements list")

    by_org: dict[str, list[dict[str, Any]]] = {}
    all_exact_orgs: set[str] = set()
    malformed_ref_values = 0

    for element in elements:
        if not isinstance(element, dict):
            continue
        tags = element.get("tags")
        if not isinstance(tags, dict):
            continue
        raw_ref = tags.get("ref:NO:orgnr")
        if raw_ref in (None, ""):
            continue
        org = normalize_org(raw_ref)
        if org is None:
            malformed_ref_values += 1
            continue
        all_exact_orgs.add(org)
        if org not in targets:
            continue
        by_org.setdefault(org, []).append(element)

    matched: list[dict[str, Any]] = []
    website_candidate_count = 0
    ambiguous_website_count = 0
    email_candidate_count = 0
    social_candidate_count = 0

    for org in sorted(by_org):
        elements_for_org = by_org[org]
        urls: set[str] = set()
        emails: set[str] = set()
        socials: set[str] = set()
        osm_refs: list[dict[str, Any]] = []

        for element in elements_for_org:
            tags = element.get("tags") or {}
            osm_refs.append({
                "type": element.get("type"),
                "id": element.get("id"),
                "name": tags.get("name"),
            })
            for key in WEBSITE_KEYS:
                url = normalize_url(tags.get(key))
                if url:
                    urls.add(url)
            for key in EMAIL_KEYS:
                value = str(tags.get(key) or "").strip()
                if "@" in value and " " not in value:
                    emails.add(value.lower())
            for key in SOCIAL_KEYS:
                value = str(tags.get(key) or "").strip()
                if value:
                    socials.add(value)

        domains = sorted({domain_of(url) for url in urls if domain_of(url)})
        website_candidate = sorted(urls)[0] if len(domains) == 1 else None
        website_ambiguous = len(domains) > 1
        if website_candidate:
            website_candidate_count += 1
        if website_ambiguous:
            ambiguous_website_count += 1
        if emails:
            email_candidate_count += 1
        if socials:
            social_candidate_count += 1

        matched.append({
            "organisation_number": org,
            "osm_element_count": len(elements_for_org),
            "osm_elements": osm_refs,
            "website_candidate": website_candidate,
            "website_domains": domains,
            "website_ambiguous": website_ambiguous,
            "email_candidates": sorted(emails),
            "social_candidates": sorted(socials),
        })

    report = {
        "source": "OpenStreetMap via public Overpass API",
        "screen_type": "exact_ref_no_orgnr_candidate_screen",
        "production_publication_enabled": False,
        "license": "ODbL-1.0",
        "source_elements": len(elements),
        "unique_exact_orgs_in_source": len(all_exact_orgs),
        "malformed_ref_no_orgnr_values": malformed_ref_values,
        "target_companies": len(targets),
        "exact_target_company_hits": len(matched),
        "exact_target_reach": len(matched) / len(targets) if targets else 0.0,
        "website_candidate_companies": website_candidate_count,
        "ambiguous_website_companies": ambiguous_website_count,
        "email_candidate_companies": email_candidate_count,
        "social_candidate_companies": social_candidate_count,
        "external_requests": 1,
        "notes": [
            "Only exact standardized ref:NO:orgnr values count; name matching is never used.",
            "A website is a candidate only when all website-like tags for the exact org resolve to one domain.",
            "OSM map-edit timestamps are not treated as business-activity evidence.",
            "Every website candidate still requires Signalpost first-party identity verification before publication.",
            "ODbL attribution/share-alike implications must be resolved before any production integration.",
        ],
    }
    return report, matched


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-json", type=Path, required=True)
    parser.add_argument("--companies", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    payload = json.loads(args.source_json.read_text(encoding="utf-8-sig"))
    targets = load_targets(args.companies)
    report, matched = screen(payload, targets)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_dir / "matched-companies.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in matched),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
