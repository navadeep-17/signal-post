from __future__ import annotations

import re
import unicodedata
from typing import Any


# Consumer mailbox domains are useful contact evidence but are not evidence that the
# mail domain is controlled by the legal entity. Keep this list intentionally narrow;
# service-provider/partner domains are allowed through and must be rejected or accepted
# by the independent fetched-page identity gate rather than by benchmark-specific rules.
GENERIC_EMAIL_DOMAINS = {
    "aol.com",
    "fastmail.com",
    "gmail.com",
    "googlemail.com",
    "hey.com",
    "hotmail.com",
    "hotmail.no",
    "icloud.com",
    "live.com",
    "live.no",
    "mail.com",
    "me.com",
    "msn.com",
    "online.no",
    "outlook.com",
    "proton.me",
    "protonmail.com",
    "yahoo.com",
    "yahoo.no",
}

LEGAL_NAME_TOKENS = {
    "as", "asa", "ans", "da", "enk", "iks", "sa", "sam", "sti", "stiftelsen",
    "nuf", "ab", "limited", "ltd", "inc", "plc",
}


def _ascii_tokens(value: Any) -> list[str]:
    text = str(value or "").translate(str.maketrans({"ø": "o", "Ø": "O", "å": "a", "Å": "A", "æ": "ae", "Æ": "AE"}))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()
    return [token for token in re.findall(r"[a-z0-9]+", text) if token]


def distinctive_legal_name_tokens(name: Any) -> list[str]:
    return [token for token in _ascii_tokens(name) if token not in LEGAL_NAME_TOKENS]


def distinctive_legal_name_compact(name: Any) -> str:
    return "".join(distinctive_legal_name_tokens(name))


def simple_two_label_domain_name(domain: str) -> str:
    """Return the normalized name label only for unambiguous two-label domains.

    Corroboration deliberately abstains for subdomains and multi-label suffix cases rather
    than consulting a public-suffix service/list at runtime. That keeps this path fully
    deterministic and prevents hidden outbound requests outside the request ledger.
    """
    normalized = _normalise_domain(domain)
    if not normalized:
        return ""
    labels = normalized.split(".")
    if len(labels) != 2:
        return ""
    return "".join(_ascii_tokens(labels[0]))


def corroborate_registry_email_domain_identity(
    profile: dict[str, Any],
    candidate_domain: str,
    assessment: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Conservatively upgrade a fetched email-domain candidate from review to exact.

    The candidate must already be in `review`, meaning independently fetched page content
    contains substantial legal-name evidence. The domain must also be a simple two-label
    domain whose name label exactly equals the normalized distinctive legal name. Manager,
    subdomain and ambiguous public-suffix cases abstain rather than guess.
    """
    if not assessment or assessment.get("publishable"):
        return assessment
    if assessment.get("status") != "review" or float(assessment.get("score") or 0) < 0.8:
        return assessment

    legal_compact = distinctive_legal_name_compact(profile.get("name"))
    domain_compact = simple_two_label_domain_name(candidate_domain)
    if not legal_compact or legal_compact != domain_compact:
        return assessment

    return {
        **assessment,
        "status": "exact",
        "score": 0.97,
        "publishable": True,
        "reasons": [
            *list(assessment.get("reasons") or []),
            "official registry email domain exactly matches the normalized distinctive legal name",
        ],
        "method": "registry_email_domain_exact_name_plus_fetched_page_v1",
    }


def _structured_identity_strings(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"name", "legalName", "alternateName"} and isinstance(child, str):
                found.append(child)
            else:
                found.extend(_structured_identity_strings(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_structured_identity_strings(child))
    return found


def _website_page_identity_parts(website: dict[str, Any]) -> list[str]:
    """Return page-derived identity text, deliberately excluding hostname/URL strings."""
    value = website.get("value") or {}
    parts: list[Any] = [
        value.get("title"),
        value.get("description"),
        value.get("identity_text_excerpt"),
        value.get("main_text_excerpt"),
        *_structured_identity_strings(value.get("structured_organisations") or []),
    ]
    rendered = value.get("js_fallback") or {}
    parts.extend([rendered.get("title"), rendered.get("main_text_excerpt")])
    for page in value.get("pages") or []:
        if not isinstance(page, dict):
            continue
        parts.extend([page.get("title"), page.get("identity_text_excerpt"), page.get("main_text_excerpt")])
    return [str(part) for part in parts if str(part or "").strip()]


def _page_contains_full_legal_name(profile: dict[str, Any], website: dict[str, Any]) -> bool:
    core = set(distinctive_legal_name_tokens(profile.get("name")))
    if not core:
        return False
    return any(core.issubset(set(_ascii_tokens(part))) for part in _website_page_identity_parts(website))


def _page_contains_org_number(profile: dict[str, Any], website: dict[str, Any]) -> bool:
    org = re.sub(r"\D", "", str(profile.get("organisation_number") or ""))
    if len(org) != 9:
        return False
    return any(org in re.sub(r"\D", "", part) for part in _website_page_identity_parts(website))


def qualify_registry_email_domain_identity(
    profile: dict[str, Any],
    candidate_domain: str,
    website: dict[str, Any],
    assessment: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Apply H1-specific publication hardening after the general website identity gate.

    Registry email domains are only discovery hints. The general gate also considers the
    hostname as identity evidence, which is appropriate for a registry-listed URL but too
    permissive for a derived candidate: a service-provider subdomain can contain a client
    name in the hostname. H1 therefore requires independently fetched *page content* to
    contain either the exact organisation number or the complete distinctive legal name.

    Single-token legal names are additionally required to own a simple two-label domain
    whose name label exactly matches that token. This avoids publishing client subdomains
    or manager domains on the strength of a short namesake alone.
    """
    strengthened = corroborate_registry_email_domain_identity(profile, candidate_domain, assessment)
    if not strengthened or not strengthened.get("publishable"):
        return strengthened

    if _page_contains_org_number(profile, website):
        return strengthened

    core = distinctive_legal_name_tokens(profile.get("name"))
    if not _page_contains_full_legal_name(profile, website):
        return {
            **strengthened,
            "status": "review",
            "score": min(float(strengthened.get("score") or 0.85), 0.85),
            "publishable": False,
            "reasons": [
                *list(strengthened.get("reasons") or []),
                "H1 candidate lacks complete legal identity in independently fetched page content",
            ],
            "method": "registry_email_domain_page_identity_guard_v1",
        }

    if len(core) == 1 and simple_two_label_domain_name(candidate_domain) != distinctive_legal_name_compact(profile.get("name")):
        return {
            **strengthened,
            "status": "review",
            "score": min(float(strengthened.get("score") or 0.85), 0.85),
            "publishable": False,
            "reasons": [
                *list(strengthened.get("reasons") or []),
                "single-token legal name requires an exact simple company domain in H1",
            ],
            "method": "registry_email_domain_page_identity_guard_v1",
        }

    return strengthened


def _normalise_domain(value: str) -> str | None:
    domain = str(value or "").strip().strip(". ").casefold()
    if not domain or len(domain) > 253 or "." not in domain:
        return None
    try:
        domain = domain.encode("idna").decode("ascii")
    except UnicodeError:
        return None
    labels = domain.split(".")
    if any(not label or len(label) > 63 for label in labels):
        return None
    label_re = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
    if not all(label_re.fullmatch(label) for label in labels):
        return None
    if len(labels[-1]) < 2 or not labels[-1].isalpha():
        return None
    return domain


def registry_email_addresses(profile: dict[str, Any]) -> list[str]:
    raw = profile.get("evidence", {}).get("registry", {}).get("value") or {}
    value = str(raw.get("epostadresse") or "").strip()
    if not value:
        return []
    addresses = []
    for part in re.split(r"[\s,;]+", value):
        candidate = part.strip("<>[](){}\"'")
        if "@" not in candidate:
            continue
        local, _, domain = candidate.rpartition("@")
        normalised = _normalise_domain(domain)
        if local and normalised:
            addresses.append(f"{local}@{normalised}")
    return list(dict.fromkeys(addresses))


def registry_email_domain_candidates(profile: dict[str, Any]) -> dict[str, Any]:
    if str(profile.get("website") or "").strip():
        return {
            "eligible": False,
            "reason": "registry_website_present",
            "addresses": [],
            "candidates": [],
        }

    addresses = registry_email_addresses(profile)
    if not addresses:
        return {
            "eligible": False,
            "reason": "registry_email_missing_or_invalid",
            "addresses": [],
            "candidates": [],
        }

    candidates = []
    generic = []
    for address in addresses:
        domain = _normalise_domain(address.rsplit("@", 1)[1])
        if not domain:
            continue
        if domain in GENERIC_EMAIL_DOMAINS:
            generic.append(domain)
            continue
        candidates.append(
            {
                "domain": domain,
                "url": domain,
                "source": "brreg_public_registry_email_domain",
            }
        )

    candidates = list({item["domain"]: item for item in candidates}.values())
    if not candidates:
        return {
            "eligible": False,
            "reason": "only_generic_email_domains",
            "addresses": addresses,
            "generic_domains": sorted(set(generic)),
            "candidates": [],
        }
    return {
        "eligible": True,
        "reason": "candidate_domains_from_registry_email",
        "addresses": addresses,
        "generic_domains": sorted(set(generic)),
        "candidates": candidates,
    }
