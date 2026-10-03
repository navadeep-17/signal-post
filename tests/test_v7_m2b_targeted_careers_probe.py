from __future__ import annotations

from norway_company_agent.targeted_careers_probe import qualify_careers_html


def test_qualifies_same_domain_careers_page_without_claiming_open_job() -> None:
    raw = b"""
    <html><head><title>Careers | Example AS</title></head>
    <body><main><h1>Careers</h1><p>Join our team and build the future with us.</p></main></body></html>
    """
    fact = qualify_careers_html(
        verified_url="https://example.no/",
        final_url="https://www.example.no/careers",
        raw=raw,
        content_type="text/html; charset=utf-8",
    )
    assert fact is not None
    assert fact["url"] == "https://www.example.no/careers"
    assert fact["marker"] == "careers"
    assert len(fact["content_sha256"]) == 64
    assert "does not assert any active vacancy" in fact["claim_scope"]


def test_rejects_unrelated_same_domain_page_without_hiring_language() -> None:
    raw = b"<html><head><title>About Example AS</title></head><body>Our history and products.</body></html>"
    assert qualify_careers_html(
        verified_url="https://example.no/",
        final_url="https://example.no/careers",
        raw=raw,
        content_type="text/html",
    ) is None


def test_rejects_redirect_outside_verified_registered_domain() -> None:
    raw = b"<html><head><title>Careers</title></head><body>Join our team.</body></html>"
    assert qualify_careers_html(
        verified_url="https://example.no/",
        final_url="https://jobs.example-evil.no/careers",
        raw=raw,
        content_type="text/html",
    ) is None


def test_rejects_non_html_response() -> None:
    assert qualify_careers_html(
        verified_url="https://example.no/",
        final_url="https://example.no/careers",
        raw=b"{}",
        content_type="application/json",
    ) is None
