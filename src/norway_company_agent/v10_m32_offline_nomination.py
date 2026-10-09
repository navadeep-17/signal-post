"""M32 experimental, purely offline *crawl nomination* challenger.

IMPORTANT: a nominated URL is NOT an exact-company fact. This code is not
wired into the live M26 runner, V8, the challenge evaluator, or any network
client. It uses synthetic/previously retained fixtures only. A later pilot
would require separate review, a strict request-slot replacement proof, and
independently fetched legal-entity evidence. Provider search material must
remain transient and private.
"""
from __future__ import annotations

from copy import deepcopy
import ipaddress
import re
from typing import Any
from urllib.parse import urlsplit

from .discovery import (
    BLOCKED_DISCOVERY_HOSTS,
    _distinctive_name_tokens,
    _tokens,
    choose_search_candidate,
    qualify_search_discovered_website,
)
from .domain_discovery import _domain_identity_strength, _page_contains_org_number
from .final_site_discovery import _has_conflicting_explicit_org_number
from .identity import apply_website_identity_gate
from .tavily_offline_candidate import _matching_independent_page, normalize_tavily_results
from .website import _registered_domain, normalize_homepage
from .zero_cost_registry_guard import registry_risk_reasons

# Hard deny before nominee scores; two-label domains keep suffix ambiguity
# from laundering external platform/subdomain results as a company's homepage.
BAD_TLDS = frozenset({"local", "localhost", "internal", "invalid", "test"})
ALLOWED_DOMAIN_STRENGTH = frozenset({"exact", "acronym", "multi"})


def _safe_first_party_homepage(raw: Any) -> str | None:
    """Only a plausible public root hostname is worth a first-party GET.

    This is syntax-only; does not resolve DNS, follow redirects or prove
    ownership. Final HTTP layer must enforce SSRF and robots restrictions.
    """
    if not isinstance(raw, str) or not raw.strip():
        return None
    raw = raw.strip()
    try:
        parsed = urlsplit(raw)
        host = (parsed.hostname or "").casefold().rstrip(".")
        port = parsed.port  # forces malformed port validation
    except ValueError:
        return None
    if (
        parsed.scheme != "https"
        or not host
        or parsed.username is not None or parsed.password is not None
        or port is not None
        or parsed.query or parsed.fragment
        or parsed.path not in ("", "/")
        or not host.isascii()
    ):
        return None
    if host in ("localhost",) or host.endswith(".localhost"):
        return None
    try:
        ipaddress.ip_address(host)
        return None
    except ValueError:
        pass
    labels = host.split(".")
    if labels[:1] == ["www"]:
        labels = labels[1:]
    if len(labels) != 2 or labels[-1] in BAD_TLDS:
        return None
    if any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", l)
           for l in labels):
        return None
    if len(labels[-1]) < 2 or not labels[-1].isalpha():
        return None
    if any(host == bad or host.endswith("." + bad) for bad in BLOCKED_DISCOVERY_HOSTS):
        return None
    return normalize_homepage(raw)


def nominate_offline(
    profile: dict[str, Any],
    parsed_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Try the ORIGINAL gate first; only if it abstains test a safer relaxed gate.

    The new gate accepts a title matching at least two distinctive legal-name
    tokens, coupled with an independently plausible name-aligned *root*
    domain or acronym domain. No org-number/snippet evidence is required
    merely to *nominate a fetch*. Never consider snippets as proof.
    """
    if str(profile.get("website") or "").strip():
        return {"status": "existing_registry_site_seed", "selected": None,
                "path": "none", "published_claims": 0}
    selected = choose_search_candidate(profile, parsed_results).get("selected")
    if selected:
        return {"status": "baseline_nomination", "selected": selected,
                "path": "baseline_unchanged", "published_claims": 0}

    name_tokens = _distinctive_name_tokens(profile)
    if len(set(name_tokens)) < 2 or len("".join(name_tokens)) < 9:
        return {"status": "weak_legal_name", "selected": None,
                "path": "none", "published_claims": 0}

    contenders: list[dict[str, Any]] = []
    for item in parsed_results[:10]:
        url = _safe_first_party_homepage(item.get("url"))
        if not url:
            continue
        title_tokens = set(_tokens(item.get("title") or ""))
        if not set(name_tokens).issubset(title_tokens):
            continue
        hostname = (urlsplit(url).hostname or "").casefold()
        strength = _domain_identity_strength(profile, hostname)
        if strength not in ALLOWED_DOMAIN_STRENGTH:
            continue
        rank = item.get("rank")
        if not isinstance(rank, int) or rank < 1:
            rank = 1000
        contenders.append({"url": url, "rank": rank, "strength": strength})
    if not contenders:
        return {"status": "challenger_abstained", "selected": None,
                "path": "none", "published_claims": 0}
    weight = {"exact": 0, "acronym": 1, "multi": 2}
    contenders.sort(key=lambda x: (weight[x["strength"]], x["rank"], x["url"]))
    return {
        "status": "challenger_nomination_for_independent_fetch_only",
        "selected": {"url": contenders[0]["url"]},
        "path": "offline_strict_root_domain_with_full_title",
        "published_claims": 0,
    }


def screen_independent_fixture(
    profile: dict[str, Any],
    *,
    payload: dict[str, Any],
    independently_fetched: dict[str, Any] | None,
) -> dict[str, Any]:
    """Reuse all M23 page-identity vetoes and M26 exact-org requirement.

    No HTTP, no persisted search strings, no company claims. This is NOT a
    production replacement for M26's verifier.
    """
    query = "offline_synthetic_query_not_a_real_provider_search"
    parsed = normalize_tavily_results(payload, query=query)
    selection = nominate_offline(profile, parsed)
    chosen = selection["selected"]
    report = {
        "status": selection["status"],
        "path": selection["path"],
        "candidate_nominated": bool(chosen),
        "identity_eligible_for_manual_review": False,
        "published_claims": 0,
        "provider_requests": 0,
        "website_requests": 0,
    }
    if not chosen or independently_fetched is None:
        return report
    candidate = str(chosen["url"])
    if not _matching_independent_page(candidate, independently_fetched):
        report["status"] = "independent_page_provenance_mismatch"
        return report
    page = deepcopy(independently_fetched)
    gated = apply_website_identity_gate(profile, page)
    website = gated["website"]
    assessment = qualify_search_discovered_website(
        profile, website, gated.get("assessment")
    )
    if _has_conflicting_explicit_org_number(profile, website):
        report["status"] = "wrong_organisation_number"
        return report
    if registry_risk_reasons(profile, website):
        report["status"] = "registry_collision"
        return report
    if (
        website.get("status") != "available"
        or not assessment or not assessment.get("publishable")
    ):
        report["status"] = "identity_not_proven"
        return report
    final_url = normalize_homepage((website.get("value") or {}).get("final_url"))
    if (
        not final_url
        or not _registered_domain(candidate)
        or _registered_domain(candidate) != _registered_domain(final_url)
    ):
        report["status"] = "untrusted_domain_redirect"
        return report
    if not _page_contains_org_number(profile, website):
        report["status"] = "exact_org_number_required_for_manual_review"
        return report
    report["status"] = "eligible_for_manual_audit_only"
    report["identity_eligible_for_manual_review"] = True
    return report
