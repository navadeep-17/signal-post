from __future__ import annotations

import hashlib
import re
from typing import Any

from .company_site_contact import _structured_node_identity


PHONE_STRATEGY = "verified_company_jsonld_norwegian_phone_v1"


def normalize_norwegian_contact_phone(value: Any) -> str | None:
    """Return conservative Norwegian E.164 or abstain."""

    text = str(value or "").strip()
    if not text:
        return None
    if re.search(r"(?i)\b(?:ext|extension|x|innvalg)\b", text):
        return None

    compact = re.sub(r"[\s().-]", "", text)
    if compact.startswith("+47"):
        compact = compact[3:]
    elif compact.startswith("0047"):
        compact = compact[4:]
    elif compact.startswith("47") and len(compact) == 10:
        compact = compact[2:]

    if not re.fullmatch(r"\d{8}", compact):
        return None
    if compact[0] in {"0", "1"}:
        return None
    return "+47" + compact


def _structured_phone_values(value: Any, *, telephone_field: bool = False) -> set[str]:
    """Traverse only schema fields explicitly named telephone."""

    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            found.update(
                _structured_phone_values(
                    child,
                    telephone_field=telephone_field or str(key).casefold() == "telephone",
                )
            )
    elif isinstance(value, list):
        for child in value:
            found.update(_structured_phone_values(child, telephone_field=telephone_field))
    elif telephone_field and isinstance(value, (str, int)):
        phone = normalize_norwegian_contact_phone(value)
        if phone:
            found.add(phone)
    return found


def company_site_contact_phone_observations(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Recover structured first-party contact phones with zero network access.

    The individual retained schema.org Organization node must independently
    identify the target using the same exact-node identity gate qualified for
    JSON-LD contact-email recovery. Telephone values never participate in
    identity matching.
    """

    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") or {}
    identity = value.get("identity_assessment") or {}
    if website.get("status") != "available" or not identity.get("publishable"):
        return []

    org = str(profile.get("organisation_number") or "")
    if len(org) != 9 or not org.isdigit():
        return []

    source_url = str(value.get("final_url") or website.get("source_url") or "").strip()
    retrieved_at = str(website.get("retrieved_at") or "").strip()
    content_sha256 = str(value.get("content_sha256") or website.get("content_sha256") or "").strip()
    if not source_url.startswith(("http://", "https://")) or not retrieved_at or len(content_sha256) != 64:
        return []

    candidates: dict[str, dict[str, Any]] = {}
    for index, node in enumerate(value.get("structured_organisations") or []):
        if not isinstance(node, dict):
            continue
        node_identity = _structured_node_identity(profile, node)
        if node_identity is None:
            continue
        for phone in sorted(_structured_phone_values(node)):
            candidates.setdefault(
                phone,
                {
                    "node_index": index,
                    "node_identity": node_identity,
                },
            )

    observations: list[dict[str, Any]] = []
    for phone in sorted(candidates):
        metadata = candidates[phone]
        node_identity = dict(metadata.get("node_identity") or {})
        observation_id = "company-site-phone-" + hashlib.sha256(
            f"{org}|{phone}|{source_url}|{content_sha256}".encode("utf-8")
        ).hexdigest()[:24]

        observations.append(
            {
                "id": observation_id,
                "organisation_number": org,
                "platform": "company_site",
                "signal_type": "company_profile",
                "source_url": source_url,
                "retrieved_at": retrieved_at,
                "content_sha256": content_sha256,
                "exact_entity": True,
                "identity_proof": [
                    {
                        "type": "website_identity_gate",
                        "status": identity.get("status"),
                        "score": identity.get("score"),
                        "method": identity.get("method"),
                    },
                    {
                        "type": "structured_organization_identity_gate",
                        "node_index": metadata.get("node_index"),
                        "method": node_identity.get("method"),
                        "observed_organisation_numbers": list(
                            node_identity.get("observed_organisation_numbers") or []
                        ),
                        "matched_name": node_identity.get("matched_name"),
                    },
                    {
                        "type": "structured_organization_telephone_field",
                        "source_url": source_url,
                        "content_sha256": content_sha256,
                    },
                ],
                "acquisition_mode": "permitted_public_page",
                "rights_status": "approved",
                "source_class": "company_site",
                "evidence_span": (
                    f"Exact company homepage schema.org Organization node publishes contact telephone {phone}"
                ),
                "contact_phone": phone,
                "metrics": {
                    "identity_score": identity.get("score"),
                    "claim_scope": (
                        "Contact telephone explicitly present in an already-retained schema.org "
                        "Organization telephone field on the exact company website; the individual "
                        "structured node independently matches the target legal entity."
                    ),
                    "network_requests_added": 0,
                },
                "strategy": PHONE_STRATEGY,
            }
        )
    return observations


def attach_company_site_contact_phone_observations(profile: dict[str, Any]) -> dict[str, Any]:
    existing = [item for item in (profile.get("external_observations") or []) if isinstance(item, dict)]
    recovered = company_site_contact_phone_observations(profile)
    by_id = {
        str(item.get("id")): item
        for item in [*existing, *recovered]
        if str(item.get("id") or "").strip()
    }
    profile["external_observations"] = sorted(
        by_id.values(),
        key=lambda row: (
            str(row.get("signal_type") or ""),
            str(row.get("platform") or ""),
            str(row.get("id") or ""),
        ),
    )
    return profile
