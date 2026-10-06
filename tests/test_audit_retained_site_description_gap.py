from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_retained_site_description_gap.py"
spec = importlib.util.spec_from_file_location("audit_retained_site_description_gap", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _profile(org: str, desc: str, publishable: bool = True) -> dict:
    return {
        "organisation_number": org,
        "name": "EXAMPLE COMPANY AS",
        "evidence": {
            "website": {
                "status": "available",
                "value": {
                    "description": desc,
                    "extraction_state": "static_complete",
                    "identity_assessment": {
                        "publishable": publishable,
                        "score": 1.0,
                        "method": "exact_test",
                    },
                },
            }
        },
    }


def test_gap_requires_exact_site_retained_description_and_missing_claim() -> None:
    profiles = [
        _profile("111111111", "Example Company leverer programvare til norske bedrifter."),
        _profile("222222222", ""),
        _profile("333333333", "Wrong candidate should not count.", publishable=False),
    ]
    outputs = {
        "111111111": {"claims": []},
        "222222222": {"claims": []},
        "333333333": {"claims": []},
    }
    report, rows = module.audit(profiles, outputs)
    assert report["exact_verified_site_companies"] == 2
    assert report["exact_sites_with_retained_meta_description"] == 1
    assert report["net_new_retained_description_candidate_companies"] == 1
    assert len(rows) == 1
    assert rows[0]["raw_description_retained"] is False
    assert "leverer programvare" not in repr(report)
    assert "leverer programvare" not in repr(rows)
