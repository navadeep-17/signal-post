from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.first_party_updates import qualify_first_party_update


def article_html(*, title="New regional grid project", published="2026-09-30", include_article=True):
    body = "<article><h1>{}</h1><p>Company-specific update text with enough substance for bounded evidence.</p></article>".format(title) if include_article else ""
    return f"""<html><head>
      <meta property='og:title' content='{title}'>
      <meta property='article:published_time' content='{published}'>
    </head><body>{body}</body></html>"""


def test_specific_dated_first_party_article_is_publishable():
    row = qualify_first_party_update(
        verified_company_url="https://example.no/",
        page_url="https://example.no/nyheter/new-regional-grid-project",
        html=article_html(),
        content_sha256="a" * 64,
        as_of=date(2026, 10, 3),
    )
    assert row["status"] == "exact_dated_update"
    assert row["publishable"] is True
    assert row["title"] == "New regional grid project"
    assert row["date_published"] == "2026-09-30"
    assert row["date_method"] == "meta_article_published_time"
    assert "Company-specific update text" in row["evidence_span"]


def test_jsonld_date_and_headline_are_preferred_when_page_url_matches():
    html = """<html><body><article><p>Detailed first-party article.</p></article>
    <script type='application/ld+json'>
    {"@type":"NewsArticle","headline":"JSON-LD company update","url":"https://example.no/aktuelt/json-update","datePublished":"2026-10-01T08:30:00+02:00"}
    </script></body></html>"""
    row = qualify_first_party_update(
        verified_company_url="https://example.no/",
        page_url="https://example.no/aktuelt/json-update",
        html=html,
        content_sha256="b" * 64,
        as_of=date(2026, 10, 3),
    )
    assert row["publishable"] is True
    assert row["title"] == "JSON-LD company update"
    assert row["date_published"] == "2026-10-01"
    assert row["date_method"] == "jsonld_article"


def test_sitemap_or_archive_surface_is_never_an_update_by_itself():
    row = qualify_first_party_update(
        verified_company_url="https://example.no/",
        page_url="https://example.no/nyheter",
        html=article_html(title="Nyheter"),
        content_sha256="c" * 64,
        as_of=date(2026, 10, 3),
    )
    assert row["status"] == "rejected"
    assert row["publishable"] is False


def test_locale_plus_archive_surface_is_rejected():
    row = qualify_first_party_update(
        verified_company_url="https://example.no/",
        page_url="https://example.no/nb/aktuelt",
        html=article_html(title="Aktuelt"),
        content_sha256="c" * 64,
        as_of=date(2026, 10, 3),
    )
    assert row["status"] == "rejected"


def test_cross_company_domain_is_rejected_even_with_good_metadata():
    row = qualify_first_party_update(
        verified_company_url="https://example.no/",
        page_url="https://other.no/news/update",
        html=article_html(),
        content_sha256="d" * 64,
        as_of=date(2026, 10, 3),
    )
    assert row["status"] == "rejected"
    assert row["publishable"] is False


def test_missing_page_level_publication_date_stays_review_only():
    html = "<html><body><article><h1>Specific company update</h1><p>Detailed first-party text.</p></article></body></html>"
    row = qualify_first_party_update(
        verified_company_url="https://example.no/",
        page_url="https://example.no/news/specific-company-update",
        html=html,
        content_sha256="e" * 64,
        as_of=date(2026, 10, 3),
    )
    assert row["status"] == "review"
    assert row["publishable"] is False
    assert row["date_published"] is None


def test_sitemap_lastmod_cannot_be_supplied_to_qualifier_as_publication_date():
    html = "<html><body><article><h1>Specific update without date</h1><p>Text.</p></article></body></html>"
    row = qualify_first_party_update(
        verified_company_url="https://example.no/",
        page_url="https://example.no/nyheter/update-with-sitemap-lastmod-only",
        html=html,
        content_sha256="f" * 64,
        as_of=date(2026, 10, 3),
    )
    assert row["publishable"] is False
    assert "publication date" in row["reasons"][0]


def test_future_publication_date_is_rejected():
    row = qualify_first_party_update(
        verified_company_url="https://example.no/",
        page_url="https://example.no/news/future-update",
        html=article_html(published="2026-10-04"),
        content_sha256="1" * 64,
        as_of=date(2026, 10, 3),
    )
    assert row["status"] == "rejected"
    assert row["publishable"] is False


def test_optional_age_limit_marks_old_article_stale_not_false_negative():
    row = qualify_first_party_update(
        verified_company_url="https://example.no/",
        page_url="https://example.no/news/old-specific-update",
        html=article_html(published="2024-01-01"),
        content_sha256="2" * 64,
        as_of=date(2026, 10, 3),
        max_age_days=365,
    )
    assert row["status"] == "stale"
    assert row["publishable"] is False


def test_generic_title_is_rejected_even_on_specific_path():
    row = qualify_first_party_update(
        verified_company_url="https://example.no/",
        page_url="https://example.no/news/archive-landing",
        html=article_html(title="News"),
        content_sha256="3" * 64,
        as_of=date(2026, 10, 3),
    )
    assert row["status"] == "rejected"
    assert row["publishable"] is False


def test_bounded_article_text_is_required():
    row = qualify_first_party_update(
        verified_company_url="https://example.no/",
        page_url="https://example.no/news/metadata-only-update",
        html=article_html(include_article=False),
        content_sha256="4" * 64,
        as_of=date(2026, 10, 3),
    )
    assert row["status"] == "review"
    assert row["publishable"] is False


def test_missing_content_hash_is_rejected():
    row = qualify_first_party_update(
        verified_company_url="https://example.no/",
        page_url="https://example.no/news/update",
        html=article_html(),
        content_sha256="short",
        as_of=date(2026, 10, 3),
    )
    assert row["status"] == "rejected"
