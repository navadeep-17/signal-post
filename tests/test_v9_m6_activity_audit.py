from __future__ import annotations

from pathlib import Path
import importlib.util


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_v9_m6_activity.py"
spec = importlib.util.spec_from_file_location("audit_v9_m6_activity", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def row(org: str, claims=None, evidence=None):
    return {
        "organisation_number": org,
        "claims": claims or [],
        "evidence": evidence or [],
    }


def update_claim(eid: str, *, date_value: str = "2026-09-10"):
    return {
        "field": "external.company_update",
        "availability": "available",
        "value": {
            "title": "Specific company update",
            "url": "https://example.no/news/update",
            "published_date": date_value,
        },
        "evidence_ids": [eid],
        "claim_scope": "fixture",
    }


def feed_evidence(eid: str):
    return {
        "id": eid,
        "source_url": "https://example.no/news/rss.xml",
        "retrieved_at": "2026-10-06T10:00:00Z",
        "effective_at": "2026-09-10",
        "content_sha256": "a" * 64,
        "claim_span": "Specific company update; published date 2026-09-10",
        "identity_proof": {"publishable": True},
        "extraction_method": "verified_same_site_rss_atom_entry_v1",
    }


def test_accepts_strict_same_site_feed_publication() -> None:
    report, manual = module.audit(
        [row("111111111")],
        [row("111111111", [update_claim("e1")], [feed_evidence("e1")])],
    )
    assert report["net_new_dated_activity_companies"] == 1
    assert report["lost_activity_publications"] == 0
    assert report["all_new_evidence_strict"] is True
    assert manual[0]["evidence_complete_and_strict"] is True


def test_rejects_sitemap_timestamp_as_publication_date() -> None:
    evidence = feed_evidence("e1")
    evidence["extraction_method"] = "sitemap_lastmod"
    report, manual = module.audit(
        [row("111111111")],
        [row("111111111", [update_claim("e1")], [evidence])],
    )
    assert report["all_new_evidence_strict"] is False
    assert manual[0]["evidence_checks"][0]["not_sitemap_or_index_timestamp"] is False


def test_future_date_is_not_strict() -> None:
    evidence = feed_evidence("e1")
    evidence["effective_at"] = "2026-10-07"
    report, manual = module.audit(
        [row("111111111")],
        [row("111111111", [update_claim("e1", date_value="2026-10-07")], [evidence])],
    )
    assert report["all_new_evidence_strict"] is False
    assert manual[0]["evidence_checks"][0]["not_future_vs_retrieval"] is False
