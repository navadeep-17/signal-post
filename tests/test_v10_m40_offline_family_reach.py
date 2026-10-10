"""M40 synthetic and adversarial typed external-family gap audit.

NO provider calls, no source requests, no fresh/holdout populations.
"""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from norway_company_agent.v10_m40_offline_family_reach import (
    FAMILY_CLAIM_FIELDS, score_evidence_family_reach,
)

def profile(org="123456789", external=None):
    return {"organisation_number":org,"name":"PRIVATE COMPANY","external_observations":external or []}

def contract(org="123456789", fields=(), platforms=None):
    platforms=platforms or {}
    return {"organisation_number":org,"claims":[
        {"field":field,"availability":"available","evidence_ids":[f"ev-{i}"],
         **({"platform":platforms[field]} if field in platforms else {})}
        for i,field in enumerate(fields)
    ]}

def obs(org="123456789",signal_type="review",platform="google_places",
        sentiment_label=None,source_class=None):
    item={
        "id":"review-private","organisation_number":org,
        "platform":platform,"signal_type":signal_type,
        "source_url":"https://example.no/review/private",
        "retrieved_at":"2026-10-01T01:00:00Z",
        "content_sha256":"a"*64,"exact_entity":True,
        "identity_proof":"independently verified synthetic exact org match",
        "acquisition_mode":"official_dataset","rights_status":"approved",
        "evidence_span":"synthetic customer experience",
    }
    if sentiment_label:
        item.update({"sentiment_label":sentiment_label,
                     "source_class":source_class or "customer_review",
                     "sentiment_model_version":"synthetic-v1"})
    return item


def test_m40_official_awards_are_not_company_news_reviews_or_sentiment():
    r=score_evidence_family_reach(
        [contract(fields=["official.support_award","external.workforce_snapshot"])],
        [profile()],
    )
    counts=r["company_counts_by_typed_family"]
    assert counts["official_support_award"]==1
    assert counts["workforce_snapshot"]==1
    for family in ("independent_reviews_or_places","independent_public_buzz_or_metrics",
                   "first_party_company_update","concrete_job_posting",
                   "labeled_independent_sentiment_input"):
        assert counts[family]==0
    assert r["official_builderr_score_measured"] is False


def test_m40_website_contact_and_social_do_not_imply_activity_or_review():
    r=score_evidence_family_reach(
        [contract(fields=["official_website","external.profile_handle","external.contact_email"])],
        [profile()],
    )
    c=r["company_counts_by_typed_family"]
    assert c["verified_company_site"]==1 and c["first_party_contact_email"]==1
    assert c["verified_social_handle"]==1
    assert c["independent_public_buzz_or_metrics"]==0
    assert c["two_verified_external_profile_platforms"]==0
    assert c["independent_reviews_or_places"]==0


def test_m40_distinct_declared_social_platforms_are_only_breadth_not_engagement():
    row=contract(fields=["external.profile_handle","external.profile_handle"],
                 platforms={"external.profile_handle":"facebook"})
    # A dictionary cannot assign different platform labels to same field;
    # explicitly specify separate claims for one company's two handles.
    row["claims"][1]["platform"]="instagram"
    r=score_evidence_family_reach([row],[profile()])
    c=r["company_counts_by_typed_family"]
    assert c["verified_social_handle"]==1
    assert c["two_verified_external_profile_platforms"]==1
    assert c["independent_public_buzz_or_metrics"]==0


def test_m40_external_observation_requires_strict_provenance_and_rights():
    p=profile(external=[obs(sentiment_label="positive")])
    r=score_evidence_family_reach([contract()],[p])
    c=r["company_counts_by_typed_family"]
    assert c["independent_reviews_or_places"]==1
    assert c["labeled_independent_sentiment_input"]==1
    assert r["companies_with_publishable_external_observations"]==1
    altered=obs(sentiment_label="positive")
    altered["rights_status"]="unknown"
    rejected=score_evidence_family_reach([contract()],[profile(external=[altered])])
    assert rejected["company_counts_by_typed_family"]["independent_reviews_or_places"]==0
    assert rejected["company_counts_by_typed_family"]["labeled_independent_sentiment_input"]==0


def test_m40_unavailable_claims_never_count_toward_coverage():
    c=contract()
    c["claims"]=[
        {"field":"external.review","availability":"not_found","evidence_ids":[]},
        {"field":"external.public_post","availability":"source_error","evidence_ids":[]},
    ]
    r=score_evidence_family_reach([c],[profile()])
    assert all(x==0 for x in r["company_counts_by_typed_family"].values())


def test_m40_real_review_and_buzz_are_distinct_typed_families():
    r=score_evidence_family_reach([
        contract("123456789",fields=["external.review","external.public_mention"]),
        contract("987654321",fields=["external.profile_metrics","external.careers_page"]),
    ],[
        profile("123456789"),profile("987654321")
    ])
    c=r["company_counts_by_typed_family"]
    assert c["independent_reviews_or_places"]==1
    assert c["independent_public_buzz_or_metrics"]==2
    assert c["company_careers_link"]==1
    assert c["concrete_job_posting"]==0


def test_m40_no_independent_source_inferred_from_company_authored_update():
    r=score_evidence_family_reach(
        [contract(fields=["external.company_update","external.careers_page"])],
        [profile()]
    )
    c=r["company_counts_by_typed_family"]
    assert c["first_party_company_update"]==1
    assert c["independent_public_buzz_or_metrics"]==0
    assert c["concrete_job_posting"]==0


def test_m40_group_counts_are_per_company_not_claim_count():
    c=contract(fields=["external.profile_handle"]*3+["external.review"]*5)
    r=score_evidence_family_reach([c],[profile()])
    assert r["company_counts_by_typed_family"]["verified_social_handle"]==1
    assert r["company_counts_by_typed_family"]["independent_reviews_or_places"]==1


def test_m40_no_private_values_or_names_in_output():
    r=score_evidence_family_reach(
        [contract(fields=["official_website","external.workforce_snapshot"])],
        [profile()]
    )
    content=json.dumps(r)
    for text in ("123456789","PRIVATE COMPANY","example.no","ev-0"):
        assert text not in content
    assert r["new_verified_coverage"]==r["new_company_http_requests"]==r["new_provider_requests"]==0
    assert r["official_builderr_recall_measured"] is False
    assert r["production_modified"] is False
    assert set(r["company_counts_by_typed_family"])==set(FAMILY_CLAIM_FIELDS)|{
        "labeled_independent_sentiment_input","two_verified_external_profile_platforms",
    }


def test_m40_cross_company_observation_veto():
    wrong=obs(org="987654321")
    with pytest.raises(ValueError):
        score_evidence_family_reach([contract()],[profile(external=[wrong])])


def test_m40_duplicates_profile_contract_mismatch_invalid_org_fail_closed():
    for cs,ps in (
        ([contract(),contract()],[profile(),profile()]),
        ([contract()],[profile("987654321")]),
        ([contract("123")],[profile("123")]),
        ([contract()],[profile(),profile("987654321")]),
    ):
        with pytest.raises(ValueError):
            score_evidence_family_reach(cs,ps)
    with pytest.raises(ValueError):
        score_evidence_family_reach([],[])
    with pytest.raises(ValueError):
        score_evidence_family_reach([contract() for _ in range(301)],
                                    [profile() for _ in range(301)])


def test_m40_claim_provenance_required_to_count_available_signal():
    c=contract()
    c["claims"]=[{"field":"external.review","availability":"available","evidence_ids":[]}]
    with pytest.raises(ValueError):
        score_evidence_family_reach([c],[profile()])


def test_m40_no_provider_credentials_http_or_production_hooks():
    source=Path("src/norway_company_agent/v10_m40_offline_family_reach.py").read_text()
    runner=Path("scripts/run_v10_m40_consumed_family_gap.py").read_text()
    for code in (source,runner):
        for forbidden in ("TAVILY_API_KEY","run_signalpost_v8.py","run_v10_m38_actions_wrapper.py",
                          "api.tavily.com","requests.get(","urllib.request","requests.post(",
                          "openai.api_key","os.environ"):
            assert forbidden not in code


def test_m40_retained_page_link_is_only_source_opportunity_not_verified_job():
    one=profile()
    one["evidence"]={"website":{"status":"available","value":{
        "identity_assessment":{"publishable":True},
        "careers_links":[{"url":"https://PRIVATE.example/jobs"}],
        "news_detail_links":[{"url":"https://PRIVATE.example/news"}],
        "job_listing_candidates":[{"title":"PRIVATE Internship"}],
        "active_hiring_signal":{"active_vacancies":True},
    }}}
    two=profile("987654321")
    two["evidence"]={"website":{"status":"available","value":{
        "identity_assessment":{"publishable":False},
        "careers_links":[{"url":"https://fake.example/jobs"}],
        "job_listing_candidates":[{"title":"Fake"}],
    }}}
    result=score_evidence_family_reach([
        contract("123456789"),contract("987654321")
    ],[one,two])
    flags=result["pre_existing_exact_site_source_surfaces"]
    assert flags["already_exact_verified_homepages"]==1
    assert flags["retained_careers_links"]==1
    assert flags["retained_news_detail_links"]==1
    assert flags["retained_job_listing_candidates"]==1
    assert flags["retained_active_hiring_marker"]==1
    assert result["company_counts_by_typed_family"]["concrete_job_posting"]==0
    assert result["company_counts_by_typed_family"]["first_party_company_update"]==0
    assert "PRIVATE Internship" not in str(result)
    assert "PRIVATE.example" not in str(result)


def test_m40_unverified_website_surfaces_do_not_inflate_opportunities():
    x=profile()
    x["evidence"]={"website":{"status":"blocked","value":{
        "identity_assessment":{"publishable":True},
        "careers_links":[{"url":"https://fake.example/jobs"}],
    }}}
    result=score_evidence_family_reach([contract()],[x])
    assert all(value==0 for value in result["pre_existing_exact_site_source_surfaces"].values())


def test_m40_strict_careers_replay_distinguishes_missing_provenance_from_real_projection():
    p=profile()
    final_url="https://private-fixture.no/"
    home_hash="b"*64
    p["evidence"]={"website":{
        "status":"available","source_url":final_url,
        "content_sha256":home_hash,"retrieved_at":"2026-10-01T10:00:00Z",
        "value":{
            "final_url":final_url,
            "identity_assessment":{"publishable":True},
            "careers_links":[{
                "url":"https://private-fixture.no/karriere",
                "homepage_url":final_url,
                "homepage_content_sha256":home_hash,
                "evidence_span":"Company homepage career link",
                "claim_scope":"Homepage links to careers surface, not job vacancy",
            }],
        },
    }}
    result=score_evidence_family_reach([contract()],[p])
    replay=result["existing_careers_projection_replay"]
    assert replay["homepage_careers_link_without_existing_claim"]==1
    assert replay["homepage_careers_link_not_projection_eligible"]==0
    assert replay["strict_existing_careers_projector_new_claim_company_candidates"]==1
    assert replay["automatically_publishable_new_claims"]==0
    assert result["company_counts_by_typed_family"]["company_careers_link"]==0
    assert result["company_counts_by_typed_family"]["concrete_job_posting"]==0
    assert "private-fixture.no" not in str(result)


def test_m40_strict_careers_replay_abstains_if_homepage_provenance_missing():
    p=profile()
    p["evidence"]={"website":{"status":"available","value":{
        "final_url":"https://private-fixture.no/",
        "identity_assessment":{"publishable":True},
        "careers_links":[{"url":"https://private-fixture.no/jobber"}],
    }}}
    result=score_evidence_family_reach([contract()],[p])
    replay=result["existing_careers_projection_replay"]
    assert replay["homepage_careers_link_without_existing_claim"]==1
    assert replay["homepage_careers_link_not_projection_eligible"]==1
    assert replay["strict_existing_careers_projector_new_claim_company_candidates"]==0
    assert replay["automatically_publishable_new_claims"]==0
