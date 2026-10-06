from __future__ import annotations

import hashlib
from typing import Any


MANAGED_FIELD = "external.hiring_intent"
EXPECTED_METHOD = "explicit_homepage_vacancy_count"


def _evidence_id(org: str, source_url: str, content_sha256: str, count: int) -> str:
    material = f"{org}|{source_url}|{content_sha256}|{count}"
    return "ev-hiring-intent-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def _confidence(website: dict[str, Any]) -> float:
    try:
        score = float((((website.get("value") or {}).get("identity_assessment") or {}).get("score")))
    except (TypeError, ValueError):
        score = 0.95
    return max(0.0, min(1.0, score))


def _qualified_homepage_intent(profile: dict[str, Any]) -> dict[str, Any] | None:
    """Return one explicit positive homepage vacancy-count signal or abstain.

    This is intentionally narrower than free-text recruitment matching. The exact verified
    homepage must already have produced the bounded explicit_homepage_vacancy_count
    observation during its existing fetch. A careers link alone is never hiring intent.
    """
    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") if isinstance(website.get("value"), dict) else {}
    assessment = value.get("identity_assessment") if isinstance(value.get("identity_assessment"), dict) else {}
    source_url = str(value.get("final_url") or website.get("source_url") or "").strip()
    digest = str(website.get("content_sha256") or value.get("content_sha256") or "").strip()
    retrieved_at = str(website.get("retrieved_at") or "").strip()
    signal = value.get("active_hiring_signal") if isinstance(value.get("active_hiring_signal"), dict) else {}

    if (
        website.get("status") != "available"
        or not assessment.get("publishable")
        or not source_url.startswith(("http://", "https://"))
        or len(digest) != 64
        or not retrieved_at
        or signal.get("method") != EXPECTED_METHOD
        or signal.get("active_vacancies") is not True
        or str(signal.get("homepage_url") or "").rstrip("/") != source_url.rstrip("/")
    ):
        return None

    try:
        count = int(signal.get("active_vacancy_count") or 0)
    except (TypeError, ValueError):
        return None
    if not 1 <= count <= 500:
        return None

    evidence_span = " ".join(str(signal.get("evidence_span") or "").split())
    if not evidence_span:
        # Older retained consumed profiles predate evidence-span retention, but the stored
        # method can only have been produced by the strict explicit-count regex.
        evidence_span = f"Explicit homepage vacancy-count signal: {count} active vacancies."

    return {
        "source_url": source_url,
        "retrieved_at": retrieved_at,
        "content_sha256": digest,
        "active_vacancy_count": count,
        "evidence_span": evidence_span[:500],
        "identity_proof": dict(assessment),
    }


def project_company_authored_hiring_intent(
    contract: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Project level-2 hiring semantics from retained exact-homepage evidence.

    Semantics are deliberately three-level:
      careers surface != company-authored hiring intent != specific active job.

    This projector manages only external.hiring_intent. It performs zero network access,
    never creates external.job_posting, and never treats a generic careers link as intent.
    """
    org = str(contract.get("organisation_number") or profile.get("organisation_number") or "")
    claims = [dict(item) for item in (contract.get("claims") or [])]
    evidence = [dict(item) for item in (contract.get("evidence") or [])]

    removed_ids = {
        str(evidence_id)
        for claim in claims
        if claim.get("field") == MANAGED_FIELD
        for evidence_id in (claim.get("evidence_ids") or [])
    }
    claims = [claim for claim in claims if claim.get("field") != MANAGED_FIELD]
    still_referenced = {
        str(evidence_id)
        for claim in claims
        for evidence_id in (claim.get("evidence_ids") or [])
    }
    evidence = [
        item
        for item in evidence
        if str(item.get("id") or "") not in (removed_ids - still_referenced)
    ]

    intent = _qualified_homepage_intent(profile)
    if intent is None:
        return {
            **contract,
            "claims": claims,
            "evidence": sorted(evidence, key=lambda item: str(item.get("id") or "")),
        }

    evidence_id = _evidence_id(
        org,
        intent["source_url"],
        intent["content_sha256"],
        int(intent["active_vacancy_count"]),
    )
    evidence_by_id = {
        str(item.get("id")): item
        for item in evidence
        if str(item.get("id") or "")
    }
    evidence_by_id[evidence_id] = {
        "id": evidence_id,
        "source_url": intent["source_url"],
        "source_class": "company_owned",
        "retrieved_at": intent["retrieved_at"],
        "content_sha256": intent["content_sha256"],
        "claim_span": intent["evidence_span"],
        "identity_proof": intent["identity_proof"],
        "extraction_method": EXPECTED_METHOD,
    }
    claims.append(
        {
            "field": MANAGED_FIELD,
            "value": {
                "active_vacancy_count": int(intent["active_vacancy_count"]),
                "source_url": intent["source_url"],
            },
            "availability": "available",
            "confidence": _confidence(((profile.get("evidence") or {}).get("website") or {})),
            "evidence_ids": [evidence_id],
            "platform": "company_site",
            "signal_type": "hiring_intent",
            "claim_scope": (
                "The exact verified company homepage explicitly reports a positive count of "
                "open positions. This is company-authored hiring intent/presence only; it is "
                "not proof of any specific vacancy. Specific active jobs require a separate "
                "external.job_posting claim."
            ),
        }
    )
    return {
        **contract,
        "claims": claims,
        "evidence": sorted(evidence_by_id.values(), key=lambda item: str(item.get("id") or "")),
    }
