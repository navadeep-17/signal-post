from __future__ import annotations

import hashlib
import re
from typing import Any
from urllib.parse import urlparse


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
DATE_PATTERNS = (
    re.compile(r"\b(20\d{2}-[01]\d-[0-3]\d)\b"),
    re.compile(r"\b([0-3]?\d[./-][01]?\d[./-]20\d{2})\b"),
    re.compile(
        r"\b([0-3]?\d\s+(?:jan(?:uar)?|feb(?:ruar)?|mar(?:s|ch)?|apr(?:il)?|mai|may|jun(?:i|e)?|jul(?:i|y)?|aug(?:ust)?|sep(?:tember)?|okt(?:ober)?|oct(?:ober)?|nov(?:ember)?|des(?:ember)?|dec(?:ember)?)\s+20\d{2})\b",
        re.IGNORECASE,
    ),
)


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
    # Titles produced by CMSs often append the company/site name. Requiring at least two
    # lexical tokens keeps one-word section labels from becoming facts while retaining
    # concrete role/update titles.
    words = re.findall(r"[\wæøåÆØÅ-]+", title, flags=re.UNICODE)
    return len(words) >= 2


def _first_date(text: str) -> str | None:
    for pattern in DATE_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return None


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
    return {"record": website, "final_url": final_url}, pages


def extract_strict_first_party_facts(profile: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Extract only explicit job cards/apply pages and dated company updates.

    This function performs no network access. It operates only on pages retained by the
    already-qualified company-site crawl and only when the website identity assessment is
    publishable. A generic careers/news index never becomes a fact by itself.
    """

    context, pages = _website_context(profile)
    if not context:
        return {"jobs": [], "updates": []}
    verified_url = str(context["final_url"])
    jobs: list[dict[str, Any]] = []
    updates: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

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
        has_apply_action = any(marker in folded_text for marker in JOB_ACTION_MARKERS)
        has_job_detail = any(marker in folded_text for marker in JOB_DETAIL_MARKERS)
        if (
            has_job_path
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
                        "evidence_span": f"{title}; explicit apply action present on verified company-owned role page"[:1000],
                    }
                )

        has_update_path = any(marker in folded_url for marker in UPDATE_PATH_MARKERS)
        published_date = _first_date(text)
        if (
            has_update_path
            and published_date
            and _specific_title(title, generic=GENERIC_UPDATE_TITLES)
        ):
            key = ("update", url)
            if key not in seen:
                seen.add(key)
                updates.append(
                    {
                        "title": title,
                        "url": url,
                        "published_date": published_date,
                        "content_sha256": content_hash,
                        "evidence_span": f"{title}; published date {published_date}"[:1000],
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
            "source_url": item["url"],
            "source_class": "company_owned",
            "retrieved_at": retrieved_at,
            "content_sha256": item.get("content_sha256"),
            "claim_span": item["evidence_span"],
        }
        claims.append(
            {
                "field": "external.job_posting",
                "value": {"title": item["title"], "url": item["url"]},
                "availability": "available",
                "confidence": 0.99,
                "evidence_ids": [evidence_id],
                "platform": "company_site",
                "signal_type": "job_posting",
                "claim_scope": "Verified company-owned role page with a specific title, job detail marker and explicit apply action; generic careers pages excluded.",
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
                "claim_scope": "Dated article/update page retained from the exact verified company-owned website; undated index pages excluded.",
            }
        )

    return {
        **contract,
        "claims": claims,
        "evidence": sorted(evidence_by_id.values(), key=lambda item: str(item.get("id") or "")),
    }
