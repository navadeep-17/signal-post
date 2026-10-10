"""M41: private, offline review of the one M40 net-new careers-link candidate.

Only retained, SHA-pinned and ALREADY CONSUMED first-party homepage evidence.
Nothing is fetched, written, published, deployed, or merged. The evaluator's
actual score and a fresh manual website review are NOT claimed.

The existing careers projection is run strictly as written. This audit adds
a deliberately HIGHER recommendation gate: the fetched homepage identity text
must explicitly contain the exact Norwegian org number as an organisation
number, no conflicting number, and first-party link provenance must match
the frozen homepage URL/content hash. A positive is STILL ONLY "eligible
for private human review", not approved publication.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from urllib.parse import urlsplit
from typing import Any

from .careers_contract import project_careers_page_claims
from .canonical_projection import project_canonical_profile,validate_canonical_projection
from .identity import _explicit_org_numbers
from .output_contract import validate_contract_object
from .synthesis import build_company_synthesis,validate_company_synthesis

KEYS=("candidate_net_new_companies","retained_site_exact_publishable",
      "homepage_has_explicit_exact_org_number","homepage_has_conflicting_org_number",
      "homepage_source_hash_valid","homepage_retrieval_timestamp_present",
      "careers_link_provenance_exact_match","careers_link_same_hostname",
      "careers_link_https","reprojected_claims_linked_to_valid_evidence",
      "contract_validator_pass","canonical_validator_pass","synthesis_validator_pass",
      "other_existing_claims_loss_count","other_existing_evidence_loss_count",
      "cross_company_changes","new_claim_published","manual_source_review_completed")

def _claims(contract:dict[str,Any], field:str)->list[dict[str,Any]]:
    return [x for x in (contract.get("claims") or []) if isinstance(x,dict)
            and x.get("field")==field and x.get("availability")=="available"]

def _host(url:str)->str:
    try:
        parsed=urlsplit(url)
        return (parsed.hostname or "").casefold().rstrip(".")
    except (TypeError,ValueError):
        return ""

def _normalized(url:str)->str:
    return url.rstrip("/")

def audit_one_archived_careers_candidate(
    contract:dict[str,Any],profile:dict[str,Any]
)->dict[str,Any]:
    """Counts/booleans ONLY. Company identity and URLs MUST NOT leave memory."""
    if not isinstance(contract,dict) or not isinstance(profile,dict):
        raise ValueError("Malformed archived company record")
    org=profile.get("organisation_number")
    if not isinstance(org,str) or len(org)!=9 or not org.isascii() or not org.isdecimal():
        raise ValueError("Invalid exact legal organisation number")
    if contract.get("organisation_number")!=org:
        raise ValueError("Cross-company contract/profile mismatch")
    if _claims(contract,"external.careers_page"):
        raise ValueError("Only previously unclaimed company allowed")
    home=((profile.get("evidence") or {}).get("website") or {})
    value=home.get("value") or {}
    if not isinstance(home,dict) or not isinstance(value,dict):
        raise ValueError("Malformed archived homepage evidence")
    assessment=value.get("identity_assessment") or {}
    if not isinstance(assessment,dict):
        raise ValueError("Malformed company identity assessment")
    root=str(value.get("final_url") or home.get("source_url") or "")
    root_hash=str(home.get("content_sha256") or "")
    root_host=_host(root)
    root_proof=(
        home.get("status")=="available"
        and assessment.get("publishable") is True
        and _host(str(home.get("source_url") or ""))==root_host
        and bool(root_host)
    )
    sha_ok=(len(root_hash)==64 and all(ch in "0123456789abcdef" for ch in root_hash.lower()))
    timestamp=bool(home.get("retrieved_at"))
    numbers=_explicit_org_numbers(value)
    exact_in_home=org in numbers
    wrong_in_home=bool(numbers-{org})
    candidate_links=value.get("careers_links") or []
    if not isinstance(candidate_links,list):
        raise ValueError("Malformed homepage careers link collection")
    link_checks=[]
    for item in candidate_links:
        if not isinstance(item,dict) or not isinstance(item.get("url"),str):
            continue
        url=item["url"]
        check={
            "same_host":bool(root_host and _host(url)==root_host),
            "https":urlsplit(url).scheme=="https",
            "origin_matches":_normalized(str(item.get("homepage_url") or ""))==_normalized(root),
            "hash_matches":str(item.get("homepage_content_sha256") or "")==root_hash,
            "has_span":bool(str(item.get("evidence_span") or "").strip()),
        }
        link_checks.append(check)
    exact_link=bool(link_checks and any(all(c.values()) for c in link_checks))

    proposed=project_careers_page_claims(deepcopy(contract),profile)
    new_claims=_claims(proposed,"external.careers_page")
    evidence={e.get("id"):e for e in proposed.get("evidence") or [] if isinstance(e,dict)}
    source_links=set(str(x.get("url") or "") for x in candidate_links if isinstance(x,dict))
    accepted_evidence=True
    for claim in new_claims:
        val=claim.get("value") or {}
        refs=claim.get("evidence_ids") or []
        if (
            not isinstance(val,dict)
            or str(val.get("url") or "") not in source_links
            or claim.get("signal_type")!="careers_page"
            or claim.get("platform")!="company_site"
            or not refs
        ):
            accepted_evidence=False
            continue
        for evidence_id in refs:
            item=evidence.get(evidence_id)
            if not item or item.get("source_url")!=root or item.get("content_sha256")!=root_hash:
                accepted_evidence=False
    accepted_evidence=bool(new_claims) and accepted_evidence

    # Strictly compare source-output records by canonical JSON representation,
    # excluding the managed careers field. No baseline evidence may disappear.
    def canonical_set(rows:list[dict[str,Any]])->set[str]:
        import json
        return {json.dumps(x,sort_keys=True,ensure_ascii=False) for x in rows}
    old_noncareers=canonical_set([x for x in contract.get("claims") or []
                                  if x.get("field")!="external.careers_page"])
    new_noncareers=canonical_set([x for x in proposed.get("claims") or []
                                  if x.get("field")!="external.careers_page"])
    claim_losses=len(old_noncareers-new_noncareers)
    old_evidence_ids={str(x.get("id")) for x in contract.get("evidence") or []
                      if isinstance(x,dict)}
    new_evidence_ids={str(x.get("id")) for x in proposed.get("evidence") or []
                      if isinstance(x,dict)}
    evidence_losses=len(old_evidence_ids-new_evidence_ids)
    contract_errors=validate_contract_object(proposed)
    canonical=project_canonical_profile(proposed)
    canonical_errors=validate_canonical_projection(canonical)
    synth=build_company_synthesis(canonical)
    synthesis_errors=validate_company_synthesis({**canonical,"synthesis":synth})
    flags={
        "candidate_net_new_companies":int(bool(new_claims)),
        "retained_site_exact_publishable":int(root_proof),
        "homepage_has_explicit_exact_org_number":int(exact_in_home),
        "homepage_has_conflicting_org_number":int(wrong_in_home),
        "homepage_source_hash_valid":int(sha_ok),
        "homepage_retrieval_timestamp_present":int(timestamp),
        "careers_link_provenance_exact_match":int(exact_link),
        "careers_link_same_hostname":int(any(c["same_host"] for c in link_checks)),
        "careers_link_https":int(any(c["https"] for c in link_checks)),
        "reprojected_claims_linked_to_valid_evidence":int(accepted_evidence),
        "contract_validator_pass":int(not contract_errors),
        "canonical_validator_pass":int(not canonical_errors),
        "synthesis_validator_pass":int(not synthesis_errors),
        "other_existing_claims_loss_count":claim_losses,
        "other_existing_evidence_loss_count":evidence_losses,
        "cross_company_changes":0,
        "new_claim_published":0,
        "manual_source_review_completed":0,
    }
    assert tuple(flags)==KEYS
    # This is a recommendation only. The original URL may no longer be live,
    # and the automated stored site assessment is not independent human review.
    candidate_for_manual_audit=bool(
        root_proof and sha_ok and timestamp and exact_in_home and not wrong_in_home
        and exact_link and accepted_evidence
        and not claim_losses and not evidence_losses
        and not contract_errors and not canonical_errors and not synthesis_errors
    )
    return {
        "schema":"m41_private_archived_careers_source_gate_v1",
        "source":"SAME_PREVIOUSLY_CONSUMED_M19_M20_ORIGINAL_REPORTS",
        "flags":flags,
        "eligible_for_separate_manual_source_review":candidate_for_manual_audit,
        "independently_manual_verified":False,
        "measured_score_improvement":False,
        "publishable_coverage_gain":0,
        "third_party_requests":0,
        "company_http_requests":0,
        "production_modified":False,
    }
