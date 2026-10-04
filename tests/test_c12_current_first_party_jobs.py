from __future__ import annotations

from bs4 import BeautifulSoup

from norway_company_agent.first_party_jobs import extract_current_first_party_jobs
from norway_company_agent.job_surface_signal import (
    extract_homepage_hiring_signal,
    extract_job_listing_candidates,
)


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def _website(*, careers_url: str = "https://www.afgruppen.no/karriere/ledige-stillinger/") -> dict:
    return {
        "status": "available",
        "source_type": "registry_linked_company_website",
        "source_url": "https://www.afgruppen.no/",
        "retrieved_at": "2026-10-04T06:00:00Z",
        "content_sha256": "a" * 64,
        "value": {
            "final_url": "https://www.afgruppen.no/",
            "registered_domain": "afgruppen.no",
            "identity_assessment": {
                "status": "exact",
                "score": 1.0,
                "publishable": True,
                "method": "fixture",
            },
            "careers_links": [
                {
                    "url": careers_url,
                    "anchor_text": "Ledige stillinger",
                    "marker": "ledige stillinger",
                }
            ],
            "job_listing_candidates": [],
            "pages": [],
        },
    }


def _surface(candidates: list[dict], *, url: str = "https://www.afgruppen.no/karriere/ledige-stillinger/") -> dict:
    return {
        "status": "available",
        "source_type": "verified_company_careers_surface_candidate",
        "source_url": url,
        "retrieved_at": "2026-10-04T06:01:00Z",
        "content_sha256": "b" * 64,
        "value": {
            "final_url": url,
            "registered_domain": "afgruppen.no",
            "job_listing_candidates": candidates,
            "pages": [],
        },
    }


def _profile(candidates: list[dict]) -> dict:
    return {
        "organisation_number": "938702675",
        "name": "AF GRUPPEN ASA",
        "evidence": {
            "website": _website(),
            "website_careers_surface": _surface(candidates),
        },
    }


def test_af_homepage_positive_vacancy_count_is_active() -> None:
    html = """
    <html><body>
      <section><strong>10</strong> Antall ledige stillinger i AF akkurat nå</section>
      <a href='/karriere/ledige-stillinger/'>Vi trenger flere nysgjerrige</a>
    </body></html>
    """
    signal = extract_homepage_hiring_signal(
        final_url="https://www.afgruppen.no/",
        soup=_soup(html),
    )
    assert signal["active_vacancies"] is True
    assert signal["active_vacancy_count"] == 10
    assert signal["method"] == "explicit_homepage_vacancy_count"


def test_granne_generic_careers_link_does_not_claim_active_vacancies() -> None:
    html = """
    <html><body>
      <a href='/ledige-stillinger'>Ledige stillinger</a>
      <p>Her oppdaterer vi så snart det kommer ledige stillinger i Granne.</p>
    </body></html>
    """
    signal = extract_homepage_hiring_signal(
        final_url="https://www.granne.no/",
        soup=_soup(html),
    )
    assert signal["active_vacancies"] is False
    assert signal["active_vacancy_count"] == 0


def test_af_careers_surface_extracts_parent_and_subsidiary_role_cards() -> None:
    html = """
    <html><body>
      <article>
        <p>AF Gruppen Konsern</p>
        <p>Frist 18.10.2026</p>
        <a href='/karriere/ledige-stillinger/2026/09/bedriftslege/'>Bedriftslege</a>
        <a href='https://candidate.example/apply/bedriftslege'>Søk på stillingen</a>
      </article>
      <article>
        <p>AF Elkraft AS</p>
        <p>Frist 20.10.2026</p>
        <a href='/karriere/ledige-stillinger/2026/09/prosjektleder-elkraft/'>Prosjektleder Elkraft</a>
      </article>
    </body></html>
    """
    rows = extract_job_listing_candidates(
        final_url="https://www.afgruppen.no/karriere/ledige-stillinger/",
        soup=_soup(html),
        structured={},
    )
    titles = {row["title"] for row in rows}
    assert "Bedriftslege" in titles
    assert "Prosjektleder Elkraft" in titles
    bedrift = next(row for row in rows if row["title"] == "Bedriftslege")
    assert bedrift["deadline_raw"] == "18.10.2026"
    assert "AF Gruppen Konsern" in bedrift["employer_context"]
    assert bedrift["application_url"] == "https://candidate.example/apply/bedriftslege"


def test_parent_projection_accepts_bedriftslege_and_rejects_subsidiary_role() -> None:
    candidates = [
        {
            "title": "Bedriftslege",
            "role_url": "https://www.afgruppen.no/karriere/ledige-stillinger/2026/09/bedriftslege/",
            "application_url": "https://candidate.example/apply/bedriftslege",
            "action_type": "explicit_apply_link",
            "deadline_raw": "18.10.2026",
            "employer_context": "AF Gruppen Konsern Frist 18.10.2026 Bedriftslege",
            "hiring_organisation": "",
            "method": "dated_role_card",
        },
        {
            "title": "Prosjektleder Elkraft",
            "role_url": "https://www.afgruppen.no/karriere/ledige-stillinger/2026/09/prosjektleder-elkraft/",
            "application_url": "https://www.afgruppen.no/karriere/ledige-stillinger/2026/09/prosjektleder-elkraft/",
            "action_type": "role_detail_link",
            "deadline_raw": "20.10.2026",
            "employer_context": "AF Elkraft AS Frist 20.10.2026 Prosjektleder Elkraft",
            "hiring_organisation": "",
            "method": "dated_role_card",
        },
    ]
    jobs = extract_current_first_party_jobs(_profile(candidates))
    assert [item["title"] for item in jobs] == ["Bedriftslege"]
    assert jobs[0]["deadline"] == "2026-10-18"
    assert jobs[0]["application_url"] == "https://candidate.example/apply/bedriftslege"
    assert jobs[0]["evidence_url"] == "https://www.afgruppen.no/karriere/ledige-stillinger/"


def test_expired_role_is_not_current() -> None:
    candidate = {
        "title": "Bedriftslege",
        "role_url": "https://www.afgruppen.no/karriere/ledige-stillinger/2026/09/bedriftslege/",
        "application_url": "https://candidate.example/apply/bedriftslege",
        "action_type": "explicit_apply_link",
        "deadline_raw": "03.10.2026",
        "employer_context": "AF Gruppen Konsern Frist 03.10.2026 Bedriftslege",
        "hiring_organisation": "",
        "method": "dated_role_card",
    }
    assert extract_current_first_party_jobs(_profile([candidate])) == []


def test_unlisted_or_empty_careers_surface_never_becomes_job() -> None:
    profile = _profile([])
    assert extract_current_first_party_jobs(profile) == []

    unlisted = _profile([
        {
            "title": "Bedriftslege",
            "role_url": "https://www.afgruppen.no/karriere/ledige-stillinger/2026/09/bedriftslege/",
            "application_url": "https://candidate.example/apply/bedriftslege",
            "deadline_raw": "18.10.2026",
            "employer_context": "AF Gruppen Konsern Frist 18.10.2026",
            "hiring_organisation": "",
        }
    ])
    unlisted["evidence"]["website"]["value"]["careers_links"] = [
        {"url": "https://www.afgruppen.no/karriere/annen-side/"}
    ]
    assert extract_current_first_party_jobs(unlisted) == []


def test_structured_job_posting_requires_target_employer_match() -> None:
    html = """
    <html><body><h1>Careers</h1></body></html>
    """
    structured = {
        "json-ld": [
            {
                "@type": "JobPosting",
                "title": "Bedriftslege",
                "validThrough": "2026-10-18",
                "url": "/karriere/ledige-stillinger/2026/09/bedriftslege/",
                "hiringOrganization": {"name": "AF Gruppen ASA"},
            }
        ]
    }
    rows = extract_job_listing_candidates(
        final_url="https://www.afgruppen.no/karriere/ledige-stillinger/",
        soup=_soup(html),
        structured=structured,
    )
    assert len(rows) == 1
    assert rows[0]["method"] == "jsonld_job_posting"
    jobs = extract_current_first_party_jobs(_profile(rows))
    assert [item["title"] for item in jobs] == ["Bedriftslege"]
