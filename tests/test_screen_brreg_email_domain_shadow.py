from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "screen_brreg_email_domain_shadow.py"
spec = importlib.util.spec_from_file_location("screen_brreg_email_domain_shadow", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_phone_match_requires_registry_phone():
    raw = {"telefon": "12 34 56 78"}
    website = {
        "value": {
            "title": "Example",
            "description": "Kontakt oss på 12 34 56 78",
            "main_text_excerpt": "",
            "identity_text_excerpt": "",
            "structured_organisations": [],
            "pages": [],
        }
    }
    assert module._page_has_phone(website, raw)
    assert not module._page_has_phone(website, {"telefon": "87 65 43 21"})


def test_strong_address_requires_postcode_and_street_token():
    raw = {
        "forretningsadresse.postnummer": "0123",
        "forretningsadresse.adresse": ["Eksempelgata 14"],
    }
    website = {
        "value": {
            "title": "",
            "description": "",
            "main_text_excerpt": "Besøk oss i Eksempelgata 14, 0123 Oslo.",
            "identity_text_excerpt": "",
            "structured_organisations": [],
            "pages": [],
        }
    }
    assert module._page_has_strong_address(website, raw)
    website["value"]["main_text_excerpt"] = "Vi holder til i Oslo 0123."
    assert not module._page_has_strong_address(website, raw)


def test_email_domain_selection_uses_strongest_candidate():
    profiles = {
        "123456789": {
            "organisation_number": "123456789",
            "name": "EXAMPLE BEDRIFT AS",
            "evidence": {
                "registry": {
                    "value": {
                        "epostadresse": "post@random-host.no;hei@examplebedrift.no"
                    }
                }
            },
        }
    }
    rows = module.candidate_rows(profiles, set())
    assert len(rows) == 1
    assert rows[0][2] == "examplebedrift.no"
    assert rows[0][3] == "exact"
