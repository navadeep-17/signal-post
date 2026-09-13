from __future__ import annotations

import re
import unicodedata
from typing import Any

import tldextract


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


def distinctive_legal_name_compact(name: Any) -> str:
    return "".join(token for token in _ascii_tokens(name) if token not in LEGAL_NAME_TOKENS)


def registrable_domain_label(domain: str) -> str:
    extracted = tldextract.extract(str(domain or "").casefold())
    return "".join(_ascii_tokens(extracted.domain))


def corroborate_registry_email_domain_identity(
    profile: dict[str, Any],
    candidate_domain: str,
    assessment: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Conservatively upgrade a fetched email-domain candidate from review to exact.

    This is intentionally narrower than the general website identity gate. The candidate
    must already be in `review`, which means independently fetched page content contains
    substantial legal-name evidence. In addition, the registrable domain label itself
    must exactly equal the normalized distinctive legal name. This excludes manager/
    service-provider domains such as `gobb.no` or `notodden.bbl.no` even if those sites
    contain pages mentioning the customer legal entity.
    """
    if not assessment or assessment.get("publishable"):
        return assessment
    if assessment.get("status") != "review" or float(assessment.get("score") or 0) < 0.8:
        return assessment

    legal_compact = distinctive_legal_name_compact(profile.get("name"))
    domain_compact = registrable_domain_label(candidate_domain)
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
    # The registry field is normally one address, but handle common separators without
    # persisting or inferring anything beyond the public registry value.
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
                # Deliberately omit a scheme so fetch_website can try HTTPS and its
                # existing HTTP fallback without adding separate discovery behavior.
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
