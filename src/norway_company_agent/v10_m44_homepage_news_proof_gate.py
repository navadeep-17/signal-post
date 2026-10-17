"""M44 private, no-network proof triage of PREVIOUSLY CONSUMED homepage news nominations.

A nomination is NEVER a publishable news claim, even when all structural checks pass.
Review-only observations are not counted as a verified article or score improvement.
No company IDs, article URLs, titles, raw snippets or source text are returned.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta, timezone
import re
from typing import Any
from urllib.parse import urlparse

from .final_site_discovery import _explicit_org_numbers
from .first_party_activity import _all_dates
from .homepage_news_signal import GENERIC_NEWS_TITLES
from .v10_m42_archived_news_funnel import news_root_cause_counts

_HEX=re.compile(r"^[0-9a-fA-F]{64}$")
_NINE=re.compile(r"^[0-9]{9}$")
_SAME_DOMAIN_TOO_WEAK="same_registered_domain_only_not_same_host"
_PUBLISH_UNSUPPORTED="not_publishable_from_homepage_nomination"
_BOUNDED_MAX_CONTEXT=500

def _host(url:Any)->str:
    try:
        parsed=urlparse(str(url or ""))
    except ValueError:
        return ""
    return (parsed.hostname or "").casefold().strip(".") if parsed.scheme=="https" else ""

def _retrieved_day(value:Any)->date|None:
    try:
        dt=datetime.fromisoformat(str(value or "").replace("Z","+00:00"))
        if dt.tzinfo is None:
            return None
        return dt.astimezone(timezone.utc).date()
    except (TypeError,ValueError,OverflowError):
        return None

def _unique_card_day(text:str,observed:date|None)->str|None:
    if not text or len(text)>_BOUNDED_MAX_CONTEXT or observed is None:
        return None
    dates=_all_dates(text)
    if len(dates)!=1:
        return None
    value=next(iter(dates))
    try:
        day=date.fromisoformat(value)
    except ValueError:
        return None
    if day>observed or day<observed-timedelta(days=366*5):
        return None
    return value

def _nomination_reasons(
    org:str, website:dict[str,Any], nomination:dict[str,Any]
)->set[str]:
    """Strict, non-claim triage. Report only fixed failure reasons."""
    value=website.get("value") or {}
    reasons:set[str]=set()
    if website.get("status")!="available" or (value.get("identity_assessment") or {}).get("publishable") is not True:
        return {"website_not_exact_verified"}
    url=str(value.get("final_url") or website.get("source_url") or "")
    actual_hash=str(website.get("content_sha256") or "")
    value_hash=str(value.get("content_sha256") or "")
    observed=_retrieved_day(website.get("retrieved_at"))
    if not _NINE.fullmatch(org):
        reasons.add("invalid_target_organisation")
    if not url.startswith("https://") or not _host(url):
        reasons.add("homepage_url_not_eligible_https")
    if not _HEX.fullmatch(actual_hash) or (value_hash and value_hash!=actual_hash):
        reasons.add("homepage_hash_missing_or_inconsistent")
    if observed is None:
        reasons.add("homepage_retrieval_time_unverified")
    n_url=str(nomination.get("url") or "")
    n_home=str(nomination.get("homepage_url") or "")
    n_hash=str(nomination.get("homepage_content_sha256") or "")
    if n_home.rstrip("/")!=url.rstrip("/") or n_hash.casefold()!=actual_hash.casefold():
        reasons.add("nomination_homepage_url_or_hash_mismatch")
    if not n_url.startswith("https://") or not _host(n_url) or _host(n_url)!=_host(url):
        reasons.add("article_url_not_same_exact_https_host")
    if nomination.get("nomination_only") is not True:
        reasons.add("nomination_semantics_missing")
    text=" ".join(str(nomination.get("dated_context") or "").split())
    if not text:
        reasons.add("no_homepage_card_local_date")
    elif _unique_card_day(text,observed) is None:
        reasons.add("card_date_missing_ambiguous_future_or_stale")
    anchor=" ".join(str(nomination.get("anchor_text") or "").split())
    if not anchor or len(anchor)<12 or len(anchor)>180 or anchor.casefold().strip(" -|:!?.") in GENERIC_NEWS_TITLES:
        reasons.add("no_specific_anchor_title")
    if not text or not anchor or anchor.casefold() not in text.casefold():
        reasons.add("anchor_title_not_in_local_dated_card")
    ids=_explicit_org_numbers(website)
    if ids!={org}:
        reasons.add("homepage_missing_exclusive_explicit_legal_id")
    return reasons

def archived_nomination_gate(
    contracts:list[dict[str,Any]], profiles:list[dict[str,Any]]
)->dict[str,Any]:
    # Baseline validator ensures 9-digit exact company sets, duplicates veto, and
    # published claims invariance in this prior-consumed data.
    baseline=news_root_cause_counts(contracts,profiles)
    categories=Counter()
    exact_homepages=0
    nominated_homepages=0
    total_links=0
    review_ready=0
    all_reasons=Counter()
    for profile in profiles:
        org=profile["organisation_number"]
        website=(profile.get("evidence") or {}).get("website") or {}
        value=website.get("value") or {}
        if website.get("status")!="available" or (value.get("identity_assessment") or {}).get("publishable") is not True:
            continue
        exact_homepages+=1
        links=value.get("news_detail_links") or []
        if not isinstance(links,list):
            raise ValueError("Invalid archived news links type")
        if links:
            nominated_homepages+=1
        for row in links:
            if not isinstance(row,dict):
                raise ValueError("Invalid archived nomination row")
            total_links+=1
            reasons=_nomination_reasons(org,website,row)
            if not reasons:
                categories["all_homepage_gate_conditions_passed_only"]=1+categories["all_homepage_gate_conditions_passed_only"]
                review_ready+=1
            else:
                for reason in reasons:
                    all_reasons[reason]+=1
            categories["nomination_only_not_article_proof"]+=1
    if exact_homepages!=baseline["stage_counts"]["exact_verified_sites"]:
        raise ValueError("Inconsistent original exact website count")
    if nominated_homepages!=baseline["stage_counts"]["homepages_with_news_link_nominations"]:
        raise ValueError("Inconsistent original nominated website count")
    if total_links!=baseline["stage_counts"]["news_link_nominations_count"]:
        raise ValueError("Inconsistent original nominated URL count")
    if sum(all_reasons.values())==0 and total_links and review_ready!=total_links:
        raise ValueError("Invalid stage arithmetic")
    return {
        "schema":"m44_prior_consumed_homepage_news_nomination_source_gate_v1",
        "archived_original_companies":len(profiles),
        "exact_verified_websites":exact_homepages,
        "news_nominating_websites":nominated_homepages,
        "nominated_urls":total_links,
        "nomination_failure_reason_counts":dict(sorted(all_reasons.items())),
        "nominated_urls_passing_all_homepage_structural_checks_for_review":review_ready,
        "independently_fetched_and_validated_article_pages":baseline["stage_counts"]["retained_successful_news_detail_pages"],
        "new_proven_eligible_dated_news_facts":0,
        "official_c300_score_delta_measured":False,
        "strict_news_claim_publications":0,
        "requires_independent_detail_article_and_human_review":True,
        "consumed_evidence_not_clean_transfer":True,
        "new_website_or_provider_requests":0,
        "production_files_modified":False
    }
