from __future__ import annotations

import hashlib
import urllib.parse
from typing import Any


def _evidence_id(org: str, careers_url: str, content_sha256: str) -> str:
    material = f"{org}|{careers_url}|{content_sha256}"
    return "ev-careers-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def _confidence(website: dict[str, Any]) -> float:
    try:
        score = float((((website.get("value") or {}).get("identity_assessment") or {}).get("score")))
    except (TypeError, ValueError):
        score = 0.95
    return max(0.0, min(1.0, score))


def _host(url: str) -> str:
    try:
        host = (urllib.parse.urlparse(url).hostname or "").casefold().rstrip(".")
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


def _same_verified_host(left: str, right: str) -> bool:
    a = _host(left)
    b = _host(right)
    return bool(a and b and a == b)


def _typed_sitemap_identity_proof(
    *,
    assessment: dict[str, Any],
    final_url: str,
    website_hash: str,
    sitemap_url: str,
    sitemap_hash: str,
    careers_url: str,
) -> list[dict[str, Any]]:
    return [
        {
            "type": "website_identity_gate",
            "status": assessment.get("status"),
            "score": assessment.get("score"),
            "publishable": assessment.get("publishable"),
            "method": assessment.get("method"),
        },
        {
            "type": "same_verified_host_sitemap_careers_surface",
            "verified_website_url": final_url,
            "verified_website_content_sha256": website_hash,
            "sitemap_url": sitemap_url,
            "sitemap_content_sha256": sitemap_hash,
            "careers_url": careers_url,
            "same_verified_host": True,
            "method": "same_verified_host_sitemap_urlset_v1",
        },
    ]


def project_careers_page_claims(
    contract: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Project exact-homepage careers links without modifying the frozen V1 projector.

    The source is the already verified company homepage. A careers link is accepted only
    when it was captured from that same homepage snapshot and therefore carries the same
    content hash. This is a narrow careers-presence claim and never an active-job claim.
    Projection is deterministic and idempotent.
    """

    org = str(contract.get("organisation_number") or profile.get("organisation_number") or "")
    claims = [dict(item) for item in (contract.get("claims") or [])]
    evidence = [dict(item) for item in (contract.get("evidence") or [])]

    managed_field = "external.careers_page"
    removed_evidence_ids = {
        evidence_id
        for claim in claims
        if claim.get("field") == managed_field
        for evidence_id in (claim.get("evidence_ids") or [])
    }
    claims = [claim for claim in claims if claim.get("field") != managed_field]
    still_referenced = {
        evidence_id
        for claim in claims
        for evidence_id in (claim.get("evidence_ids") or [])
    }
    evidence = [
        item
        for item in evidence
        if item.get("id") not in (removed_evidence_ids - still_referenced)
    ]

    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") or {}
    assessment = value.get("identity_assessment") or {}
    final_url = str(value.get("final_url") or website.get("source_url") or "").strip()
    website_hash = str(website.get("content_sha256") or "").strip()
    retrieved_at = website.get("retrieved_at")

    if (
        website.get("status") != "available"
        or not assessment.get("publishable")
        or not final_url.startswith(("http://", "https://"))
        or len(website_hash) != 64
        or not retrieved_at
    ):
        return {
            **contract,
            "claims": claims,
            "evidence": sorted(evidence, key=lambda item: str(item.get("id") or "")),
        }

    evidence_by_id = {str(item.get("id")): item for item in evidence if item.get("id")}
    seen_urls: set[str] = set()
    for careers in value.get("careers_links") or []:
        if not isinstance(careers, dict):
            continue
        careers_url = str(careers.get("url") or "").strip()
        homepage_url = str(careers.get("homepage_url") or "").strip()
        homepage_hash = str(careers.get("homepage_content_sha256") or "").strip()
        if (
            not careers_url.startswith(("http://", "https://"))
            or careers_url in seen_urls
            or homepage_url != final_url
            or homepage_hash != website_hash
        ):
            continue

        evidence_id = _evidence_id(org, careers_url, website_hash)
        evidence_by_id[evidence_id] = {
            "id": evidence_id,
            "source_url": final_url,
            "source_class": "company_owned",
            "retrieved_at": retrieved_at,
            "content_sha256": website_hash,
            "claim_span": str(careers.get("evidence_span") or f"Homepage careers link: {careers_url}"),
        }
        claims.append(
            {
                "field": managed_field,
                "value": {
                    "url": careers_url,
                    "anchor_text": str(careers.get("anchor_text") or "").strip() or None,
                },
                "availability": "available",
                "confidence": _confidence(website),
                "evidence_ids": [evidence_id],
                "platform": "company_site",
                "signal_type": "careers_page",
                "claim_scope": str(careers.get("claim_scope") or ""),
            }
        )
        seen_urls.add(careers_url)

    sitemap = ((profile.get("evidence") or {}).get("website_sitemap_careers") or {})
    sitemap_value = sitemap.get("value") if isinstance(sitemap.get("value"), dict) else {}
    careers_url = str(sitemap_value.get("careers_url") or "").strip()
    sitemap_url = str(sitemap.get("source_url") or "").strip()
    sitemap_hash = str(sitemap.get("content_sha256") or "").strip()
    sitemap_retrieved_at = sitemap.get("retrieved_at")
    bound_verified_url = str(sitemap_value.get("verified_website_url") or "").strip()
    bound_website_hash = str(sitemap_value.get("verified_website_content_sha256") or "").strip()
    sitemap_assessment = (
        sitemap_value.get("identity_assessment")
        if isinstance(sitemap_value.get("identity_assessment"), dict)
        else {}
    )
    try:
        sitemap_identity_score = float(sitemap_assessment.get("score") or 0)
    except (TypeError, ValueError):
        sitemap_identity_score = 0.0

    if (
        sitemap.get("status") == "available"
        and careers_url.startswith(("http://", "https://"))
        and careers_url not in seen_urls
        and sitemap_url.startswith(("http://", "https://"))
        and len(sitemap_hash) == 64
        and sitemap_retrieved_at
        and bound_verified_url == final_url
        and bound_website_hash == website_hash
        and _same_verified_host(sitemap_url, final_url)
        and _same_verified_host(careers_url, final_url)
        and sitemap_assessment.get("status") == "exact"
        and sitemap_assessment.get("publishable") is True
        and sitemap_identity_score >= 0.95
        and bool(str(sitemap_assessment.get("method") or "").strip())
        and sitemap_value.get("lastmod_used_as_publication_date") is False
    ):
        evidence_id = _evidence_id(org, careers_url, sitemap_hash)
        evidence_by_id[evidence_id] = {
            "id": evidence_id,
            "source_url": sitemap_url,
            "source_class": "company_owned",
            "retrieved_at": sitemap_retrieved_at,
            "content_sha256": sitemap_hash,
            "claim_span": (
                f"Same-host sitemap lists careers surface: {careers_url}"
            )[:1000],
            "identity_proof": _typed_sitemap_identity_proof(
                assessment=sitemap_assessment,
                final_url=final_url,
                website_hash=website_hash,
                sitemap_url=sitemap_url,
                sitemap_hash=sitemap_hash,
                careers_url=careers_url,
            ),
            "extraction_method": "verified_company_sitemap_careers_surface_v1",
        }
        claims.append(
            {
                "field": managed_field,
                "value": {
                    "url": careers_url,
                    "anchor_text": None,
                },
                "availability": "available",
                "confidence": max(_confidence(website), sitemap_identity_score),
                "evidence_ids": [evidence_id],
                "platform": "company_site",
                "signal_type": "careers_page",
                "claim_scope": str(
                    sitemap_value.get("claim_scope")
                    or (
                        "Exact verified company site's same-host sitemap lists a generic careers/hiring surface. "
                        "This proves careers-surface presence only and does not assert recruitment intent "
                        "or a currently open vacancy."
                    )
                ),
            }
        )
        seen_urls.add(careers_url)

    return {
        **contract,
        "claims": claims,
        "evidence": sorted(evidence_by_id.values(), key=lambda item: str(item.get("id") or "")),
    }
