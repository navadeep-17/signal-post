from __future__ import annotations

from norway_company_agent import v9_m12_late_registry_domain as m12


def _profile(org: str, name: str, email: str, *, municipality: str = "TESTBY"):
    return {
        "organisation_number": org,
        "name": name,
        "website": "",
        "municipality": municipality,
        "evidence": {
            "registry": {
                "status": "available",
                "value": {
                    "epostadresse": email,
                    "forretningsadresse.poststed": municipality,
                    "forretningsadresse.kommune": municipality,
                    "forretningsadresse.postnummer": "1234",
                    "forretningsadresse.adresse": "Testveien 1",
                },
            },
            "website": {"status": "not_found"},
        },
    }


def test_collapses_malformed_multilabel_only_when_exact_legal_name() -> None:
    m = m12
    p = _profile("828829092", "EMILSEN FISK AS", "post@emilsen.fisk.com")
    candidate = m.select_late_registry_domain_candidate(p)
    assert candidate
    assert candidate["domain"] == "emilsenfisk.com"
    assert candidate["registry_email_domain"] == "emilsen.fisk.com"
    assert candidate["strategy"] == "collapsed_exact_registry_email_domain"


def test_unrelated_nonconsumer_registry_domain_is_late_nomination_only() -> None:
    m = m12
    p = _profile("988936987", "ARILD BRÅTEN REGNSKAP AS", "vidar@abras.no")
    candidate = m.select_late_registry_domain_candidate(p)
    assert candidate
    assert candidate["domain"] == "abras.no"
    assert candidate["strategy"] == "late_unrelated_registry_email_domain"


def test_consumer_mail_family_is_never_used_even_with_unlisted_tld() -> None:
    m = m12
    p = _profile("936455298", "VESTNOR TRANSPORT AS", "person@hotmail.es")
    assert m.select_late_registry_domain_candidate(p) is None


def test_existing_m2_name_related_domain_is_not_stolen_by_m12() -> None:
    m = m12
    p = _profile("979943377", "VOLF AS", "post@volf.no")
    assert m.select_late_registry_domain_candidate(p) is None


def test_exact_org_number_on_independently_fetched_page_can_verify_brand_domain() -> None:
    m = m12
    p = _profile("988936987", "ARILD BRÅTEN REGNSKAP AS", "vidar@abras.no")
    website = {
        "status": "available",
        "source_url": "https://abras.no/",
        "value": {
            "title": "Arild Bråten Regnskap AS",
            "main_text_excerpt": "Arild Bråten Regnskap AS. Org nr 988 936 987.",
            "identity_text_excerpt": "Org nr 988 936 987",
            "pages": [],
        },
    }
    result = m.qualify_late_registry_domain_identity(
        p, website, {"status": "review", "score": 0.4, "publishable": False}
    )
    assert result["publishable"] is True
    assert result["status"] == "exact"
    assert result["score"] == 1.0


def test_email_domain_itself_never_proves_identity() -> None:
    m = m12
    p = _profile("988936987", "ARILD BRÅTEN REGNSKAP AS", "vidar@abras.no")
    website = {
        "status": "available",
        "source_url": "https://abras.no/",
        "value": {
            "title": "Generic accounting",
            "main_text_excerpt": "Welcome to our accounting company.",
            "identity_text_excerpt": "",
            "pages": [],
        },
    }
    result = m.qualify_late_registry_domain_identity(
        p, website, {"status": "review", "score": 0.8, "publishable": False}
    )
    assert result["publishable"] is False
    assert result["status"] == "review"


def test_late_slot_never_exceeds_existing_four_request_ceiling(monkeypatch) -> None:
    m = m12
    p = _profile("988936987", "ARILD BRÅTEN REGNSKAP AS", "vidar@abras.no")

    def fake_fetch(url: str, *, source_type: str, timeout: float):
        assert url == "https://abras.no/"
        return (
            {
                "status": "available",
                "source_url": url,
                "source_type": source_type,
                "content_sha256": "a" * 64,
                "value": {
                    "final_url": url,
                    "registered_domain": "abras.no",
                    "title": "Arild Bråten Regnskap AS",
                    "main_text_excerpt": "Arild Bråten Regnskap AS. Org nr 988936987.",
                    "identity_text_excerpt": "Org nr 988936987",
                    "pages": [],
                    "structured_organisations": [],
                },
            },
            {"requests": 2, "bytes": 100, "latencies_ms": [1]},
        )

    monkeypatch.setattr(m, "fetch_bounded_homepage", fake_fetch)
    monkeypatch.setattr(
        m,
        "apply_website_identity_gate",
        lambda profile, record: {
            "website": record,
            "assessment": {"status": "review", "score": 0.5, "publishable": False},
        },
    )
    monkeypatch.setattr(m, "apply_registry_risk_guard", lambda profile: (profile, []))

    out, result = m.evaluate_request_neutral_late_fallback(
        p, timeout=1, base_site_logical_requests=2
    )
    assert result["attempted"] is True
    assert result["m12_candidate_attempted"] is True
    assert result["requests_added"] == 2
    assert result["post_site_logical_requests"] == 4
    assert result["verified"] is True
    assert out["website"] == "https://abras.no/"


def test_when_no_m12_candidate_original_h1g_behavior_is_preserved(monkeypatch) -> None:
    m = m12
    p = _profile("979943377", "VOLF AS", "post@volf.no")
    marker = {"organisation_number": "979943377", "website": ""}

    def fake_h1g(profile, *, timeout, base_site_logical_requests):
        return marker, {
            "candidate_available": True,
            "attempted": True,
            "verified": False,
            "requests_added": 2,
            "bytes_added": 0,
            "latencies_ms": [],
            "guard_reasons": [],
        }

    monkeypatch.setattr(m, "evaluate_hyphenated_no_fallback", fake_h1g)
    out, result = m.evaluate_request_neutral_late_fallback(
        p, base_site_logical_requests=2
    )
    assert out is marker
    assert result["m12_candidate_attempted"] is False
    assert result["m12_strategy"] == "preserve_h1g_no_m12_candidate"
