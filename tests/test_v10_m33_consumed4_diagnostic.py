"""M33: mocked transport only, frozen historical 20 and hard four-search ceiling."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"scripts"),str(ROOT/"src")]
from run_v10_m33_consumed4_diagnostic import (
    _assert_frozen_history, diagnose_one, diagnostic,
)
from norway_company_agent.tavily_bounded_transport import SearchResult

M=json.loads((ROOT/"evaluation/v10_m24_consumed_dev_20.json").read_text())
IDS=[n for group in ("m19_a","m19_b","m20_a") for n in M["selected_per_cohort"][group]]

def profiles():
    return [{"organisation_number":n,"name":"NORDLYS MARIN TEKNOLOGI AS",
             "municipality":"TROMSO","website":""} for n in IDS]

def history():
    return {"schema":"m26_consumed_development_manual_review_only",
            "type":"PREVIOUSLY_CONSUMED_NOT_FRESH",
            "selection_sha256":M["selected_list_sha256"],
            "requested_companies":20,"attempted_companies":20,
            "aborted":False,"published_company_claims":0,
            "manually_reviewable_exact_org_sites":0,"qualified_v8_modified":False,
            "rows":[{"organisation_number":n,"status":("no_candidate_qualified_for_independent_fetch"
                    if i<17 else "first_party_identity_rejected"),"published_claims":0}
                    for i,n in enumerate(IDS)]}

def test_freezes_existing_four_abstainers():
    x=_assert_frozen_history(profiles(),history())
    assert len(x)==4
    assert [p["organisation_number"] for p in x]==IDS[:4]

def test_history_wrong_order_and_new_results_fail_closed():
    import pytest
    p=profiles()
    with pytest.raises(ValueError): _assert_frozen_history(p[::-1],history())
    h=history();h["rows"][0]["status"]="manual_exact_org_site_review_required"
    with pytest.raises(ValueError): _assert_frozen_history(p,h)

def test_dry_run_cannot_call_network():
    def deny(*a,**k): raise AssertionError("Network called")
    x=diagnostic(profiles(),history(),live=False,api_key="ignored",
                 search_fn=deny,fetch_fn=deny)
    assert x["attempted"]==0 and x["reserved_logical_http"]==0
    assert x["new_published_claims"]==0

def test_no_key_fails_before_search():
    import pytest
    with pytest.raises(ValueError):
        diagnostic(profiles(),history(),live=True,api_key="",
                   search_fn=lambda *a,**k:1/0)

def test_empty_results_no_first_party_fetch():
    calls=[]
    def empty(*a,**k):
        calls.append("search")
        return SearchResult("ok_transient_candidates_only",1,2,{"results":[]})
    x=diagnose_one(profiles()[0],api_key="synthetic",
                   search_fn=empty,fetch_fn=lambda *a,**k:1/0)
    assert calls==["search"] and x["raw_result_count"]==0
    assert x["site_logical_reserved"]==1 and x["status"]=="no_valid_search_urls"

def test_abort_after_first_provider_error():
    calls=[]
    def rate(*a,**k):
        calls.append("search")
        return SearchResult("rate_limited_or_out_of_credits",1,2)
    x=diagnostic(profiles(),history(),live=True,api_key="synthetic",
                 search_fn=rate,fetch_fn=lambda *a,**k:1/0)
    assert calls==["search"] and x["attempted"]==1 and x["aborted"]
    assert x["reserved_conservative_challenge_charge"]==2

def test_four_mock_searches_never_exceed_ceiling():
    calls=[]
    def search(*a,**k):
        calls.append("search")
        return SearchResult("ok_transient_candidates_only",1,2,{"results":[]})
    x=diagnostic(profiles(),history(),live=True,api_key="synthetic",
                 search_fn=search,fetch_fn=lambda *a,**k:1/0)
    assert len(calls)==4
    assert x["attempted"]==4 and not x["aborted"]
    assert x["ceiling_search_basic_requests"]==4
    assert x["ceiling_first_party_logical_http"]==8
    assert x["ceiling_challenge_charge"]==24
    assert x["reserved_logical_http"]==4 and x["new_published_claims"]==0

def test_private_funnel_records_nomination_but_never_provider_snippets():
    from run_v10_m33_consumed4_diagnostic import _result_categories
    url="https://nordlysmarin.no/"
    calls=[]
    def search(*a,**kw):
        calls.append("search")
        return SearchResult("ok_transient_candidates_only",1,2,{
            "results":[{"url":"https://proff.no/selskap/example",
                        "title":"Nordlys Marin Teknologi AS","content":"directory"},
                       {"url":url,"title":"NORDLYS MARIN TEKNOLOGI AS",
                        "content":"UNTRUSTED_PROVIDER_SNIPPET",
                        "raw_content":"UNTRUSTED_PROVIDER_RAW"}],
            "answer":"UNTRUSTED_PROVIDER_ANSWER"})
    def fetched(site,**kw):
        assert site==url
        calls.append("fetch")
        text="NORDLYS MARIN TEKNOLOGI AS. Organisasjonsnummer 928949605. Tromso."
        return {"status":"available","source_url":url,"value":{
            "requested_url":url,"final_url":url,"title":"NORDLYS MARIN TEKNOLOGI AS",
            "description":"","identity_text_excerpt":text,
            "main_text_excerpt":text,"structured_organisations":[],
            "pages":[],"social_links":[],"content_sha256":"synthetic_hash"}}, {"requests":2}
    x=diagnose_one(profiles()[0],api_key="synthetic",search_fn=search,
                   fetch_fn=fetched)
    assert calls==["search","fetch"]
    assert x["raw_result_count"]==2
    assert x["baseline_nominated"] is False
    assert x["challenger_nominated"] is True
    assert x["url_categories"]["directory_or_social_host"]==1
    assert x["url_categories"]["safe_root_https_homepage"]==1
    assert x["site_logical_reserved"]==3
    assert x["conservative_request_charge_reserved"]==6
    assert x["published_company_claims"]==0
    assert "UNTRUSTED_PROVIDER" not in str(x)


def test_wrong_organisation_number_never_qualifies():
    url="https://nordlysmarin.no/"
    def search(*a,**kw):
        return SearchResult("ok_transient_candidates_only",1,2,{
            "results":[{"url":url,"title":"NORDLYS MARIN TEKNOLOGI AS",
                        "content":"Marine technology"}]})
    def wrong(site,**kw):
        text="NORDLYS MARIN TEKNOLOGI AS. Organisasjonsnummer 987654321. Tromso."
        return {"status":"available","source_url":url,"value":{
            "requested_url":url,"final_url":url,"title":"NORDLYS MARIN TEKNOLOGI AS",
            "description":"","identity_text_excerpt":text,
            "main_text_excerpt":text,"structured_organisations":[],
            "pages":[],"social_links":[]}}, {"requests":2}
    x=diagnose_one(profiles()[0],api_key="synthetic",search_fn=search,
                   fetch_fn=wrong)
    assert x["first_party_fetch_attempted"] is True
    assert x["manual_review_candidate"] is False
    assert x["status"]=="identity_rejected"
    assert x["published_company_claims"]==0


def test_four_searches_eight_first_party_slots_max():
    url="https://nordlysmarin.no/"
    calls=[]
    def search(*a,**kw):
        calls.append("search")
        return SearchResult("ok_transient_candidates_only",1,2,{
            "results":[{"url":url,"title":"NORDLYS MARIN TEKNOLOGI AS",
                        "content":"Marine technology"}]})
    def fetch(site,**kw):
        calls.append("fetch")
        return {"status":"unavailable"}, {"requests":2}
    x=diagnostic(profiles(),history(),live=True,api_key="synthetic",
                 search_fn=search,fetch_fn=fetch)
    assert calls==["search","fetch"]*4
    assert x["requested"]==4 and x["attempted"]==4
    assert x["reserved_logical_http"]==12
    assert x["reserved_conservative_challenge_charge"]==24
    assert x["new_published_claims"]==0
