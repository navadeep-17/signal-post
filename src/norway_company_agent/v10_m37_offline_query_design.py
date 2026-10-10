"""M37 OFFLINE ONLY: pre-register single-search query hypotheses.

This file is a string compiler/shape audit, NOT a search client, query
dispatcher, score evaluator, provider API integration, or recommendation to
spend credits. It cannot infer real provider recall. The M33/M34 report has
no retained result titles/URLs, so retrospective query comparison is impossible.

Only one query variant may be compiled per hypothetical company attempt.
No live transport consumes this file; original M26/V8 query remains unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from .discovery import build_company_search_query, _distinctive_name_tokens

QUERY_VARIANTS = (
    "v8_unchanged",
    "legal_name_municipality_homepage",
    "distinctive_name_municipality_website",
)
MAX_QUERY_CHARS = 180
MAX_HYPOTHETICAL_BASIC_SEARCHES_PER_COMPANY = 1
SITE_REQUEST_SLOT_REPLACEMENT_REQUIRED = True


@dataclass(frozen=True)
class OfflineQueryHypothesis:
    variant: str
    transient_query: str
    max_search_requests_if_separately_authorized: int = 1
    production_enabled: bool = False
    proven_coverage_lift: bool = False
    def __post_init__(self) -> None:
        if self.variant not in QUERY_VARIANTS:
            raise ValueError("Unregistered query variant")
        if not self.transient_query or len(self.transient_query) > MAX_QUERY_CHARS:
            raise ValueError("Unsafe or overlong search query")
        if self.max_search_requests_if_separately_authorized != 1:
            raise ValueError("No multi-query or fallback search permitted")
        if self.production_enabled or self.proven_coverage_lift:
            raise ValueError("Offline hypothesis cannot claim deployment or score lift")


def _legal_name_and_registry(profile: dict[str, Any]) -> tuple[str, str, str]:
    if not isinstance(profile, dict):
        raise ValueError("Expected registry company profile")
    raw_name = str(profile.get("name") or "")
    raw_municipality = str(profile.get("municipality") or "")
    # Reject controls *before* whitespace normalization (which would erase
    # newline injection attempts and conceal the original field).
    for raw in (raw_name, raw_municipality):
        if any(ord(ch) < 32 for ch in raw):
            raise ValueError("Control characters are forbidden in query inputs")
    name = " ".join(raw_name.split())
    municipality = " ".join(raw_municipality.split())
    org = str(profile.get("organisation_number") or "")
    if not (len(org) == 9 and org.isascii() and org.isdecimal()):
        raise ValueError("Require exact nine-digit Norwegian organisation number")
    if not name or not municipality:
        raise ValueError("Require legal name and municipality")
    # Prevent uncontrolled multiline/quoted expansion in single-query templates.
    # Legal company names can contain punctuation; this is *experimental only*.
    for value in (name, municipality):
        if any(ord(ch) < 32 or ch in '"\\<>{}' for ch in value):
            raise ValueError("Unsafe control, quoting or delimiter in source fields")
        if len(value) > 120:
            raise ValueError("Source field too long for bounded query")
    return name, org, municipality


def build_offline_one_query(
    profile: dict[str, Any], *, variant: str
) -> OfflineQueryHypothesis:
    """Compile exactly ONE query. Caller cannot provide a list or fallback."""
    if not isinstance(variant, str) or variant not in QUERY_VARIANTS:
        raise ValueError("Select exactly one pre-registered variant")
    name, org, municipality = _legal_name_and_registry(profile)

    if variant == "v8_unchanged":
        query = build_company_search_query(profile)
    elif variant == "legal_name_municipality_homepage":
        # Hypothesis: omitting orgnr may reduce directory-only emphasis while
        # retaining the full entity name plus local disambiguation.
        query = f'"{name}" {municipality} hjemmeside'
    else:
        # Hypothesis: a shorter distinctive-name phrase may surface a
        # brand-first homepage missing the corporate legal suffix.
        distinctive = _distinctive_name_tokens(profile)
        if len(distinctive) < 2 or len("".join(distinctive)) < 9:
            raise ValueError("Distinctive-name query unsafe for ambiguous legal name")
        query = f'"{" ".join(distinctive)}" {municipality} nettside'

    if len(query) > MAX_QUERY_CHARS or "\n" in query:
        raise ValueError("Overlong or multiline query")
    return OfflineQueryHypothesis(variant=variant, transient_query=query)


def compare_query_shapes_offline(profile: dict[str, Any]) -> dict[str, Any]:
    """Anonymous design comparison only; NOT observed search performance.

    Returns static query-shape metadata, NOT the legal name, orgnr, location
    or actual generated query. Does not rank or recommend a provider.
    """
    outputs: list[dict[str, Any]] = []
    for variant in QUERY_VARIANTS:
        try:
            q = build_offline_one_query(profile, variant=variant)
        except ValueError:
            outputs.append({
                "variant": variant,
                "eligible_for_hypothetical_single_search": False,
                "reason": "insufficient_safe_distinctive_name_or_input",
            })
            continue
        outputs.append({
            "variant": q.variant,
            "eligible_for_hypothetical_single_search": True,
            "includes_org_number": variant == "v8_unchanged",
            "uses_full_legal_name": variant != "distinctive_name_municipality_website",
            "includes_municipality": True,
            "explicit_homepage_keyword": variant != "v8_unchanged",
            "max_search_requests": 1,
            "observed_provider_result_count": None,
            "verified_new_websites": None,
        })
    return {
        "schema": "m37_offline_single_query_design_comparison_v1",
        "query_variants": outputs,
        "method": "deterministic_structure_only_no_search",
        "per_company_hypothetical_basic_search_cap": 1,
        "must_replace_existing_site_slot_if_integrated": True,
        "third_party_requests_executed": 0,
        "website_requests_executed": 0,
        "measured_query_recall": False,
        "official_score_measured": False,
        "production_modified": False,
    }
