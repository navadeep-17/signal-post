"""M43 synthetic checks: no unsupported inferencing from not-found feed evidence."""
import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from norway_company_agent.v10_m43_archived_news_source_failures import _status_reason,source_failure_categories

@pytest.mark.parametrize("status,note,expected",[
    ("not_found","HTTP 404","http_404_or_410"),
    ("not_found","HTTP 410","http_404_or_410"),
    ("not_found","Feed contains no qualified current dated same-site entries","fetched_or_parsed_but_no_eligible_entries"),
    ("not_found","unknown","other_not_found_no_specific_recoverable_source"),
    ("not_found","Verified website URL cannot nominate a same-site feed candidate","invalid_verified_url_for_feed_nomination"),
    ("source_error","HTTP 503","non_404_http_error"),
    ("source_error","TimeoutError: timeout","network_or_parsing_source_exception"),
    ("blocked","robots.txt disallows this user agent","robots_blocked"),
    ("available","valid","eligible_feed_with_dated_entries"),
])
def test_fixed_feed_failure_taxonomy(status,note,expected):
    assert _status_reason(status,note)==expected

def make_rows(status=None,note="",nominated=False,org="123456789"):
    url="https://synthetic.invalid/"
    site={
        "status":"available","source_url":url,"retrieved_at":"2026-10-01T10:00:00Z",
        "value":{"final_url":url,"pages":[],"identity_assessment":{"publishable":True},
            "news_detail_links":[{"url":url+"news/article"}] if nominated else []}
    }
    evidence={"website":site}
    if status:
        evidence["website_activity_feed"]={
            "status":status,"source_type":"verified_company_activity_feed","note":note,
            "source_url":url+"feed/","retrieved_at":"2026-10-01T10:00:00Z",
            "content_sha256":"a"*64,"value":{"verified_website_url":url,"entries":[]}
        }
    profile={"organisation_number":org,"evidence":evidence}
    contract={"organisation_number":org,"claims":[],"evidence":[]}
    return contract,profile

def test_missing_news_detail_not_mislabeled_as_invalid_article():
    c,p=make_rows(status="not_found",note="HTTP 404",nominated=True)
    result=source_failure_categories([c],[p])
    assert result["exact_verified_sites"]==1
    assert result["source_reasons"]=={"http_404_or_410":1}
    assert result["news_nomination_intersections"]["news_nominated_sites_with_no_retained_detail"]==1
    assert result["eligible_existing_claims_lost_in_projection"]==0
    assert result["no_fetch_no_proven_new_scored_news"] is True
    assert result["official_score_delta"] is None
    assert "123456789" not in str(result)
    assert "synthetic.invalid" not in str(result)

def test_no_retained_feed_attempt_is_unknown_not_source_absence():
    c,p=make_rows(nominated=True)
    r=source_failure_categories([c],[p])
    assert r["source_reasons"]=={"no_retained_attempt_cannot_attribute_cause":1}
    assert r["news_nomination_intersections"]["news_nominated_sites_with_missing_feed_attempt"]==1
    assert r["missing_retained_source_is_not_proof_of_absence"] is True

def test_no_network_or_private_source_output():
    path=ROOT/"src/norway_company_agent/v10_m43_archived_news_source_failures.py"
    runner=ROOT/"scripts/run_v10_m43_archived_news_source_failures.py"
    for content in (path.read_text(),runner.read_text()):
        for forbidden in ("urllib.request","requests.get(","requests.post(","TAVILY_API_KEY","GOOGLE_API_KEY","actions/upload-artifact"):
            assert forbidden not in content
