from __future__ import annotations

import hashlib
import re
import urllib.parse
from typing import Any


SOCIAL_PROFILE_HOSTS = {
    "linkedin": "linkedin.com",
    "facebook": "facebook.com",
    "instagram": "instagram.com",
    "x": "x.com",
    "youtube": "youtube.com",
    "tiktok": "tiktok.com",
}
LEGAL_SUFFIXES = {"as", "asa", "da", "sa", "enk", "ans", "ba", "nuf"}


def _safe_profile_url(platform: str, profile_url: str) -> bool:
    """Reject malformed or non-profile social URLs before they become claims."""

    expected_host = SOCIAL_PROFILE_HOSTS.get(platform)
    if not expected_host:
        return False
    try:
        parsed = urllib.parse.urlparse(profile_url)
    except ValueError:
        return False
    host = (parsed.hostname or "").casefold().removeprefix("www.")
    if parsed.scheme not in {"http", "https"} or host != expected_host:
        return False

    raw_parts = [urllib.parse.unquote(part).strip() for part in parsed.path.split("/") if part.strip()]
    lowered = [part.casefold() for part in raw_parts]
    if not raw_parts:
        return False

    social_domains = tuple(SOCIAL_PROFILE_HOSTS.values())
    for part in lowered:
        if part.startswith(("http:", "https:", "www.")):
            return False
        if any(domain in part for domain in social_domains):
            return False

    if platform == "linkedin":
        return len(raw_parts) == 2 and lowered[0] == "company"
    if platform in {"instagram", "x"}:
        return len(raw_parts) == 1
    if platform == "tiktok":
        return len(raw_parts) == 1 and raw_parts[0].startswith("@")
    if platform == "youtube":
        if len(raw_parts) == 1:
            return raw_parts[0].startswith("@")
        return len(raw_parts) == 2 and lowered[0] in {"channel", "user", "c"}
    if platform == "facebook":
        return len(raw_parts) == 1 or (len(raw_parts) == 2 and lowered[0] == "p")
    return False


def _identity_text(value: str) -> str:
    return (
        str(value or "")
        .casefold()
        .replace("æ", "ae")
        .replace("ø", "o")
        .replace("å", "a")
    )


def _identity_tokens(value: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]+", _identity_text(value)) if token]


def _compact_identity(value: str) -> str:
    return "".join(_identity_tokens(value))


def _social_profile_identifier(platform: str, profile_url: str) -> str | None:
    """Return a human-readable social identifier, or None for intentionally opaque IDs."""

    parsed = urllib.parse.urlparse(profile_url)
    parts = [urllib.parse.unquote(part).strip() for part in parsed.path.split("/") if part.strip()]
    if not parts:
        return None
    lowered = [part.casefold() for part in parts]

    if platform == "linkedin" and len(parts) == 2 and lowered[0] == "company":
        return parts[1]
    if platform in {"instagram", "x"} and len(parts) == 1:
        return parts[0].lstrip("@")
    if platform == "tiktok" and len(parts) == 1:
        return parts[0].lstrip("@")
    if platform == "facebook":
        if len(parts) == 1:
            return None if parts[0].isdigit() else parts[0]
        if len(parts) == 2 and lowered[0] == "p":
            return parts[1]
    if platform == "youtube":
        if len(parts) == 1 and parts[0].startswith("@"):
            return parts[0].lstrip("@")
        if len(parts) == 2 and lowered[0] in {"user", "c"}:
            return parts[1]
        # YouTube channel IDs are intentionally opaque. Exact homepage declaration is the
        # only usable zero-network identity evidence for these URLs, so preserve that case.
        if len(parts) == 2 and lowered[0] == "channel":
            return None
    return None


def _matching_handle_assessment(value: dict[str, Any], platform: str, profile_url: str) -> dict[str, Any] | None:
    for item in value.get("social_link_assessments") or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("platform") or "").strip() != platform:
            continue
        if str(item.get("url") or "").strip().rstrip("/") != profile_url.rstrip("/"):
            continue
        return item
    return None


def _direct_declaration_identity_allowed(
    *,
    profile: dict[str, Any],
    source_url: str,
    platform: str,
    profile_url: str,
    handle_assessment: dict[str, Any] | None,
) -> bool:
    """Reject readable vendor/theme handles that conflict with the verified company identity.

    A publishable existing handle assessment remains authoritative. Opaque platform IDs (for
    example a YouTube channel ID) preserve the previously qualified exact-homepage rule. For
    readable handles that failed/no handle assessment, require deterministic overlap with the
    exact verified site's hostname or with meaningful legal-name tokens. This blocks template,
    CMS and agency social links without introducing provider-specific blacklists.
    """

    if handle_assessment is not None and handle_assessment.get("publishable"):
        return True

    identifier = _social_profile_identifier(platform, profile_url)
    if identifier is None:
        return True
    candidate = _compact_identity(identifier)
    if len(candidate) < 4:
        return False

    host = (urllib.parse.urlparse(source_url).hostname or "").casefold().removeprefix("www.")
    site_label = host.split(".", 1)[0]
    site_brand = _compact_identity(site_label)
    if len(site_brand) >= 4 and (candidate in site_brand or site_brand in candidate):
        return True

    name_tokens = [
        token
        for token in _identity_tokens(str(profile.get("name") or ""))
        if token not in LEGAL_SUFFIXES and len(token) >= 4
    ]
    matched = [token for token in name_tokens if token in candidate or candidate in token]
    if len(matched) >= 2:
        return True
    if len(matched) == 1 and len(matched[0]) >= 6:
        return True
    return False


def _primary_page_provenance(
    website: dict[str, Any],
) -> tuple[dict[str, Any], str, str, str] | None:
    """Prove that pages[0] is the immutable exact homepage snapshot."""

    value = website.get("value") or {}
    source_url = str(value.get("final_url") or website.get("source_url") or "").strip()
    content_sha256 = str(value.get("content_sha256") or website.get("content_sha256") or "").strip()
    retrieved_at = str(website.get("retrieved_at") or "").strip()
    pages = [page for page in (value.get("pages") or []) if isinstance(page, dict)]
    if not source_url.startswith(("http://", "https://")) or len(content_sha256) != 64 or not retrieved_at or not pages:
        return None
    primary = pages[0]
    if str(primary.get("url") or "").rstrip("/") != source_url.rstrip("/"):
        return None
    if str(primary.get("content_sha256") or "") != content_sha256:
        return None
    return primary, source_url, content_sha256, retrieved_at


def _direct_homepage_declarations(value: dict[str, Any]) -> list[dict[str, str]]:
    """Return raw HTML social URLs retained from one exact homepage snapshot.

    ``apply_website_identity_gate`` stores the original extracted HTML links in
    ``discovered_social_links`` before applying the older handle-name heuristic. C12 can
    materialize a declaration only when the retained snapshot consists of exactly one
    proven homepage and the declared identity also passes the direct-declaration guard.
    JSON-LD ``sameAs`` intentionally stays on the previously qualified V6e recovery path so
    that existing production semantics remain unchanged.
    """

    found: dict[tuple[str, str], dict[str, str]] = {}
    for item in value.get("discovered_social_links") or []:
        if not isinstance(item, dict):
            continue
        platform = str(item.get("platform") or "").strip()
        profile_url = str(item.get("url") or "").strip()
        if platform and profile_url:
            found[(platform, profile_url)] = {"platform": platform, "url": profile_url}
    return [found[key] for key in sorted(found)]


def _observation(
    *,
    org: str,
    website_identity: dict[str, Any],
    platform: str,
    profile_url: str,
    source_url: str,
    content_sha256: str,
    retrieved_at: str,
    strategy: str,
    handle_assessment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    observation_id = "company-site-handle-" + hashlib.sha256(
        f"{org}|{platform}|{profile_url}|{source_url}|{content_sha256}|{strategy}".encode("utf-8")
    ).hexdigest()[:24]
    website_score = float(website_identity.get("score") or 0.95)
    proof: list[dict[str, Any]] = [
        {
            "type": "website_identity_gate",
            "status": website_identity.get("status"),
            "score": website_identity.get("score"),
            "method": website_identity.get("method"),
        },
        {
            "type": "primary_homepage_provenance",
            "source_url": source_url,
            "content_sha256": content_sha256,
        },
        {
            "type": "company_page_declared_social_link",
            "platform": platform,
            "profile_url": profile_url,
            "source_url": source_url,
        },
    ]
    if handle_assessment is not None:
        proof.append(
            {
                "type": "social_handle_identity_gate",
                "score": handle_assessment.get("identity_score"),
                "method": handle_assessment.get("method"),
                "matched_tokens": list(handle_assessment.get("matched_tokens") or []),
            }
        )

    return {
        "id": observation_id,
        "organisation_number": org,
        "platform": platform,
        "signal_type": "profile_handle",
        "source_url": source_url,
        "retrieved_at": retrieved_at,
        "content_sha256": content_sha256,
        "exact_entity": True,
        "identity_proof": proof,
        "acquisition_mode": "permitted_public_page",
        "rights_status": "approved",
        "source_class": "company_site",
        "evidence_span": f"Exact company homepage declares {platform} profile {profile_url}",
        "profile_url": profile_url,
        "metrics": {
            "identity_score": max(0.0, min(1.0, website_score)),
            "claim_scope": (
                "Social profile URL directly declared by the retained exact-company homepage; "
                "the social-platform page/content was not fetched or independently verified."
            ),
            "network_requests_added": 0,
            "social_handle_name_match_required": handle_assessment is not None,
        },
        "strategy": strategy,
    }


def company_site_social_observations(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Project exact company-page social declarations into material typed claims.

    Direct homepage declarations remain zero-network, but Q8 showed that template/theme
    vendor links can also appear in an exact company's HTML. Human-readable profile handles
    therefore need either the existing publishable handle assessment or deterministic
    alignment with the exact company/site identity. Opaque channel identifiers retain the
    C12 rule because their URL contains no readable entity name to compare.

    The rule remains limited to single-page snapshots with immutable homepage URL/hash
    provenance. Multi-page legacy snapshots can contain merged social candidates without
    per-link provenance and therefore continue to abstain here, leaving the previously
    qualified V6e recovery path unchanged.
    """

    website = ((profile.get("evidence") or {}).get("website") or {})
    value = website.get("value") or {}
    website_identity = value.get("identity_assessment") or {}
    if website.get("status") != "available" or not website_identity.get("publishable"):
        return []

    org = str(profile.get("organisation_number") or "")
    if len(org) != 9 or not org.isdigit():
        return []

    provenance = _primary_page_provenance(website)
    if provenance is None:
        return []
    _primary, source_url, content_sha256, retrieved_at = provenance
    pages = [page for page in (value.get("pages") or []) if isinstance(page, dict)]

    observations: dict[tuple[str, str], dict[str, Any]] = {}

    if len(pages) == 1:
        for item in _direct_homepage_declarations(value):
            platform = str(item.get("platform") or "").strip()
            profile_url = str(item.get("url") or "").strip()
            if not platform or not _safe_profile_url(platform, profile_url):
                continue
            assessment = _matching_handle_assessment(value, platform, profile_url)
            if not _direct_declaration_identity_allowed(
                profile=profile,
                source_url=source_url,
                platform=platform,
                profile_url=profile_url,
                handle_assessment=assessment,
            ):
                continue
            observations[(platform, profile_url)] = _observation(
                org=org,
                website_identity=website_identity,
                platform=platform,
                profile_url=profile_url,
                source_url=source_url,
                content_sha256=content_sha256,
                retrieved_at=retrieved_at,
                strategy="verified_company_homepage_declaration_c12_v1",
                handle_assessment=assessment if assessment and assessment.get("publishable") else None,
            )

    if len(pages) == 1:
        for item in value.get("social_link_assessments") or []:
            if not isinstance(item, dict) or not item.get("publishable"):
                continue
            platform = str(item.get("platform") or "").strip()
            profile_url = str(item.get("url") or "").strip()
            if not platform or not _safe_profile_url(platform, profile_url):
                continue
            observations.setdefault(
                (platform, profile_url),
                _observation(
                    org=org,
                    website_identity=website_identity,
                    platform=platform,
                    profile_url=profile_url,
                    source_url=source_url,
                    content_sha256=content_sha256,
                    retrieved_at=retrieved_at,
                    strategy="verified_company_page_handle_extraction_v1",
                    handle_assessment=item,
                ),
            )

    return sorted(observations.values(), key=lambda row: (row["platform"], row["profile_url"], row["id"]))


def attach_company_site_social_observations(profile: dict[str, Any]) -> dict[str, Any]:
    """Attach C12/H2a plus qualified V6e recovery without adding network requests."""

    existing = [item for item in (profile.get("external_observations") or []) if isinstance(item, dict)]
    h2a = company_site_social_observations(profile)
    by_id = {
        str(item.get("id")): item
        for item in [*existing, *h2a]
        if str(item.get("id") or "").strip()
    }
    profile["external_observations"] = sorted(
        by_id.values(), key=lambda row: (str(row.get("signal_type") or ""), str(row.get("platform") or ""), str(row.get("id") or ""))
    )

    from .zero_network_social_recovery import recover_company_site_social_observations

    recovered = recover_company_site_social_observations(profile)
    by_id.update(
        {
            str(item.get("id")): item
            for item in recovered
            if str(item.get("id") or "").strip()
        }
    )
    profile["external_observations"] = sorted(
        by_id.values(), key=lambda row: (str(row.get("signal_type") or ""), str(row.get("platform") or ""), str(row.get("id") or ""))
    )
    return profile
