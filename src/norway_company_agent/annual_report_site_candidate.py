from __future__ import annotations

import re
import urllib.parse
from typing import Any

from .domain_discovery import _page_contains_org_number, _page_matches_registry_location
from .final_site_discovery import fetch_bounded_homepage, _has_conflicting_explicit_org_number
from .identity import apply_website_identity_gate
from .website import _registered_domain

STRATEGY = "official_annual_report_site_candidate_v1"

URL_RE = re.compile(r"(?i)\b(?:https?://|www\.)[a-z0-9æøå._~:/?#\[\]@!$&'()*+,;=%-]+")
EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+\-]+@([A-Z0-9.-]+\.[A-Z]{2,})\b")
LEGAL_SUFFIXES = {"as", "asa", "ans", "da", "enk", "nuf", "sa", "ba", "ks", "iks", "kf", "sf", "sti"}
BLOCKED_DOMAINS = {
    "brreg.no", "altinn.no", "nav.no", "skatteetaten.no", "regjeringen.no", "lovdata.no",
    "facebook.com", "instagram.com", "linkedin.com", "youtube.com", "youtu.be", "x.com", "twitter.com", "tiktok.com",
    "gmail.com", "googlemail.com", "hotmail.com", "outlook.com", "live.com", "icloud.com", "yahoo.com", "protonmail.com",
    "microsoft.com", "microsoftonline.com", "sharepoint.com", "docusign.com", "signant.no", "signicat.com",
}
NEGATIVE_CONTEXT = (
    "revisor", "auditor", "audit", "revisjon", "regnskapsfører", "regnskapsforer", "accountant",
    "advokat", "lawyer", "bankforbindelse", "bank connection", "signert", "signed by", "digital signatur",
)
POSITIVE_CONTEXT = (
    "nettside", "hjemmeside", "website", "webside", "www.", "e-post", "epost", "email", "kontakt",
)


def _fold(value: Any) -> str:
    text = str(value or "").translate(str.maketrans({"ø": "o", "Ø": "O", "å": "a", "Å": "A", "æ": "ae", "Æ": "AE"})).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", text))


def _name_tokens(name: str) -> list[str]:
    return [token for token in _fold(name).split() if token not in LEGAL_SUFFIXES and len(token) > 1]


def _domain_tokens(domain: str) -> list[str]:
    host = domain.casefold().removeprefix("www.")
    label = host.split(".")[0]
    return [token for token in re.findall(r"[a-z0-9]+", label) if len(token) > 1]


def _root_url(value: str) -> str | None:
    raw = str(value or "").strip().rstrip(".,;:)]}>\"'")
    if raw.casefold().startswith("www."):
        raw = "https://" + raw
    try:
        parsed = urllib.parse.urlparse(raw)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    host = parsed.hostname.casefold().rstrip(".")
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError:
        return None
    return f"{parsed.scheme}://{host}/"


def _context(text: str, start: int, end: int, radius: int = 240) -> str:
    return " ".join(text[max(0, start - radius):min(len(text), end + radius)].split())[:900]


def _blocked(domain: str) -> bool:
    domain = domain.casefold().removeprefix("www.")
    return any(domain == item or domain.endswith("." + item) for item in BLOCKED_DOMAINS)


def _score_candidate(profile: dict[str, Any], domain: str, source_kind: str, context: str) -> tuple[float, dict[str, Any]]:
    name_tokens = _name_tokens(str(profile.get("name") or ""))
    domain_tokens = set(_domain_tokens(domain))
    matched = sorted(set(name_tokens) & domain_tokens)
    overlap = len(matched) / len(set(name_tokens)) if name_tokens else 0.0
    compact_name = "".join(name_tokens)
    compact_domain = "".join(_domain_tokens(domain))
    distinctive = max(name_tokens, key=len, default="")
    context_folded = _fold(context)
    context_name_hits = [token for token in name_tokens if token in context_folded]
    negative = any(marker in context.casefold() for marker in NEGATIVE_CONTEXT)
    positive = any(marker in context.casefold() for marker in POSITIVE_CONTEXT)

    score = 4.0 if source_kind == "explicit_url" else 2.5
    score += 5.0 * overlap
    if compact_name and len(compact_name) >= 5 and compact_name in compact_domain:
        score += 4.0
    if distinctive and len(distinctive) >= 5 and distinctive in compact_domain:
        score += 2.0
    if context_name_hits:
        score += min(3.0, float(len(set(context_name_hits))))
    if positive:
        score += 1.5
    if negative:
        score -= 8.0
    if len(compact_domain) <= 3:
        score -= 3.0
    return score, {
        "name_overlap": round(overlap, 4),
        "matched_name_tokens": matched,
        "context_name_tokens": sorted(set(context_name_hits)),
        "positive_context": positive,
        "negative_context": negative,
    }


def extract_annual_report_site_candidates(
    profile: dict[str, Any],
    *,
    text: str,
    source_url: str,
    content_sha256: str,
    max_candidates: int = 3,
) -> list[dict[str, Any]]:
    """Nominate explicit report URLs/email domains; never publish a website from text alone."""
    org = re.sub(r"\D", "", str(profile.get("organisation_number") or ""))
    if len(org) != 9 or org not in re.sub(r"\D", "", text):
        return []

    candidates: dict[str, dict[str, Any]] = {}

    def consider(raw_url: str, source_kind: str, span: str) -> None:
        root = _root_url(raw_url)
        if not root:
            return
        domain = _registered_domain(root) or ""
        if not domain or _blocked(domain):
            return
        score, features = _score_candidate(profile, domain, source_kind, span)
        # A report mention with no company/domain association is normally auditor/vendor noise.
        if score < 5.0 or features["negative_context"]:
            return
        row = {
            "url": root,
            "domain": domain,
            "source_kind": source_kind,
            "score": round(score, 4),
            "features": features,
            "report_source_url": source_url,
            "report_content_sha256": content_sha256,
            "evidence_span": span[:900],
            "strategy": STRATEGY,
            "publication_status": "candidate_only_requires_independent_fetch_and_identity_gate",
        }
        previous = candidates.get(domain)
        if previous is None or (row["score"], source_kind == "explicit_url") > (previous["score"], previous["source_kind"] == "explicit_url"):
            candidates[domain] = row

    for match in URL_RE.finditer(text):
        consider(match.group(0), "explicit_url", _context(text, match.start(), match.end()))
    for match in EMAIL_RE.finditer(text):
        domain = match.group(1).casefold().rstrip(".")
        consider("https://" + domain + "/", "email_domain", _context(text, match.start(), match.end()))

    ranked = sorted(
        candidates.values(),
        key=lambda row: (-float(row["score"]), row["source_kind"] != "explicit_url", len(row["domain"]), row["domain"]),
    )
    return ranked[:max(0, int(max_candidates))]


def verify_annual_report_site_candidate(
    profile: dict[str, Any],
    candidate: dict[str, Any],
    *,
    timeout: float = 6.0,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Fetch one nominated domain and require strong exact-company corroboration."""
    website = ((profile.get("evidence") or {}).get("website") or {})
    identity = ((website.get("value") or {}).get("identity_assessment") or {})
    if website.get("status") == "available" and identity.get("publishable"):
        return None, {"status": "website_already_verified", "requests": 0}

    record, metrics = fetch_bounded_homepage(
        str(candidate.get("url") or ""),
        source_type="official_annual_report_website_candidate",
        timeout=timeout,
    )
    gated = apply_website_identity_gate(profile, record)
    candidate_record = gated["website"]
    assessment = gated.get("assessment") or {}
    if candidate_record.get("status") != "available" or not assessment.get("publishable"):
        return None, {**metrics, "status": "identity_gate_rejected", "assessment": assessment}
    if _has_conflicting_explicit_org_number(profile, candidate_record):
        return None, {**metrics, "status": "conflicting_organisation_number", "assessment": assessment}

    exact_org = _page_contains_org_number(profile, candidate_record)
    location_match = _page_matches_registry_location(profile, candidate_record)
    explicit_report_url = candidate.get("source_kind") == "explicit_url"
    name_overlap = float((candidate.get("features") or {}).get("name_overlap") or 0.0)

    # Strong publication proof: exact org on homepage; or exact-site identity + BRREG
    # location; or an explicit exact-org annual-report URL plus exact homepage identity
    # and substantive legal-name/domain association. Email-domain mentions never get the
    # third route because they may belong to an auditor/accountant listed in the report.
    accepted = bool(
        exact_org
        or location_match
        or (explicit_report_url and name_overlap >= 0.5 and float(assessment.get("score") or 0.0) >= 0.95)
    )
    if not accepted:
        return None, {
            **metrics,
            "status": "strong_corroboration_missing",
            "assessment": assessment,
            "exact_org": exact_org,
            "location_match": location_match,
        }

    value = candidate_record.get("value") or {}
    value["annual_report_candidate_proof"] = {
        "source_kind": candidate.get("source_kind"),
        "report_source_url": candidate.get("report_source_url"),
        "report_content_sha256": candidate.get("report_content_sha256"),
        "report_evidence_span": candidate.get("evidence_span"),
        "candidate_score": candidate.get("score"),
        "exact_org_on_homepage": exact_org,
        "registry_location_match": location_match,
    }
    candidate_record["value"] = value
    candidate_record["source_class"] = "company_owned_candidate"
    return candidate_record, {**metrics, "status": "verified", "assessment": assessment, "exact_org": exact_org, "location_match": location_match}
