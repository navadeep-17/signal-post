"""M39 source-path provenance inventory from synthetic, offline-only records."""
from __future__ import annotations

import json
import sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from norway_company_agent.v10_m39_offline_existing_evidence_inventory import (
    FIELDS, aggregate_existing_signals, inspect_existing_profile_signals
)


def company(org="123456789", *,
            name="NORDLYS MARIN TEKNOLOGI AS",
            email=None,website="",bulk_site=None,live_site=None,site_record=None,
            social=False):
    reg={"navn":name}
    if email is not None:reg["epostadresse"]=email
    if bulk_site is not None:reg["hjemmeside"]=bulk_site
    ev={"registry":{"status":"available","value":reg}}
    if live_site is not None:
        ev["registry_live"]={"status":"available","value":{"website":live_site}}
    if site_record is not None:
        ev["website"]=site_record
    if social:
        ev["website"]={"status":"available","value":{
            "identity_assessment":{"publishable":True},
            "social_links":["https://www.linkedin.com/company/legitimate"]
        }}
    return {"organisation_number":org,"name":name,"municipality":"TROMSØ",
            "website":website,"evidence":ev}


def test_m39_missing_website_and_generic_email_not_owned_domain():
    row=company(email="contact@gmail.com")
    r=inspect_existing_profile_signals(row)
    assert r["no_registry_site_signal_anywhere"]
    assert r["registry_email_present"]
    assert r["registry_email_generic_or_rejected"]
    assert not r["registry_email_company_domain_candidate"]
    assert r["legal_name_compact_guess_available"]
    assert r["legal_name_hyphenated_guess_available"]
    assert r["no_new_registered_source_url_signal"]
    assert not r["verified_site_social_link_recovery_eligible"]


def test_m39_registry_business_email_is_existing_h1a_candidate_not_new_claim():
    row=company(email="post@nordlysmarin.no")
    r=inspect_existing_profile_signals(row)
    assert r["registry_email_present"]
    assert not r["registry_email_generic_or_rejected"]
    assert r["registry_email_company_domain_candidate"]
    assert not r["no_new_registered_source_url_signal"]
    assert not r["verified_existing_site"]


def test_m39_multiple_email_domains_are_only_candidates():
    r=inspect_existing_profile_signals(company(
        email="hei@nordlysmarin.no; faktura@nordlysmarinteknologi.no"
    ))
    assert r["registry_multiple_company_email_domains"]
    assert r["registry_email_company_domain_candidate"]
    assert not r["verified_existing_site"]


def test_m39_raw_registry_website_not_projected_to_profile_is_explicit_review_gap():
    p=company(bulk_site="https://nordlysmarin.no/")
    r=inspect_existing_profile_signals(p)
    assert r["bulk_registry_site_field_present"]
    assert r["registry_site_evidence_missing_from_profile"]
    assert not r["profile_site_seed_present"]
    assert not r["no_registry_site_signal_anywhere"]
    assert r["no_new_registered_source_url_signal"] is False
    assert not r["verified_existing_site"]


def test_m39_live_registry_website_without_seed_is_review_flag_only():
    r=inspect_existing_profile_signals(company(live_site="https://nordlysmarin.no/"))
    assert r["live_registry_site_field_present"]
    assert r["registry_site_evidence_missing_from_profile"]
    assert not r["verified_existing_site"]


def test_m39_existing_profile_seed_is_not_a_new_site():
    r=inspect_existing_profile_signals(company(
        website="https://nordlysmarin.no/",
        bulk_site="https://nordlysmarin.no/",
        email="post@nordlysmarin.no"
    ))
    assert r["profile_site_seed_present"]
    assert not r["registry_site_evidence_missing_from_profile"]
    assert not r["verified_existing_site"]
    assert not r["registry_email_company_domain_candidate"]


def test_m39_existing_unverified_available_homepage_not_promoted():
    p=company(site_record={"status":"available","value":{
        "identity_assessment":{"publishable":False},
        "social_links":["https://linkedin.com/company/other"]
    }})
    r=inspect_existing_profile_signals(p)
    assert r["existing_website_evidence_available_unverified"]
    assert not r["verified_existing_site"]
    assert not r["verified_site_social_link_recovery_eligible"]


def test_m39_existing_unavailable_homepage_is_not_new_source():
    r=inspect_existing_profile_signals(company(
        site_record={"status":"source_error","value":None}
    ))
    assert r["existing_website_evidence_nonavailable"]
    assert not r["verified_existing_site"]


def test_m39_social_recovery_requires_preverified_identity():
    r=inspect_existing_profile_signals(company(social=True))
    assert r["verified_existing_site"]
    assert r["verified_site_social_link_recovery_eligible"]


def test_m39_report_is_fixed_aggregates_and_no_identifiers_or_provider_content():
    rows=[
        company(org="123456789",email="post@nordlysmarin.no"),
        company(org="987654321",email="someone@gmail.com"),
        company(org="444555666",bulk_site="https://example.no/"),
    ]
    report=aggregate_existing_signals(rows)
    assert report["profiles_inspected"]==3
    flags=report["non_exclusive_company_flags"]
    assert set(flags)==set(FIELDS)
    assert flags["registry_email_company_domain_candidate"]==1
    assert flags["registry_email_generic_or_rejected"]==1
    assert flags["registry_site_evidence_missing_from_profile"]==1
    assert flags["bulk_registry_site_field_present"]==1
    assert report["verified_new_websites"]==0
    assert report["additional_external_http_requests"]==0
    assert report["provider_credits_used"]==0
    assert report["company_ownership_inferred"] is False
    text=json.dumps(report)
    for forbidden in ("nordlysmarin","123456789","987654321","444555666",
                      "post@",".no/","example.no","someone@"):
        assert forbidden not in text


def test_m39_missing_email_is_not_mistaken_for_generic_mailbox():
    r=inspect_existing_profile_signals(company())
    assert not r["registry_email_present"]
    assert not r["registry_email_generic_or_rejected"]
    assert not r["registry_email_company_domain_candidate"]


def test_m39_existing_email_discovery_evidence_flag_only():
    p=company(email="post@nordlysmarin.no")
    p["evidence"]["website_email_discovery"]={"status":"not_found","value":{
        "candidate_domain":"nordlysmarin.no","publishable":False
    }}
    r=inspect_existing_profile_signals(p)
    assert r["h1a_email_discovery_record_present"]
    assert not r["h1a_email_discovery_record_absent"]
    assert not r["verified_existing_site"]


def test_m39_wrong_org_duplicate_missing_location_and_invalid_inputs_fail_closed():
    rows=[
        company(org="123"),
        company(org="12345678x"),
        company(org="123456789",name=""),
        company(org="123456789")|{"municipality":""},
        company(org="123456789")|{"evidence":[]},
    ]
    for row in rows:
        with pytest.raises(ValueError):
            inspect_existing_profile_signals(row)
    with pytest.raises(ValueError):
        aggregate_existing_signals([company(),company()])
    with pytest.raises(ValueError):
        aggregate_existing_signals([])
    with pytest.raises(ValueError):
        aggregate_existing_signals([company() for _ in range(301)])


def test_m39_module_has_no_http_secret_or_production_call():
    source=(ROOT/"src/norway_company_agent/v10_m39_offline_existing_evidence_inventory.py").read_text()
    for blocked in (
        "api.tavily.com","TAVILY_API_KEY","execute_bounded_search(",
        "urllib.request","requests.get(","requests.post(",
        "run_signalpost_v8.py","run_v10_m38_actions_wrapper.py",
        "os.environ",
    ):
        assert blocked not in source
