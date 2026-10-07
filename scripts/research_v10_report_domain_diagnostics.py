#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from norway_company_agent.annual_report_site_nomination import (  # noqa: E402
    EXCLUDED_REGISTERED_DOMAINS,
    evaluate_annual_report_site_candidates,
    extract_annual_report_site_candidates,
)
from norway_company_agent.batch import profiles_from_bulk, read_organisation_inputs  # noqa: E402
from norway_company_agent.domain_discovery import (  # noqa: E402
    GENERIC_EMAIL_DOMAINS,
    _domain_identity_strength,
    distinctive_legal_name_tokens,
    registry_email_domain_candidates,
)
from norway_company_agent.zero_cost_discovery import deterministic_domain_candidates  # noqa: E402
from screen_v10_m16_annual_report_bare_domain import fetch_report_text  # noqa: E402


DOMAIN_RE = re.compile(
    r"(?i)(?<![a-z0-9.-])"
    r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"(?:no|com|net|org|eu|io|as)\b"
)
GENERIC_CONTACT_LOCALS = {
    "info", "post", "kontakt", "contact", "booking", "office", "admin",
    "firmapost", "mail", "hello", "hei", "kundeservice",
}
POSITIVE_CONTEXT = {
    "kontakt", "contact", "e-post", "epost", "email", "mail",
    "nettside", "website", "hjemmeside", "web", "www",
}
NEGATIVE_CONTEXT = {
    "revisor", "revisjon", "auditor", "audit", "regnskapsfører",
    "regnskapsforer", "accounting", "advokat", "bank", "signering",
    "visma", "tripletex", "poweroffice", "azets", "deloitte", "kpmg", "pwc",
}
EXTRA_SERVICE_DOMAINS = {
    "bdo.no", "pwc.no", "kpmg.no", "deloitte.no", "ey.com",
    "visma.com", "visma.no", "tripletex.no", "poweroffice.no", "azets.no",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{lineno}: object expected")
        rows.append(value)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _rootish_domain(host: str) -> str:
    labels = str(host or "").casefold().strip(".").split(".")
    if labels and labels[0] == "www":
        labels = labels[1:]
    if len(labels) < 2:
        return ""
    return ".".join(labels[-2:])


def _preceding_email_local(text: str, start: int) -> str:
    if start < 1 or text[start - 1] != "@":
        return ""
    left = text[max(0, start - 80):start - 1]
    m = re.search(r"([A-Za-z0-9._%+-]{1,64})$", left)
    return (m.group(1) if m else "").casefold()


def domain_mentions(profile: dict[str, Any], text: str) -> list[dict[str, Any]]:
    org = re.sub(r"\D", "", str(profile.get("organisation_number") or ""))
    if len(org) != 9 or org not in re.sub(r"\D", "", str(text or "")):
        return []

    already_tried: set[str] = set()
    for row in deterministic_domain_candidates(profile, max_candidates=2).get("candidates") or []:
        if row.get("domain"):
            already_tried.add(str(row["domain"]).casefold().rstrip("."))
    for row in registry_email_domain_candidates(profile).get("candidates") or []:
        if row.get("domain"):
            already_tried.add(str(row["domain"]).casefold().rstrip("."))

    explicit = {
        str(row.get("domain") or "").casefold().rstrip(".")
        for row in extract_annual_report_site_candidates(profile, text, max_candidates=30)
        if row.get("domain")
    }
    already_tried |= explicit

    legal_tokens = distinctive_legal_name_tokens(profile.get("name"))
    by_domain: dict[str, dict[str, Any]] = {}

    for match in DOMAIN_RE.finditer(str(text or "")):
        raw_host = match.group(0).casefold().rstrip(".")
        domain = _rootish_domain(raw_host)
        if not domain:
            continue

        prefix = str(text or "")[max(0, match.start() - 12):match.start()].casefold()
        explicit_form = (
            raw_host.startswith("www.")
            or prefix.endswith("http://")
            or prefix.endswith("https://")
        )
        email_local = _preceding_email_local(str(text or ""), match.start())
        method = "email_domain" if email_local else "bare_domain"

        start = max(0, match.start() - 220)
        end = min(len(str(text or "")), match.end() + 220)
        context = " ".join(str(text or "")[start:end].split())
        folded = context.casefold()

        strength = _domain_identity_strength(profile, domain)
        score = {
            "exact": 6,
            "multi": 5,
            "acronym": 4,
            "partial": 1,
            "none": 0,
        }.get(strength, 0)
        if email_local:
            score += 4 if email_local in GENERIC_CONTACT_LOCALS else 2
        if any(token in folded for token in POSITIVE_CONTEXT):
            score += 3
        if org in re.sub(r"\D", "", context):
            score += 2
        if legal_tokens and all(token in folded for token in legal_tokens):
            score += 2
        negative_hits = sorted(token for token in NEGATIVE_CONTEXT if token in folded)
        if negative_hits:
            score -= 6

        generic = (
            domain in GENERIC_EMAIL_DOMAINS
            or domain in EXCLUDED_REGISTERED_DOMAINS
            or domain in EXTRA_SERVICE_DOMAINS
        )
        row = by_domain.get(domain)
        candidate = {
            "domain": domain,
            "url": f"https://{domain}/",
            "method": method,
            "email_local": email_local or None,
            "identity_strength": strength,
            "score": score,
            "already_tried": domain in already_tried,
            "explicit_m15_form": explicit_form or domain in explicit,
            "generic_or_service": generic,
            "negative_context_hits": negative_hits,
            "evidence_span": context[:600],
            "position": match.start(),
        }
        if row is None or int(candidate["score"]) > int(row["score"]):
            by_domain[domain] = candidate

    return sorted(
        by_domain.values(),
        key=lambda row: (
            -int(row["score"]),
            bool(row["already_tried"]),
            bool(row["generic_or_service"]),
            int(row["position"]),
            str(row["domain"]),
        ),
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, action="append", required=True)
    p.add_argument("--prior-screen", type=Path, action="append", required=True)
    p.add_argument("--bulk", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--verified", type=Path, required=True)
    p.add_argument("--annual-timeout", type=float, default=60.0)
    p.add_argument("--ocr-pages", type=int, default=8)
    p.add_argument("--ocr-dpi", type=int, default=110)
    p.add_argument("--site-timeout", type=float, default=6.0)
    p.add_argument("--min-start-interval", type=float, default=2.1)
    args = p.parse_args()

    if len(args.manifest) != len(args.prior_screen):
        raise ValueError("--manifest and --prior-screen counts must match")

    organisations: list[str] = []
    baseline_verified: dict[str, bool] = {}
    for manifest_path, screen_path in zip(args.manifest, args.prior_screen):
        manifest = read_organisation_inputs(manifest_path)
        screen = read_jsonl(screen_path)
        screen_by_org = {
            str(row.get("organisation_number") or ""): row
            for row in screen
        }
        for row in manifest:
            org = str(row["organisation_number"])
            if org in organisations:
                raise ValueError(f"duplicate organisation across research cohorts: {org}")
            organisations.append(org)
            prior = screen_by_org.get(org)
            if prior is None:
                raise ValueError(f"missing prior screen row for {org}")
            baseline_verified[org] = bool(prior.get("baseline_verified_website"))

    if len(organisations) != 40:
        raise ValueError(f"expected combined consumed 40, got {len(organisations)}")

    profiles, snapshot = profiles_from_bulk(args.bulk, organisations)
    profiles_by_org = {
        str(profile.get("organisation_number") or ""): profile
        for profile in profiles
    }

    rows: list[dict[str, Any]] = []
    verified: list[dict[str, Any]] = []
    reports_requested = 0
    reports_available = 0
    report_bytes = 0
    site_requests = 0
    site_bytes = 0
    companies_with_mentions = 0
    companies_with_untried = 0
    candidates_attempted = 0
    all_domain_counter: Counter[str] = Counter()
    last_report_start = 0.0

    for org in organisations:
        item: dict[str, Any] = {
            "organisation_number": org,
            "baseline_verified_website": baseline_verified[org],
            "report": None,
            "mentions": [],
            "attempted_candidate": None,
            "verified": False,
        }
        if baseline_verified[org]:
            item["status"] = "baseline_already_verified"
            rows.append(item)
            continue

        now = time.monotonic()
        wait = float(args.min_start_interval) - (now - last_report_start)
        if wait > 0:
            time.sleep(wait)
        last_report_start = time.monotonic()

        text, report = fetch_report_text(
            profiles_by_org[org],
            timeout=args.annual_timeout,
            ocr_pages=args.ocr_pages,
            ocr_dpi=args.ocr_dpi,
        )
        item["report"] = report
        reports_requested += int(report.get("request_count") or 0)
        report_bytes += int(report.get("bytes") or 0)
        if text is None:
            item["status"] = str(report.get("status") or "report_unavailable")
            rows.append(item)
            continue
        reports_available += 1

        mentions = domain_mentions(profiles_by_org[org], text)
        item["mentions"] = mentions
        if mentions:
            companies_with_mentions += 1
            for mention in mentions:
                all_domain_counter[str(mention["domain"])] += 1

        eligible = [
            mention
            for mention in mentions
            if not mention["already_tried"]
            and not mention["explicit_m15_form"]
            and not mention["generic_or_service"]
            and int(mention["score"]) >= 2
        ]
        if not eligible:
            item["status"] = "no_untried_research_candidate"
            rows.append(item)
            continue

        companies_with_untried += 1
        top = eligible[0]
        item["attempted_candidate"] = top
        candidates_attempted += 1

        _enriched, result = evaluate_annual_report_site_candidates(
            profiles_by_org[org],
            [
                {
                    "domain": top["domain"],
                    "url": top["url"],
                    "method": "research_broader_report_domain",
                    "evidence_span": top["evidence_span"],
                }
            ],
            timeout=args.site_timeout,
            max_candidates=1,
        )
        item["site_evaluation"] = result
        site_requests += int(result.get("requests") or 0)
        site_bytes += int(result.get("bytes") or 0)
        item["verified"] = bool(result.get("verified"))
        item["status"] = "research_verified" if item["verified"] else "research_candidate_rejected"

        if item["verified"]:
            candidate_result = (result.get("candidate_results") or [{}])[0]
            verified.append(
                {
                    "organisation_number": org,
                    "candidate_domain": top["domain"],
                    "candidate_score": top["score"],
                    "candidate_method": top["method"],
                    "candidate_identity_strength": top["identity_strength"],
                    "candidate_context": top["evidence_span"],
                    "selected_url": result.get("selected_url"),
                    "website_content_sha256": candidate_result.get("website_content_sha256"),
                    "identity_status": candidate_result.get("identity_status"),
                    "identity_score": candidate_result.get("identity_score"),
                    "identity_reasons": candidate_result.get("identity_reasons"),
                    "manual_review_required": True,
                    "production_evidence": False,
                }
            )
        rows.append(item)

    report = {
        "research": "v10_consumed_annual_report_domain_diagnostic",
        "research_only": True,
        "promotion_authorized": False,
        "fresh_qualification_authorized": False,
        "companies": len(organisations),
        "baseline_verified_companies_skipped": sum(baseline_verified.values()),
        "annual_report_requests": reports_requested,
        "annual_reports_available": reports_available,
        "annual_report_bytes": report_bytes,
        "companies_with_any_domain_mentions": companies_with_mentions,
        "companies_with_untried_ranked_domain": companies_with_untried,
        "research_candidates_attempted": candidates_attempted,
        "candidate_site_requests": site_requests,
        "candidate_site_bytes": site_bytes,
        "research_verified_websites": len(verified),
        "registry_snapshot_sha256": snapshot.get("registry_snapshot_sha256"),
        "top_domain_mentions": [
            {"domain": domain, "companies": count}
            for domain, count in all_domain_counter.most_common(30)
        ],
        "interpretation_rule": (
            "This diagnostic uses already-consumed M15/M16 companies only. Any verified site "
            "is research evidence for designing a future pre-registered hypothesis, not a "
            "promotion result and not qualification evidence."
        ),
    }

    write_jsonl(args.output, rows)
    write_jsonl(args.verified, verified)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
