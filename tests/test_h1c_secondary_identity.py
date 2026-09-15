from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import norway_company_agent.final_site_discovery as final_site  # noqa: E402
from norway_company_agent.evidence import evidence  # noqa: E402


def _profile(*, email: str = "") -> dict:
    return {
        "organisation_number": "933200353",
        "name": "OSLO MIKROSEMENT AS",
        "legal_form": "AS",
        "website": "",
        "municipality": "NITTEDAL",
        "evidence": {
            "registry": evidence(
                "registry",
                "available",
                "official_registry_bulk",
                final_site.BRREG_BULK_URL,
                value={
                    "navn": "OSLO MIKROSEMENT AS",
                    "epostadresse": email,
                    "forretningsadresse.adresse": "Carl Bergersens vei 47A",
                    "forretningsadresse.postnummer": "1481",
                    "forretningsadresse.poststed": "HAGAN",
                    "forretningsadresse.kommune": "NITTEDAL",
                },
                content_sha256="b" * 64,
                source_row_key="933200353",
                retrieved_at="2026-09-15T00:00:00Z",
            ),
        },
    }


def _website(
    url: str,
    *,
    title: str,
    text: str,
    identity_links: list[str] | None = None,
    digest: str = "a" * 64,
    status: str = "available",
) -> dict:
    if status != "available":
        return evidence(
            "website",
            status,
            "test",
            url,
            note="fixture",
            retrieved_at="2026-09-15T00:00:00Z",
        )
    value = {
        "requested_url": url,
        "final_url": url,
        "registered_domain": "oslomikrosement.no" if "oslomikrosement.no" in url else "mail.invalid",
        "title": title,
        "description": "",
        "main_text_excerpt": text,
        "social_links": [],
        "structured_organisations": [],
        "content_sha256": digest,
        "extraction_state": "static_complete",
        "identity_links": identity_links or [],
        "pages": [
            {
                "url": url,
                "title": title,
                "main_text_excerpt": text,
                "content_sha256": digest,
            }
        ],
        "crawl_errors": [],
    }
    return evidence(
        "website",
        "available",
        "test",
        url,
        value=value,
        content_sha256=digest,
        note="fixture",
        retrieved_at="2026-09-15T00:00:00Z",
    )


def _h1c_plan(row, max_candidates=1):
    return {
        "eligible": True,
        "reason": "fixture",
        "candidates": [
            {
                "domain": "oslomikrosement.no",
                "url": "https://oslomikrosement.no/",
                "strategy": "legal_name_compact",
            }
        ],
    }


def test_title_domain_only_h1c_is_rejected_when_secondary_page_contradicts_registry(monkeypatch):
    homepage = _website(
        "https://oslomikrosement.no/",
        title="Oslo Mikrosement drives i samarbeid med Basebeton - Mikrosement",
        text="Oslo Mikrosement spesialiserer seg på moderne overflater. " * 12,
        identity_links=["https://oslomikrosement.no/contact/"],
    )
    contact = _website(
        "https://oslomikrosement.no/contact/",
        title="Kontakt - Oslo Mikrosement",
        text="Kontakt oss i Oslo og Gjettum. Basebeton samarbeid og showroom.",
        digest="c" * 64,
    )
    calls: list[str] = []

    def fake_fetch(url, *, source_type, timeout=6.0, max_bytes=750_000):
        calls.append(url)
        record = homepage if len(calls) == 1 else contact
        return record, {"requests": 2, "bytes": 100, "latencies_ms": [10]}

    monkeypatch.setattr(final_site, "registry_email_domain_candidates", lambda row: {"eligible": False, "reason": "none", "candidates": []})
    monkeypatch.setattr(final_site, "deterministic_domain_candidates", _h1c_plan)
    monkeypatch.setattr(final_site, "fetch_bounded_homepage", fake_fetch)

    row, metrics = final_site.discover_final_website(_profile())

    assert calls == ["https://oslomikrosement.no/", "https://oslomikrosement.no/contact/"]
    assert metrics["requests"] == 4
    assert metrics["h1c_secondary_attempted"] is True
    assert metrics["h1c_secondary_verified"] is False
    assert metrics["promoted"] is False
    assert row["evidence"]["website"]["status"] == "not_found"
    assessment = row["evidence"]["website_discovered_zero_cost"]["value"]["identity_assessment"]
    assert assessment["publishable"] is False
    assert "secondary" in " ".join(assessment["reasons"]).casefold()


def test_title_domain_h1c_is_promoted_when_secondary_page_matches_registry_location(monkeypatch):
    homepage = _website(
        "https://oslomikrosement.no/",
        title="Oslo Mikrosement - Mikrosement",
        text="Oslo Mikrosement lager moderne overflater. " * 12,
        identity_links=["https://oslomikrosement.no/kontakt/"],
    )
    contact = _website(
        "https://oslomikrosement.no/kontakt/",
        title="Kontakt - Oslo Mikrosement",
        text="Carl Bergersens vei 47A, 1481 Hagan. Kontakt Oslo Mikrosement.",
        digest="d" * 64,
    )
    calls: list[str] = []

    def fake_fetch(url, *, source_type, timeout=6.0, max_bytes=750_000):
        calls.append(url)
        record = homepage if len(calls) == 1 else contact
        return record, {"requests": 2, "bytes": 100, "latencies_ms": [10]}

    monkeypatch.setattr(final_site, "registry_email_domain_candidates", lambda row: {"eligible": False, "reason": "none", "candidates": []})
    monkeypatch.setattr(final_site, "deterministic_domain_candidates", _h1c_plan)
    monkeypatch.setattr(final_site, "fetch_bounded_homepage", fake_fetch)

    row, metrics = final_site.discover_final_website(_profile())

    assert metrics["requests"] == 4
    assert metrics["h1c_secondary_attempted"] is True
    assert metrics["h1c_secondary_verified"] is True
    assert metrics["promoted"] is True
    assert metrics["selected_source"] == "h1c_deterministic_domain"
    assert row["website"] == "https://oslomikrosement.no/"
    assessment = row["evidence"]["website"]["value"]["identity_assessment"]
    assert assessment["publishable"] is True
    assert any("secondary" in reason.casefold() for reason in assessment["reasons"])


def test_weak_h1c_abstains_when_previous_probe_consumed_secondary_budget(monkeypatch):
    failed_email = _website(
        "https://mail.invalid/",
        title="",
        text="",
        status="source_error",
    )
    homepage = _website(
        "https://oslomikrosement.no/",
        title="Oslo Mikrosement - Mikrosement",
        text="Oslo Mikrosement lager moderne overflater. " * 12,
        identity_links=["https://oslomikrosement.no/kontakt/"],
    )
    calls: list[str] = []

    def fake_fetch(url, *, source_type, timeout=6.0, max_bytes=750_000):
        calls.append(url)
        record = failed_email if len(calls) == 1 else homepage
        return record, {"requests": 2, "bytes": 100, "latencies_ms": [10]}

    monkeypatch.setattr(
        final_site,
        "registry_email_domain_candidates",
        lambda row: {
            "eligible": True,
            "reason": "fixture",
            "candidates": [{"domain": "mail.invalid", "url": "https://mail.invalid/", "source": "fixture"}],
        },
    )
    monkeypatch.setattr(final_site, "deterministic_domain_candidates", _h1c_plan)
    monkeypatch.setattr(final_site, "fetch_bounded_homepage", fake_fetch)

    row, metrics = final_site.discover_final_website(_profile(email="post@mail.invalid"))

    assert metrics["requests"] == final_site.MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE == 4
    assert calls == ["https://mail.invalid/", "https://oslomikrosement.no/"]
    assert metrics["h1c_secondary_attempted"] is False
    assert metrics["promoted"] is False
    assert row["evidence"]["website"]["status"] == "not_found"
