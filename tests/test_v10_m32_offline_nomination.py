"""Synthetic M32 challenger; no provider traffic, no company HTTP, zero claims."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.discovery import choose_search_candidate
from norway_company_agent.tavily_offline_candidate import normalize_tavily_results, offline_screen
from norway_company_agent.v10_m32_offline_nomination import (
    _safe_first_party_homepage, nominate_offline, screen_independent_fixture,
)

COMPANY = "NORDLYS MARIN TEKNOLOGI AS"
ORG = "123456789"
SITE = "https://nordlysmarin.no/"


def profile(*, name=COMPANY, org=ORG, website=""):
    return {"name": name, "organisation_number": org,
            "municipality": "TROMSØ", "website": website}


def result(*, url=SITE, title=COMPANY, snippet="Marine systems in Tromsø", rank=1):
    return {"url": url, "title": title, "snippet": snippet,
            "rank": rank, "provider": "synthetic", "query": "offline"}


def provider_payload(**kw):
    r = result(**kw)
    return {"results": [{"url": r["url"], "title": r["title"],
                         "content": r["snippet"], "score": 0.999,
                         "raw_content": "UNTRUSTED_RAW_PROVIDER_OUTPUT"}],
            "answer": "UNTRUSTED_AI_SUMMARY"}


def webpage(*, url=SITE, requested_url=SITE,
            text=f"Velkommen til {COMPANY}. Organisasjonsnummer 123 456 789. Kontor i Tromsø.",
            title=COMPANY, status="available"):
    return {"status": status, "source_type": "synthetic_independent_page",
            "source_url": url, "value": {
                "requested_url": requested_url, "final_url": url,
                "title": title, "description": "",
                "identity_text_excerpt": text, "main_text_excerpt": text,
                "structured_organisations": [], "pages": [], "social_links": [],
            }}


def test_legacy_selection_abstains_on_plausible_first_party_site_without_org_in_snippet():
    data = result()
    old = choose_search_candidate(profile(), [data])
    assert old["abstained"] is True


def test_challenger_nominates_first_party_homepage_without_organisation_snippet():
    selected = nominate_offline(profile(), [result()])
    assert selected["path"] == "offline_strict_root_domain_with_full_title"
    assert selected["selected"]["url"] == SITE
    assert selected["published_claims"] == 0


def test_full_legal_name_domain_was_already_nominated_by_baseline():
    old=result(url="https://nordlysmarinteknologi.no/")
    picked=choose_search_candidate(profile(),[old])
    assert picked["selected"] is not None
    selected=nominate_offline(profile(),[old])
    assert selected["path"]=="baseline_unchanged"


def test_unsafe_hostname_substring_looks_accepted_to_legacy_but_is_rejected_here():
    deceptive=result(url="https://nordlysmarinteknologi.no.attacker.com/")
    # An unsafe historical fetch nomination is not a true legal-entity claim,
    # but it should not be inherited by a more conservative new experiment.
    assert choose_search_candidate(profile(),[deceptive])["selected"] is not None
    assert nominate_offline(profile(),[deceptive])["selected"] is None


def test_challenger_never_replaces_existing_baseline_candidate():
    old = result(snippet="Organisasjonsnummer 123 456 789, Tromsø")
    baseline = choose_search_candidate(profile(), [old])
    challenger = nominate_offline(profile(), [old])
    assert baseline["selected"] is not None
    assert challenger["path"] == "baseline_unchanged"
    assert challenger["selected"]["url"] == baseline["selected"]["url"]


def test_registry_website_seed_is_a_terminal_skip():
    x = nominate_offline(profile(website="https://registry-authorised.no/"), [result()])
    assert x["selected"] is None
    assert x["status"] == "existing_registry_site_seed"


def test_name_aligned_legal_acronym_nomination_without_snippet_org():
    row=profile(name="ARKITEKTFIRMA JON VIKØREN AS")
    item=result(url="https://arkjv.no/", title="Arkitektfirma Jon Vikøren AS",
                snippet="Et arkitektkontor i Oslo")
    assert choose_search_candidate(row, [item])["abstained"]
    x=nominate_offline(row,[item])
    assert x["selected"]["url"] == "https://arkjv.no/"
    assert x["path"].startswith("offline_")


def test_hyphenated_full_name_root_domain_is_eligible_for_a_crawl():
    x=nominate_offline(profile(),[result(url="https://nordlys-marin-teknologi.no/")])
    assert x["selected"]["url"] == "https://nordlys-marin-teknologi.no/"


def test_multi_token_alias_domain_first_party_root_is_eligible():
    row=profile(name="STIAN OLSEN BÅTMEKANIKK AS")
    x=nominate_offline(row,[result(url="https://stianolsen.no/",
                                    title="Stian Olsen Båtmekanikk AS")])
    assert x["selected"]["url"] == "https://stianolsen.no/"


def test_single_or_generic_name_risks_stay_quarantined():
    row=profile(name="FJORD AS")
    x=nominate_offline(row,[result(url="https://fjord.no/",title="FJORD AS")])
    assert x["selected"] is None
    assert x["status"] == "weak_legal_name"
    row=profile(name="NORGE AS")
    assert nominate_offline(row,[result(url="https://norge.no/",title="NORGE AS")])["selected"] is None


def test_partial_name_domain_never_enters_relaxed_gate():
    x=nominate_offline(profile(),[result(url="https://nordlys.no/")])
    assert x["selected"] is None


def test_parent_or_directory_must_not_become_company_owned_crawl():
    for bad in ("https://parentgroup.no/", "https://proff.no/",
                "https://linkedin.com/", "https://example.com/",
                "https://nordlysmarinteknologi.no.attacker.com/"):
        x=nominate_offline(profile(),[result(url=bad)])
        assert x["selected"] is None, bad


def test_aggregator_with_org_and_name_is_still_blocked_by_unchanged_baseline():
    for bad in ("https://proff.no/selskap/abc/", "https://linkedin.com/company/abc/"):
        x=nominate_offline(profile(),[result(
            url=bad, snippet=f"{COMPANY} Org 123456789 Tromsø"
        )])
        assert x["selected"] is None


def test_title_only_company_name_on_unrelated_host_is_not_ownership():
    assert nominate_offline(profile(),[result(
        url="https://morenyheter.no/", title=f"Nyheter: {COMPANY}",
        snippet=f"{COMPANY} startet i 2026"
    )])["selected"] is None


def test_search_title_tokens_required_exactly_not_parent_or_similar():
    for title in ("Nordlys Marin Holding AS",
                  "Nordlys Teknologi AS", "Nordlys Marin Group AS",
                  "Nordlys Marin Teknologier AS"):
        x=nominate_offline(profile(),[result(title=title)])
        assert x["selected"] is None, title


def test_raw_first_party_url_gate_rejects_http_private_hosts_paths_credentials_and_ports():
    urls=(
        "http://nordlysmarinteknologi.no/",
        "https://user:pass@nordlysmarinteknologi.no/",
        "https://nordlysmarinteknologi.no:8443/",
        "https://nordlysmarinteknologi.no/kontakt",
        "https://nordlysmarinteknologi.no/?utm=tracking",
        "https://nordlysmarinteknologi.no/#kontakt",
        "https://nordlysmarinteknologi.no.attacker.com/",
        "https://127.0.0.1/",
        "https://localhost/",
        "https://nordlysmarinteknologi.local/",
        "https://nordlysmarinteknologi.internal/",
        "https://nordlysmarinteknologi.test/",
        "https://nordlysmarinteknologi.no.evil.com/",
        "javascript:alert('a')",
        "nordlysmarinteknologi.no",
    )
    for url in urls:
        assert _safe_first_party_homepage(url) is None, url


def test_root_url_and_www_are_allowed_but_not_identity_claim():
    assert _safe_first_party_homepage(SITE)==SITE
    assert _safe_first_party_homepage("https://www.nordlysmarinteknologi.no/") == (
        "https://www.nordlysmarinteknologi.no/"
    )


def test_challenger_selection_deterministic_strength_over_provider_rank():
    opts=[
        result(url="https://stianolsen.no/",title="Stian Olsen Båtmekanikk AS",rank=1),
        result(url="https://stianolsenbatmekanikk.no/",title="Stian Olsen Båtmekanikk AS",rank=3),
    ]
    x=nominate_offline(profile(name="STIAN OLSEN BÅTMEKANIKK AS"),opts)
    assert x["selected"]["url"]=="https://stianolsenbatmekanikk.no/"


def test_empty_malformed_or_provider_generated_text_cannot_make_claims():
    for p in ({}, {"results":[]}, {"results":[{}]}, {"results":"wrong"}):
        results=normalize_tavily_results(p,query="synthetic")
        x=nominate_offline(profile(),results)
        assert x["selected"] is None
        assert x["published_claims"]==0


def test_offline_nomination_without_page_never_qualifies_publication():
    p=provider_payload()
    x=screen_independent_fixture(profile(),payload=p,independently_fetched=None)
    assert x["candidate_nominated"] is True
    assert x["identity_eligible_for_manual_review"] is False
    assert x["published_claims"]==0
    assert "UNTRUSTED" not in str(x)
    assert ORG not in str(x)


def test_identity_check_requires_exact_number_from_independently_fetched_page():
    x=screen_independent_fixture(profile(),payload=provider_payload(),
                                 independently_fetched=webpage())
    assert x["status"]=="eligible_for_manual_audit_only"
    assert x["identity_eligible_for_manual_review"] is True
    assert x["published_claims"]==0


def test_wrong_organisation_number_in_first_party_page_is_rejected():
    x=screen_independent_fixture(
        profile(),payload=provider_payload(),
        independently_fetched=webpage(text=f"{COMPANY}. Organisasjonsnummer 987654321. Tromsø.")
    )
    assert x["status"] in ("wrong_organisation_number","identity_not_proven")
    assert x["identity_eligible_for_manual_review"] is False


def test_identity_never_passes_on_company_title_and_location_without_exact_org():
    x=screen_independent_fixture(
        profile(),payload=provider_payload(),
        independently_fetched=webpage(text=f"Velkommen til {COMPANY} i Tromsø.")
    )
    assert x["identity_eligible_for_manual_review"] is False
    assert x["status"] in ("identity_not_proven","exact_org_number_required_for_manual_review")


def test_first_party_provenance_must_match_exact_nominated_url():
    x=screen_independent_fixture(
        profile(),payload=provider_payload(),
        independently_fetched=webpage(requested_url="https://parentgroup.no/")
    )
    assert x["status"]=="independent_page_provenance_mismatch"


def test_redirect_to_another_registered_domain_is_rejected():
    x=screen_independent_fixture(
        profile(),payload=provider_payload(),
        independently_fetched=webpage(url="https://parentgroup.no/")
    )
    assert x["identity_eligible_for_manual_review"] is False


def test_foreign_same_core_entity_does_not_pass_page_gate():
    x=screen_independent_fixture(
        profile(),payload=provider_payload(),
        independently_fetched=webpage(
            title=COMPANY,
            text="Nordlys Marin Teknologi AB svensk selskap i Tromsø uten norsk org nummer.")
    )
    assert x["identity_eligible_for_manual_review"] is False


def test_site_denied_or_unavailable_never_passes():
    for status in ("blocked","failed","not_found"):
        x=screen_independent_fixture(
            profile(),payload=provider_payload(),
            independently_fetched=webpage(status=status)
        )
        assert x["identity_eligible_for_manual_review"] is False


def test_old_m23_separate_production_contiguous_logic_remains_unchanged():
    # Legacy M23 nominee gate abstains on this *same* synthetic search
    # while the isolated M32 challenger can nominate for an independent fetch.
    p=provider_payload()
    before=offline_screen(profile(),p)
    after=screen_independent_fixture(profile(),payload=p,independently_fetched=webpage())
    assert before["status"]=="no_qualifying_search_candidate"
    assert after["identity_eligible_for_manual_review"]
    assert before["published_claims"]==after["published_claims"]==0


def test_provider_results_never_persist_in_challenger_audit():
    item=screen_independent_fixture(
        profile(),payload=provider_payload(),
        independently_fetched=webpage()
    )
    assert "nordlysmarin.no" not in str(item)
    assert ORG not in str(item)
    assert "UNTRUSTED_RAW_PROVIDER_OUTPUT" not in str(item)
    assert "UNTRUSTED_AI_SUMMARY" not in str(item)
