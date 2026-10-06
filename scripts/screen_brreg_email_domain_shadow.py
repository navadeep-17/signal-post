#!/usr/bin/env python3
"""Research-only shadow verification of strong BRREG email-domain site candidates.

No production verifier is changed. Candidates come only from an exact BRREG registry
email attached to the target legal entity and are limited to domains whose label has
strong legal-name morphology. The experiment measures whether exact registry phone or
strong address corroboration can safely recover sites that omit the full legal name.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import gzip
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.domain_discovery import (  # noqa: E402
    GENERIC_EMAIL_DOMAINS,
    _domain_from_url,
    _domain_identity_strength,
    _page_contains_full_legal_name,
    _page_contains_org_number,
    _page_matches_registry_location,
    _website_page_identity_parts,
    qualify_registry_email_domain_identity,
)
from norway_company_agent.final_site_discovery import (  # noqa: E402
    _explicit_org_numbers,
    fetch_bounded_homepage,
)
from norway_company_agent.identity import apply_website_identity_gate  # noqa: E402


def norm_org(value: Any) -> str | None:
    digits = re.sub(r"\D", "", str(value or ""))
    return digits if len(digits) == 9 else None


def email_domains(value: Any) -> list[str]:
    out: list[str] = []
    for part in re.split(r"[\s,;]+", str(value or "").strip()):
        candidate = part.strip("<>[](){}\"'")
        if "@" not in candidate:
            continue
        local, _, domain = candidate.rpartition("@")
        domain = domain.strip().strip(".").casefold()
        if local and domain and "." in domain and domain not in GENERIC_EMAIL_DOMAINS:
            out.append(domain)
    return list(dict.fromkeys(out))


def read_profiles(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for file in sorted(path.rglob("profiles.jsonl")):
        for line in file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            org = norm_org(row.get("organisation_number"))
            if not org or org in out:
                raise ValueError(f"invalid/duplicate profile org {org!r}")
            out[org] = row
    if len(out) != 1000:
        raise ValueError(f"expected 1000 profiles, got {len(out)}")
    return out


def current_website_orgs(path: Path) -> set[str]:
    found: set[str] = set()
    seen: set[str] = set()
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            org = norm_org(row.get("organisation_number"))
            if not org or org in seen:
                raise ValueError(f"invalid/duplicate output org {org!r}")
            seen.add(org)
            for claim in row.get("claims") or []:
                if (
                    isinstance(claim, dict)
                    and claim.get("field") == "official_website"
                    and claim.get("availability") == "available"
                    and claim.get("value")
                ):
                    found.add(org)
                    break
    if len(seen) != 1000:
        raise ValueError(f"expected 1000 output rows, got {len(seen)}")
    return found


def registry_raw(profile: dict[str, Any]) -> dict[str, Any]:
    return ((profile.get("evidence") or {}).get("registry") or {}).get("value") or {}


def _phone_values(raw: dict[str, Any]) -> list[str]:
    found: list[str] = []
    for key in ("telefon", "mobil", "mobiltelefon", "telefonnummer"):
        value = raw.get(key)
        if isinstance(value, list):
            values = value
        else:
            values = [value]
        for item in values:
            digits = re.sub(r"\D", "", str(item or ""))
            # Norwegian national phone numbers are normally 8 digits. Keep +47 form too.
            if len(digits) >= 8:
                found.append(digits[-8:])
    return list(dict.fromkeys(found))


def _page_has_phone(website: dict[str, Any], raw: dict[str, Any]) -> bool:
    phones = _phone_values(raw)
    if not phones:
        return False
    for part in _website_page_identity_parts(website):
        digits = re.sub(r"\D", "", part)
        if any(phone in digits for phone in phones):
            return True
    return False


def _page_has_strong_address(website: dict[str, Any], raw: dict[str, Any]) -> bool:
    parts = " ".join(_website_page_identity_parts(website)).casefold()
    normalized = re.sub(r"[^a-z0-9æøå]+", " ", parts)
    tokens = set(normalized.split())

    postcode = re.sub(r"\D", "", str(raw.get("forretningsadresse.postnummer") or ""))
    address = raw.get("forretningsadresse.adresse")
    if isinstance(address, list):
        address_text = " ".join(str(x or "") for x in address)
    else:
        address_text = str(address or "")
    addr_tokens = [
        token.casefold()
        for token in re.findall(r"[A-Za-zÆØÅæøå0-9]+", address_text)
        if len(token) >= 4 and not token.isdigit()
    ]
    # Stronger than the production location helper: require both the exact postcode
    # and at least one meaningful street/address token.
    return bool(
        len(postcode) == 4
        and postcode in tokens
        and addr_tokens
        and any(token in tokens for token in addr_tokens)
    )


def candidate_rows(
    profiles: dict[str, dict[str, Any]],
    current_websites: set[str],
) -> list[tuple[str, dict[str, Any], str, str]]:
    rows: list[tuple[str, dict[str, Any], str, str]] = []
    rank = {"exact": 3, "acronym": 2, "multi": 1}
    for org, profile in profiles.items():
        if org in current_websites:
            continue
        domains = email_domains(registry_raw(profile).get("epostadresse"))
        strong: list[tuple[int, str, str]] = []
        for domain in domains:
            strength = _domain_identity_strength(profile, domain)
            if strength in rank:
                strong.append((rank[strength], domain, strength))
        if not strong:
            continue
        strong.sort(key=lambda x: (-x[0], x[1]))
        _, domain, strength = strong[0]
        rows.append((org, profile, domain, strength))
    return sorted(rows, key=lambda x: x[0])


def evaluate_one(item: tuple[str, dict[str, Any], str, str], timeout: float) -> dict[str, Any]:
    org, profile, domain, source_strength = item
    record, metrics = fetch_bounded_homepage(
        domain,
        source_type="research_brreg_email_domain_shadow_candidate",
        timeout=timeout,
    )
    record["source_class"] = "company_owned_candidate"
    gated = apply_website_identity_gate(profile, record)
    website = gated["website"]
    assessment = qualify_registry_email_domain_identity(
        profile, domain, website, gated.get("assessment")
    )
    if assessment is not None:
        value = website.get("value") or {}
        value["identity_assessment"] = assessment
        website["value"] = value

    status = str(website.get("status") or "")
    final_domain = _domain_from_url(
        (website.get("value") or {}).get("final_url") or website.get("source_url")
    )
    final_strength = _domain_identity_strength(profile, final_domain)
    target = org
    explicit = _explicit_org_numbers(website)
    conflicting = bool(explicit and target not in explicit)
    exact_org = target in explicit or _page_contains_org_number(profile, website)
    full_name = _page_contains_full_legal_name(profile, website)
    raw = registry_raw(profile)
    phone = _page_has_phone(website, raw)
    strong_address = _page_has_strong_address(website, raw)
    location_any = _page_matches_registry_location(profile, website)
    current_publishable = bool(
        status == "available" and assessment and assessment.get("publishable")
    )

    safe_same_domain = bool(
        status == "available"
        and source_strength == "exact"
        and final_strength == "exact"
        and not conflicting
    )
    shadow_phone = bool(
        safe_same_domain
        and phone
        and not current_publishable
    )
    shadow_address = bool(
        safe_same_domain
        and strong_address
        and not current_publishable
    )

    return {
        "organisation_number": org,
        "legal_name": str(profile.get("name") or ""),
        "candidate_domain": domain,
        "source_domain_strength": source_strength,
        "final_domain": final_domain,
        "final_domain_strength": final_strength,
        "fetch_status": status,
        "current_assessment_status": str((assessment or {}).get("status") or ""),
        "current_publishable": current_publishable,
        "current_assessment_reasons": list((assessment or {}).get("reasons") or []),
        "explicit_target_org": exact_org,
        "explicit_conflicting_org": conflicting,
        "explicit_org_numbers": sorted(explicit),
        "full_legal_name_on_page": full_name,
        "registry_phone_match": phone,
        "registry_strong_address_match": strong_address,
        "registry_any_location_match": location_any,
        "shadow_exact_domain_plus_phone": shadow_phone,
        "shadow_exact_domain_plus_strong_address": shadow_address,
        "logical_requests": int(metrics.get("requests") or 0),
        "bytes_received": int(metrics.get("bytes") or 0),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles-dir", type=Path, required=True)
    ap.add_argument("--production-output-gz", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--timeout", type=float, default=6.0)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    profiles = read_profiles(args.profiles_dir)
    current = current_website_orgs(args.production_output_gz)
    candidates = candidate_rows(profiles, current)

    rows: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(evaluate_one, item, args.timeout) for item in candidates]
        for future in concurrent.futures.as_completed(futures):
            rows.append(future.result())
    rows.sort(key=lambda x: x["organisation_number"])

    status_counts = Counter(row["fetch_status"] for row in rows)
    assessment_counts = Counter(row["current_assessment_status"] for row in rows)
    current_promotions = [row for row in rows if row["current_publishable"]]
    shadow_phone = [row for row in rows if row["shadow_exact_domain_plus_phone"]]
    shadow_address = [row for row in rows if row["shadow_exact_domain_plus_strong_address"]]
    shadow_union = {
        row["organisation_number"]: row
        for row in [*shadow_phone, *shadow_address]
    }

    report = {
        "screen_type": "brreg_email_domain_shadow_identity_corroboration",
        "cohort_companies": 1000,
        "current_verified_website_companies": len(current),
        "attempted_strong_email_domain_companies": len(rows),
        "source_strength_counts": dict(Counter(row["source_domain_strength"] for row in rows)),
        "fetch_status_counts": dict(status_counts),
        "current_assessment_status_counts": dict(assessment_counts),
        "current_replay_publishable_companies": len(current_promotions),
        "explicit_target_org_companies": sum(bool(row["explicit_target_org"]) for row in rows),
        "explicit_conflicting_org_companies": sum(bool(row["explicit_conflicting_org"]) for row in rows),
        "full_legal_name_companies": sum(bool(row["full_legal_name_on_page"]) for row in rows),
        "registry_phone_match_companies": sum(bool(row["registry_phone_match"]) for row in rows),
        "registry_strong_address_match_companies": sum(bool(row["registry_strong_address_match"]) for row in rows),
        "shadow_phone_only_new_companies": len(shadow_phone),
        "shadow_address_only_new_companies": len(shadow_address),
        "shadow_union_new_companies": len(shadow_union),
        "shadow_union_reach": round(len(shadow_union) / 1000, 6),
        "logical_site_requests": sum(row["logical_requests"] for row in rows),
        "bytes_received": sum(row["bytes_received"] for row in rows),
        "production_publication_enabled": False,
        "verifier_changed": False,
        "notes": [
            "No production identity rule is changed by this experiment.",
            "Only strong BRREG registered-email domains for companies lacking a frozen verified website are attempted.",
            "Shadow candidates require exact legal-name domain morphology on both candidate and final domain, no conflicting explicit org number, and an independently observed exact BRREG phone or strong address match.",
            "Every shadow candidate still requires manual audit and adversarial regression before any production proposal.",
        ],
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    # Persist only the small would-be-promotion set for manual precision audit.
    audit_rows = [shadow_union[key] for key in sorted(shadow_union)]
    (args.output_dir / "shadow-manual-audit.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in audit_rows),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
