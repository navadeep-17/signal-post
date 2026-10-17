"""M43: evidence-grounded failure categories for M42 first-party dated-news funnel.

Offline ONLY. The sole purpose is to decide whether existing retained source
proof supports a no-network fix. No inferred title/date/job or company identity.
No org numbers, URLs, notes, site source, or company-level rows in output.
"""
from __future__ import annotations
from collections import Counter
from typing import Any

def _status_reason(status:str,note:str)->str:
    """Classify known collector statuses into fixed, privacy-safe categories."""
    value=note.casefold()
    if status=="available":
        return "eligible_feed_with_dated_entries"
    if status=="not_found":
        if value.startswith("http 404") or value.startswith("http 410"):
            return "http_404_or_410"
        if "contains no qualified current dated same-site entries" in value:
            return "fetched_or_parsed_but_no_eligible_entries"
        if "cannot nominate a same-site feed candidate" in value:
            return "invalid_verified_url_for_feed_nomination"
        return "other_not_found_no_specific_recoverable_source"
    if status=="source_error":
        if value.startswith("http "):
            return "non_404_http_error"
        return "network_or_parsing_source_exception"
    if status=="blocked":
        if "robot" in value:
            return "robots_blocked"
        if "exceeds byte limit" in value:
            return "feed_byte_limit_blocked"
        return "other_safety_block"
    return "other_retained_status"

def source_failure_categories(
    contracts:list[dict[str,Any]],profiles:list[dict[str,Any]]
)->dict[str,Any]:
    """Aggregate source failure types for *exact same* profile/org cohorts."""
    from .v10_m42_archived_news_funnel import news_root_cause_counts
    # Strong deterministic join, duplicates and references veto before counting.
    baseline=news_root_cause_counts(contracts,profiles)
    categories=Counter()
    intersections=Counter()
    seen=0
    for p in profiles:
        e=p.get("evidence") or {}
        site=e.get("website") or {}
        val=site.get("value") or {}
        identity=val.get("identity_assessment") or {}
        if site.get("status")!="available" or identity.get("publishable") is not True:
            continue
        seen+=1
        nominated=bool(val.get("news_detail_links") or [])
        feed=e.get("website_activity_feed") or {}
        if not feed:
            reason="no_retained_attempt_cannot_attribute_cause"
        else:
            reason=_status_reason(str(feed.get("status") or ""),str(feed.get("note") or ""))
        categories[reason]+=1
        intersections["news_nominated_sites"]+=int(nominated)
        intersections["news_nominated_sites_with_no_retained_detail"]+=int(
            nominated and (e.get("website_news_detail") or {}).get("status")!="available"
        )
        intersections["news_nominated_sites_with_missing_feed_attempt"]+=int(
            nominated and not bool(feed)
        )
        intersections["news_nominated_sites_with_feed_available"]+=int(
            nominated and feed.get("status")=="available"
        )
        intersections["news_nominated_sites_with_feed_not_found"]+=int(
            nominated and feed.get("status")=="not_found"
        )
        intersections["news_nominated_sites_with_feed_source_error"]+=int(
            nominated and feed.get("status")=="source_error"
        )
    if seen!=baseline["stage_counts"]["exact_verified_sites"]:
        raise ValueError("Verified site denominator mismatch")
    if sum(categories.values())!=seen:
        raise ValueError("Incomplete exact-site source status categories")
    return {
        "schema":"m43_archived_news_source_failure_classification_v1",
        "basis":"same_SHA_PINNED_previously_consumed_300_V8_sources",
        "exact_verified_sites":seen,
        "source_reasons":dict(sorted(categories.items())),
        "news_nomination_intersections":dict(sorted(intersections.items())),
        "missing_retained_source_is_not_proof_of_absence":True,
        "no_fetch_no_proven_new_scored_news":True,
        "eligible_existing_claims_lost_in_projection":baseline["current_projector_read_only_replay"].get(
            "original_available_update_claims_lost_in_replay",0
        ),
        "requests_to_companies":0,
        "paid_provider_requests":0,
        "official_score_delta":None,
        "production_changed":False,
    }
