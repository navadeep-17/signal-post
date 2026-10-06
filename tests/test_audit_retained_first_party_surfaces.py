from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_retained_first_party_surfaces.py"
spec = importlib.util.spec_from_file_location("audit_retained_first_party_surfaces", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def profile(pages):
    return {
        "organisation_number": "999999999",
        "evidence": {
            "website": {
                "status": "available",
                "source_url": "https://example.no/",
                "value": {
                    "final_url": "https://example.no/",
                    "identity_assessment": {"publishable": True},
                    "pages": pages,
                },
            }
        },
    }


def page(url, title):
    return {"url": url, "title": title, "content_sha256": "a" * 64, "main_text_excerpt": ""}


def test_retained_careers_page_requires_same_company_and_explicit_marker():
    p = profile([
        page("https://example.no/", "Example"),
        page("https://example.no/karriere/", "Karriere"),
        page("https://jobs.example.no/ledige-stillinger/", "Ledige stillinger"),
        page("https://other.no/careers/", "Careers"),
        page("https://example.no/news/jobs-are-growing/", "News"),
    ])
    rows = module.retained_careers_pages(p)
    assert [r["url"] for r in rows] == [
        "https://example.no/karriere/",
        "https://jobs.example.no/ledige-stillinger/",
    ]


def test_career_marker_accepts_explicit_title_when_path_is_neutral():
    assert module._career_marker("https://example.no/people/", "Work with us") == "title:work with us"
    assert module._career_marker("https://example.no/news/", "Company news") is None
