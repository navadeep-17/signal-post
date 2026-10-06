from __future__ import annotations

from datetime import date, datetime, timezone
import re
from typing import Any
from urllib.parse import unquote, urlparse


CAREERS_ANCHOR_TERMS = (
    "career",
    "careers",
    "join our team",
    "work with us",
    "job opportunities",
    "karriere",
    "jobb hos oss",
    "jobbe hos oss",
    "ledige stillinger",
    "ledige-stillinger",
    "stillinger",
    "vacancies",
    "vacancy",
)
CAREERS_PATH_TERMS = (
    "career",
    "careers",
    "karriere",
    "jobb",
    "jobber",
    "stilling",
    "stillinger",
    "ledige stillinger",
    "vacancy",
    "vacancies",
)
NON_ACTIVITY_PATH_SEGMENTS = {
    "profil",
    "profile",
    "profiles",
    "person",
    "persons",
    "user",
    "users",
    "bruker",
    "brukere",
    "bolig",
    "boliger",
    "property",
    "properties",
    "listing",
    "listings",
    "annonse",
    "annonser",
}
GENERIC_CMS_TITLES = {
    "hello world",
    "hei verden",
    "sample post",
    "sample page",
}
MAX_CAREERS_ANCHOR_CHARS = 160


def _fold(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _bounded_phrase_marker(text: str, terms: tuple[str, ...]) -> str | None:
    folded = _fold(text)
    for term in terms:
        if re.search(rf"(?<!\w){re.escape(term.casefold())}(?!\w)", folded, re.IGNORECASE):
            return term
    return None


def _path_text(url: str) -> str:
    try:
        path = unquote(urlparse(str(url or "")).path).casefold()
    except ValueError:
        return ""
    return re.sub(r"[-_/]+", " ", path)


def _path_segments(url: str) -> set[str]:
    try:
        parsed = urlparse(str(url or ""))
    except ValueError:
        return set()
    return {
        unquote(part).strip().casefold()
        for part in parsed.path.split("/")
        if part.strip()
    }


def _retrieval_date(value: Any) -> date | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).date()


def _iso_date(value: Any) -> date | None:
    try:
        parsed = date.fromisoformat(str(value or "").strip())
    except (TypeError, ValueError):
        return None
    return parsed


def _careers_claim_precise(claim: dict[str, Any]) -> bool:
    value = claim.get("value")
    if not isinstance(value, dict):
        return False
    url = str(value.get("url") or "").strip()
    anchor = " ".join(str(value.get("anchor_text") or "").split())
    if not url.startswith(("http://", "https://")):
        return False
    if _path_segments(url) & NON_ACTIVITY_PATH_SEGMENTS:
        return False
    path_marker = _bounded_phrase_marker(_path_text(url), CAREERS_PATH_TERMS)
    anchor_marker = None
    if anchor and len(anchor) <= MAX_CAREERS_ANCHOR_CHARS:
        anchor_marker = _bounded_phrase_marker(anchor, CAREERS_ANCHOR_TERMS)
    return bool(path_marker or anchor_marker)


def _company_update_precise(
    claim: dict[str, Any],
    evidence_by_id: dict[str, dict[str, Any]],
) -> bool:
    value = claim.get("value")
    if not isinstance(value, dict):
        return False
    title = _fold(value.get("title")).strip(" .!?:;-")
    url = str(value.get("url") or "").strip()
    published = _iso_date(value.get("published_date"))
    if not title or title in GENERIC_CMS_TITLES or not url.startswith(("http://", "https://")) or published is None:
        return False
    if _path_segments(url) & NON_ACTIVITY_PATH_SEGMENTS:
        return False

    refs = [str(ref) for ref in (claim.get("evidence_ids") or []) if ref]
    if not refs:
        return False
    observed_dates: list[date] = []
    for ref in refs:
        evidence = evidence_by_id.get(ref)
        if not evidence:
            return False
        observed = _retrieval_date(evidence.get("retrieved_at"))
        if observed is None:
            return False
        observed_dates.append(observed)
    return published <= max(observed_dates)


def project_external_precision_guard(contract: dict[str, Any]) -> dict[str, Any]:
    """Fail closed on evaluator-visible external careers/activity false positives.

    This pass is zero-network and only removes claims that fail narrow semantic/date guards.
    Existing claim/evidence values are never rewritten. Evidence exclusively referenced by
    removed claims is dropped; shared evidence remains intact.
    """
    claims = [dict(item) for item in (contract.get("claims") or []) if isinstance(item, dict)]
    evidence = [dict(item) for item in (contract.get("evidence") or []) if isinstance(item, dict)]
    evidence_by_id = {str(item.get("id")): item for item in evidence if item.get("id")}

    kept: list[dict[str, Any]] = []
    removed_refs: set[str] = set()
    for claim in claims:
        field = str(claim.get("field") or "")
        keep = True
        if field == "external.careers_page":
            keep = _careers_claim_precise(claim)
        elif field == "external.company_update":
            keep = _company_update_precise(claim, evidence_by_id)
        if keep:
            kept.append(claim)
        else:
            removed_refs.update(str(ref) for ref in (claim.get("evidence_ids") or []) if ref)

    still_referenced = {
        str(ref)
        for claim in kept
        for ref in (claim.get("evidence_ids") or [])
        if ref
    }
    retained_evidence = [
        item
        for item in evidence
        if str(item.get("id") or "") not in (removed_refs - still_referenced)
    ]
    return {
        **contract,
        "claims": kept,
        "evidence": sorted(retained_evidence, key=lambda item: str(item.get("id") or "")),
    }
