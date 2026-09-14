from __future__ import annotations

import re
import unicodedata
from typing import Any
from urllib.parse import urlparse


# Consumer mailbox domains are useful contact evidence but are not evidence that the
# mail domain is controlled by the legal entity. Keep this list intentionally narrow;
# service-provider/partner domains are allowed through and must be rejected or accepted
# by the independently fetched page identity gate rather than by benchmark-specific rules.
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


def _simple_site_label_tokens(domain: str) -> list[str]:
    """Return name-label tokens only for an unambiguous two-label site domain.

    A leading `www.` is ignored. Other subdomains and multi-label suffix ambiguity abstain
    rather than consulting a public-suffix service at runtime.
    """
    normalized = _normalise_domain(domain)
    if not normalized:
        return []
    labels = normalized.split(".")
    if len(labels) == 3 and labels[0] == "www":
        labels = labels[1:]
    if len(labels) != 2:
        return []
    return [token for token in _ascii_tokens(labels[0]) if token not in LEGAL_NAME_TOKENS]


def simple_two_label_domain_name(domain: str) -> str:
    return "".join(_simple_site_label_tokens(domain))


def _domain_from_url(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if "://" not in text:
        return _normalise_domain(text) or ""
    try:
        return _normalise_domain(urlparse(text).hostname or "") or ""
    except ValueError:
        return ""


def _legal_aliases(legal_tokens: list[str]) -> set[str]:
    if not legal_tokens:
        return set()
    aliases = {"".join(legal_tokens), "".join(token[:1] for token in legal_tokens)}
    if len(legal_tokens) >= 2:
        aliases.add(legal_tokens[0][:3] + "".join(token[:1] for token in legal_tokens[1:]))
        aliases.add(legal_tokens[0][:4] + "".join(token[:1] for token in legal_tokens[1:]))
    return {alias for alias in aliases if len(alias) >= 3}


def _domain_identity_strength(profile: dict[str, Any], domain: str) -> str:
    """Classify how strongly a simple domain label corresponds to the legal name."""
    domain_tokens = _simple_site_label_tokens(domain)
    legal_tokens = distinctive_legal_name_tokens(profile.get("name"))
    if not domain_tokens or not legal_tokens:
        return "none"

    domain_compact = "".join(domain_tokens)
    legal_compact = "".join(legal_tokens)
    if domain_compact == legal_compact:
        return "exact"
    if domain_compact in _legal_aliases(legal_tokens):
        return "acronym"

    # A domain can concatenate two or more legal tokens, e.g. stian+olsen.
    for start in range(len(legal_tokens)):
        for stop in range(start + 2, len(legal_tokens) + 1):
            if domain_compact == "".join(legal_tokens[start:stop]):
                return "multi"

    def matches(domain_token: str, legal_token: str) -> bool:
        if domain_token == legal_token:
            return True
        if len(domain_token) >= 4 and domain_token in legal_token:
            return True
        if len(legal_token) >= 4 and legal_token in domain_token:
            return True
        return False

    matched_domain_tokens = [
        token for token in domain_tokens if any(matches(token, legal) for legal in legal_tokens)
    ]
    if len(domain_tokens) >= 2 and len(matched_domain_tokens) == len(domain_tokens):
        return "multi"
    if matched_domain_tokens:
        return "partial"
    return "none"


def corroborate_registry_email_domain_identity(
    profile: dict[str, Any],
    candidate_domain: str,
    assessment: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Conservatively upgrade an independently fetched email-domain candidate review."""
    if not assessment or assessment.get("publishable"):
        return assessment
    if assessment.get("status") != "review" or float(assessment.get("score") or 0) < 0.8:
        return assessment

    if _domain_identity_strength(profile, candidate_domain) != "exact":
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
    """Return independently fetched page text, deliberately excluding URL/hostname text."""
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


def _page_matches_registry_location(profile: dict[str, Any], website: dict[str, Any]) -> bool:
    raw = profile.get("evidence", {}).get("registry", {}).get("value") or {}
    corpus = " ".join(_website_page_identity_parts(website))
    normalized_corpus = " ".join(_ascii_tokens(corpus))
    corpus_tokens = set(normalized_corpus.split())

    postcode = re.sub(r"\D", "", str(raw.get("forretningsadresse.postnummer") or ""))
    if len(postcode) == 4 and postcode in corpus_tokens:
        return True

    address_tokens = [
        token for token in _ascii_tokens(raw.get("forretningsadresse.adresse"))
        if len(token) >= 5 and not token.isdigit()
    ]
    if any(token in corpus_tokens for token in address_tokens):
        return True

    places = {
        " ".join(_ascii_tokens(raw.get("forretningsadresse.poststed"))),
        " ".join(_ascii_tokens(raw.get("forretningsadresse.kommune"))),
        " ".join(_ascii_tokens(profile.get("municipality"))),
    }
    for place in places:
        if len(place.replace(" ", "")) >= 5 and place and place in normalized_corpus:
            return True
    return False


def _downgrade(strengthened: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        **strengthened,
        "status": "review",
        "score": min(float(strengthened.get("score") or 0.85), 0.85),
        "publishable": False,
        "reasons": [*list(strengthened.get("reasons") or []), reason],
        "method": "registry_email_domain_page_identity_guard_v2",
    }


def qualify_registry_email_domain_identity(
    profile: dict[str, Any],
    candidate_domain: str,
    website: dict[str, Any],
    assessment: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Apply H1-specific publication hardening after the general website identity gate.

    An email domain is only a discovery hint. Publication requires page-level legal identity
    plus a company-compatible candidate/final domain. This blocks parent, franchise, manager
    and namesake domains whose pages merely mention the target legal entity.
    """
    strengthened = corroborate_registry_email_domain_identity(profile, candidate_domain, assessment)
    if not strengthened or not strengthened.get("publishable"):
        return strengthened

    if _page_contains_org_number(profile, website):
        return strengthened
    if not _page_contains_full_legal_name(profile, website):
        return _downgrade(
            strengthened,
            "H1 candidate lacks complete legal identity in independently fetched page content",
        )

    final_domain = _domain_from_url((website.get("value") or {}).get("final_url") or website.get("source_url"))
    strengths = {
        _domain_identity_strength(profile, candidate_domain),
        _domain_identity_strength(profile, final_domain),
    }
    if strengths.intersection({"exact", "multi", "acronym"}):
        return strengthened
    if "partial" in strengths and _page_matches_registry_location(profile, website):
        return strengthened

    return _downgrade(
        strengthened,
        "H1 page mentions the legal name but domain ownership is not sufficiently corroborated",
    )


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
