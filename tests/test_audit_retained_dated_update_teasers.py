from __future__ import annotations

import datetime as dt
import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_retained_dated_update_teasers.py"
spec = importlib.util.spec_from_file_location("audit_retained_dated_update_teasers", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def profile(org: str, *, anchor: str, context: str, url: str = "https://example.no/news/item") -> dict:
    return {
        "organisation_number": org,
        "evidence": {
            "website": {
                "status": "available",
                "source_url": "https://example.no/",
                "content_sha256": "a" * 64,
                "value": {
                    "final_url": "https://example.no/",
                    "content_sha256": "a" * 64,
                    "identity_assessment": {"publishable": True},
                    "news_detail_links": [
                        {
                            "url": url,
                            "anchor_text": anchor,
                            "marker": "dated_homepage_card",
                            "dated_context": context,
                            "homepage_content_sha256": "a" * 64,
                        }
                    ],
                },
            }
        },
    }


def contract(org: str, *, existing: bool = False) -> dict:
    claims = []
    if existing:
        claims.append(
            {
                "field": "external.company_update",
                "availability": "available",
                "value": {"title": "Existing"},
            }
        )
    return {"organisation_number": org, "claims": claims}


def test_strict_card_requires_specific_anchor_and_unique_recent_date() -> None:
    profiles = [
        profile(
            "111111111",
            anchor="Ny fabrikk åpner i Bergen",
            context="03.06.26 Ny fabrikk åpner i Bergen Les mer",
        ),
        profile(
            "222222222",
            anchor="Les mer",
            context="04.06.26 Vi lanserer nytt produkt Les mer",
        ),
        profile(
            "333333333",
            anchor="Ny avtale inngått med kunde",
            context="03.06.26 Ny avtale inngått. Oppdatert 04.06.26",
        ),
        profile(
            "444444444",
            anchor="Ny investering i produksjon",
            context="03.06.24 Ny investering i produksjon",
        ),
    ]
    contracts = [contract(x["organisation_number"]) for x in profiles]
    result = module.audit(
        profiles,
        contracts,
        as_of=dt.date(2026, 10, 6),
        lookback_days=365,
    )
    assert result["strict_specific_headline_dated_card_companies"] == 1
    assert result["generic_anchor_only_companies"] == 1
    assert result["ambiguous_or_unparsed_date_links"] == 1
    assert result["out_of_window_links"] == 1


def test_existing_update_is_not_net_new() -> None:
    profiles = [
        profile(
            "111111111",
            anchor="Ny fabrikk åpner i Bergen",
            context="03.06.26 Ny fabrikk åpner i Bergen",
        )
    ]
    result = module.audit(
        profiles,
        [contract("111111111", existing=True)],
        as_of=dt.date(2026, 10, 6),
        lookback_days=365,
    )
    assert result["strict_specific_headline_dated_card_companies"] == 1
    assert result["strict_net_new_dated_update_teaser_companies"] == 0


def test_cross_domain_card_is_rejected() -> None:
    profiles = [
        profile(
            "111111111",
            anchor="Ny fabrikk åpner i Bergen",
            context="03.06.26 Ny fabrikk åpner i Bergen",
            url="https://other.no/news/item",
        )
    ]
    result = module.audit(
        profiles,
        [contract("111111111")],
        as_of=dt.date(2026, 10, 6),
        lookback_days=365,
    )
    assert result["cross_domain_links_rejected"] == 1
    assert result["strict_specific_headline_dated_card_companies"] == 0
