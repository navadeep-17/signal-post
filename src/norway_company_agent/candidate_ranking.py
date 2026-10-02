from __future__ import annotations

import json
import math
import re
import urllib.parse
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from .domain_discovery import GENERIC_EMAIL_DOMAINS, distinctive_legal_name_tokens, registry_email_addresses

RULES_RANKER_ID = "website.candidate_rank.rules.v1"
ML_RANKER_ID = "website.candidate_rank.ml.v1"
MODEL_SCHEMA = "signalpost.website_candidate_logistic.v1"
MAX_GENERATED_CANDIDATES = 12

GENERIC_DOMAIN_WORDS = {
    "company", "firma", "group", "gruppen", "holding", "invest", "investering",
    "norge", "norway", "service", "services", "solutions", "consult", "consulting",
    "tech", "technology", "butikk", "shop", "studio", "partner", "partners",
}
COMMON_SINGLE_TOKENS = {
    "alpha", "arena", "best", "bygg", "data", "design", "digital", "drift", "energi",
    "fjord", "global", "hus", "media", "nord", "nordic", "nova", "partner", "service",
    "smart", "studio", "tech", "vest", "vision",
}
FEATURE_NAMES = [
    "registry_domain_equal", "registry_email_domain_equal", "legal_compact_equal",
    "legal_hyphen_equal", "legal_name_similarity", "distinctive_token_overlap",
    "tld_no", "tld_com", "municipality_token", "acronym_only_risk",
    "generic_word_risk", "common_single_token_risk", "label_length_norm",
    "hyphen_count_norm", "digit_risk",
]


def _normalise_ascii(value: Any) -> str:
    text = str(value or "").translate(str.maketrans({
        "ø": "o", "Ø": "O", "å": "a", "Å": "A", "æ": "ae", "Æ": "AE"
    })).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", text))


def _tokens(value: Any) -> list[str]:
    return [token for token in _normalise_ascii(value).split() if token]


def _valid_domain(domain: str) -> bool:
    if not domain or len(domain) > 253 or "." not in domain:
        return False
    labels = domain.casefold().strip(".").split(".")
    if any(not label or len(label) > 63 for label in labels):
        return False
    label_re = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
    return all(bool(label_re.fullmatch(label)) for label in labels)


def _domain_from_url(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if "://" not in text:
        text = "https://" + text
    try:
        host = (urllib.parse.urlparse(text).hostname or "").casefold().removeprefix("www.")
    except ValueError:
        return ""
    return host if _valid_domain(host) else ""


def _domain_label(domain: str) -> str:
    host = _domain_from_url(domain)
    labels = host.split(".") if host else []
    return labels[-2] if len(labels) >= 2 else ""


def _tld(domain: str) -> str:
    host = _domain_from_url(domain)
    return host.rsplit(".", 1)[-1] if "." in host else ""


def registry_domain(profile: dict[str, Any]) -> str:
    raw = ((profile.get("evidence") or {}).get("registry") or {}).get("value") or {}
    for value in (profile.get("website"), raw.get("hjemmeside"), raw.get("internettadresse")):
        domain = _domain_from_url(value)
        if domain:
            return domain
    return ""


def registry_email_domains(profile: dict[str, Any]) -> list[str]:
    domains: list[str] = []
    for address in registry_email_addresses(profile):
        domain = _domain_from_url(address.rpartition("@")[2])
        if domain and domain not in GENERIC_EMAIL_DOMAINS and domain not in domains:
            domains.append(domain)
    return domains


def verified_email_domains(profile: dict[str, Any]) -> list[str]:
    domains: list[str] = []
    for observation in profile.get("external_observations") or []:
        if not isinstance(observation, dict):
            continue
        email = str(observation.get("contact_email") or "").strip().casefold()
        if "@" not in email:
            continue
        domain = _domain_from_url(email.rsplit("@", 1)[-1])
        if domain and domain not in GENERIC_EMAIL_DOMAINS and domain not in domains:
            domains.append(domain)
    return domains


def _safe_acronym(tokens: list[str]) -> str:
    if len(tokens) < 3:
        return ""
    acronym = "".join(token[0] for token in tokens if token)
    if not 3 <= len(acronym) <= 8:
        return ""
    if acronym in COMMON_SINGLE_TOKENS or acronym in GENERIC_DOMAIN_WORDS:
        return ""
    return acronym


def generate_candidate_set(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Return one bounded zero-cost candidate set shared by every V6c ranker."""
    tokens = distinctive_legal_name_tokens(profile.get("name"))
    compact = "".join(tokens)
    hyphen = "-".join(tokens)
    municipality = "".join(_tokens(profile.get("municipality")))
    acronym = _safe_acronym(tokens)
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(domain: str, strategy: str, source_strength: str) -> None:
        domain = _domain_from_url(domain)
        if not domain or domain in seen or len(candidates) >= MAX_GENERATED_CANDIDATES:
            return
        seen.add(domain)
        candidates.append({"domain": domain, "url": f"https://{domain}/", "strategy": strategy, "source_strength": source_strength})

    reg_domain = registry_domain(profile)
    if reg_domain:
        add(reg_domain, "registry_domain", "official_registry")
    for domain in registry_email_domains(profile):
        add(domain, "registry_email_domain", "official_registry")
    for domain in verified_email_domains(profile):
        add(domain, "verified_email_domain", "verified_first_party")
    if 3 <= len(compact) <= 63:
        add(f"{compact}.no", "legal_compact_no", "generated")
        add(f"{compact}.com", "legal_compact_com", "generated")
    if len(tokens) >= 2 and 3 <= len(hyphen) <= 63:
        add(f"{hyphen}.no", "legal_hyphen_no", "generated")
        add(f"{hyphen}.com", "legal_hyphen_com", "generated")
    if acronym:
        add(f"{acronym}.no", "safe_acronym_no", "generated")
        add(f"{acronym}.com", "safe_acronym_com", "generated")
    if municipality and len(tokens) <= 2 and compact and municipality not in compact:
        joined = compact + municipality
        dashed = f"{compact}-{municipality}"
        if len(joined) <= 63:
            add(f"{joined}.no", "legal_compact_municipality_no", "generated")
        if len(dashed) <= 63:
            add(f"{dashed}.no", "legal_hyphen_municipality_no", "generated")
    return candidates


def feature_vector(profile: dict[str, Any], candidate: dict[str, Any]) -> dict[str, float]:
    domain = _domain_from_url(candidate.get("domain") or candidate.get("url"))
    label = _domain_label(domain)
    tld = _tld(domain)
    legal_tokens = distinctive_legal_name_tokens(profile.get("name"))
    legal_compact = "".join(legal_tokens)
    legal_hyphen = "-".join(legal_tokens)
    label_compact = "".join(_tokens(label))
    label_tokens = [token for token in re.split(r"[-_]+", label.casefold()) if token]
    municipality_compact = "".join(_tokens(profile.get("municipality")))
    acronym = _safe_acronym(legal_tokens)
    reg_domain = registry_domain(profile)
    email_domains = set(registry_email_domains(profile) + verified_email_domains(profile))
    legal_set = set(legal_tokens)
    candidate_token_set = set(_tokens(" ".join(label_tokens)))
    overlap = len(legal_set & candidate_token_set) / len(legal_set) if legal_set else 0.0
    similarity = SequenceMatcher(None, legal_compact, label_compact).ratio() if legal_compact and label_compact else 0.0
    return {
        "registry_domain_equal": float(bool(reg_domain and domain == reg_domain)),
        "registry_email_domain_equal": float(domain in email_domains),
        "legal_compact_equal": float(bool(legal_compact and label_compact == legal_compact)),
        "legal_hyphen_equal": float(bool(legal_hyphen and label == legal_hyphen)),
        "legal_name_similarity": float(similarity),
        "distinctive_token_overlap": float(overlap),
        "tld_no": float(tld == "no"),
        "tld_com": float(tld == "com"),
        "municipality_token": float(bool(municipality_compact and municipality_compact in label_compact)),
        "acronym_only_risk": float(bool(acronym and label_compact == acronym and legal_compact != acronym)),
        "generic_word_risk": float(bool(candidate_token_set and candidate_token_set <= GENERIC_DOMAIN_WORDS)),
        "common_single_token_risk": float(len(legal_tokens) == 1 and legal_tokens[0] in COMMON_SINGLE_TOKENS),
        "label_length_norm": min(len(label) / 40.0, 1.5),
        "hyphen_count_norm": min(label.count("-") / 3.0, 1.0),
        "digit_risk": float(any(ch.isdigit() for ch in label)),
    }


def rules_score(profile: dict[str, Any], candidate: dict[str, Any]) -> float:
    f = feature_vector(profile, candidate)
    # Official registry/domain signals outrank pure spelling guesses. The remaining terms
    # order only the zero-cost generated candidates; none of these scores can publish a site.
    return (
        18.0 * f["registry_domain_equal"] + 14.0 * f["registry_email_domain_equal"]
        + 5.2 * f["legal_compact_equal"] + 4.8 * f["legal_hyphen_equal"]
        + 2.8 * f["legal_name_similarity"] + 1.8 * f["distinctive_token_overlap"]
        + 0.9 * f["tld_no"] + 0.35 * f["tld_com"] - 0.55 * f["municipality_token"]
        - 2.0 * f["acronym_only_risk"] - 2.5 * f["generic_word_risk"]
        - 1.8 * f["common_single_token_risk"] - 0.30 * f["label_length_norm"]
        - 0.25 * f["hyphen_count_norm"] - 0.75 * f["digit_risk"]
    )


def load_model(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        raise ValueError("ML candidate ranking requires a local model path")
    model = json.loads(Path(path).read_text(encoding="utf-8"))
    if model.get("schema") != MODEL_SCHEMA or model.get("feature_names") != FEATURE_NAMES:
        raise ValueError("Candidate-ranker model schema does not match runtime")
    return model


def ml_score(profile: dict[str, Any], candidate: dict[str, Any], model: dict[str, Any]) -> float:
    features = feature_vector(profile, candidate)
    means = model.get("means") or {}
    scales = model.get("scales") or {}
    weights = model.get("weights") or {}
    z = float(model.get("intercept") or 0.0)
    for name in FEATURE_NAMES:
        scale = float(scales.get(name) or 1.0) or 1.0
        z += float(weights.get(name) or 0.0) * ((float(features[name]) - float(means.get(name) or 0.0)) / scale)
    z = max(-40.0, min(40.0, z))
    return 1.0 / (1.0 + math.exp(-z))


def rank_candidates(profile: dict[str, Any], candidates: list[dict[str, Any]], *, ranker_id: str, model: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for candidate in candidates:
        features = feature_vector(profile, candidate)
        if ranker_id == RULES_RANKER_ID:
            score = rules_score(profile, candidate)
        elif ranker_id == ML_RANKER_ID:
            if model is None:
                raise ValueError("ML ranker requires a trained local model")
            score = ml_score(profile, candidate, model)
        else:
            raise ValueError(f"Unknown candidate ranker: {ranker_id}")
        ranked.append({**candidate, "ranker_id": ranker_id, "rank_score": float(score), "features": features})
    ranked.sort(key=lambda row: (-float(row["rank_score"]), row["domain"], row["strategy"]))
    for index, row in enumerate(ranked, start=1):
        row["rank"] = index
    return ranked


def attempted_domains(profile: dict[str, Any]) -> set[str]:
    domains: set[str] = set()
    evidence_map = profile.get("evidence") or {}
    website = evidence_map.get("website") or {}
    for value in (profile.get("website"), website.get("source_url"), (website.get("value") or {}).get("requested_url"), (website.get("value") or {}).get("final_url")):
        domain = _domain_from_url(value)
        if domain:
            domains.add(domain)
    for key in ("website_email_discovery", "website_discovery_zero_cost", "website_h1g_hyphenated_no_discovery", "website_wikidata_discovery"):
        record = evidence_map.get(key) or {}
        value = record.get("value") or {}
        for item in (value.get("candidate_domain"), value.get("selected_url"), value.get("independent_page_url"), record.get("source_url")):
            domain = _domain_from_url(item)
            if domain:
                domains.add(domain)
    return domains


def ranked_probe_plan(profile: dict[str, Any], *, ranker_id: str, model: dict[str, Any] | None = None, max_probes: int = 2) -> dict[str, Any]:
    if max_probes not in {1, 2}:
        raise ValueError("V6c max_probes must be 1 or 2")
    candidates = generate_candidate_set(profile)
    tried = attempted_domains(profile)
    eligible = [candidate for candidate in candidates if candidate["domain"] not in tried]
    ranked = rank_candidates(profile, eligible, ranker_id=ranker_id, model=model)
    return {
        "ranker_id": ranker_id,
        "generated_candidates": candidates,
        "attempted_domains": sorted(tried),
        "eligible_candidates": ranked,
        "probe_candidates": ranked[:max_probes],
        "max_probes": max_probes,
        "policy": "Rank scores nominate network probes only; the existing exact-company identity gate remains authoritative.",
    }
