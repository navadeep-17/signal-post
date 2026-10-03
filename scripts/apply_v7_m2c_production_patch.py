from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one patch target, found {count}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


# 1. Pure zero-network extraction from an already-fetched exact-company homepage.
(ROOT / "src/norway_company_agent/homepage_careers_signal.py").write_text(
    '''from __future__ import annotations

import re
import urllib.parse
from typing import Any

from bs4 import BeautifulSoup

from .website import _registered_domain

CAREERS_TERMS = (
    "career",
    "careers",
    "join our team",
    "work with us",
    "job opportunities",
    "karriere",
    "jobb hos oss",
    "jobbe hos oss",
    "ledige stillinger",
    "stillinger",
    "vacancies",
    "vacancy",
)


def _same_registered_domain(left: str, right: str) -> bool:
    try:
        a = _registered_domain(left)
        b = _registered_domain(right)
    except Exception:
        return False
    return bool(a and b and a == b)


def extract_careers_links(
    *,
    verified_url: str,
    final_url: str,
    soup: BeautifulSoup,
    homepage_content_sha256: str,
) -> list[dict[str, Any]]:
    """Return explicit same-domain careers surfaces declared by a verified homepage.

    This is a narrow hiring-presence signal only. It never claims an active vacancy and
    never follows or fetches the careers link. External ATS/job-board links are excluded.
    """
    if not _same_registered_domain(final_url, verified_url):
        return []

    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for anchor in soup.select("a[href]"):
        href = str(anchor.get("href") or "").strip()
        if not href:
            continue
        absolute = urllib.parse.urljoin(final_url, href)
        try:
            parsed = urllib.parse.urlparse(absolute)
        except ValueError:
            continue
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            continue
        normalized = urllib.parse.urlunparse(
            (parsed.scheme, parsed.netloc, parsed.path or "/", "", parsed.query, "")
        )
        if normalized in seen or not _same_registered_domain(normalized, verified_url):
            continue
        anchor_text = " ".join(anchor.get_text(" ", strip=True).split())
        haystack = urllib.parse.unquote(f"{parsed.path} {anchor_text}").casefold()
        marker = next(
            (term for term in CAREERS_TERMS if re.search(re.escape(term), haystack, re.IGNORECASE)),
            None,
        )
        if not marker:
            continue
        seen.add(normalized)
        rows.append(
            {
                "url": normalized,
                "anchor_text": anchor_text[:240],
                "marker": marker,
                "homepage_url": final_url,
                "homepage_content_sha256": homepage_content_sha256,
                "evidence_span": f"Homepage link: {anchor_text or normalized}"[:500],
                "claim_scope": (
                    "Exact verified company homepage explicitly links to a same-domain careers/hiring surface. "
                    "This is a hiring-presence signal only and does not assert an active vacancy."
                ),
            }
        )
    rows.sort(key=lambda item: (len(urllib.parse.urlparse(item["url"]).path), item["url"]))
    return rows[:4]
''',
    encoding="utf-8",
)

# 2. Preserve the explicit careers links while the already-budgeted homepage HTML is in memory.
replace_once(
    "src/norway_company_agent/final_site_discovery.py",
    "from .evidence import evidence\n",
    "from .evidence import evidence\nfrom .homepage_careers_signal import extract_careers_links\n",
)
replace_once(
    "src/norway_company_agent/final_site_discovery.py",
    '''            "social_links": _social_links(final_url, soup),\n            "structured_organisations": _jsonld_organisations(structured),\n''',
    '''            "social_links": _social_links(final_url, soup),\n            "careers_links": extract_careers_links(\n                verified_url=final_url,\n                final_url=final_url,\n                soup=soup,\n                homepage_content_sha256=digest,\n            ),\n            "structured_organisations": _jsonld_organisations(structured),\n''',
)

# 3. Project narrow careers-page claims from exact company-owned homepage evidence.
replace_once(
    "src/norway_company_agent/output_contract.py",
    '''    social_links = value.get("social_links") or []\n    if social_links:\n        _add_claim(\n            claims,\n            evidence_entries,\n            org=org,\n            evidence_key="website",\n            record=record,\n            field="social_links",\n            value=social_links,\n            availability="available",\n            claim_span=f"Verified social links published on {final_url}",\n        )\n''',
    '''    social_links = value.get("social_links") or []\n    if social_links:\n        _add_claim(\n            claims,\n            evidence_entries,\n            org=org,\n            evidence_key="website",\n            record=record,\n            field="social_links",\n            value=social_links,\n            availability="available",\n            claim_span=f"Verified social links published on {final_url}",\n        )\n\n    for ordinal, careers in enumerate(value.get("careers_links") or []):\n        if not isinstance(careers, dict):\n            continue\n        careers_url = str(careers.get("url") or "").strip()\n        if not careers_url:\n            continue\n        _add_claim(\n            claims,\n            evidence_entries,\n            org=org,\n            evidence_key=f"website:careers:{ordinal}",\n            record=record,\n            field="external.careers_page",\n            value={\n                "url": careers_url,\n                "anchor_text": str(careers.get("anchor_text") or "").strip() or None,\n            },\n            availability="available",\n            claim_span=str(careers.get("evidence_span") or f"Homepage careers link: {careers_url}"),\n            extra={\n                "platform": "company_site",\n                "signal_type": "careers_page",\n                "claim_scope": str(careers.get("claim_scope") or ""),\n            },\n        )\n''',
)

# 4. Canonicalize careers presence distinctly from a concrete job posting.
replace_once(
    "src/norway_company_agent/canonical_projection.py",
    '''    "social_profile": "public.social_profile",\n    "job_posting": "hiring.job_posting",\n''',
    '''    "social_profile": "public.social_profile",\n    "careers_page": "hiring.careers_page",\n    "job_posting": "hiring.job_posting",\n''',
)
replace_once(
    "src/norway_company_agent/canonical_projection.py",
    '''    for claim in index.get("external.job_posting") or []:\n        facts.append(_fact("job_posting", claim))\n''',
    '''    for claim in index.get("external.careers_page") or []:\n        facts.append(_fact("careers_page", claim))\n    for claim in index.get("external.job_posting") or []:\n        facts.append(_fact("job_posting", claim))\n''',
)
replace_once(
    "src/norway_company_agent/canonical_projection.py",
    '''        "company_website": [item for item in facts if item["type"] in website_keys],\n        "jobs": [item for item in facts if item["type"] == "job_posting"],\n        "public_activity": [item for item in facts if item["type"] in activity_keys],\n''',
    '''        "company_website": [item for item in facts if item["type"] in website_keys],\n        "hiring_signals": [item for item in facts if item["type"] == "careers_page"],\n        "jobs": [item for item in facts if item["type"] == "job_posting"],\n        "public_activity": [item for item in facts if item["type"] in activity_keys],\n''',
)
replace_once(
    "src/norway_company_agent/canonical_projection.py",
    '''            item.get("availability") == "available"\n            for item in (canonical["jobs"] + canonical["public_activity"])\n''',
    '''            item.get("availability") == "available"\n            for item in (canonical["hiring_signals"] + canonical["jobs"] + canonical["public_activity"])\n''',
)
replace_once(
    "src/norway_company_agent/canonical_projection.py",
    '''    for key in ("company_record", "financials", "people", "locations", "company_website", "jobs", "public_activity"):\n''',
    '''    for key in ("company_record", "financials", "people", "locations", "company_website", "hiring_signals", "jobs", "public_activity"):\n''',
)

# 5. Make the deterministic synthesis distinguish hiring presence from a concrete vacancy.
replace_once(
    "src/norway_company_agent/synthesis.py",
    '''    website = _first(contract, "website")\n    jobs = _facts_by_type(contract, "job_posting")\n''',
    '''    website = _first(contract, "website")\n    careers_pages = _facts_by_type(contract, "careers_page")\n    jobs = _facts_by_type(contract, "job_posting")\n''',
)
replace_once(
    "src/norway_company_agent/synthesis.py",
    '''    if jobs:\n        external_bits.append(f"Strict job postings published: {len(jobs)}.")\n        external_facts.extend(jobs)\n    else:\n        external_bits.append("No strict job posting is published for this run.")\n''',
    '''    if careers_pages:\n        external_bits.append(f"Verified company-owned careers surfaces published: {len(careers_pages)}.")\n        external_facts.extend(careers_pages)\n    if jobs:\n        external_bits.append(f"Strict job postings published: {len(jobs)}.")\n        external_facts.extend(jobs)\n    else:\n        external_bits.append("No specific active job posting is independently verified for this run.")\n''',
)
replace_once(
    "src/norway_company_agent/synthesis.py",
    '''    if not jobs:\n        unknowns.append("No strict job posting is published.")\n''',
    '''    if not careers_pages and not jobs:\n        unknowns.append("No verified careers surface or strict job posting is published.")\n    elif careers_pages and not jobs:\n        unknowns.append("A verified careers surface is published, but no specific active job posting is independently verified.")\n''',
)
replace_once(
    "src/norway_company_agent/synthesis.py",
    '''    hiring_text = (\n        f"{len(jobs)} strict job posting(s) are published."\n        if jobs\n        else "No strict job posting is published for this run."\n    )\n''',
    '''    if jobs:\n        hiring_text = f"{len(jobs)} strict job posting(s) are published."\n        if careers_pages:\n            hiring_text += f" {len(careers_pages)} verified company-owned careers surface(s) are also published."\n    elif careers_pages:\n        hiring_text = (\n            f"{len(careers_pages)} verified company-owned careers surface(s) are published; "\n            "no specific active job posting is independently verified."\n        )\n    else:\n        hiring_text = "No verified careers surface or strict job posting is published for this run."\n''',
)
replace_once(
    "src/norway_company_agent/synthesis.py",
    '''        "hiring": _decision_item("hiring", hiring_text, jobs, evidence_by_id),\n''',
    '''        "hiring": _decision_item("hiring", hiring_text, [*careers_pages, *jobs], evidence_by_id),\n''',
)

# 6. Focused production regressions: same-domain only, semantic separation, canonical area, synthesis.
(ROOT / "tests/test_v7_m2c_production.py").write_text(
    '''from __future__ import annotations

from bs4 import BeautifulSoup

from norway_company_agent.canonical_projection import project_canonical_profile, validate_canonical_projection
from norway_company_agent.homepage_careers_signal import extract_careers_links
from norway_company_agent.output_contract import project_terminal_envelope, validate_contract_object
from norway_company_agent.synthesis import build_company_synthesis, validate_company_synthesis


def _careers_rows(html: str) -> list[dict]:
    return extract_careers_links(
        verified_url="https://example.no/",
        final_url="https://www.example.no/",
        soup=BeautifulSoup(html, "lxml"),
        homepage_content_sha256="a" * 64,
    )


def test_extracts_explicit_same_domain_careers_surface() -> None:
    rows = _careers_rows('<nav><a href="/om-oss/jobb-hos-oss">Jobb hos oss</a></nav>')
    assert len(rows) == 1
    assert rows[0]["url"] == "https://www.example.no/om-oss/jobb-hos-oss"
    assert "does not assert an active vacancy" in rows[0]["claim_scope"]


def test_rejects_external_ats_as_company_owned_careers_surface() -> None:
    rows = _careers_rows('<a href="https://jobs.vendor.test/example">Careers</a>')
    assert rows == []


def test_careers_surface_projects_without_becoming_job_posting() -> None:
    careers = _careers_rows('<a href="/careers">Careers</a>')
    profile = {
        "organisation_number": "123456789",
        "name": "EXAMPLE AS",
        "run_metrics": {"requests": 0, "latencies_ms": []},
        "evidence": {
            "website": {
                "field": "website",
                "status": "available",
                "source_type": "registry_linked_company_website",
                "source_url": "https://www.example.no/",
                "retrieved_at": "2026-10-03T00:00:00+00:00",
                "content_sha256": "a" * 64,
                "value": {
                    "final_url": "https://www.example.no/",
                    "identity_assessment": {"publishable": True, "score": 0.99},
                    "careers_links": careers,
                },
            }
        },
    }
    envelope = {
        "run_id": "m2c-test",
        "organisation_number": "123456789",
        "state": "complete",
        "started_at": "2026-10-03T00:00:00+00:00",
        "completed_at": "2026-10-03T00:00:01+00:00",
        "profile": profile,
    }
    contract = project_terminal_envelope(envelope)
    assert not validate_contract_object(contract)
    careers_claims = [claim for claim in contract["claims"] if claim.get("field") == "external.careers_page"]
    assert len(careers_claims) == 1
    assert careers_claims[0]["signal_type"] == "careers_page"
    assert careers_claims[0]["value"]["url"] == "https://www.example.no/careers"
    assert not [claim for claim in contract["claims"] if claim.get("field") == "external.job_posting"]

    canonical = project_canonical_profile(contract)
    assert not validate_canonical_projection(canonical)
    careers_facts = [fact for fact in canonical["canonical_facts"] if fact.get("type") == "careers_page"]
    assert len(careers_facts) == 1
    assert careers_facts[0]["canonical_field"] == "hiring.careers_page"
    assert canonical["canonical_profile"]["data_areas"]["hiring_and_public_activity"] is True
    assert canonical["canonical_profile"]["jobs"] == []

    canonical["synthesis"] = build_company_synthesis(canonical)
    assert not validate_company_synthesis(canonical)
    hiring = canonical["synthesis"]["decision_brief"]["hiring"]
    assert "careers surface" in hiring["text"].lower()
    assert "no specific active job posting" in hiring["text"].lower()
    assert hiring["evidence"]
''',
    encoding="utf-8",
)

(ROOT / "docs/V7_M2C_CAREERS_PRODUCTION.md").write_text(
    '''# V7 M2C — verified homepage careers signals\n\n## Purpose\n\nBuilderr's official diagnostic explicitly cited company-owned careers pages as missed hiring signals. M2C publishes a narrow hiring-presence fact from an exact-verified company homepage without claiming that a specific vacancy is open.\n\n## Production boundary\n\n- The company website must already pass the existing exact-company publication gate.\n- Careers discovery happens while the already-budgeted homepage HTML is in memory.\n- Only explicit same-registered-domain careers/hiring links are retained.\n- External ATS/job-board URLs are not represented as company-owned careers pages.\n- No careers URL is fetched by M2C.\n- The claim type is `external.careers_page`; it is never `external.job_posting`.\n- Canonical fact: `hiring.careers_page`.\n- Synthesis says hiring presence is known while explicitly stating when no specific active job is independently verified.\n- Incremental network requests: 0.\n- Third-party API cost: $0.\n\n## Evidence\n\nThe evidence is the exact verified homepage that declared the careers link, including its retrieval timestamp, content hash and bounded link text.\n\n## Promotion evidence\n\nThe preceding experiment (PR #61) transferred to a fresh unseen 100-company cohort with 2 companies exposing exact same-domain careers surfaces and zero wrong-company publications. The production implementation removes the experiment's homepage re-fetch, so discovery uses zero extra requests.\n''',
    encoding="utf-8",
)

print("Applied V7 M2C production patch")
