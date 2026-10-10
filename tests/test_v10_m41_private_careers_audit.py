"""M41 synthetic safety tests; zero live requests or company identity exposure."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"scripts")]

import pytest
from norway_company_agent.v10_m41_private_careers_audit import audit_one_archived_careers_candidate
from norway_company_agent.output_contract import project_terminal_envelope

ORG="123456789"
URL="https://company-example.no/"
H="a"*64

def fixture(*,org=ORG,identity=True,hash_matches=True,homepage_org=True,wrong_org=False,
            same_host=True):
    profile={
        "organisation_number":org,"name":"EXAMPLE INDUSTRIES AS","municipality":"OSLO",
        "run_metrics":{"requests":1},
        "evidence":{"website":{
            "field":"website","status":"available",
            "source_url":URL,"retrieved_at":"2026-10-01T01:02:03Z",
            "content_sha256":H,
            "value":{
                "final_url":URL,
                "title":"Example Industries",
                "main_text_excerpt":"Example Industries manufacturing and information.",
                "identity_text_excerpt":("Org nr "+org if homepage_org else "Welcome")
                      + (" Org nr 987654321" if wrong_org else ""),
                "identity_assessment":{"publishable":identity,"score":0.99},
                "careers_links":[{
                    "url":(URL+"karriere" if same_host else "https://other-company.no/karriere"),
                    "homepage_url":URL,
                    "homepage_content_sha256":H if hash_matches else "b"*64,
                    "evidence_span":"Homepage links to careers, without active vacancies",
                    "claim_scope":"Only careers link present, no actual vacancies proven",
                }],
            },
        }},
    }
    envelope={
        "run_id":"m41-synthetic-test",
        "organisation_number":org,
        "state":"complete",
        "started_at":"2026-10-01T01:02:03Z",
        "completed_at":"2026-10-01T01:02:04Z",
        "profile":profile
    }
    return project_terminal_envelope(envelope),profile


def test_valid_exact_org_homepage_and_careers_provenance_qualifies_only_for_human_review():
    contract,p=fixture()
    outcome=audit_one_archived_careers_candidate(contract,p)
    flags=outcome["flags"]
    assert flags["candidate_net_new_companies"]==1
    assert flags["retained_site_exact_publishable"]==1
    assert flags["homepage_has_explicit_exact_org_number"]==1
    assert flags["homepage_has_conflicting_org_number"]==0
    assert flags["careers_link_provenance_exact_match"]==1
    assert flags["contract_validator_pass"]==1
    assert flags["canonical_validator_pass"]==1
    assert flags["synthesis_validator_pass"]==1
    assert flags["other_existing_claims_loss_count"]==0
    assert flags["other_existing_evidence_loss_count"]==0
    assert outcome["eligible_for_separate_manual_source_review"] is True
    assert outcome["independently_manual_verified"] is False
    assert outcome["publishable_coverage_gain"]==0
    assert outcome["production_modified"] is False
    assert "company-example.no" not in str(outcome)
    assert ORG not in str(outcome)


@pytest.mark.parametrize("args,flag",[
    ({"homepage_org":False},"homepage_has_explicit_exact_org_number"),
    ({"wrong_org":True},"homepage_has_conflicting_org_number"),
    ({"hash_matches":False},"careers_link_provenance_exact_match"),
    ({"identity":False},"retained_site_exact_publishable"),
    ({"same_host":False},"careers_link_provenance_exact_match"),
])
def test_absence_or_conflict_in_site_identity_and_link_proof_blocks_positive(args,flag):
    contract,p=fixture(**args)
    output=audit_one_archived_careers_candidate(contract,p)
    assert output["eligible_for_separate_manual_source_review"] is False
    assert flag in output["flags"]
    assert output["publishable_coverage_gain"]==0


def test_no_original_careers_company_allowed():
    c,p=fixture()
    c["claims"].append({
        "field":"external.careers_page","availability":"available",
        "value":{"url":URL+"karriere"},"evidence_ids":["ev-unused"]
    })
    with pytest.raises(ValueError):
        audit_one_archived_careers_candidate(c,p)


def test_org_mismatch_and_forged_org_fail_before_projection():
    c,p=fixture()
    p["organisation_number"]="987654321"
    with pytest.raises(ValueError):
        audit_one_archived_careers_candidate(c,p)
    c,p=fixture()
    p["organisation_number"]="123"
    with pytest.raises(ValueError):
        audit_one_archived_careers_candidate(c,p)


def test_source_timestamp_and_hash_veto_remains_private():
    c,p=fixture()
    p["evidence"]["website"]["retrieved_at"]=None
    p["evidence"]["website"]["content_sha256"]="unsafe"
    o=audit_one_archived_careers_candidate(c,p)
    assert not o["eligible_for_separate_manual_source_review"]
    assert o["flags"]["homepage_retrieval_timestamp_present"]==0
    assert o["flags"]["homepage_source_hash_valid"]==0
    assert o["approved_for_automatic_publication"]==0 if "approved_for_automatic_publication" in o else True


def test_no_source_http_no_org_or_url_emit_in_audit_module():
    source=(ROOT/"src/norway_company_agent/v10_m41_private_careers_audit.py").read_text()
    runner=(ROOT/"scripts/run_v10_m41_private_careers_audit.py").read_text()
    for code in (source,runner):
        for fragment in (
            "TAVILY_API_KEY","SIGNALPOST_PILOT_REPORT_KEY",
            "requests.get(","requests.post(","urllib.request",
            "run_signalpost_v8.py","api.tavily.com",
        ):
            assert fragment not in code
    assert "print(json.dumps(report,sort_keys=True))" in runner
