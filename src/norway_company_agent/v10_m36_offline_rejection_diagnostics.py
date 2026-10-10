"""M36 internal, OFFLINE-ONLY search-to-crawl rejection diagnostics.

Accept transient provider-neutral candidate-shaped dictionaries, return ONLY
fixed-name reason COUNTS/boolean cohort flags. Never persist the input candidates
or registry IDs. No HTTP, no credentials, no provider client, no production hook.

An HTTPS root URL is *syntactically* plausible, NOT proven first-party owned.
Every positive still requires independent webpage fetch, exact Norwegian legal
entity evidence and a human audit; none is performed by this module.

M33 retained no provider titles, snippets or URLs, so this does not retrospectively
diagnose the four previously consumed results. Offline synthetic fixtures only.
"""
from __future__ import annotations

from collections import Counter
import re
from typing import Any
from urllib.parse import urlsplit

from .discovery import (
    BLOCKED_DISCOVERY_HOSTS,
    _distinctive_name_tokens,
    _tokens,
    score_search_candidate,
)
from .domain_discovery import _domain_identity_strength
from .v10_m32_offline_nomination import _safe_first_party_homepage, nominate_offline
from .v10_m35_shadow_rejection_analysis import shadow_nominate_for_fixture_only

# Stable anonymous field names; neither search rank nor source text is preserved.
REASON_FIELDS = (
    "invalid_or_missing_url",
    "directory_or_social_host",
    "unsafe_or_non_root_url",
    "safe_https_root",
    "weak_legal_name",
    "full_legal_name_title_missing",
    "deterministic_domain_alias_missing",
    "both_title_and_alias_missing",
    "registry_municipality_snippet_missing",
    "exact_org_search_evidence_missing",
    "legacy_per_result_fetch_nomination",
    "m32_per_result_fetch_nomination",
    "m35_shadow_per_result_fetch_nomination",
)
MAX_TRANSIENT_RESULTS = 10


def _validate_profile(profile: dict[str, Any]) -> None:
    org = str(profile.get("organisation_number") or "")
    if not (len(org) == 9 and org.isascii() and org.isdecimal()):
        raise ValueError("Offline diagnosis requires validated nine-digit organisation number")
    if not str(profile.get("name") or "").strip():
        raise ValueError("Offline diagnosis requires nonempty legal name")
    if not str(profile.get("municipality") or "").strip():
        raise ValueError("Offline diagnosis requires a registry municipality")


def _classify_one(profile: dict[str, Any], candidate: dict[str, Any]) -> dict[str, bool]:
    """Binary flags only. Never include URL, title, snippet, orgnr or rank."""
    flags = {field: False for field in REASON_FIELDS}
    raw_url = candidate.get("url")
    if not isinstance(raw_url, str) or not raw_url.strip():
        flags["invalid_or_missing_url"] = True
        return flags
    try:
        parsed = urlsplit(raw_url)
        host = (parsed.hostname or "").casefold().removeprefix("www.")
    except (ValueError, TypeError):
        flags["invalid_or_missing_url"] = True
        return flags
    if not host or parsed.scheme not in {"https", "http"}:
        flags["invalid_or_missing_url"] = True
        return flags
    if any(host == bad or host.endswith("." + bad) for bad in BLOCKED_DISCOVERY_HOSTS):
        flags["directory_or_social_host"] = True
        return flags
    safe_url = _safe_first_party_homepage(raw_url)
    if not safe_url:
        flags["unsafe_or_non_root_url"] = True
        return flags
    flags["safe_https_root"] = True

    legal_tokens = set(_distinctive_name_tokens(profile))
    title_tokens = set(_tokens(candidate.get("title")))
    if len(legal_tokens) < 2 or len("".join(legal_tokens)) < 9:
        flags["weak_legal_name"] = True
    flags["full_legal_name_title_missing"] = not bool(legal_tokens) or not legal_tokens.issubset(title_tokens)

    safe_host = urlsplit(safe_url).hostname or ""
    strength = _domain_identity_strength(profile, safe_host)
    flags["deterministic_domain_alias_missing"] = strength not in {"exact", "acronym", "multi"}
    flags["both_title_and_alias_missing"] = bool(
        flags["full_legal_name_title_missing"] and flags["deterministic_domain_alias_missing"]
    )

    municipality = set(_tokens(profile.get("municipality")))
    flags["registry_municipality_snippet_missing"] = not municipality.issubset(
        set(_tokens(candidate.get("snippet")))
    )
    org = str(profile.get("organisation_number"))
    evidence = str(candidate.get("title") or "") + " " + str(candidate.get("snippet") or "")
    flags["exact_org_search_evidence_missing"] = org not in re.sub(r"\D", "", evidence)

    # These flags describe *fetch-nomination rules*, NOT company identity truth.
    flags["legacy_per_result_fetch_nomination"] = bool(
        score_search_candidate(profile, candidate).get("publishable_candidate")
    )
    flags["m32_per_result_fetch_nomination"] = bool(
        nominate_offline(profile, [candidate]).get("selected")
    )
    flags["m35_shadow_per_result_fetch_nomination"] = bool(
        shadow_nominate_for_fixture_only(profile, [candidate]).get("selected")
    )
    return flags


def summarize_transient_candidate_rejections(
    profile: dict[str, Any], results: list[dict[str, Any]]
) -> dict[str, Any]:
    """No source strings in output; counts overlap and must not be summed.

    This is a private Signalpost *workflow diagnostic*, not a provider benchmark.
    All user/source materials remain transient, no queries are executed.
    """
    _validate_profile(profile)
    if not isinstance(results, list):
        raise ValueError("Expected transient candidate list")
    counts: Counter[str] = Counter()
    inspected = 0
    for item in results[:MAX_TRANSIENT_RESULTS]:
        inspected += 1
        if not isinstance(item, dict):
            counts["invalid_or_missing_url"] += 1
            continue
        flags = _classify_one(profile, item)
        counts.update(k for k, present in flags.items() if present)
    data = {
        "schema": "m36_internal_rejection_counts_offline_v1",
        "source": "SYNTHETIC_OR_EXPLICITLY_TRANSIENT_ONLY",
        "inspected": inspected,
        "max_candidates": MAX_TRANSIENT_RESULTS,
        "reason_counts_overlap": True,
        "reasons": {field: counts[field] for field in REASON_FIELDS},
        "published_claims": 0,
        "provider_http_requests": 0,
        "company_http_requests": 0,
        "real_site_lift_verified": False,
        "production_modified": False,
    }
    assert all(0 <= value <= inspected for value in data["reasons"].values())
    assert data["reasons"]["safe_https_root"] + sum(
        data["reasons"][field] for field in (
            "invalid_or_missing_url", "directory_or_social_host", "unsafe_or_non_root_url"
        )
    ) == inspected
    return data
