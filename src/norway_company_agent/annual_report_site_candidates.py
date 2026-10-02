from __future__ import annotations

import re
import urllib.parse
from typing import Any

from .domain_discovery import (
    GENERIC_EMAIL_DOMAINS,
    _domain_identity_strength,
    _normalise_domain,
    distinctive_legal_name_tokens,
)

URL_RE = re.compile(r"(?i)\b(?:https?://|www\.)[a-z0-9æøå][a-z0-9æøå._~:/?#\[\]@!$&'()*+,;=%-]{2,250}")
EMAIL_RE = re.compile(r"(?i)\b[a-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}@([a-z0-9æøå.-]+\.[a-zæøå]{2,24})\b")
DOMAIN_RE = re.compile(r"(?i)(?<![@\w.-])([a-z0-9æøå](?:[a-z0-9æøå-]{0,62}\.)+(?:no|com|net|org|io|co|eu))(?![\w.-])")

POSITIVE_WEB_LABELS = re.compile(r"(?i)\b(?:hjemmeside|nettside|website|webside|web\s*[:.]|www\s*[:.])\b")
POSITIVE_CONTACT_LABELS = re.compile(r"(?i)\b(?:e-?post|email|mail|kontakt|contact)\b")
NEGATIVE_PROVIDER_CONTEXT = re.compile(
    r"(?i)\b(?:revisor|revisjon|auditor|audit|regnskapsforer|regnskapsfører|accounting|"
    r"advokat|lawyer|legal adviser|bank|forsikring|insurance|megler|broker|"
    r"systemleverandor|systemleverandør|leverandor|leverandør)\b"
)
NOISY_HOSTS = {
    "brreg.no", "altinn.no", "skatteetaten.no", "nav.no", "arbeidsplassen.nav.no",
    "regnskapnorge.no", "finanstilsynet.no", "dnb.no", "sparebank1.no", "nordea.no",
    "pwc.no", "ey.com", "kpmg.no", "deloitte.no", "bdo.no",
    "microsoft.com", "adobe.com", "google.com",
}


def _ascii_fold(value: Any) -> str:
    return str(value or "").translate(str.maketrans({"ø": "o", "Ø": "O", "å": "a", "Å": "A", "æ": "ae", "Æ": "AE"})).casefold()


def _context(text: str, start: int, end: int, radius: int = 260) -> str:
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    return " ".join(text[left:right].replace("\n", " ").split())[:700]


def _legal_name_in_context(profile: dict[str, Any], context: str) -> bool:
    tokens = distinctive_legal_name_tokens(profile.get("name"))
    if not tokens:
        return False
    folded = _ascii_fold(context)
    observed = set(re.findall(r"[a-z0-9]+", folded))
    return set(tokens).issubset(observed)


def _org_in_context(profile: dict[str, Any], context: str) -> bool:
    target = re.sub(r"\D", "", str(profile.get("organisation_number") or ""))
    return len(target) == 9 and target in re.sub(r"\D", "", context)


def _root_url(domain: str, original_url: str | None = None) -> str:
    scheme = "https"
    if original_url:
        parsed = urllib.parse.urlparse(original_url if "://" in original_url else "https://" + original_url)
        if parsed.scheme in {"http", "https"}:
            scheme = parsed.scheme
    return f"{scheme}://{domain}/"


def _clean_url_match(raw: str) -> tuple[str, str] | None:
    candidate = raw.strip().rstrip(".,;:!?)]}>'\"")
    if candidate.casefold().startswith("www."):
        candidate = "https://" + candidate
    try:
        parsed = urllib.parse.urlparse(candidate)
    except ValueError:
        return None
    domain = _normalise_domain(parsed.hostname or "")
    if not domain:
        return None
    return domain, _root_url(domain, candidate)


def _score_candidate(
    profile: dict[str, Any],
    *,
    domain: str,
    context: str,
    source_kind: str,
    explicit_web_url: bool,
) -> tuple[int, list[str], list[str]]:
    score = 0
    positive: list[str] = []
    negative: list[str] = []
    strength = _domain_identity_strength(profile, domain)
    strength_points = {"exact": 6, "multi": 5, "acronym": 4, "partial": 2, "none": 0}
    score += strength_points.get(strength, 0)
    if strength != "none":
        positive.append(f"legal_name_domain_{strength}")
    if domain.endswith(".no"):
        score += 1
        positive.append("norwegian_tld")
    if explicit_web_url:
        score += 2
        positive.append("explicit_url_in_report")
    if source_kind == "email_domain":
        score += 1
        positive.append("domain_from_report_email")
    if _legal_name_in_context(profile, context):
        score += 3
        positive.append("legal_name_in_local_context")
    if _org_in_context(profile, context):
        score += 4
        positive.append("target_org_number_in_local_context")
    if POSITIVE_WEB_LABELS.search(context):
        score += 3
        positive.append("explicit_website_label")
    if POSITIVE_CONTACT_LABELS.search(context):
        score += 1
        positive.append("contact_label")
    if NEGATIVE_PROVIDER_CONTEXT.search(context):
        score -= 5
        negative.append("professional_service_provider_context")
    if domain in NOISY_HOSTS or any(domain.endswith("." + host) for host in NOISY_HOSTS):
        score -= 8
        negative.append("known_non_company_service_host")
    return score, positive, negative


def extract_annual_report_site_candidates(profile: dict[str, Any], text: str, *, max_candidates: int = 8) -> list[dict[str, Any]]:
    """Nominate site candidates from exact-org annual-report text without any network use.

    These rows are discovery hints only. They are never evidence of website ownership and
    must pass the existing independent exact-company website identity gate before publication.
    """
    candidates: dict[str, dict[str, Any]] = {}

    def consider(domain: str, *, url: str, context: str, source_kind: str, explicit_web_url: bool, raw: str) -> None:
        normalized = _normalise_domain(domain)
        if not normalized or normalized in GENERIC_EMAIL_DOMAINS:
            return
        score, positive, negative = _score_candidate(
            profile,
            domain=normalized,
            context=context,
            source_kind=source_kind,
            explicit_web_url=explicit_web_url,
        )
        row = {
            "domain": normalized,
            "url": url,
            "source_kind": source_kind,
            "score": score,
            "positive_reasons": positive,
            "negative_reasons": negative,
            "context": context,
            "raw_match": raw[:260],
            "publication_evidence": False,
        }
        prior = candidates.get(normalized)
        if prior is None or (score, source_kind == "explicit_url") > (int(prior["score"]), prior["source_kind"] == "explicit_url"):
            candidates[normalized] = row

    url_spans: list[tuple[int, int]] = []
    for match in URL_RE.finditer(text):
        cleaned = _clean_url_match(match.group(0))
        if not cleaned:
            continue
        domain, url = cleaned
        url_spans.append((match.start(), match.end()))
        consider(
            domain,
            url=url,
            context=_context(text, match.start(), match.end()),
            source_kind="explicit_url",
            explicit_web_url=True,
            raw=match.group(0),
        )

    for match in EMAIL_RE.finditer(text):
        domain = _normalise_domain(match.group(1))
        if not domain:
            continue
        consider(
            domain,
            url=_root_url(domain),
            context=_context(text, match.start(), match.end()),
            source_kind="email_domain",
            explicit_web_url=False,
            raw=match.group(0),
        )

    # Bare domains are useful only when the report itself labels them as a website or the
    # domain strongly resembles the target legal entity. Avoid duplicating URL/email spans.
    for match in DOMAIN_RE.finditer(text):
        if any(start <= match.start() < end for start, end in url_spans):
            continue
        domain = _normalise_domain(match.group(1))
        if not domain or domain in GENERIC_EMAIL_DOMAINS:
            continue
        context = _context(text, match.start(), match.end())
        strength = _domain_identity_strength(profile, domain)
        if strength == "none" and not POSITIVE_WEB_LABELS.search(context):
            continue
        consider(
            domain,
            url=_root_url(domain),
            context=context,
            source_kind="bare_domain",
            explicit_web_url=False,
            raw=match.group(0),
        )

    rows = sorted(
        candidates.values(),
        key=lambda item: (-int(item["score"]), bool(item["negative_reasons"]), item["domain"]),
    )
    for index, row in enumerate(rows):
        row["rank"] = index + 1
        row["probe_recommendation"] = (
            "high" if int(row["score"]) >= 8 and not row["negative_reasons"]
            else "medium" if int(row["score"]) >= 5 and not row["negative_reasons"]
            else "reject"
        )
    return rows[:max_candidates]
