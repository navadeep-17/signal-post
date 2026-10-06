#!/usr/bin/env python3
"""Zero-network audit of exact-site meta/OG description projection gaps.

Reads archived retained profiles and the frozen 1000-company output. A candidate
exists only when:
- the retained website evidence is available;
- its identity assessment is already publishable/exact;
- a non-empty retained homepage meta/OG description exists; and
- no available company_description claim exists in the frozen output.

No description text is retained in the report/audit; only fingerprints and
bounded diagnostics are emitted.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


LEGAL_SUFFIX = re.compile(r"(?i)\s+(?:ASA|AS|ANS|DA|NUF|SA|BA|KS|IKS|HF|KF|SF)\s*$")
WORD_RE = re.compile(r"[0-9A-Za-zÆØÅæøå]{3,}")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def read_profiles(directory: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(directory.rglob("profiles.jsonl")):
        rows.extend(read_jsonl(path))
    return rows


def output_index(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    with gzip.open(path, "rt", encoding="utf-8") as h:
        for line in h:
            if not line.strip():
                continue
            row = json.loads(line)
            org = str(row.get("organisation_number") or "")
            if org:
                out[org] = row
    return out


def available_claim(row: dict[str, Any], field: str) -> bool:
    return any(
        isinstance(c, dict)
        and c.get("field") == field
        and c.get("availability") == "available"
        and c.get("value") not in (None, "", [], {})
        for c in row.get("claims") or []
    )


def exact_website(profile: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]] | None:
    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") or {}
    identity = value.get("identity_assessment") or {}
    if website.get("status") != "available" or not identity.get("publishable"):
        return None
    return website, value


def name_tokens(value: str) -> set[str]:
    stripped = LEGAL_SUFFIX.sub("", str(value or "").strip()).casefold()
    return {x.casefold() for x in WORD_RE.findall(stripped) if len(x) >= 4}


def audit(
    profiles: list[dict[str, Any]],
    outputs: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    exact_sites = 0
    exact_with_retained_description = 0
    output_description_companies = 0
    exact_missing_output_description = 0
    retained_description_gap = 0

    identity_methods = Counter()
    extraction_states = Counter()
    length_bands = Counter()
    token_match = Counter()
    audit_rows: list[dict[str, Any]] = []

    for profile in profiles:
        org = str(profile.get("organisation_number") or "")
        output = outputs.get(org)
        if not output:
            continue
        if available_claim(output, "company_description"):
            output_description_companies += 1

        exact = exact_website(profile)
        if exact is None:
            continue
        _, value = exact
        exact_sites += 1

        desc = str(value.get("description") or "").strip()
        if desc:
            exact_with_retained_description += 1

        if available_claim(output, "company_description"):
            continue
        exact_missing_output_description += 1
        if not desc:
            continue

        retained_description_gap += 1
        identity = value.get("identity_assessment") or {}
        identity_methods[str(identity.get("method") or "unknown")] += 1
        extraction_states[str(value.get("extraction_state") or "unknown")] += 1

        n = len(desc)
        if n < 40:
            band = "<40"
        elif n < 80:
            band = "40-79"
        elif n < 160:
            band = "80-159"
        elif n < 320:
            band = "160-319"
        else:
            band = "320+"
        length_bands[band] += 1

        tokens = name_tokens(str(profile.get("name") or ""))
        desc_tokens = name_tokens(desc)
        matched = sorted(tokens & desc_tokens)
        token_match["has_legal_name_token" if matched else "no_legal_name_token"] += 1

        digits = set(re.findall(r"(?<!\d)\d{9}(?!\d)", desc))
        different_org_numbers = sorted(x for x in digits if x != org)
        audit_rows.append(
            {
                "organisation_number": org,
                "legal_name": profile.get("name"),
                "description_characters": n,
                "description_fingerprint": hashlib.sha256(desc.encode("utf-8")).hexdigest()[:12],
                "identity_method": identity.get("method"),
                "identity_score": identity.get("score"),
                "extraction_state": value.get("extraction_state"),
                "legal_name_token_match": bool(matched),
                "matched_legal_name_token_count": len(matched),
                "explicit_different_org_number_count": len(different_org_numbers),
                "raw_description_retained": False,
            }
        )

    report = {
        "screen_type": "retained_exact_site_description_projection_gap",
        "companies": len(profiles),
        "exact_verified_site_companies": exact_sites,
        "exact_sites_with_retained_meta_description": exact_with_retained_description,
        "current_company_description_companies": output_description_companies,
        "exact_sites_missing_current_company_description": exact_missing_output_description,
        "net_new_retained_description_candidate_companies": retained_description_gap,
        "candidate_reach_pct": round(100 * retained_description_gap / len(profiles), 3) if profiles else 0.0,
        "candidate_identity_methods": dict(sorted(identity_methods.items())),
        "candidate_extraction_states": dict(sorted(extraction_states.items())),
        "candidate_length_bands": dict(sorted(length_bands.items())),
        "candidate_legal_name_token_match": dict(sorted(token_match.items())),
        "network_requests": 0,
        "production_publication_enabled": False,
        "privacy_boundary": {
            "raw_descriptions_retained": False,
            "description_fingerprint_only": True,
        },
        "notes": [
            "This audit measures a projection gap only; it does not authorize publishing homepage meta descriptions.",
            "Website identity must already be publishable before a retained description is considered.",
            "Any non-zero candidates require a separate quality/precision replay before promotion.",
        ],
    }
    return report, audit_rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles-dir", type=Path, required=True)
    ap.add_argument("--output-contract-gz", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--audit", type=Path, required=True)
    args = ap.parse_args()

    profiles = read_profiles(args.profiles_dir)
    outputs = output_index(args.output_contract_gz)
    if len(profiles) != 1000 or len(outputs) != 1000:
        raise SystemExit(f"expected 1000 profiles/outputs, got {len(profiles)}/{len(outputs)}")
    report, rows = audit(profiles, outputs)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.audit.write_text(
        "".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in rows),
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
