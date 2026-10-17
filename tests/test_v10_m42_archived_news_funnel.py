"""Synthetic adversarial tests for M42 archived-only dated news funnel."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from norway_company_agent.v10_m42_archived_news_funnel import news_root_cause_counts

ORG="123456789"
HASH="a"*64
def sample(org:str=ORG,*,exact:bool=True,nomination:bool=False,feed_status:str|None=None):
    site="https://company.example.no/"
    evidence={
        "website":{
            "status":"available" if exact else "not_found",
            "source_url":site,
            "content_sha256":HASH,
            "retrieved_at":"2026-10-01T10:00:00+00:00",
            "value":{
                "final_url":site,
                "identity_assessment":{"publishable":exact,"score":0.99},
                "pages":[],
                "news_detail_links":(
                    [{"url":site+"nyheter/specific","homepage_url":site,
                      "homepage_content_sha256":HASH}] if nomination else []
                )
            }
        }
    }
    if feed_status:
        evidence["website_activity_feed"]={
            "source_type":"verified_company_activity_feed",
            "status":feed_status,
            "source_url":site+"feed/",
            "content_sha256":"b"*64,
            "retrieved_at":"2026-10-01T10:00:00+00:00",
            "value":{"verified_website_url":site,"entries":[]}
        }
    profile={"organisation_number":org,"name":"COMPANY AS","evidence":evidence}
    contract={"organisation_number":org,"claims":[],"evidence":[]}
    return contract,profile

def test_only_nominated_links_are_not_published_news():
    contract,profile=sample(nomination=True)
    r=news_root_cause_counts([contract],[profile])
    v=r["stage_counts"]
    assert v["total_companies"]==1
    assert v["exact_verified_sites"]==1
    assert v["homepages_with_news_link_nominations"]==1
    assert v["retained_successful_news_detail_pages"]==0
    assert v["published_company_update_claims"]==0
    assert r["proven_new_correct_company_news_claims"]==0
    assert not r["official_score_delta_measured"]
    assert r["new_company_web_requests"]==0
    assert r["main_or_submitted_sha_modified"] is False
    assert "123456789" not in str(r)
    assert "example.no" not in str(r)

def test_undiscovered_company_is_not_treated_as_negative_news():
    c,p=sample(exact=False,nomination=True)
    o=news_root_cause_counts([c],[p])
    s=o["stage_counts"]
    assert s["exact_verified_sites"]==0
    assert s["news_link_nominations_count"]==0
    assert s["companies_with_published_company_updates"]==0

def test_missing_feed_is_distinguished_from_nonavailable_feed():
    c1,p1=sample()
    c2,p2=sample(org="987654321",feed_status="not_found")
    out=news_root_cause_counts([c1,c2],[p1,p2])
    assert out["verified_site_feed_status_counts"]=={
        "no_retained_feed_attempt":1,"not_found":1
    }

def test_replayed_output_claims_are_not_counted_as_proven_coverage():
    c,p=sample()
    result=news_root_cause_counts([c],[p])
    assert result["current_projector_read_only_replay"].get("replay_new_update_candidate_claims_post_guard",0)==0
    assert result["official_c300_news_reference_match_measured"] is False
    assert result["fresh_independent_transfer_measured"] is False

def test_contract_and_profile_must_agree():
    c,p=sample()
    p["organisation_number"]="987654321"
    with pytest.raises(ValueError):
        news_root_cause_counts([c],[p])

def test_duplicate_company_is_rejected():
    c,p=sample()
    with pytest.raises(ValueError):
        news_root_cause_counts([c,deepcopy(c)],[p,deepcopy(p)])

def test_no_new_requests_or_sensitive_archive_output():
    runner=(ROOT/"scripts/run_v10_m42_archived_news_funnel.py").read_text()
    module=(ROOT/"src/norway_company_agent/v10_m42_archived_news_funnel.py").read_text()
    for s in (runner,module):
        for f in ("requests.get(","requests.post(","urllib.request","api.tavily.com","TAVILY_API_KEY","actions/upload-artifact"):
            assert f not in s
    assert "audit_pinned_archives(files)" in runner
