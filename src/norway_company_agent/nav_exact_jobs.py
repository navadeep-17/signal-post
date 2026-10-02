from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

LEGAL_SUFFIXES = {"AS", "ASA", "ANS", "DA", "ENK", "NUF", "SA", "BA", "KS", "IKS", "HF", "KF", "SF", "STI"}


def normalize_org(value: Any) -> str | None:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits if len(digits) == 9 else None


def normalize_name(value: Any) -> str:
    text = str(value or "").upper()
    tokens = re.findall(r"[A-Z0-9ÆØÅ]+", text)
    meaningful = [token for token in tokens if token not in LEGAL_SUFFIXES]
    return " ".join(meaningful if meaningful else tokens).strip()


def build_target_index(profiles: list[dict[str, Any]]) -> dict[str, Any]:
    by_target: dict[str, dict[str, Any]] = {}
    org_to_target: dict[str, str] = {}
    name_to_targets: dict[str, set[str]] = {}

    for profile in profiles:
        target_org = normalize_org(profile.get("organisation_number"))
        target_name = normalize_name(profile.get("name"))
        if not target_org or not target_name:
            continue
        allowed_orgs = {target_org}
        names = {target_name}
        locations = ((((profile.get("evidence") or {}).get("locations") or {}).get("value") or {}).get("locations") or [])
        for row in locations:
            if not isinstance(row, dict):
                continue
            sub_org = normalize_org(row.get("organisation_number"))
            sub_name = normalize_name(row.get("name"))
            if sub_org:
                allowed_orgs.add(sub_org)
            if sub_name:
                names.add(sub_name)
        by_target[target_org] = {
            "target_org": target_org,
            "target_name": str(profile.get("name") or ""),
            "allowed_orgs": sorted(allowed_orgs),
            "candidate_names": sorted(names),
        }
        for org in allowed_orgs:
            # A BRREG subunit belongs to exactly one parent in this target set. If a malformed
            # cohort ever contradicts that, omit the ambiguous reverse mapping.
            prior = org_to_target.get(org)
            if prior is None:
                org_to_target[org] = target_org
            elif prior != target_org:
                org_to_target.pop(org, None)
        for name in names:
            if name:
                name_to_targets.setdefault(name, set()).add(target_org)

    return {
        "by_target": by_target,
        "org_to_target": org_to_target,
        "name_to_targets": {name: sorted(values) for name, values in name_to_targets.items()},
    }


def nominate_targets(business_name: Any, index: dict[str, Any]) -> list[str]:
    """Aggressively nominate detail requests; nomination is never publication evidence."""
    business = normalize_name(business_name)
    if not business:
        return []
    exact = list((index.get("name_to_targets") or {}).get(business) or [])
    if exact:
        return sorted(set(exact))

    # Only widen nomination for substantive multi-token names. Final acceptance still
    # requires an exact NAV employer organisation number belonging to the target/main or
    # an already-retained BRREG subunit.
    business_tokens = set(business.split())
    if len(business_tokens) < 2 or len(business) < 8:
        return []
    nominated: set[str] = set()
    for known, targets in (index.get("name_to_targets") or {}).items():
        known_tokens = set(str(known).split())
        if len(known_tokens) < 2 or len(str(known)) < 8:
            continue
        overlap = business_tokens & known_tokens
        if len(overlap) < 2:
            continue
        if business_tokens.issubset(known_tokens) or known_tokens.issubset(business_tokens):
            nominated.update(str(target) for target in targets)
    return sorted(nominated)


def _iso_date(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def extract_exact_active_job(
    detail: dict[str, Any],
    index: dict[str, Any],
    *,
    nominated_targets: list[str] | None = None,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    """Accept only a current NAV vacancy whose employer org exactly maps to a target.

    Header/business-name matching is deliberately excluded from the acceptance proof.
    """
    payload = detail.get("ad_content") or detail.get("json") or detail
    if not isinstance(payload, dict):
        return None
    status = str(detail.get("status") or payload.get("status") or "ACTIVE").upper()
    if status != "ACTIVE":
        return None
    employer = payload.get("employer") or {}
    if not isinstance(employer, dict):
        return None
    employer_org = normalize_org(employer.get("orgnr"))
    if not employer_org:
        return None
    target_org = (index.get("org_to_target") or {}).get(employer_org)
    if not target_org:
        return None
    if nominated_targets and target_org not in set(nominated_targets):
        return None

    title = " ".join(str(payload.get("title") or payload.get("jobtitle") or "").split())
    if not title:
        return None
    expires = _iso_date(payload.get("expires"))
    now = now or datetime.now(timezone.utc)
    if expires is not None and expires < now:
        return None

    work_locations = payload.get("workLocations") if isinstance(payload.get("workLocations"), list) else []
    compact_locations: list[dict[str, Any]] = []
    for row in work_locations[:10]:
        if not isinstance(row, dict):
            continue
        compact_locations.append({
            key: row.get(key)
            for key in ("country", "address", "city", "postalCode", "county", "municipal")
            if row.get(key) not in {None, ""}
        })

    return {
        "target_org": str(target_org),
        "employer_org": employer_org,
        "employer_name": employer.get("name"),
        "title": title[:500],
        "uuid": payload.get("uuid") or detail.get("uuid"),
        "published": payload.get("published"),
        "updated": payload.get("updated") or detail.get("sistEndret"),
        "expires": payload.get("expires"),
        "application_due": payload.get("applicationDue"),
        "application_url": payload.get("applicationUrl"),
        "source_url": payload.get("sourceurl") or payload.get("link"),
        "employment_type": payload.get("engagementtype"),
        "extent": payload.get("extent"),
        "position_count": payload.get("positioncount"),
        "work_locations": compact_locations,
        "identity": "exact_nav_employer_main_or_retained_brreg_subunit_org_number",
    }
