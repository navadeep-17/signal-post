#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one anchor, found {count}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_final_site() -> None:
    path = ROOT / "src" / "norway_company_agent" / "final_site_discovery.py"
    replace_once(
        path,
        "from .homepage_news_signal import extract_news_detail_links\nfrom .identity import apply_website_identity_gate\n",
        "from .homepage_news_signal import extract_news_detail_links\nfrom .job_surface_signal import extract_homepage_hiring_signal, extract_job_listing_candidates\nfrom .identity import apply_website_identity_gate\n",
    )
    replace_once(
        path,
        "        published_date_candidates = _page_date_candidates(soup)\n        digest = hashlib.sha256(raw).hexdigest()\n",
        "        published_date_candidates = _page_date_candidates(soup)\n        active_hiring_signal = extract_homepage_hiring_signal(final_url=final_url, soup=soup)\n        job_listing_candidates = extract_job_listing_candidates(\n            final_url=final_url, soup=soup, structured=structured\n        )\n        digest = hashlib.sha256(raw).hexdigest()\n",
    )
    replace_once(
        path,
        '            "published_date_candidates": published_date_candidates,\n            "social_links": _social_links(final_url, soup),\n',
        '            "published_date_candidates": published_date_candidates,\n            "active_hiring_signal": active_hiring_signal,\n            "job_listing_candidates": job_listing_candidates,\n            "social_links": _social_links(final_url, soup),\n',
    )

    careers_helper = '''def _careers_link_priority(item: dict[str, Any]) -> tuple[int, int, str]:
    url = str(item.get("url") or "")
    marker = str(item.get("marker") or "").casefold()
    path = urllib.parse.unquote(urllib.parse.urlparse(url).path).casefold()
    haystack = f"{path} {marker}"
    if "ledige-stillinger" in haystack or "ledige stillinger" in haystack:
        priority = 0
    elif any(term in haystack for term in ("/jobs", "/jobber", "vacanc", "stillinger")):
        priority = 1
    else:
        priority = 2
    return priority, len(path), url


def _attach_bounded_careers_surface(
    primary: dict[str, Any],
    *,
    evidence_map: dict[str, Any],
    total: dict[str, Any],
    timeout: float,
) -> bool:
    """Spend the final two site requests on one active first-party careers surface.

    A generic careers link never triggers a follow-up. The exact homepage must itself
    expose an explicit positive vacancy count. Homepage role observations are already
    retained by the first fetch, so they do not consume this slot.
    """
    if not _publishable(primary):
        return False
    if int(total.get("requests") or 0) + 2 > MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE:
        return False
    value = primary.get("value") or {}
    if value.get("job_listing_candidates"):
        return False
    hiring = value.get("active_hiring_signal") or {}
    if not hiring.get("active_vacancies") or int(hiring.get("active_vacancy_count") or 0) <= 0:
        return False
    links = [item for item in (value.get("careers_links") or []) if isinstance(item, dict) and item.get("url")]
    if not links:
        return False

    candidate = sorted(links, key=_careers_link_priority)[0]
    candidate_url = str(candidate["url"])
    total["careers_surface_attempted"] = True
    total["careers_surface_candidate_url"] = candidate_url
    surface, ops = fetch_bounded_homepage(
        candidate_url,
        source_type="verified_company_careers_surface_candidate",
        timeout=timeout,
    )
    _add_metrics(total, ops)

    primary_domain = str(value.get("registered_domain") or "")
    surface_value = surface.get("value") or {}
    surface_domain = str(surface_value.get("registered_domain") or "")
    accepted = bool(
        surface.get("status") == "available"
        and primary_domain
        and surface_domain == primary_domain
        and str(surface_value.get("final_url") or surface.get("source_url") or "").rstrip("/")
        == candidate_url.rstrip("/")
    )
    if accepted:
        evidence_map["website_careers_surface"] = surface
        total["careers_surface_retained"] = True
        return True

    total["careers_surface_retained"] = False
    return False


'''
    replace_once(
        path,
        "def _attach_bounded_news_detail(\n",
        careers_helper + "def _attach_bounded_news_detail(\n",
    )
    replace_once(
        path,
        '        "news_detail_attempted": False,\n        "news_detail_retained": False,\n',
        '        "careers_surface_attempted": False,\n        "careers_surface_retained": False,\n        "news_detail_attempted": False,\n        "news_detail_retained": False,\n',
    )
    replace_once(
        path,
        '''            _attach_bounded_news_detail(
                registry_terminal, evidence_map=evidence_map, total=total, timeout=timeout
            )
''',
        '''            if not _attach_bounded_careers_surface(
                registry_terminal, evidence_map=evidence_map, total=total, timeout=timeout
            ):
                _attach_bounded_news_detail(
                    registry_terminal, evidence_map=evidence_map, total=total, timeout=timeout
                )
''',
    )
    replace_once(
        path,
        '''                _attach_bounded_news_detail(
                    candidate_record, evidence_map=evidence_map, total=total, timeout=timeout
                )
''',
        '''                if not _attach_bounded_careers_surface(
                    candidate_record, evidence_map=evidence_map, total=total, timeout=timeout
                ):
                    _attach_bounded_news_detail(
                        candidate_record, evidence_map=evidence_map, total=total, timeout=timeout
                    )
''',
    )
    replace_once(
        path,
        '''                _attach_bounded_news_detail(
                    (row.get("evidence") or {}).get("website") or candidate_record,
                    evidence_map=evidence_map,
                    total=total,
                    timeout=timeout,
                )
''',
        '''                selected_website = (row.get("evidence") or {}).get("website") or candidate_record
                if not _attach_bounded_careers_surface(
                    selected_website,
                    evidence_map=evidence_map,
                    total=total,
                    timeout=timeout,
                ):
                    _attach_bounded_news_detail(
                        selected_website,
                        evidence_map=evidence_map,
                        total=total,
                        timeout=timeout,
                    )
''',
    )


def patch_activity() -> None:
    path = ROOT / "src" / "norway_company_agent" / "first_party_activity.py"
    replace_once(
        path,
        "from urllib.parse import parse_qs, urlparse\n\n\nJOB_PATH_MARKERS",
        "from urllib.parse import parse_qs, urlparse\n\nfrom .first_party_jobs import extract_current_first_party_jobs\n\n\nJOB_PATH_MARKERS",
    )
    replace_once(
        path,
        '''    jobs: list[dict[str, Any]] = []
    updates: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
''',
        '''    jobs: list[dict[str, Any]] = extract_current_first_party_jobs(profile)
    updates: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = {
        ("job", str(item.get("url") or "")) for item in jobs if item.get("url")
    }
''',
    )
    replace_once(
        path,
        '''        evidence_by_id[evidence_id] = {
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
                "claim_scope": "Verified company-owned role detail page with a specific title, job detail marker and explicit apply action; generic careers pages excluded.",
            }
        )
''',
        '''        evidence_by_id[evidence_id] = {
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
''',
    )


def main() -> None:
    patch_final_site()
    patch_activity()


if __name__ == "__main__":
    main()
