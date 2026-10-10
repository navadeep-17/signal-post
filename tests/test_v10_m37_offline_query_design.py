"""M37 query-structure hypotheses only. NO SEARCH PROVIDER OR HTTP."""
from __future__ import annotations

from pathlib import Path
import sys
import json
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from norway_company_agent.discovery import build_company_search_query
from norway_company_agent.v10_m37_offline_query_design import (
    QUERY_VARIANTS, MAX_QUERY_CHARS, OfflineQueryHypothesis,
    build_offline_one_query, compare_query_shapes_offline,
)

NAME="NORDLYS MARIN TEKNOLOGI AS"
ORG="123456789"


def profile(**kwargs):
    return {"name":NAME,"organisation_number":ORG,
            "municipality":"TROMSØ"} | kwargs


def test_m37_exact_original_query_is_unmodified():
    a=build_offline_one_query(profile(),variant="v8_unchanged")
    assert a.transient_query==build_company_search_query(profile())
    assert a.transient_query=='"NORDLYS MARIN TEKNOLOGI AS" 123456789 TROMSØ'
    assert a.max_search_requests_if_separately_authorized==1
    assert a.production_enabled is False
    assert a.proven_coverage_lift is False


def test_m37_legal_name_municipality_without_org_number():
    a=build_offline_one_query(profile(),variant="legal_name_municipality_homepage")
    assert a.transient_query=='"NORDLYS MARIN TEKNOLOGI AS" TROMSØ hjemmeside'
    assert ORG not in a.transient_query


def test_m37_distinctive_legal_name_without_legal_form():
    a=build_offline_one_query(profile(),variant="distinctive_name_municipality_website")
    assert a.transient_query=='"nordlys marin teknologi" TROMSØ nettside'
    assert " AS" not in a.transient_query
    assert ORG not in a.transient_query


def test_m37_only_one_mutually_exclusive_variant_no_fallback():
    assert len(QUERY_VARIANTS)==3
    for invalid in ("all","", "any", "try_all", "fallback",None,
                    ["v8_unchanged","legal_name_municipality_homepage"]):
        with pytest.raises(ValueError):
            build_offline_one_query(profile(),variant=invalid)


def test_m37_short_ambiguous_name_cannot_use_distinctive_name_search():
    with pytest.raises(ValueError):
        build_offline_one_query(profile(name="FJORD AS"),
                                variant="distinctive_name_municipality_website")
    x=compare_query_shapes_offline(profile(name="FJORD AS"))
    assert x["query_variants"][0]["eligible_for_hypothetical_single_search"]
    assert x["query_variants"][2]["eligible_for_hypothetical_single_search"] is False


def test_m37_control_characters_and_quote_injection_fail_closed():
    for bad in ('NORDLYS" OR example', 'NORDLYS\\M', 'NORDLYS\nMARIN',
                'NORDLYS\rMARIN','<script>',"NORDLYS {X}"):
        with pytest.raises(ValueError):
            build_offline_one_query(profile(name=bad),
                                    variant="legal_name_municipality_homepage")
    for bad in ('OSLO\nsite:evil.tld', '"OSLO"', "A\\B"):
        with pytest.raises(ValueError):
            build_offline_one_query(profile(municipality=bad),
                                    variant="v8_unchanged")


def test_m37_field_size_and_query_limit_are_bounded():
    with pytest.raises(ValueError):
        build_offline_one_query(profile(name="AB"*90),variant="v8_unchanged")
    assert MAX_QUERY_CHARS<=180
    for variant in QUERY_VARIANTS:
        value=build_offline_one_query(profile(),variant=variant)
        assert len(value.transient_query)<=MAX_QUERY_CHARS


def test_m37_compiler_does_not_make_network_calls_on_invalid_profiles():
    for p in (
        profile(name=""),profile(municipality=""),
        profile(organisation_number="12345678"),
        profile(organisation_number="not a number"),
    ):
        for variant in QUERY_VARIANTS:
            with pytest.raises(ValueError):
                build_offline_one_query(p,variant=variant)


def test_m37_query_shape_comparison_contains_no_company_source_fields():
    data=compare_query_shapes_offline(profile())
    assert data["schema"]=="m37_offline_single_query_design_comparison_v1"
    assert len(data["query_variants"])==3
    assert sum(row["max_search_requests"] for row in data["query_variants"])==3  # shapes NOT scheduled calls
    assert data["per_company_hypothetical_basic_search_cap"]==1
    assert data["third_party_requests_executed"]==0
    assert data["website_requests_executed"]==0
    assert data["measured_query_recall"] is False
    assert data["official_score_measured"] is False
    assert data["must_replace_existing_site_slot_if_integrated"] is True
    assert all(row["observed_provider_result_count"] is None for row in data["query_variants"])
    assert all(row["verified_new_websites"] is None for row in data["query_variants"])
    serialized=json.dumps(data)
    for sensitive in (NAME,ORG,"TROMSØ","nordlys", "PRIVATE", "https:"):
        assert sensitive not in serialized


def test_m37_cannot_construct_pretend_successful_real_query():
    with pytest.raises(ValueError):
        OfflineQueryHypothesis(variant="v8_unchanged",transient_query="A",
                               max_search_requests_if_separately_authorized=2)
    with pytest.raises(ValueError):
        OfflineQueryHypothesis(variant="v8_unchanged",transient_query="A",
                               production_enabled=True)
    with pytest.raises(ValueError):
        OfflineQueryHypothesis(variant="v8_unchanged",transient_query="A",
                               proven_coverage_lift=True)
    with pytest.raises(ValueError):
        OfflineQueryHypothesis(variant="fictional",transient_query="A")


def test_m37_no_provider_calls_secrets_or_runner_hooks():
    source=(ROOT/"src/norway_company_agent/v10_m37_offline_query_design.py").read_text()
    for blocked in (
        "TAVILY_API_KEY","api.tavily.com","execute_bounded_search(",
        "run_signalpost_v8.py","run_v10_m33_consumed4_diagnostic.py",
        "urllib.request","requests.post(", "os.environ[",
    ):
        assert blocked not in source
