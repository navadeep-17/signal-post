from __future__ import annotations

from pathlib import Path
import sys
from urllib.parse import urlparse

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import norway_company_agent.final_site_discovery as final_site  # noqa: E402
from norway_company_agent.evidence import evidence  # noqa: E402


def _profile(
    *,
    email: str = "",
    organisation_number: str = "933200353",
    name: str = "OSLO MIKROSEMENT AS",
    municipality: str = "NITTEDAL",
    address: str = "Carl Bergersens vei 47A",
    postcode: str = "1481",
    poststed: str = "HAGAN",
) -> dict:
    return {
        "organisation_number": organisation_number,
        "name": name,
        "legal_form": "AS",
        "website": "",
        "municipality": municipality,
        "evidence": {
            "registry": evidence(
                "registry",
                "available",
                "official_registry_bulk",
                final_site.BRREG_BULK_URL,
                value={
                    "navn": name,
                    "epostadresse": email,
                    "forretningsadresse.adresse": address,
                    "forretningsadresse.postnummer": postcode,
                    "forretningsadresse.poststed": poststed,
                    "forretningsadresse.kommune": municipality,
                },
                content_sha256="b" * 64,
                source_row_key=organisation_number,
                retrieved_at="2026-09-15T00:00:00Z",
            ),
        },
    }


def _website(
    url: str,
    *,
    title: str,
    text: str,
    identity_text: str = "",
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
    domain = (urlparse(url).hostname or "").removeprefix("www.")
    value = {
        "requested_url": url,
        "final_url": url,
        "registered_domain": domain,
        "title": title,
        "description": "",
        "identity_text_excerpt": identity_text,
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
                "identity_text_excerpt": identity_text,
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


def test_footer_identity_text_recovers_exact_org_number_without_main_text():
    soup = BeautifulSoup(
        """
        <html>
          <body>
            <main><p>Premium mikrosement og moderne overflater.</p></main>
            <footer class="site-footer">
              <p>OSLO MIKROSEMENT AS</p>
              <p>Org.nr 933 200 353</p>
              <p>Carl Bergersens vei 47A, 1481 Hagan</p>
            </footer>
          </body>
        </html>
        """,
        "lxml",
    )
    excerpt = final_site._identity_text_excerpt(soup)
    assert "933 200 353" in excerpt
    assert "Carl Bergersens vei 47A" in excerpt

    website = _website(
        "https://oslomikrosement.no/",
        title="Oslo Mikrosement",
        text="Premium mikrosement og moderne overflater.",
        identity_text=excerpt,
    )

    assert final_site._page_contains_org_number(_profile(), website) is True


def test_footer_identity_text_does_not_copy_arbitrary_main_content():
    soup = BeautifulSoup(
        """
        <html>
          <body>
            <main><p>Org.nr 933 200 353 appears only in arbitrary main content.</p></main>
            <footer><p>Copyright 2026</p></footer>
          </body>
        </html>
        """,
        "lxml",
    )
    excerpt = final_site._identity_text_excerpt(soup)
    assert "933 200 353" not in excerpt
    assert "Copyright 2026" in excerpt


def test_secondary_identity_links_prioritize_privacy_legal_over_contact():
    soup = BeautifulSoup(
        """
        <html><body>
          <a href="/kontakt/">Kontakt</a>
          <a href="/personvernerklaering/">Personvernerklæring</a>
          <a href="/om-oss/">Om oss</a>
        </body></html>
        """,
        "lxml",
    )
    links = final_site._secondary_identity_links("https://okonomibistand.no/", soup)
    assert links[0] == "https://okonomibistand.no/personvernerklaering/"
    assert "https://okonomibistand.no/kontakt/" in links


def test_explicit_different_org_number_is_conflict_but_target_org_wins():
    profile = _profile(
        organisation_number="925531618",
        name="ØKONOMIBISTAND AS",
        municipality="KRØDSHERAD",
        address="Rundskogen 25",
        postcode="3536",
        poststed="NORESUND",
    )
    wrong = _website(
        "https://okonomibistand.no/personvernerklaering/",
        title="Personvernerklæring",
        text="Denne siden eies og driftes av ØkonomiBistand Regnskap AS, Org. nr. 929327446.",
    )
    assert final_site._explicit_org_numbers(wrong) == {"929327446"}
    assert final_site._has_conflicting_explicit_org_number(profile, wrong) is True

    mixed = _website(
        "https://okonomibistand.no/legal/",
        title="Legal",
        text="Org.nr 929327446. ØKONOMIBISTAND AS org nr 925 531 618.",
    )
    assert final_site._has_conflicting_explicit_org_number(profile, mixed) is False


def test_shared_address_wrong_entity_is_rejected_after_privacy_page(monkeypatch):
    profile = _profile(
        organisation_number="925531618",
        name="ØKONOMIBISTAND AS",
        municipality="KRØDSHERAD",
        address="Rundskogen 25",
        postcode="3536",
        poststed="NORESUND",
    )
    homepage = _website(
        "https://okonomibistand.no/",
        title="ØkonomiBistand - Regnskap og økonomi",
        text="ØkonomiBistand AS hjelper bedrifter med regnskap og økonomi. " * 10,
        identity_text="Rundskogen 25, 3536 Noresund",
        identity_links=[
            "https://okonomibistand.no/personvernerklaering/",
            "https://okonomibistand.no/kontakt/",
        ],
    )
    privacy = _website(
        "https://okonomibistand.no/personvernerklaering/",
        title="Personvernerklæring - ØkonomiBistand",
        text=(
            "Denne siden eies og driftes av ØkonomiBistand Regnskap AS, "
            "Org. nr. 929327446, Rundskogen 25, 3536 Noresund."
        ),
        identity_text="Org. nr. 929327446, Rundskogen 25, 3536 Noresund",
        digest="e" * 64,
    )
    calls: list[str] = []

    def fake_fetch(url, *, source_type, timeout=6.0, max_bytes=750_000):
        calls.append(url)
        record = homepage if len(calls) == 1 else privacy
        return record, {"requests": 2, "bytes": 100, "latencies_ms": [10]}

    monkeypatch.setattr(final_site, "registry_email_domain_candidates", lambda row: {"eligible": False, "reason": "none", "candidates": []})
    monkeypatch.setattr(
        final_site,
        "deterministic_domain_candidates",
        lambda row, max_candidates=1: {
            "eligible": True,
            "reason": "fixture",
            "candidates": [{
                "domain": "okonomibistand.no",
                "url": "https://okonomibistand.no/",
                "strategy": "legal_name_compact",
            }],
        },
    )
    monkeypatch.setattr(final_site, "fetch_bounded_homepage", fake_fetch)

    row, metrics = final_site.discover_final_website(profile)

    assert calls == [
        "https://okonomibistand.no/",
        "https://okonomibistand.no/personvernerklaering/",
    ]
    assert metrics["requests"] == final_site.MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE == 4
    assert metrics["h1c_secondary_attempted"] is True
    assert metrics["h1c_secondary_verified"] is False
    assert metrics["promoted"] is False
    assert row["evidence"]["website"]["status"] == "not_found"
    assessment = row["evidence"]["website_discovered_zero_cost"]["value"]["identity_assessment"]
    assert assessment["publishable"] is False
    assert "different organisation number" in " ".join(assessment["reasons"]).casefold()


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
