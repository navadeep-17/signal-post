from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import re
from typing import Any
from urllib.parse import urlparse

from .first_party_activity_provenance import project_first_party_activity_provenance


def _evidence_id(org: str, feed: dict[str, Any], entry: dict[str, Any]) -> str:
    material = "|".join(
        (
            org,
            str(feed.get("source_url") or ""),
            str(feed.get("content_sha256") or ""),
            str(entry.get("url") or ""),
            str(entry.get("published_date") or ""),
            str(entry.get("title") or ""),
        )
    )
    return "ev-first-party-feed-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").casefold().strip(".")
    except ValueError:
        return ""


def _same_verified_site(url: str, verified_url: str) -> bool:
    candidate = _host(url)
    verified = _host(verified_url)
    if not candidate or not verified:
        return False
    return candidate == verified or candidate.endswith("." + verified) or verified.endswith("." + candidate)


def _valid_iso_date(value: str) -> bool:
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return False
    return parsed.isoformat() == value





def _retrieval_date(value: str) -> date | None:
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





def _retrieval_date(value: str) -> date | None:
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


def _qualified_feed_entries(profile: dict[str, Any]) -> list[dict[str, Any]]:
    evidence_map = profile.get("evidence") or {}
    website = evidence_map.get("website") or {}
    website_value = website.get("value") or {}
    assessment = website_value.get("identity_assessment") or {}
    feed = evidence_map.get("website_activity_feed") or {}
    feed_value = feed.get("value") or {}

    if website.get("status") != "available" or not assessment.get("publishable"):
        return []
    if feed.get("status") != "available":
        return []
    if feed.get("source_type") != "verified_company_activity_feed":
        return []

    feed_url = str(feed.get("source_url") or "").strip()
    feed_hash = str(feed.get("content_sha256") or "").strip().casefold()
    retrieved_at = str(feed.get("retrieved_at") or "").strip()
    observed_on = _retrieval_date(retrieved_at)
    if (
        not feed_url.startswith(("http://", "https://"))
        or not re.fullmatch(r"[0-9a-f]{64}", feed_hash)
        or observed_on is None
    ):
        return []

    verified_url = str(website_value.get("final_url") or website.get("source_url") or "").strip()
    observed_on = _retrieval_date(retrieved_at)
    if observed_on is None:
        return []
    retained_verified_url = str(feed_value.get("verified_website_url") or "").strip()
    if (
        not verified_url
        or retained_verified_url.rstrip("/") != verified_url.rstrip("/")
        or not _same_verified_site(feed_url, verified_url)
    ):
        return []

    rows: list[dict[str, Any]] = []
    for entry in feed_value.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        title = str(entry.get("title") or "").strip()
        article_url = str(entry.get("url") or "").strip()
        published_date = str(entry.get("published_date") or "").strip()
        evidence_span = str(entry.get("evidence_span") or "").strip()
        if not title or not article_url.startswith(("http://", "https://")):
            continue
        if (
            not _same_verified_site(article_url, verified_url)
            or not _valid_iso_date(published_date)
            or date.fromisoformat(published_date) > observed_on
            or not evidence_span
        ):
            continue
        rows.append(dict(entry))
    return rows


def project_first_party_feed_updates(
    contract: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Append dated feed-backed company updates without replacing page-backed updates.

    Identity is inherited only from an already exact-verified website. The cited evidence
    remains the RSS/Atom snapshot that actually supplied the title, article URL and date;
    the article destination is never represented as fetched unless another collector did
    fetch it independently.

    Before feed projection, the V8 first-party postprojection also closes evaluator-visible
    provenance on older page-backed job/update rows using only their existing verified-site
    evidence. That pass is zero-network and cannot add or remove claims.
    """
    org = str(contract.get("organisation_number") or profile.get("organisation_number") or "")
    if not org or org != str(profile.get("organisation_number") or ""):
        return contract

    contract = project_first_party_activity_provenance(contract)
    entries = _qualified_feed_entries(profile)
    if not entries:
        return contract

    feed = ((profile.get("evidence") or {}).get("website_activity_feed") or {})
    website = ((profile.get("evidence") or {}).get("website") or {})
    identity_assessment = ((website.get("value") or {}).get("identity_assessment") or {})
    claims = [dict(item) for item in (contract.get("claims") or [])]
    evidence = [dict(item) for item in (contract.get("evidence") or [])]
    evidence_by_id = {str(item.get("id")): item for item in evidence if item.get("id")}

    existing_update_keys = {
        (
            str((claim.get("value") or {}).get("url") or ""),
            str((claim.get("value") or {}).get("published_date") or ""),
            str((claim.get("value") or {}).get("title") or ""),
        )
        for claim in claims
        if claim.get("field") == "external.company_update" and isinstance(claim.get("value"), dict)
    }

    for entry in entries:
        key = (
            str(entry.get("url") or ""),
            str(entry.get("published_date") or ""),
            str(entry.get("title") or ""),
        )
        if key in existing_update_keys:
            continue
        evidence_id = _evidence_id(org, feed, entry)
        evidence_by_id[evidence_id] = {
            "id": evidence_id,
            "source_url": feed.get("source_url"),
            "source_class": "company_owned",
            "retrieved_at": feed.get("retrieved_at"),
            "effective_at": entry.get("published_date"),
            "content_sha256": feed.get("content_sha256"),
            "claim_span": entry.get("evidence_span"),
            "identity_proof": identity_assessment,
            "extraction_method": "verified_same_site_rss_atom_entry_v1",
        }
        claims.append(
            {
                "field": "external.company_update",
                "value": {
                    "title": entry.get("title"),
                    "url": entry.get("url"),
                    "published_date": entry.get("published_date"),
                },
                "availability": "available",
                "confidence": 0.99,
                "evidence_ids": [evidence_id],
                "platform": "company_site",
                "signal_type": "company_update",
                "claim_scope": (
                    "Dated same-site RSS/Atom entry from an exact verified company-owned website; "
                    "feed snapshot supplies title, article URL and publication/update date; cross-domain and undated entries excluded."
                ),
            }
        )
        existing_update_keys.add(key)

    return {
        **contract,
        "claims": claims,
        "evidence": sorted(evidence_by_id.values(), key=lambda item: str(item.get("id") or "")),
    }
