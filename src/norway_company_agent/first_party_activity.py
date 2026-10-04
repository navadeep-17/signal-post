from __future__ import annotations

import hashlib
import re
from datetime import date
from typing import Any
from urllib.parse import parse_qs, urlparse

from .first_party_jobs import extract_current_first_party_jobs


JOB_PATH_MARKERS = (
    "/job",
    "/jobs",
    "/career",
    "/careers",
    "/stilling",
    "/stillinger",
    "/ledige-stillinger",
    "/vacanc",
)
JOB_ACTION_MARKERS = (
    "apply now",
    "apply for",
    "application deadline",
    "send application",
    "søk nå",
    "søk stillingen",
    "send søknad",
    "søknadsfrist",
)
JOB_DETAIL_MARKERS = (
    "full-time",
    "part-time",
    "full time",
    "part time",
    "heltid",
    "deltid",
    "arbeidssted",
    "location",
    "position",
    "stilling",
)
GENERIC_JOB_TITLES = {
    "jobs",
    "job",
    "careers",
    "career",
    "vacancies",
    "vacancy",
    "ledige stillinger",
    "ledige stillinger hos oss",
    "karriere",
    "karriere hos oss",
    "jobb hos oss",
    "jobb",
}
GENERIC_JOB_PATH_SEGMENTS = {
    "job",
    "jobs",
    "career",
    "careers",
    "jobb",
    "jobber",
    "stilling",
    "stillinger",
    "ledige-stillinger",
    "vacancy",
    "vacancies",
}
JOB_DETAIL_QUERY_KEYS = {"job", "jobid", "job_id", "position", "positionid", "vacancy", "opening", "gh_jid"}
UPDATE_PATH_MARKERS = (
    "/news",
    "/nyheter",
    "/aktuelt",
    "/blog",
    "/press",
    "/presse",
)
GENERIC_UPDATE_TITLES = {
    "news",
    "nyheter",
    "aktuelt",
    "blog",
    "press",
    "presse",
}
GENERIC_UPDATE_PATH_SEGMENTS = {"news", "nyheter", "aktuelt", "blog", "press", "presse"}
GENERIC_CMS_PLACEHOLDER_TITLES = {
    "hello world",
    "hello world!",
    "sample page",
    "sample post",
}
GENERIC_CMS_PLACEHOLDER_MARKERS = (
    "welcome to wordpress",
    "this is your first post",
    "edit or delete it, then start writing",
)
SHORT_NUMERIC_DATE_PATTERN = re.compile(r"\b([0-3]?\d)[./-]([01]?\d)[./-](\d{2})\b")
DATE_PATTERNS = (
    re.compile(r"\b(20\d{2}-[01]\d-[0-3]\d)(?=$|[Tt\s])"),
    re.compile(r"\b([0-3]?\d[./-][01]?\d[./-]20\d{2})\b"),
    re.compile(
        r"\b([0-3]?\d\s+(?:jan(?:uar)?|feb(?:ruar)?|mar(?:s|ch)?|apr(?:il)?|mai|may|jun(?:i|e)?|jul(?:i|y)?|aug(?:ust)?|sep(?:tember)?|okt(?:ober)?|oct(?:ober)?|nov(?:ember)?|des(?:ember)?|dec(?:ember)?)\s+20\d{2})\b",
        re.IGNORECASE,
    ),
)
DATE_METHOD_PRIORITY = {
    "jsonld_newsarticle_date_published": 0,
    "jsonld_article_date_published": 0,
    "meta_article_published_time": 0,
    "meta_itemprop_date_published": 1,
    "meta_name_pubdate": 2,
    "meta_name_date": 2,
    "time_datetime": 3,
    "time_text": 4,
    "date_labelled_element": 4,
}


def _fold(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").casefold().strip(".")
    except ValueError:
        return ""


def _same_verified_site(page_url: str, verified_url: str) -> bool:
    page_host = _host(page_url)
    verified_host = _host(verified_url)
    if not page_host or not verified_host:
        return False
    if page_host == verified_host:
        return True
    return page_host.endswith("." + verified_host) or verified_host.endswith("." + page_host)


def _specific_title(title: str, *, generic: set[str]) -> bool:
    folded = _fold(title)
    if not folded or folded in generic:
        return False
    segments = re.split(r"\s*(?:\||–|—|:)\s*|\s+-\s+", folded, maxsplit=1)
    if len(segments) > 1 and segments[0].strip() in generic:
        return False
    words = re.findall(r"[\wæøåÆØÅ-]+", title, flags=re.UNICODE)
    return len(words) >= 2


def _detail_page_url(url: str, *, generic_segments: set[str], allow_query_keys: set[str] | None = None) -> bool:
    """Reject section roots such as /careers and /news even when their text looks rich."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    segments = [segment.casefold() for segment in parsed.path.split("/") if segment]
    if not segments:
        return False
    generic_positions = [index for index, segment in enumerate(segments) if segment in generic_segments]
    if generic_positions and generic_positions[-1] < len(segments) - 1:
        return True
    if allow_query_keys:
        query_keys = {key.casefold() for key in parse_qs(parsed.query, keep_blank_values=False)}
        if query_keys & allow_query_keys:
            return True
    return False


def _specific_non_root_page_url(url: str, *, generic_segments: set[str]) -> bool:
    """Allow a homepage-nominated root-level article slug, never a home/archive root."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    segments = [segment.casefold() for segment in parsed.path.split("/") if segment]
    if not segments:
        return False
    if len(segments) == 1 and segments[0] in generic_segments:
        return False
    return True


def _first_date(text: str) -> str | None:
    short = SHORT_NUMERIC_DATE_PATTERN.search(text)
    if short:
        day, month, year = (int(short.group(1)), int(short.group(2)), 2000 + int(short.group(3)))
        try:
            parsed = date(year, month, day)
        except ValueError:
            pass
        else:
            return parsed.isoformat()
    for pattern in DATE_PATTERNS:
        match = pattern.search(text)
        if match:
            raw = match.group(1)
            numeric = re.fullmatch(r"([0-3]?\d)[./-]([01]?\d)[./-](20\d{2})", raw)
            if numeric:
                try:
                    return date(int(numeric.group(3)), int(numeric.group(2)), int(numeric.group(1))).isoformat()
                except ValueError:
                    return None
            return raw
    return None


def _all_dates(text: str) -> set[str]:
    """Return unique normalized date values visible in unstructured page text."""
    values: set[str] = set()
    occupied: list[tuple[int, int]] = []
    for match in SHORT_NUMERIC_DATE_PATTERN.finditer(text):
        parsed = _first_date(match.group(0))
        if parsed:
            values.add(parsed)
            occupied.append(match.span())
    for pattern in DATE_PATTERNS:
        for match in pattern.finditer(text):
            if any(start <= match.start() < end for start, end in occupied):
                continue
            parsed = _first_date(match.group(0))
            if parsed:
                values.add(parsed)
    return values


def _select_publication_date(page: dict[str, Any], text: str) -> dict[str, str] | None:
    """Select a publication date by semantic strength; abstain on same-rank conflicts.

    Strong page-local publication metadata outranks weaker dynamic/labelled dates. If no
    semantic candidate exists, unstructured text is usable only when it contains exactly
    one unique date. Feed/sitemap metadata is intentionally absent from this selector.
    """
    ranked: list[tuple[int, str, str, str]] = []
    for item in page.get("published_date_candidates") or []:
        if not isinstance(item, dict):
            continue
        raw = " ".join(str(item.get("raw") or "").split())
        method = str(item.get("method") or "").strip()
        if not raw or method not in DATE_METHOD_PRIORITY:
            continue
        parsed = _first_date(raw)
        if parsed:
            ranked.append((DATE_METHOD_PRIORITY[method], parsed, method, raw))
    if ranked:
        strongest = min(item[0] for item in ranked)
        strongest_rows = [item for item in ranked if item[0] == strongest]
        strongest_dates = {item[1] for item in strongest_rows}
        if len(strongest_dates) != 1:
            return None
        chosen_date = next(iter(strongest_dates))
        chosen = next(item for item in strongest_rows if item[1] == chosen_date)
        return {"date": chosen[1], "method": chosen[2], "raw": chosen[3]}

    text_dates = _all_dates(text)
    if len(text_dates) == 1:
        chosen_date = next(iter(text_dates))
        return {"date": chosen_date, "method": "unambiguous_page_text", "raw": chosen_date}
    return None


def _is_generic_cms_placeholder(title: str, text: str) -> bool:
    folded_title = _fold(title).strip(" !?.")
    folded_text = _fold(text)
    if folded_title in {value.strip(" !?.") for value in GENERIC_CMS_PLACEHOLDER_TITLES}:
        return True
    return sum(marker in folded_text for marker in GENERIC_CMS_PLACEHOLDER_MARKERS) >= 2


def _website_context(profile: dict[str, Any]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") or {}
    assessment = value.get("identity_assessment") or {}
    if website.get("status") != "available" or not assessment.get("publishable"):
        return None, []
    final_url = str(value.get("final_url") or website.get("source_url") or "").strip()
    if not final_url:
        return None, []
    pages = [page for page in (value.get("pages") or []) if isinstance(page, dict)]

    detail = ((profile.get("evidence") or {}).get("website_news_detail") or {})
    detail_value = detail.get("value") or {}
    detail_pages = [page for page in (detail_value.get("pages") or []) if isinstance(page, dict)]
    nominated = {
        str(item.get("url") or "").rstrip("/")
        for item in (value.get("news_detail_links") or [])
        if isinstance(item, dict) and item.get("url")
    }
    if (
        detail.get("status") == "available"
        and detail.get("source_type") == "verified_company_news_detail_candidate"
        and detail_pages
    ):
        page = detail_pages[0]
        page_url = str(page.get("url") or detail_value.get("final_url") or detail.get("source_url") or "").strip()
        if page_url.rstrip("/") in nominated and _same_verified_site(page_url, final_url):
            retained = dict(page)
            retained["c12_homepage_news_nomination"] = True
            pages.append(retained)
    return {"record": website, "final_url": final_url}, pages


def extract_strict_first_party_facts(profile: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Extract only explicit job detail/apply pages and dated company update details."""
    context, pages = _website_context(profile)
    if not context:
        return {"jobs": [], "updates": []}
    verified_url = str(context["final_url"])
    jobs: list[dict[str, Any]] = extract_current_first_party_jobs(profile)
    updates: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = {
        ("job", str(item.get("url") or "")) for item in jobs if item.get("url")
    }

    for page in pages:
        url = str(page.get("url") or "").strip()
        if not url.startswith(("http://", "https://")) or not _same_verified_site(url, verified_url):
            continue
        title = str(page.get("title") or "").strip()
        text = " ".join(
            part for part in (
                title,
                str(page.get("main_text_excerpt") or ""),
                str(page.get("identity_text_excerpt") or ""),
            ) if part
        )
        folded_url = _fold(url)
        folded_text = _fold(text)
        content_hash = str(page.get("content_sha256") or "").strip()

        has_job_path = any(marker in folded_url for marker in JOB_PATH_MARKERS)
        has_job_detail_url = _detail_page_url(
            url,
            generic_segments=GENERIC_JOB_PATH_SEGMENTS,
            allow_query_keys=JOB_DETAIL_QUERY_KEYS,
        )
        has_apply_action = any(marker in folded_text for marker in JOB_ACTION_MARKERS)
        has_job_detail = any(marker in folded_text for marker in JOB_DETAIL_MARKERS)
        if (
            has_job_path
            and has_job_detail_url
            and has_apply_action
            and has_job_detail
            and _specific_title(title, generic=GENERIC_JOB_TITLES)
        ):
            key = ("job", url)
            if key not in seen:
                seen.add(key)
                jobs.append(
                    {
                        "title": title,
                        "url": url,
                        "content_sha256": content_hash,
                        "evidence_span": f"{title}; explicit apply action present on verified company-owned role detail page"[:1000],
                    }
                )

        homepage_news_nomination = bool(page.get("c12_homepage_news_nomination"))
        has_update_path = any(marker in folded_url for marker in UPDATE_PATH_MARKERS) or homepage_news_nomination
        has_update_detail_url = _detail_page_url(url, generic_segments=GENERIC_UPDATE_PATH_SEGMENTS) or (
            homepage_news_nomination
            and _specific_non_root_page_url(url, generic_segments=GENERIC_UPDATE_PATH_SEGMENTS)
        )
        date_evidence = _select_publication_date(page, text)
        if (
            has_update_path
            and has_update_detail_url
            and date_evidence
            and _specific_title(title, generic=GENERIC_UPDATE_TITLES)
            and not _is_generic_cms_placeholder(title, text)
        ):
            key = ("update", url)
            if key not in seen:
                seen.add(key)
                published_date = date_evidence["date"]
                method = date_evidence["method"]
                raw = date_evidence["raw"]
                updates.append(
                    {
                        "title": title,
                        "url": url,
                        "published_date": published_date,
                        "date_extraction_method": method,
                        "date_evidence": raw,
                        "content_sha256": content_hash,
                        "evidence_span": (
                            f"{title}; published date {published_date}; "
                            f"date evidence {method}: {raw}"
                        )[:1000],
                    }
                )

    jobs.sort(key=lambda item: (item["title"].casefold(), item["url"]))
    updates.sort(key=lambda item: (str(item.get("published_date") or ""), item["title"].casefold(), item["url"]), reverse=True)
    return {"jobs": jobs, "updates": updates}


def _evidence_id(org: str, kind: str, item: dict[str, Any]) -> str:
    material = "|".join(
        (
            org,
            kind,
            str(item.get("url") or ""),
            str(item.get("content_sha256") or ""),
            str(item.get("title") or ""),
        )
    )
    return "ev-first-party-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def project_first_party_activity_claims(
    contract: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Attach strict first-party jobs/updates to an OUTPUT_CONTRACT object idempotently."""
    managed_fields = {"external.job_posting", "external.company_update"}
    claims = [dict(item) for item in (contract.get("claims") or [])]
    evidence = [dict(item) for item in (contract.get("evidence") or [])]

    removed_ids = {
        evidence_id
        for claim in claims
        if claim.get("field") in managed_fields
        for evidence_id in (claim.get("evidence_ids") or [])
    }
    claims = [claim for claim in claims if claim.get("field") not in managed_fields]
    still_referenced = {
        evidence_id
        for claim in claims
        for evidence_id in (claim.get("evidence_ids") or [])
    }
    evidence_by_id = {
        str(item.get("id")): item
        for item in evidence
        if item.get("id") and item.get("id") not in (removed_ids - still_referenced)
    }

    extracted = extract_strict_first_party_facts(profile)
    org = str(contract.get("organisation_number") or profile.get("organisation_number") or "")
    website = ((profile.get("evidence") or {}).get("website") or {})
    retrieved_at = website.get("retrieved_at")

    for item in extracted["jobs"]:
        evidence_id = _evidence_id(org, "job", item)
        evidence_by_id[evidence_id] = {
            "id": evidence_id,
            "source_url": item.get("evidence_url") or item["url"],
            "source_class": "company_owned",
            "retrieved_at": item.get("retrieved_at") or retrieved_at,
            "content_sha256": item.get("content_sha256"),
            "claim_span": item["evidence_span"],
        }
        job_value = {"title": item["title"], "url": item["url"]}
        if item.get("application_url"):
            job_value["application_url"] = item["application_url"]
        if item.get("deadline"):
            job_value["deadline"] = item["deadline"]
        claims.append(
            {
                "field": "external.job_posting",
                "value": job_value,
                "availability": "available",
                "confidence": 0.99,
                "evidence_ids": [evidence_id],
                "platform": "company_site",
                "signal_type": "job_posting",
                "claim_scope": item.get("claim_scope") or "Verified company-owned role detail page with a specific title, job detail marker and explicit apply action; generic careers pages excluded.",
            }
        )

    for item in extracted["updates"]:
        evidence_id = _evidence_id(org, "update", item)
        evidence_by_id[evidence_id] = {
            "id": evidence_id,
            "source_url": item["url"],
            "source_class": "company_owned",
            "retrieved_at": retrieved_at,
            "effective_at": item["published_date"],
            "content_sha256": item.get("content_sha256"),
            "claim_span": item["evidence_span"],
        }
        claims.append(
            {
                "field": "external.company_update",
                "value": {
                    "title": item["title"],
                    "url": item["url"],
                    "published_date": item["published_date"],
                },
                "availability": "available",
                "confidence": 0.99,
                "evidence_ids": [evidence_id],
                "platform": "company_site",
                "signal_type": "company_update",
                "claim_scope": "Dated article/update detail page retained from the exact verified company-owned website; section indexes and undated pages excluded.",
            }
        )

    return {
        **contract,
        "claims": claims,
        "evidence": sorted(evidence_by_id.values(), key=lambda item: str(item.get("id") or "")),
    }
