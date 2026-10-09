"""M35 only synthetic scenario matrix. No provider calls or website HTTP.

M33 real report contained only private aggregate URL shape counts:
two of four companies had root-shaped URLs but none nominated for crawling.
Source titles, snippets and URLs were deliberately not retained. THESE TESTS
ARE NOT A RETROSPECTIVE SCORING OF THOSE REAL PROVIDER RESULTS.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from norway_company_agent.v10_m35_shadow_rejection_analysis import (
    _potential_explicit_nine_digit_numbers,
    diagnose_url_nomination_reasons,
    shadow_nominate_for_fixture_only,
)
from norway_company_agent.v10_m32_offline_nomination import nominate_offline

NAME="NORDLYS MARIN TEKNOLOGI AS"
ORG="123456789"
SHORT="https://nordlysmarin.no/"
EXACT="https://nordlysmarinteknologi.no/"


def prof(*,name=NAME,org=ORG,municipality="TROMSØ"):
    return {"name":name,"organisation_number":org,
            "municipality":municipality,"website":""}


def cand(*,url=SHORT,title="Nordlys Marin | Velkommen",
         snippet="Marine tjenester i Tromsø",rank=1):
    return {"url":url,"title":title,"snippet":snippet,
            "rank":rank,"query":"synthetic_not_provider_query",
            "provider":"synthetic_test"}


def test_partial_legal_title_and_short_root_original_and_m32_both_abstain():
    x=cand()
    assert nominate_offline(prof(),[x])["selected"] is None
    n=shadow_nominate_for_fixture_only(prof(),[x])
    assert n["mode"]=="shadow_title_shortened_nomination_only"
    assert n["selected"]["url"]==SHORT
    assert n["published_claims"]==n["provider_requests"]==n["company_http_requests"]==0


def test_exact_legal_name_root_with_short_title_is_shadow_fetch_only():
    x=cand(url=EXACT)
    assert nominate_offline(prof(),[x])["selected"] is None
    r=shadow_nominate_for_fixture_only(prof(),[x])
    assert r["mode"]=="shadow_title_shortened_nomination_only"
    assert r["selected"]["url"]==EXACT


def test_complete_title_baseline_or_m32_stays_unmodified():
    x=cand(title=NAME)
    a=nominate_offline(prof(),[x])
    assert a["selected"] is not None
    b=shadow_nominate_for_fixture_only(prof(),[x])
    assert b["mode"]=="existing_m32_unchanged"
    assert b["selected"]["url"]==a["selected"]["url"]


def test_exact_legal_name_hostname_full_title_is_not_counted_as_shadow_gain():
    x=cand(url=EXACT,title=NAME)
    assert shadow_nominate_for_fixture_only(prof(),[x])["mode"]=="existing_m32_unchanged"


def test_unsafe_and_directory_hosts_never_nominated_even_with_ideal_metadata():
    for url in (
        "https://nordlysmarin.no.attacker.com/",
        "https://proff.no/",
        "https://linkedin.com/",
        "http://nordlysmarin.no/",
        "https://127.0.0.1/",
        "https://nordlysmarin.local/",
        "https://nordlysmarin.no/about/",
        "https://nordlysmarin.no/?q=spam",
        "https://user:pass@nordlysmarin.no/",
        "https://nordlysmarin.no:8443/",
        "https://parentgroup.no/",
    ):
        a=shadow_nominate_for_fixture_only(prof(),[cand(url=url)])
        assert a["selected"] is None,url
        assert a["published_claims"]==0


def test_no_naming_alignment_rejects_safe_root_website_shape():
    for url in ("https://northmedia.no/","https://nordlys.no/",
                "https://news-nordlysmarin.no/"):
        r=shadow_nominate_for_fixture_only(prof(),[cand(url=url)])
        assert r["selected"] is None,url


def test_reject_parent_company_and_wrong_incorporated_name_titles():
    for title in (
        "Nordlys Marin Holding AS",
        "Nordlys Marin Group",
        "Nordlys Marin Konsern",
        "Nordlys Marin AB",
        "Nordlys Marin Technologies AS",
        "Nordlys Marin Subsidiary",
    ):
        x=shadow_nominate_for_fixture_only(prof(),[cand(title=title)])
        assert x["selected"] is None,title


def test_reject_incomplete_name_with_municipality_absent_or_wrong():
    for snippet in ("Services for businesses","Office in Oslo",
                    "We sell marine equipment internationally"):
        x=shadow_nominate_for_fixture_only(prof(),[cand(snippet=snippet)])
        assert x["selected"] is None,snippet


def test_wrong_org_in_result_metadata_is_veto_not_positive_proof():
    for s in ("Org nr 987654321, Tromsø", "Org 987 654 321 Tromsø",
              "Org nr 987.654.321, Tromsø"):
        x=shadow_nominate_for_fixture_only(prof(),[cand(snippet=s)])
        assert x["selected"] is None,s
    x=shadow_nominate_for_fixture_only(prof(),[
        cand(snippet="Organisasjonsnummer 123 456 789, Tromsø")])
    assert x["selected"] is not None
    assert x["published_claims"]==0


def test_weak_short_legal_names_never_use_relaxed_title_rule():
    for name,title in (
        ("FJORD AS","Fjord | Velkommen"),
        ("NORDLYS MARIN AS","Nordlys | Velkommen"),
        ("NORGE AS","Norge | Homepage"),
    ):
        x=shadow_nominate_for_fixture_only(prof(name=name),[cand(title=title)])
        assert x["selected"] is None


def test_title_overlap_must_include_first_distinctive_token_and_two_total():
    for title in ("Marin Teknologi | Velkommen",
                  "Nordlys | Marine websites",
                  "Example Bedrift | Norlys Marin"):
        assert shadow_nominate_for_fixture_only(prof(),[cand(title=title)])["selected"] is None,title


def test_different_legal_form_away_from_title_is_not_proof():
    result=shadow_nominate_for_fixture_only(prof(),[
        cand(title="Nordlys Marin",snippet="Service company in Tromsø")])
    assert result["mode"]=="shadow_title_shortened_nomination_only"
    assert result["published_claims"]==0


def test_prefer_exact_identity_domain_over_partial_alias_and_search_rank():
    mixed=[
        cand(url=SHORT,title="Nordlys Marin",rank=1),
        cand(url=EXACT,title="Nordlys Marin",rank=3),
    ]
    r=shadow_nominate_for_fixture_only(prof(),mixed)
    assert r["selected"]["url"]==EXACT
    assert r["published_claims"]==0


def test_no_source_content_in_reason_summary():
    candidates=[
        cand(title="Nordlys Marin",snippet="Tromsø and SECRET_PROVIDER_TEXT"),
        cand(url="https://proff.no/selskap/a",title=NAME),
        cand(url="https://parentgroup.no/",title=NAME),
        cand(url=EXACT,title=NAME),
    ]
    x=diagnose_url_nomination_reasons(prof(),candidates)
    assert x["safe_root_count"]==3
    assert x["blocked_root_count"]==1
    assert x["full_title_mismatch_count"]==1
    assert x["allowed_domain_alias_mismatch_count"]==1
    assert x["published_claims"]==0
    assert x["provider_requests"]==x["independent_company_http_requests"]==0
    for sensitive in (ORG,SHORT,EXACT,NAME,"SECRET_PROVIDER_TEXT","Tromsø","parentgroup"):
        assert sensitive not in str(x)


def test_invalid_organisation_and_missing_municipality_cannot_shadow_nominate():
    for p in (prof(org="123"),prof(org=""),
              prof(municipality="")):
        x=shadow_nominate_for_fixture_only(p,[cand()])
        assert x["selected"] is None


def test_transient_number_scanner_finds_compact_and_spaced_forms():
    x=_potential_explicit_nine_digit_numbers("n 123456789 and 987 654 321 or 222.333.444")
    assert x=={"123456789","987654321","222333444"}


def test_empty_and_malformed_search_candidates_fail_closed():
    for items in ([],[{}],[{"url":"not-a-url","title":"Nordlys Marin","snippet":"Tromsø"}]):
        x=shadow_nominate_for_fixture_only(prof(),items)
        assert x["selected"] is None and x["published_claims"]==0


def test_determinism_input_order_for_equally_strong_candidates():
    candidates=[
        cand(url="https://www.nordlysmarinteknologi.no/",rank=2),
        cand(url=EXACT,rank=1),
    ]
    p=prof()
    a=shadow_nominate_for_fixture_only(p,candidates)
    b=shadow_nominate_for_fixture_only(p,list(reversed(candidates)))
    assert a["selected"]["url"]==b["selected"]["url"]==EXACT


def test_source_code_no_live_search_and_no_production_reference():
    source=(ROOT/"src/norway_company_agent/v10_m35_shadow_rejection_analysis.py").read_text()
    for disallowed in (
        "api.tavily.com/search","execute_bounded_search(",
        "requests.get(","requests.post(","urllib.request.urlopen(",
        "TAVILY_API_KEY","os.environ[","run_signalpost_v8.py",
        "run_v10_m33_consumed4_diagnostic.py",
    ):
        assert disallowed not in source
