from __future__ import annotations

import re
import urllib.parse
from typing import Any, Iterable

from bs4 import BeautifulSoup, Tag

ACTIVE_COUNT_PHRASES = (
    "ledige stillinger",
    "open positions",
    "open roles",
    "open vacancies",
    "vacancies",
)
GENERIC_ROLE_TITLES = {
    "jobb",
    "jobber",
    "jobs",
    "karriere",
    "career",
    "careers",
    "ledige stillinger",
    "stillinger",
    "vacancies",
    "vacancy",
    "les mer",
    "read more",
    "se mer",
}
CAREER_PATH_SEGMENTS = {
    "career",
    "careers",
    "karriere",
    "jobb",
    "jobber",
    "jobs",
    "stilling",
    "stillinger",
    "ledige-stillinger",
    "vacancy",
    "vacancies",
}
APPLY_TEXT_MARKERS = (
    "søk på stillingen",
    "søk stillingen",
    "send søknad",
    "søk nå",
    "apply now",
    "apply for",
    "apply",
)
DATE_TOKEN = r"(?:20\d{2}-[01]?\d-[0-3]?\d|[0-3]?\d[./-][01]?\d[./-](?:20)?\d{2})"
DATE_RE = re.compile(rf"\b({DATE_TOKEN})\b")
ACTIVE_VACANCY_COUNT_PATTERNS = (
    re.compile(r"\b(\d{1,3})\s+(?:antall\s+)?ledige\s+stillinger\b", re.I),
    re.compile(r"\bantall\s+ledige\s+stillinger(?:\s+[^\d\s]+){0,6}\s+(\d{1,3})\b", re.I),
    re.compile(r"\b(\d{1,3})\s+(?:open\s+positions|open\s+roles|open\s+vacancies|vacancies)\b", re.I),
    re.compile(r"\b(?:open\s+positions|open\s+roles|open\s+vacancies|vacancies)\s*[:\-]?\s*(\d{1,3})\b", re.I),
)


def _fold(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _slug_fold(value: str) -> str:
    return (
        _fold(value)
        .replace("æ", "ae")
        .replace("ø", "o")
        .replace("å", "a")
    )


def _normalized_host(url: str) -> str:
    try:
        host = (urllib.parse.urlparse(url).hostname or "").casefold().rstrip(".")
    except ValueError:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host


def same_company_host(left: str, right: str) -> bool:
    a = _normalized_host(left)
    b = _normalized_host(right)
    if not a or not b:
        return False
    return a == b or a.endswith("." + b) or b.endswith("." + a)


def _specific_title(value: str) -> bool:
    title = " ".join(str(value or "").split()).strip(" -|:")
    if not title or _fold(title) in GENERIC_ROLE_TITLES:
        return False
    words = re.findall(r"[\wæøåÆØÅ-]+", title, flags=re.UNICODE)
    if len(words) >= 2:
        return True
    return len(words) == 1 and len(words[0].strip("-")) >= 5


def _specific_job_path(url: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError:
        return False
    segments = [urllib.parse.unquote(part).casefold() for part in parsed.path.split("/") if part]
    if not segments:
        return False
    positions = [index for index, part in enumerate(segments) if part in CAREER_PATH_SEGMENTS]
    return bool(positions and positions[-1] < len(segments) - 1)


def _title_from_role_url(anchor_text: str, role_url: str) -> str:
    """Trim wrapped role-card metadata only when the URL slug proves the leading title.

    Some careers cards wrap role title, location, employer and deadline in one anchor. For
    a specific same-site role URL, use the final slug only as a structural hint: it must
    match the leading anchor words after conservative Norwegian-to-ASCII folding. If it
    does not match, preserve the original anchor text unchanged.
    """
    title = " ".join(str(anchor_text or "").split()).strip()
    if not title:
        return title
    try:
        parsed = urllib.parse.urlparse(role_url)
    except ValueError:
        return title
    segments = [urllib.parse.unquote(part) for part in parsed.path.split("/") if part]
    if not segments:
        return title
    slug = segments[-1].strip().casefold()
    if not slug or slug.isdigit():
        return title
    slug_words = [part for part in re.split(r"[-_]+", slug) if part]
    if not slug_words or len(slug_words) > 8:
        return title
    anchor_words = re.findall(r"[\wæøåÆØÅ-]+", title, flags=re.UNICODE)
    if len(anchor_words) < len(slug_words):
        return title
    leading = [_slug_fold(word) for word in anchor_words[: len(slug_words)]]
    normalized_slug = [_slug_fold(word) for word in slug_words]
    if leading != normalized_slug:
        return title
    cleaned = " ".join(anchor_words[: len(slug_words)]).strip()
    return cleaned if _specific_title(cleaned) else title


def _nearest_dated_context(anchor: Tag, *, max_chars: int = 900) -> str:
    """Return the smallest nearby card-like text containing an explicit numeric date."""
    node: Tag | None = anchor
    fallback = " ".join(anchor.get_text(" ", strip=True).split())
    for _ in range(6):
        if node is None:
            break
        text = " ".join(node.get_text(" ", strip=True).split())
        if text and len(text) <= max_chars and DATE_RE.search(text):
            return text
        parent = node.parent
        node = parent if isinstance(parent, Tag) else None
    return fallback


def _application_link(container: Tag | None, base_url: str, role_url: str) -> tuple[str | None, str | None]:
    if container is None:
        return None, None
    for anchor in container.select("a[href]"):
        text = _fold(anchor.get_text(" ", strip=True))
        if not text or not any(marker in text for marker in APPLY_TEXT_MARKERS):
            continue
        href = str(anchor.get("href") or "").strip()
        absolute = urllib.parse.urljoin(base_url, href)
        parsed = urllib.parse.urlparse(absolute)
        if parsed.scheme in {"http", "https"} and parsed.hostname:
            return absolute, "explicit_apply_link"
    return role_url, "role_detail_link"


def extract_homepage_hiring_signal(*, final_url: str, soup: BeautifulSoup) -> dict[str, Any]:
    """Return conservative homepage-only evidence that active vacancies exist now.

    A generic careers link is not enough. The page must contain an explicit vacancy-count
    phrase such as ``10 Antall ledige stillinger`` or ``10 open positions``. Broad numeric
    proximity is intentionally rejected so unrelated phone numbers, years, statistics or
    navigation counters cannot consume the bounded careers-follow-up slot.
    """
    text = " ".join(soup.get_text(" ", strip=True).split())[:30_000]
    counts: list[int] = []
    for pattern in ACTIVE_VACANCY_COUNT_PATTERNS:
        for match in pattern.finditer(text):
            try:
                value = int(match.group(1))
            except (TypeError, ValueError):
                continue
            if 0 < value <= 500:
                counts.append(value)
    count = max(counts) if counts else 0
    return {
        "active_vacancy_count": count,
        "active_vacancies": count > 0,
        "method": "explicit_homepage_vacancy_count" if count > 0 else "none",
        "homepage_url": final_url,
    }


def _iter_json_objects(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_json_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_json_objects(child)


def _structured_job_candidates(structured: dict[str, Any], base_url: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in _iter_json_objects((structured or {}).get("json-ld") or []):
        raw_type = item.get("@type")
        types = [raw_type] if isinstance(raw_type, str) else list(raw_type or []) if isinstance(raw_type, list) else []
        if not any(str(value).casefold() == "jobposting" for value in types):
            continue
        title = " ".join(str(item.get("title") or "").split())
        valid_through = " ".join(str(item.get("validThrough") or item.get("valid_through") or "").split())
        raw_url = str(item.get("url") or "").strip()
        role_url = urllib.parse.urljoin(base_url, raw_url) if raw_url else ""
        hiring = item.get("hiringOrganization") or item.get("hiring_organization") or {}
        hiring_name = ""
        if isinstance(hiring, dict):
            hiring_name = " ".join(str(hiring.get("name") or "").split())
        if not (_specific_title(title) and valid_through and role_url.startswith(("http://", "https://"))):
            continue
        rows.append(
            {
                "title": title[:300],
                "role_url": role_url,
                "application_url": role_url,
                "action_type": "structured_job_posting",
                "deadline_raw": valid_through[:200],
                "employer_context": hiring_name[:500],
                "hiring_organisation": hiring_name[:300],
                "method": "jsonld_job_posting",
            }
        )
    return rows


def extract_job_listing_candidates(
    *,
    final_url: str,
    soup: BeautifulSoup,
    structured: dict[str, Any] | None = None,
    limit: int = 12,
) -> list[dict[str, Any]]:
    """Extract role-card observations from one first-party hiring surface.

    These are page observations only. Publication requires the strict projector to prove
    target-employer match and currentness against the page retrieval timestamp.
    """
    rows = _structured_job_candidates(structured or {}, final_url)
    seen = {(str(item.get("title") or "").casefold(), str(item.get("role_url") or "")) for item in rows}

    for anchor in soup.select("a[href]"):
        if len(rows) >= limit:
            break
        href = str(anchor.get("href") or "").strip()
        if not href:
            continue
        role_url = urllib.parse.urljoin(final_url, href)
        try:
            parsed = urllib.parse.urlparse(role_url)
        except ValueError:
            continue
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            continue
        same_host = same_company_host(role_url, final_url)
        raw_title = " ".join(anchor.get_text(" ", strip=True).split())
        title = _title_from_role_url(raw_title, role_url) if same_host else raw_title
        if not _specific_title(title):
            continue

        context = _nearest_dated_context(anchor)
        deadline = DATE_RE.search(context)
        if not deadline:
            continue

        if same_host and not _specific_job_path(role_url):
            continue

        container: Tag | None = anchor
        for _ in range(5):
            if container is None:
                break
            text = " ".join(container.get_text(" ", strip=True).split())
            if DATE_RE.search(text) and len(text) <= 900:
                break
            parent = container.parent
            container = parent if isinstance(parent, Tag) else None

        application_url, action_type = _application_link(container, final_url, role_url)
        key = (title.casefold(), role_url)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "title": title[:300],
                "role_url": role_url,
                "application_url": application_url,
                "action_type": action_type,
                "deadline_raw": deadline.group(1)[:200],
                "employer_context": context[:900],
                "hiring_organisation": "",
                "method": "dated_role_card",
            }
        )

    rows.sort(key=lambda item: (str(item.get("deadline_raw") or ""), str(item.get("title") or "").casefold(), str(item.get("role_url") or "")))
    return rows[:limit]
