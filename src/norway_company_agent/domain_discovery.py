from __future__ import annotations

import re
from typing import Any


# Consumer mailboxes and ISP-hosted mailbox domains are useful contact evidence but are
# not evidence that the mail domain is controlled by the legal entity. Keep this list
# intentionally generic; company/service-provider domains are still allowed through and
# must be rejected or accepted by the independent fetched-page identity gate.
GENERIC_EMAIL_DOMAINS = {
    "aol.com",
    "broadpark.no",
    "fastmail.com",
    "gmail.com",
    "googlemail.com",
    "hey.com",
    "hotmail.com",
    "hotmail.no",
    "icloud.com",
    "live.com",
    "live.no",
    "lyse.net",
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

_EMAIL_DOMAIN_RE = re.compile(r"@([A-Za-z0-9.-]+\.[A-Za-z]{2,63})(?=$|[\s,;>])")


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
