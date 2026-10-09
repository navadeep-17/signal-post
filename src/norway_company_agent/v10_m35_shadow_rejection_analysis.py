"""M35: OFFLINE-ONLY shadow diagnosis for previously rejected homepage-shaped URLs.

Source-derived: M33 aggregate 2/4 had HTTPS root-looking URLs, 0 nominations.
Their original provider titles/snippets/URLs were NOT retained. This module
does not reconstruct those records or claim any observed lift. It classifies
synthetic results, tries unchanged M32 first and proposes a narrower alternate
*fetch nomination* for controlled fixture study only.

NO HTTP, provider credential, persistence, deployment or production imports
from this module. Fetch nomination NEVER establishes a legal-entity website.
"""
from __future__ import annotations

from collections import Counter
import re
from typing import Any
from urllib.parse import urlsplit

from .discovery import _distinctive_name_tokens, _tokens
from .domain_discovery import _domain_identity_strength
from .v10_m32_offline_nomination import _safe_first_party_homepage, nominate_offline

# No third-party result can be accepted as proof of exact entity identity.
# A title using a DIFFERENT registered business name is a strong collision cue.
TITLE_LEGAL_MARKERS = frozenset({"as", "asa", "ab", "ans", "nuf", "ltd", "limited", "inc"})
# These labels are only INTERNAL classification flags; do not log source text.
ALLOWED_SHADOW_ROOT_STRENGTHS = frozenset({"exact", "multi"})


def _potential_explicit_nine_digit_numbers(text: str) -> set[str]:
    """Bounded conservatism: refuse result evidence containing a wrong orgnr.

    Matches compact 9 digits and spaced 3+3+3 digits. This is a veto only,
    NOT an acceptance signal, and may reject benign telephone numbers.
    """
    if len(text) > 3000:
        text = text[:3000]
    raw = re.findall(r"(?<!\d)\d{9}(?!\d)|(?<!\d)\d{3}[ .]\d{3}[ .]\d{3}(?!\d)", text)
    return {re.sub(r"\D", "", item) for item in raw}


def diagnose_url_nomination_reasons(
    profile: dict[str, Any], results: list[dict[str, Any]]
) -> dict[str, Any]:
    """Return ONLY per-cohort safe reason-code counts, NEVER URLs or text.

    This is not a reconstruction of the M33 report; input is a synthetic
    controlled test collection. The counts overlap by reason.
    """
    title_mismatch = 0
    alias_mismatch = 0
    safe_root_count = 0
    blocked_root_count = 0
    domain_strength = Counter()
    name_tokens = set(_distinctive_name_tokens(profile))
    for candidate in results[:10]:
        safe_url = _safe_first_party_homepage(candidate.get("url"))
        if not safe_url:
            blocked_root_count += 1
            continue
        safe_root_count += 1
        title_tokens = set(_tokens(candidate.get("title")))
        if not name_tokens or not name_tokens <= title_tokens:
            title_mismatch += 1
        strength = _domain_identity_strength(profile, urlsplit(safe_url).hostname or "")
        if strength not in {"exact", "acronym", "multi"}:
            alias_mismatch += 1
        domain_strength[strength] += 1
    return {
        "safe_root_count": safe_root_count,
        "blocked_root_count": blocked_root_count,
        "full_title_mismatch_count": title_mismatch,
        "allowed_domain_alias_mismatch_count": alias_mismatch,
        "domain_strength_counts": dict(sorted(domain_strength.items())),
        "published_claims": 0,
        "provider_requests": 0,
        "independent_company_http_requests": 0,
    }


def shadow_nominate_for_fixture_only(
    profile: dict[str, Any], results: list[dict[str, Any]]
) -> dict[str, Any]:
    """Baseline/M32 first; then *title-shortened* company roots for testing.

    The shadow fallback is intentionally NOT wired to production or live M33.
    It demands:
      - at least three distinctive legal-name tokens;
      - two or more shared distinctive tokens in the title, including the first;
      - only a two-label HTTPS root, no blocked directory/social/IP domain;
      - an exact or deterministic multi-token company-name root;
      - corroborating registry municipality in the transient snippet;
      - no conflicting explicit nine-digit number in provider metadata;
      - no other legal-name suffix in an incomplete company title.
    All these are nomination hints; actual site ownership remains unknown.
    """
    existing = nominate_offline(profile, results)
    if existing["selected"]:
        return {
            "mode": "existing_m32_unchanged",
            "selected": existing["selected"],
            "published_claims": 0,
            "provider_requests": 0,
            "company_http_requests": 0,
        }
    tokens = _distinctive_name_tokens(profile)
    if len(set(tokens)) < 3 or len("".join(tokens)) < 12:
        return {
            "mode": "shadow_abstained",
            "selected": None,
            "published_claims": 0,
            "provider_requests": 0,
            "company_http_requests": 0,
        }
    municipality = set(_tokens(profile.get("municipality")))
    if not municipality:
        return {
            "mode": "shadow_abstained",
            "selected": None,
            "published_claims": 0,
            "provider_requests": 0,
            "company_http_requests": 0,
        }
    exact_org = re.sub(r"\D", "", str(profile.get("organisation_number") or ""))
    if len(exact_org) != 9:
        return {
            "mode": "shadow_abstained",
            "selected": None,
            "published_claims": 0,
            "provider_requests": 0,
            "company_http_requests": 0,
        }
    eligible: list[tuple[int, int, str]] = []
    for item in results[:10]:
        safe_url = _safe_first_party_homepage(item.get("url"))
        if not safe_url:
            continue
        host = urlsplit(safe_url).hostname or ""
        strength = _domain_identity_strength(profile, host)
        if strength not in ALLOWED_SHADOW_ROOT_STRENGTHS:
            continue
        title_tokens = set(_tokens(item.get("title")))
        overlap = title_tokens & set(tokens)
        if tokens[0] not in title_tokens or len(overlap) < 2 or len(overlap) == len(set(tokens)):
            continue  # existing M32 must handle complete titles; no score inflation
        # A different incorporated legal-name title is a hard collision signal.
        if title_tokens & TITLE_LEGAL_MARKERS:
            continue
        # Strong municipality corroboration helps avoid content farm headlines.
        snippet_tokens = set(_tokens(item.get("snippet")))
        if not municipality.issubset(snippet_tokens):
            continue
        explicit_numbers = _potential_explicit_nine_digit_numbers(
            str(item.get("title") or "") + " " + str(item.get("snippet") or "")
        )
        if any(number != exact_org for number in explicit_numbers):
            continue
        rank = item.get("rank")
        if not isinstance(rank, int) or rank < 1:
            rank = 10_000
        eligible.append((0 if strength == "exact" else 1, rank, safe_url))
    if not eligible:
        return {
            "mode": "shadow_abstained",
            "selected": None,
            "published_claims": 0,
            "provider_requests": 0,
            "company_http_requests": 0,
        }
    eligible.sort()
    # These URL values are synthetic fixture materials only; caller must never
    # serialize original provider candidate lists or publish company identity.
    return {
        "mode": "shadow_title_shortened_nomination_only",
        "selected": {"url": eligible[0][2]},
        "published_claims": 0,
        "provider_requests": 0,
        "company_http_requests": 0,
    }
