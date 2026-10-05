from __future__ import annotations

import copy
import re
from typing import Any
from urllib.parse import urlparse


LEGACY_ACTIVITY_METHOD_BY_FIELD = {
    "external.company_update": "verified_same_site_dated_detail_page_v1",
    "external.job_posting": "verified_same_site_job_detail_page_v1",
}
EXPECTED_SIGNAL_TYPE_BY_FIELD = {
    "external.company_update": "company_update",
    "external.job_posting": "job_posting",
}


def _present(value: Any) -> bool:
    return value is not None and value != ""


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").casefold().strip(".")
    except ValueError:
        return ""


def _same_verified_site(url: str, verified_url: str) -> bool:
    candidate = _host(url)
    verified = _host(verified_url)
    if not candidate or not verified:
        return False
    return candidate == verified or candidate.endswith("." + verified) or verified.endswith("." + candidate)


def _valid_sha256(value: Any) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{64}", str(value or "").strip()))


def _verified_website_identity(contract: dict[str, Any]) -> tuple[str, Any] | None:
    evidence_by_id = {
        str(item.get("id")): item
        for item in (contract.get("evidence") or [])
        if isinstance(item, dict) and item.get("id")
    }
    for claim in contract.get("claims") or []:
        if not isinstance(claim, dict):
            continue
        if claim.get("field") != "official_website" or claim.get("availability") != "available":
            continue
        website_url = str(claim.get("value") or "").strip()
        if not website_url.startswith(("http://", "https://")):
            continue
        for evidence_id in claim.get("evidence_ids") or []:
            row = evidence_by_id.get(str(evidence_id))
            if row is None:
                continue
            source_url = str(row.get("source_url") or "").strip()
            identity_proof = row.get("identity_proof")
            if (
                source_url.startswith(("http://", "https://"))
                and _same_verified_site(source_url, website_url)
                and _present(identity_proof)
            ):
                return website_url, identity_proof
    return None


def _legacy_activity_evidence_matches(
    *,
    claim: dict[str, Any],
    row: dict[str, Any],
    website_url: str,
) -> bool:
    field = str(claim.get("field") or "")
    expected_signal_type = EXPECTED_SIGNAL_TYPE_BY_FIELD.get(field)
    if expected_signal_type is None:
        return False
    if claim.get("availability") != "available":
        return False
    if claim.get("platform") != "company_site" or claim.get("signal_type") != expected_signal_type:
        return False

    value = claim.get("value")
    if not isinstance(value, dict):
        return False
    claim_url = str(value.get("url") or "").strip()
    if not claim_url.startswith(("http://", "https://")) or not _same_verified_site(claim_url, website_url):
        return False

    evidence_id = str(row.get("id") or "")
    if not evidence_id.startswith("ev-first-party-") or evidence_id.startswith("ev-first-party-feed-"):
        return False
    source_url = str(row.get("source_url") or "").strip()
    if (
        row.get("source_class") != "company_owned"
        or not source_url.startswith(("http://", "https://"))
        or not _same_verified_site(source_url, website_url)
        or not _same_verified_site(source_url, claim_url)
        or not _valid_sha256(row.get("content_sha256"))
    ):
        return False

    if field == "external.company_update":
        published_date = str(value.get("published_date") or "").strip()
        if not published_date or str(row.get("effective_at") or "").strip() != published_date:
            return False

    return True


def project_first_party_activity_provenance(contract: dict[str, Any]) -> dict[str, Any]:
    """Expose retained exact-site proof for legacy page-backed jobs and updates.

    The legacy C12 activity projector already publishes only same-site detail pages under an
    exact verified company website. Older final evidence rows did not carry that website
    identity proof or a named extraction method. This deterministic pass fills only those
    two evaluator-visible provenance fields on the exact legacy evidence rows it can prove.

    It performs no network access and never changes claims, evidence IDs, source URLs,
    source hashes, confidence, availability, or existing provenance.
    """

    website_identity = _verified_website_identity(contract)
    if website_identity is None:
        return contract
    website_url, identity_proof = website_identity

    claims = [dict(item) for item in (contract.get("claims") or [])]
    evidence = [dict(item) for item in (contract.get("evidence") or [])]
    evidence_by_id = {str(item.get("id")): item for item in evidence if item.get("id")}

    for claim in claims:
        field = str(claim.get("field") or "")
        method = LEGACY_ACTIVITY_METHOD_BY_FIELD.get(field)
        if method is None:
            continue
        for evidence_id in claim.get("evidence_ids") or []:
            row = evidence_by_id.get(str(evidence_id))
            if row is None or not _legacy_activity_evidence_matches(
                claim=claim,
                row=row,
                website_url=website_url,
            ):
                continue
            if not _present(row.get("identity_proof")):
                row["identity_proof"] = copy.deepcopy(identity_proof)
            if not _present(row.get("extraction_method")):
                row["extraction_method"] = method

    return {
        **contract,
        "claims": claims,
        "evidence": evidence,
    }
