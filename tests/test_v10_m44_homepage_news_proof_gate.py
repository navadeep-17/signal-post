"""M44 synthetic adversarial first-party homepage news nomination checks."""
from __future__ import annotations
from copy import deepcopy
import sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from norway_company_agent.v10_m44_homepage_news_proof_gate import (
    _nomination_reasons, _unique_card_day, archived_nomination_gate,
)

ORG="123456789"
HOME="https://corp.example.no/"
SHA="a"*64

def _synthetic(rows:int=1):
    site={
        "status":"available",
        "source_url":HOME,
        "retrieved_at":"2026-10-01T10:00:00+00:00",
        "content_sha256":SHA,
        "value":{
            "final_url":HOME,
            "content_sha256":SHA,
            "identity_assessment":{"publishable":True},
            "identity_text_excerpt":"Organisasjonsnummer: "+ORG,
            "pages":[],
            "news_detail_links":[{
                "url":HOME+"aktuelt/contract",
                "homepage_url":HOME,
                "homepage_content_sha256":SHA,
                "nomination_only":True,
                "anchor_text":"Signed major new logistics contract",
                "dated_context":"2026-09-15 Signed major new logistics contract",
                "marker":"aktuelt",
            }]
        },
    }
    c={"organisation_number":ORG,"claims":[],"evidence":[]}
    p={"organisation_number":ORG,"evidence":{"website":site}}
    return c,p

def test_validated_homepage_nomination_is_only_human_review_candidate():
    c,p=_synthetic()
    r=archived_nomination_gate([c],[p])
    assert r["nominated_urls"]==1
    assert r["nominated_urls_passing_all_homepage_structural_checks_for_review"]==1
    assert r["new_proven_eligible_dated_news_facts"]==0
    assert r["strict_news_claim_publications"]==0
    assert r["official_c300_score_delta_measured"] is False
    assert r["independently_fetched_and_validated_article_pages"]==0
    assert r["requires_independent_detail_article_and_human_review"] is True
    for private in ("123456789","corp.example.no","Signed major","2026-09-15"):
        assert private not in str(r)

@pytest.mark.parametrize("change,expected",[
    ({"nomination":{"homepage_content_sha256":"b"*64}},"nomination_homepage_url_or_hash_mismatch"),
    ({"nomination":{"homepage_url":"https://other.example.no/"}},"nomination_homepage_url_or_hash_mismatch"),
    ({"nomination":{"url":"https://other.example.no/aktuelt/contract"}},"article_url_not_same_exact_https_host"),
    ({"nomination":{"url":"http://corp.example.no/aktuelt/contract"}},"article_url_not_same_exact_https_host"),
    ({"nomination":{"anchor_text":"Les mer"}},"no_specific_anchor_title"),
    ({"nomination":{"dated_context":"Unspecified week Signed major new logistics contract"}},"no_homepage_card_local_date"),
    ({"nomination":{"dated_context":"2026-09-15 and 2026-09-16 Signed major new logistics contract"}},"card_date_missing_ambiguous_future_or_stale"),
    ({"nomination":{"dated_context":"2026-11-01 Signed major new logistics contract"}},"card_date_missing_ambiguous_future_or_stale"),
    ({"nomination":{"dated_context":"2026-09-15 Totally unrelated news"}},"anchor_title_not_in_local_dated_card"),
    ({"website":{"content_sha256":"b"*64}},"homepage_hash_missing_or_inconsistent"),
    ({"website":{"retrieved_at":"invalid"}},"homepage_retrieval_time_unverified"),
    ({"nomination":{"nomination_only":False}},"nomination_semantics_missing"),
    ({"website_value":{"identity_text_excerpt":"Organisasjonsnummer: 987654321"}},"homepage_missing_exclusive_explicit_legal_id"),
    ({"website_value":{"identity_text_excerpt":"Organisasjonsnummer: 123456789\nOrganisasjonsnummer: 987654321"}},"homepage_missing_exclusive_explicit_legal_id"),
])
def test_each_boundary_blocks_promotion(change,expected):
    c,p=_synthetic()
    w=p["evidence"]["website"]
    if "nomination" in change:
        w["value"]["news_detail_links"][0].update(change["nomination"])
    if "website" in change:
        w.update(change["website"])
    if "website_value" in change:
        w["value"].update(change["website_value"])
    assert expected in _nomination_reasons(ORG,w,w["value"]["news_detail_links"][0])

def test_identity_gate_cannot_approve_unverified_site():
    c,p=_synthetic()
    p["evidence"]["website"]["value"]["identity_assessment"]["publishable"]=False
    r=archived_nomination_gate([c],[p])
    assert r["exact_verified_websites"]==0
    assert r["news_nominating_websites"]==0
    assert r["nominated_urls"]==0

def test_distinct_company_sets_required():
    c,p=_synthetic()
    p["organisation_number"]="987654321"
    with pytest.raises(ValueError):
        archived_nomination_gate([c],[p])

def test_no_network_or_confidential_output_path():
    runner=(ROOT/"scripts/run_v10_m44_homepage_news_proof_gate.py").read_text()
    core=(ROOT/"src/norway_company_agent/v10_m44_homepage_news_proof_gate.py").read_text()
    for content in (core,runner):
        for forbidden in ("requests.get(","requests.post(","urllib.request","api.tavily.com","TAVILY_API_KEY","actions/upload-artifact"):
            assert forbidden not in content
    assert "audit_pinned_archives(files)" in runner
