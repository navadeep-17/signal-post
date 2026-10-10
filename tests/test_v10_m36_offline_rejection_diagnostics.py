"""M36 offline synthetic-only rejection stage tests: no HTTP/provider/real data."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from norway_company_agent.v10_m36_offline_rejection_diagnostics import (
    REASON_FIELDS, MAX_TRANSIENT_RESULTS, _classify_one,
    summarize_transient_candidate_rejections,
)

COMPANY="NORDLYS MARIN TEKNOLOGI AS"
ORG="123456789"
ROOT_URL="https://nordlysmarin.no/"


def profile(**updates):
    return {"name":COMPANY,"organisation_number":ORG,"municipality":"TROMSØ",
            "website":"","evidence":{"registry":{"source":"synthetic"}}} | updates


def candidate(url=ROOT_URL,title="Nordlys Marin",snippet="Marine engineering in Tromsø",
              rank=1):
    return {"url":url,"title":title,"snippet":snippet,"rank":rank,
            "provider":"SYNTHETIC_ONLY","query":"PRIVATE_SYNTHETIC_QUERY",
            "raw_content":"PRIVATE_SYNTHETIC_RAW_PROVIDER_OUTPUT",
            "score":0.99}


def test_m36_synthetic_partial_title_nomination_failure_reason_is_visible():
    flags=_classify_one(profile(),candidate())
    assert flags["safe_https_root"]
    assert flags["full_legal_name_title_missing"]
    assert not flags["deterministic_domain_alias_missing"]
    assert not flags["registry_municipality_snippet_missing"]
    assert flags["exact_org_search_evidence_missing"]
    assert not flags["legacy_per_result_fetch_nomination"]
    assert not flags["m32_per_result_fetch_nomination"]
    assert flags["m35_shadow_per_result_fetch_nomination"]


def test_m36_synthetic_domain_alias_failure_is_distinct_from_title_mismatch():
    flags=_classify_one(profile(),candidate(
        url="https://unrelated-example.no/",
        title=COMPANY,
        snippet="Norwegian firm in Tromsø"))
    assert flags["safe_https_root"]
    assert not flags["full_legal_name_title_missing"]
    assert flags["deterministic_domain_alias_missing"]
    assert not flags["both_title_and_alias_missing"]
    assert not flags["m32_per_result_fetch_nomination"]


def test_m36_synthetic_both_name_evidence_gates_fail():
    flags=_classify_one(profile(),candidate(
        url="https://unrelated-example.no/",title="Unrelated company in Oslo",
        snippet="Welcome"))
    assert flags["safe_https_root"]
    assert flags["both_title_and_alias_missing"]
    assert flags["registry_municipality_snippet_missing"]
    assert not flags["m35_shadow_per_result_fetch_nomination"]


def test_m36_original_gate_success_is_only_crawl_nomination_not_publication():
    flags=_classify_one(profile(),candidate(
        url="https://nordlysmarinteknologi.no/",title=COMPANY,
        snippet="Marine engineering in Tromsø"))
    assert flags["legacy_per_result_fetch_nomination"]
    assert flags["m32_per_result_fetch_nomination"]
    assert flags["m35_shadow_per_result_fetch_nomination"]
    assert not flags["full_legal_name_title_missing"]


def test_m36_directory_social_and_unsafe_nesting_quarantined():
    variants=(
      ("https://proff.no/selskap/123456789", "directory_or_social_host"),
      ("https://linkedin.com/company/brand", "directory_or_social_host"),
      ("https://nordlysmarin.no.attacker.com/", "unsafe_or_non_root_url"),
      ("https://nordlysmarin.no/kontakt", "unsafe_or_non_root_url"),
      ("http://nordlysmarin.no/", "unsafe_or_non_root_url"),
      ("https://user:pass@nordlysmarin.no/", "unsafe_or_non_root_url"),
      ("https://nordlysmarin.no:8443/", "unsafe_or_non_root_url"),
      ("http://127.0.0.1/", "unsafe_or_non_root_url"),
      ("https://nordlysmarin.local/", "unsafe_or_non_root_url"),
      ("javascript:alert('x')","invalid_or_missing_url"),
    )
    for url,reason in variants:
        flags=_classify_one(profile(),candidate(url))
        assert flags[reason] and not flags["safe_https_root"],url
        assert not any(flags[key] for key in (
            "legacy_per_result_fetch_nomination",
            "m32_per_result_fetch_nomination",
            "m35_shadow_per_result_fetch_nomination",
        )),url


def test_m36_summary_counts_overlapping_and_no_provider_metadata_leak():
    data=summarize_transient_candidate_rejections(profile(),[
        candidate(),
        candidate(url="https://unrelated-example.no/",title=COMPANY),
        candidate(url="https://proff.no/selskap/company"),
        candidate(url="https://nordlysmarin.no/about"),
        candidate(url="javascript:alert(1)"),
        candidate(url="https://nordlysmarinteknologi.no/",title=COMPANY)
    ])
    assert data["inspected"]==6
    rc=data["reasons"]
    assert rc["safe_https_root"]==3
    assert rc["directory_or_social_host"]==1
    assert rc["unsafe_or_non_root_url"]==1
    assert rc["invalid_or_missing_url"]==1
    assert rc["full_legal_name_title_missing"]==1
    assert rc["deterministic_domain_alias_missing"]==1
    assert rc["m32_per_result_fetch_nomination"]==1
    assert rc["m35_shadow_per_result_fetch_nomination"]==2
    assert data["provider_http_requests"]==data["company_http_requests"]==data["published_claims"]==0
    output=json.dumps(data)
    for forbidden in (COMPANY,ORG,"nordlysmarin","unrelated-example",
                      "PRIVATE_SYNTHETIC", "proff.no","Tromsø","score"):
        assert forbidden not in output
    assert set(rc)==set(REASON_FIELDS)


def test_m36_does_not_store_sources_on_malformed_or_empty_inputs():
    assert summarize_transient_candidate_rejections(profile(),[])["inspected"]==0
    data=summarize_transient_candidate_rejections(profile(),[
        {}, None, "bad", {"url":"", "title":"SECRET"}
    ])
    assert data["inspected"]==4
    assert data["reasons"]["invalid_or_missing_url"]==4
    assert "SECRET" not in str(data)


def test_m36_max_ten_candidate_diagnostic_and_not_all_raw_provider_results():
    docs=[candidate(url="https://proff.no/selskap/x") for _ in range(50)]
    out=summarize_transient_candidate_rejections(profile(),docs)
    assert out["inspected"]==MAX_TRANSIENT_RESULTS==10
    assert out["reasons"]["directory_or_social_host"]==10


def test_m36_invalid_profile_rejected_without_network():
    for modifications in (
        {"organisation_number":"123"},
        {"organisation_number":"0000000000"},
        {"organisation_number":"12345678x"},
        {"name":""},
        {"municipality":""},
    ):
        with pytest.raises(ValueError):
            summarize_transient_candidate_rejections(profile(**modifications),[])


def test_m36_output_no_urls_org_numbers_queries_or_search_rank():
    output=summarize_transient_candidate_rejections(profile(),[
        candidate(title="TOP_SECRET_COMPANY_NAME",rank=9)
    ])
    assert output["real_site_lift_verified"] is False
    assert output["production_modified"] is False
    assert "url" not in output and "rows" not in output and "provider" not in output
    assert "TOP_SECRET" not in str(output)
    assert ORG not in str(output)


def test_m36_module_has_no_network_credential_or_production_change():
    source=(ROOT/"src/norway_company_agent/v10_m36_offline_rejection_diagnostics.py").read_text()
    for blocked in ("TAVILY_API_KEY", "api.tavily.com", "execute_bounded_search(",
                    "urllib.request", "requests.get(", "requests.post(",
                    "run_signalpost_v8.py", "os.environ["):
        assert blocked not in source
