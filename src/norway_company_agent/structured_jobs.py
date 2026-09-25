from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse

LEGAL_TOKENS = {
    "as", "asa", "ans", "da", "enk", "iks", "sa", "sam", "sti", "stiftelsen",
    "nuf", "ab", "limited", "ltd", "inc", "plc", "the", "og", "and",
}


def _tokens(value: Any) -> list[str]:
    text = str(value or "").translate(str.maketrans({"ø": "o", "Ø": "O", "å": "a", "Å": "A", "æ": "ae", "Æ": "AE"}))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()
    return [token for token in re.findall(r"[a-z0-9]+", text) if token not in LEGAL_TOKENS and len(token) > 1]


def _walk(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _types(node: dict[str, Any]) -> set[str]:
    raw = node.get("@type") or node.get("type")
    values = raw if isinstance(raw, list) else [raw]
    return {str(value).strip().casefold() for value in values if str(value or "").strip()}


def _org_name(node: dict[str, Any]) -> str | None:
    raw = node.get("hiringOrganization") or node.get("hiring_organization")
    if isinstance(raw, dict):
        for key in ("legalName", "name"):
            value = str(raw.get(key) or "").strip()
            if value:
                return value
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def _http_url(value: Any, base_url: str) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    resolved = urljoin(base_url, raw)
    parsed = urlparse(resolved)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    return resolved


def extract_job_postings(structured: Any, *, base_url: str) -> list[dict[str, Any]]:
    """Extract only explicit schema.org JobPosting objects from already-parsed markup.

    This function performs no network access and intentionally ignores generic
    careers text, navigation labels, and unstructured role-like phrases.
    """
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for node in _walk(structured):
        if "jobposting" not in _types(node):
            continue
        title = str(node.get("title") or node.get("name") or "").strip()
        job_url = _http_url(node.get("url"), base_url)
        if not title or not job_url:
            continue
        key = (title.casefold(), job_url)
        if key in seen:
            continue
        seen.add(key)
        employment = node.get("employmentType")
        if isinstance(employment, list):
            employment_type: Any = [str(value) for value in employment if str(value or "").strip()]
        else:
            employment_type = str(employment).strip() if employment is not None else None
        description = re.sub(r"\s+", " ", str(node.get("description") or "")).strip()
        rows.append(
            {
                "title": title[:500],
                "url": job_url,
                "hiring_organization": _org_name(node),
                "date_posted": str(node.get("datePosted") or "").strip() or None,
                "valid_through": str(node.get("validThrough") or "").strip() or None,
                "employment_type": employment_type,
                "description_excerpt": description[:1200] or None,
            }
        )
    return rows


def hiring_organisation_matches(legal_name: str, hiring_organisation: str | None) -> bool:
    """Conservative legal-name check for a structured JobPosting employer."""
    if not hiring_organisation:
        return False
    target = _tokens(legal_name)
    observed = set(_tokens(hiring_organisation))
    if not target or not observed:
        return False
    target_set = set(target)
    if target_set.issubset(observed):
        return True
    overlap = target_set & observed
    if len(target_set) == 1:
        return bool(overlap)
    return len(overlap) >= 2 and len(overlap) / len(target_set) >= 0.75
