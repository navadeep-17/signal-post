"""M38 consent-gated one-query experiment; all tests use mock transports.

Never uses a real provider key or external first-party HTTP.
"""
from __future__ import annotations
import io
import json
import sys
import urllib.error
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"scripts")]
from norway_company_agent.v10_m38_alternative_search import (
    FROZEN_VARIANT,_single_alternative_body,execute_bounded_alternative,
)
from norway_company_agent.tavily_bounded_transport import TAVILY_SEARCH_ENDPOINT, SearchResult
from run_v10_m38_pre_registered_pilot import run_m38,_validate_previous_four

MANIFEST=json.loads((ROOT/"evaluation/v10_m24_consumed_dev_20.json").read_text())
IDS=[num for group in ("m19_a","m19_b","m20_a") for num in MANIFEST["selected_per_cohort"][group]]
SITE="https://nordlysmarin.no/"


def profiles():
    return [{"organisation_number":num,
             "name":"NORDLYS MARIN TEKNOLOGI AS",
             "municipality":"TROMSØ","website":""} for num in IDS]


def prev20():
    return {
        "schema":"m26_consumed_development_manual_review_only",
        "type":"PREVIOUSLY_CONSUMED_NOT_FRESH",
        "selection_sha256":MANIFEST["selected_list_sha256"],
        "requested_companies":20,"attempted_companies":20,
        "aborted":False,"published_company_claims":0,
        "manually_reviewable_exact_org_sites":0,"qualified_v8_modified":False,
        "rows":[{"organisation_number":num,
                 "status":("no_candidate_qualified_for_independent_fetch"
                           if i<17 else "first_party_identity_rejected"),
                 "published_claims":0}
                for i,num in enumerate(IDS)]
    }


def prev4():
    return {
        "schema":"m33_consumed4_funnel_minimal_private_v1",
        "source":"PREVIOUSLY_CONSUMED_M24_20_ONLY",
        "m24_digest":MANIFEST["selected_list_sha256"],
        "requested":4,"attempted":4,"aborted":False,
        "new_published_claims":0,"qualified_v8_modified":False,
        "reserved_logical_http":4,
        "rows":[{"organisation_number":num,
                 "normalized_url_result_count":2,
                 "baseline_nominated":False,"challenger_nominated":False,
                 "manual_review_candidate":False,"first_party_fetch_attempted":False,
                 "published_company_claims":0}
                for num in IDS[:4]]
    }


class FakeResponse:
    def __init__(self,data:bytes,url=TAVILY_SEARCH_ENDPOINT):
        self.stream=io.BytesIO(data);self.url=url
    def __enter__(self):return self
    def __exit__(self,*a):pass
    def geturl(self):return self.url
    def read(self,n):return self.stream.read(n)


class FakeOpener:
    def __init__(self,response):
        self.response=response
        self.calls=[]
    def open(self,request,timeout):
        self.calls.append((request,timeout))
        if isinstance(self.response,Exception):raise self.response
        return self.response


def test_m38_query_is_one_frozen_homepage_variant_with_original_transport_security():
    body=_single_alternative_body(profiles()[0])
    assert FROZEN_VARIANT=="legal_name_municipality_homepage"
    assert body["query"]=='"NORDLYS MARIN TEKNOLOGI AS" TROMSØ hjemmeside'
    assert "928949605" not in body["query"]
    assert body["search_depth"]=="basic" and body["auto_parameters"] is False
    assert body["include_answer"] is False
    assert body["include_raw_content"] is False and body["include_images"] is False
    assert body["max_results"]<=10


def test_m38_search_transport_sends_exact_one_POST_and_never_exposes_result_as_fact():
    opener=FakeOpener(FakeResponse(b'{"results":[{"url":"https://nordlysmarin.no/","title":"Nordlys Marin"}]}'))
    x=execute_bounded_alternative(profiles()[0],api_key="FAKE_TEST_KEY",opener=opener)
    assert x.status=="ok_transient_candidates_only"
    assert x.logical_requests_charged==1 and x.conservative_challenge_charge==2
    assert len(opener.calls)==1
    request,timeout=opener.calls[0]
    assert request.get_method()=="POST"
    assert request.full_url==TAVILY_SEARCH_ENDPOINT
    payload=json.loads(request.data)
    assert payload["query"]=='"NORDLYS MARIN TEKNOLOGI AS" TROMSØ hjemmeside'
    assert payload["include_answer"] is False
    assert timeout==8.0
    assert x.audit()["published_company_claims"]==0
    assert not x.audit()["payload_persisted"]


def test_m38_missing_key_refuses_all_network():
    def no_call(*a,**kw):raise AssertionError("HTTP attempted")
    opener=FakeOpener(None)
    x=execute_bounded_alternative(profiles()[0],api_key="",opener=opener)
    assert x.status=="no_key_no_request"
    assert not opener.calls


def test_m38_no_redirect_follow_or_retry_on_ratelimit():
    for code,expected in ((301,"redirect_blocked"),(401,"invalid_or_forbidden_key"),
                          (403,"invalid_or_forbidden_key"),(429,"rate_limited_or_out_of_credits"),
                          (500,"provider_http_error")):
        response=urllib.error.HTTPError(TAVILY_SEARCH_ENDPOINT,code,"mock failure",{},None)
        opener=FakeOpener(response)
        result=execute_bounded_alternative(profiles()[0],api_key="FAKE",opener=opener)
        assert result.status==expected
        assert len(opener.calls)==1
        assert result.logical_requests_charged==1


def test_m38_cross_origin_response_rejected():
    x=execute_bounded_alternative(profiles()[0],api_key="FAKE",
         opener=FakeOpener(FakeResponse(b'{"results":[]}',url="https://attacker.example/")))
    assert x.status=="unexpected_response_origin"


def test_m38_invalid_json_schema_large_response_and_timeout():
    cases=(
      (b'not json',"invalid_json_response"),
      (b'{"results":{}}',"invalid_search_response"),
      (b'x'*524289,"oversized_provider_response")
    )
    for data,status in cases:
        x=execute_bounded_alternative(profiles()[0],api_key="FAKE",
            opener=FakeOpener(FakeResponse(data)))
        assert x.status==status
    with pytest.raises(ValueError):
        execute_bounded_alternative(profiles()[0],api_key="FAKE",timeout_seconds=8.1)


def test_m38_dry_run_never_searches_or_fetches():
    def no_call(*a,**kw):raise AssertionError("unexpected external request")
    x=run_m38(profiles(),prev20(),prev4(),live=False,api_key="discard",
              search_fn=no_call,fetch_fn=no_call)
    assert x["query_alt_diagnostic"]["attempted"]==0
    assert x["query_alt_diagnostic"]["reserved_logical_http"]==0
    assert x["historical_m33_companies_with_normalized_urls"]==4
    assert x["historical_m33_m32_nominations"]==0
    assert x["reason_counts"]["inspected_total"]==0
    assert x["published_company_claims"]==0
    assert x["provider_search_content_persisted"] is False


def test_m38_refuses_modified_prev_cohort_or_fabricated_historical_positive():
    inputs=(
      prev4() | {"attempted":3},
      prev4() | {"aborted":True},
      prev4() | {"source":"FRESH"},
    )
    for old in inputs:
        with pytest.raises(ValueError):
            run_m38(profiles(),prev20(),old,live=False)
    old=prev4()
    old["rows"][0]["first_party_fetch_attempted"]=True
    with pytest.raises(ValueError):
        _validate_previous_four(profiles()[:4],old)


def test_m38_one_search_per_company_and_reason_counts_are_safe():
    calls=[]
    def search(profile,*,api_key,timeout_seconds):
        assert api_key=="FAKE"
        calls.append(profile["organisation_number"])
        return SearchResult("ok_transient_candidates_only",1,2,{
            "results":[{"url":"https://proff.no/selskap/example",
                        "title":"DIRECTORY SECRET","content":"provider snippet"},
                       {"url":SITE, "title":"Nordlys Marin",
                        "content":"Tromsø company BRAND_PRIVATE_SNIPPET",
                        "raw_content":"PRIVATE_SOURCE_DETAILS"}]})
    def fetch(*a,**kw):
        raise AssertionError("M32 must abstain on shortened result title")
    x=run_m38(profiles(),prev20(),prev4(),live=True,api_key="FAKE",
              search_fn=search,fetch_fn=fetch)
    assert calls==IDS[:4] and len(calls)==4
    d=x["query_alt_diagnostic"]
    assert d["requested"]==4 and d["attempted"]==4 and not d["aborted"]
    assert d["reserved_logical_http"]==4
    assert d["reserved_conservative_challenge_charge"]==8
    assert sum(r["private_internal_result_items_inspected"] for r in d["rows"])==8
    assert x["reason_counts"]["inspected_total"]==8
    assert x["reason_counts"]["safe_https_root"]==4
    assert x["reason_counts"]["directory_or_social_host"]==4
    assert x["reason_counts"]["full_legal_name_title_missing"]==4
    assert x["reason_counts"]["m35_shadow_per_result_fetch_nomination"]==4
    assert x["published_company_claims"]==0
    for secret in ("BRAND_PRIVATE_SNIPPET","PRIVATE_SOURCE_DETAILS","DIRECTORY SECRET",SITE):
        assert secret not in str(x)


def test_m38_abort_on_first_provider_error_no_double_credit():
    for status in ("rate_limited_or_out_of_credits","invalid_or_forbidden_key"):
        calls=[]
        def err(*a,**kw):
            calls.append("provider")
            return SearchResult(status,1,2)
        x=run_m38(profiles(),prev20(),prev4(),live=True,api_key="FAKE",
                  search_fn=err,fetch_fn=lambda *a,**kw:1/0)
        assert calls==["provider"]
        assert x["query_alt_diagnostic"]["aborted"] is True
        assert x["query_alt_diagnostic"]["attempted"]==1
        assert x["query_alt_diagnostic"]["reserved_logical_http"]==1


def test_m38_code_has_no_auto_key_access_and_single_pre_registered_variant():
    alt=(ROOT/"src/norway_company_agent/v10_m38_alternative_search.py").read_text()
    script=(ROOT/"scripts/run_v10_m38_pre_registered_pilot.py").read_text()
    assert 'FROZEN_VARIANT = "legal_name_municipality_homepage"' in alt
    for code in (alt,script):
        assert "os.environ" not in code
        assert "run_signalpost_v8.py" not in code
        assert "run_signalpost_final.py" not in code
