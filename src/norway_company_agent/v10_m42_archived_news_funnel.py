"""M42 read-only archived dated-company-news funnel, not a score simulation.

Only source snapshots that were ALREADY CONSUMED by M19-A/B and M20-A V8.
Never return company identifiers, titles, URLs, article excerpts or archive rows.
Zero external requests; no new claims are published; no score improvement proven.

The stage labels distinguish observed evidence, extraction eligibility and current
claim publication. A news *nomination* is NOT evidence of a dated news article.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from .first_party_activity import extract_strict_first_party_facts
from .first_party_feed_contract import _qualified_feed_entries, project_first_party_feed_updates
from .external_precision_guard import project_external_precision_guard

def _available_updates(contract:dict[str,Any])->list[dict[str,Any]]:
    return [x for x in (contract.get("claims") or [])
            if isinstance(x,dict) and x.get("field")=="external.company_update"
            and x.get("availability")=="available"]

def _keys(claims:list[dict[str,Any]])->set[tuple[str,str,str]]:
    result=set()
    for x in claims:
        v=x.get("value") or {}
        if not isinstance(v,dict):
            raise ValueError("Malformed published update value")
        result.add((str(v.get("title") or ""),str(v.get("url") or ""),
                    str(v.get("published_date") or "")))
    return result

def news_root_cause_counts(
    contracts:list[dict[str,Any]],profiles:list[dict[str,Any]]
)->dict[str,Any]:
    if not contracts or len(contracts)!=len(profiles) or len(contracts)>300:
        raise ValueError("Unexpected consumed cohort length")
    by_profile={}
    for p in profiles:
        if not isinstance(p,dict):
            raise ValueError("Malformed retained profile")
        org=p.get("organisation_number")
        if not isinstance(org,str) or len(org)!=9 or not org.isascii() or not org.isdecimal() or org in by_profile:
            raise ValueError("Duplicate or invalid retained company")
        by_profile[org]=p
    by_contract={}
    for c in contracts:
        if not isinstance(c,dict):
            raise ValueError("Malformed archived contract")
        org=c.get("organisation_number")
        if org in by_contract or org not in by_profile:
            raise ValueError("Cross-company or duplicate archived output")
        by_contract[org]=c
    if set(by_contract)!=set(by_profile):
        raise ValueError("Company sets do not match exactly")

    stages=Counter()
    feed_status=Counter()
    page_status=Counter()
    projection=Counter()
    for org in sorted(by_contract):
        c=by_contract[org]
        p=by_profile[org]
        e=p.get("evidence") or {}
        if not isinstance(e,dict):
            raise ValueError("Malformed retained evidence")
        site=e.get("website") or {}
        if not isinstance(site,dict):
            raise ValueError("Malformed retained website")
        site_value=site.get("value") or {}
        assessment=site_value.get("identity_assessment") or {}
        if not isinstance(site_value,dict) or not isinstance(assessment,dict):
            raise ValueError("Malformed retained website identity")
        exact=site.get("status")=="available" and assessment.get("publishable") is True
        stages["total_companies"]+=1
        stages["exact_verified_sites"]+=int(exact)
        news=site_value.get("news_detail_links") or []
        if not isinstance(news,list):
            raise ValueError("Malformed homepage news nominations")
        stages["homepages_with_news_link_nominations"]+=int(exact and bool(news))
        stages["news_link_nominations_count"]+=len(news) if exact else 0
        detail=e.get("website_news_detail") or {}
        if not isinstance(detail,dict):
            raise ValueError("Malformed retained news page")
        if exact:
            page_status[str(detail.get("status") or "no_retained_news_detail")]+=1
        detail_available=exact and detail.get("status")=="available"
        stages["retained_successful_news_detail_pages"]+=int(detail_available)
        detail_value=detail.get("value") or {}
        pages=(detail_value.get("pages") or []) if isinstance(detail_value,dict) else []
        stages["retained_news_detail_pages_with_page_data"]+=int(detail_available and bool(pages))

        feed=e.get("website_activity_feed") or {}
        if not isinstance(feed,dict):
            raise ValueError("Malformed first-party feed record")
        feed_value=feed.get("value") or {}
        if not isinstance(feed_value,dict):
            raise ValueError("Malformed first-party feed content")
        if exact:
            feed_status[str(feed.get("status") or "no_retained_feed_attempt")]+=1
        stages["exact_sites_with_retained_feed_evidence"]+=int(exact and bool(feed))
        stages["available_first_party_feeds"]+=int(exact and feed.get("status")=="available")
        accepted=_qualified_feed_entries(p)
        stages["feed_companies_with_strict_entries"]+=int(exact and bool(accepted))
        stages["feed_strict_entry_count"]+=len(accepted) if exact else 0
        extracted=extract_strict_first_party_facts(p)
        updates=extracted["updates"]
        stages["page_companies_with_strict_dated_updates"]+=int(bool(updates))
        stages["page_strict_dated_update_count"]+=len(updates)

        original=_available_updates(c)
        stages["companies_with_published_company_updates"]+=int(bool(original))
        stages["published_company_update_claims"]+=len(original)
        by_evidence={row.get("id"):row for row in c.get("evidence") or [] if isinstance(row,dict)}
        origin_methods=set()
        for claim in original:
            methods={str((by_evidence.get(ref) or {}).get("extraction_method") or "")
                     for ref in (claim.get("evidence_ids") or [])}
            if "verified_same_site_rss_atom_entry_v1" in methods:
                origin_methods.add("feed")
                stages["published_feed_update_claims"]+=1
            else:
                origin_methods.add("page_or_unclassified")
                stages["published_page_or_unclassified_update_claims"]+=1
        stages["companies_with_published_feed_updates"]+=int("feed" in origin_methods)
        stages["companies_with_published_page_or_unclassified_updates"]+=int("page_or_unclassified" in origin_methods)

        # Offline replay of exactly the submitted V8 postprojection and narrow
        # precision veto. Compare typed values, NEVER count a candidate as fact.
        with_feed=project_first_party_feed_updates(c,p)
        with_guard=project_external_precision_guard(with_feed)
        before=_keys(original)
        intermediate=_keys(_available_updates(with_feed))
        after=_keys(_available_updates(with_guard))
        projection["replay_new_update_candidate_claims_pre_guard"]+=len(intermediate-before)
        projection["replay_new_update_candidate_companies_pre_guard"]+=int(bool(intermediate-before))
        projection["replay_new_update_candidate_claims_post_guard"]+=len(after-before)
        projection["replay_new_update_candidate_companies_post_guard"]+=int(bool(after-before))
        projection["precision_guard_removed_update_claims"]+=len(intermediate-after)
        projection["precision_guard_removed_update_companies"]+=int(bool(intermediate-after))
        projection["original_available_update_claims_lost_in_replay"]+=len(before-after)
        projection["original_available_update_companies_lost_in_replay"]+=int(bool(before-after))

    assert stages["exact_verified_sites"]<=stages["total_companies"]
    assert stages["companies_with_published_company_updates"]<=stages["total_companies"]
    assert stages["published_feed_update_claims"]+stages["published_page_or_unclassified_update_claims"]==stages["published_company_update_claims"]
    return {
        "schema":"m42_prior_consumed_dated_news_funnel_v1",
        "source":"M19_A_M19_B_M20_A_SHA_FROZEN_PRIOR_CONSUMED_V8_ONLY",
        "stage_counts":dict(sorted(stages.items())),
        "verified_site_feed_status_counts":dict(sorted(feed_status.items())),
        "verified_site_news_detail_status_counts":dict(sorted(page_status.items())),
        "current_projector_read_only_replay":dict(sorted(projection.items())),
        "proven_new_correct_company_news_claims":0,
        "official_c300_news_reference_match_measured":False,
        "official_score_delta_measured":False,
        "fresh_independent_transfer_measured":False,
        "new_company_web_requests":0,
        "new_provider_requests":0,
        "third_party_cost_usd":0,
        "main_or_submitted_sha_modified":False,
    }
