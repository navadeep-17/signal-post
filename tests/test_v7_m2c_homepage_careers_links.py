from __future__ import annotations

from norway_company_agent.homepage_careers_links import extract_careers_links


def test_extracts_same_domain_careers_link_from_verified_homepage_html() -> None:
    raw = b"""
    <html><body>
      <nav>
        <a href="/about">About</a>
        <a href="/careers">Careers</a>
      </nav>
    </body></html>
    """
    rows = extract_careers_links(
        verified_url="https://example.no/",
        final_url="https://www.example.no/",
        raw=raw,
        content_type="text/html",
    )
    assert len(rows) == 1
    assert rows[0]["url"] == "https://www.example.no/careers"
    assert rows[0]["marker"] == "career"
    assert rows[0]["anchor_text"] == "Careers"
    assert len(rows[0]["homepage_content_sha256"]) == 64
    assert "does not assert an active vacancy" in rows[0]["claim_scope"]


def test_extracts_localized_careers_link_without_fixed_path_guessing() -> None:
    raw = b"""
    <html><body><a href="/om-oss/jobb-hos-oss">Jobb hos oss</a></body></html>
    """
    rows = extract_careers_links(
        verified_url="https://example.no/",
        final_url="https://example.no/",
        raw=raw,
        content_type="text/html",
    )
    assert len(rows) == 1
    assert rows[0]["url"] == "https://example.no/om-oss/jobb-hos-oss"


def test_rejects_external_job_board_link_as_company_owned_careers_signal() -> None:
    raw = b"""
    <html><body><a href="https://jobs.vendor.example/careers/example">Careers</a></body></html>
    """
    assert extract_careers_links(
        verified_url="https://example.no/",
        final_url="https://example.no/",
        raw=raw,
        content_type="text/html",
    ) == []


def test_rejects_non_hiring_navigation_link() -> None:
    raw = b"<html><body><a href='/contact'>Contact</a></body></html>"
    assert extract_careers_links(
        verified_url="https://example.no/",
        final_url="https://example.no/",
        raw=raw,
        content_type="text/html",
    ) == []
