from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_bil_sports_club_classifier.py"
spec = importlib.util.spec_from_file_location("audit_bil_sports_club_classifier", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def profile(name: str, activity: str = "", purpose: str = "") -> dict:
    return {
        "organisation_number": "999999999",
        "name": name,
        "evidence": {
            "registry": {
                "value": {
                    "aktivitet": activity,
                    "vedtektsfestetFormaal": purpose,
                }
            }
        },
    }


def test_old_classifier_misreads_plain_bil_but_corrected_does_not():
    row = profile("BRANDSRUD BIL AS")
    report = module.audit([row] * 1000)
    assert report["old_classifier_positive_companies"] == 1000
    assert report["corrected_classifier_positive_companies"] == 0
    assert report["old_only_plain_bil_companies"] == 1000
    assert report["old_only_bil_as_companies"] == 1000


def test_corrected_classifier_preserves_explicit_b_i_l():
    row = profile("ACME B.I.L.")
    assert module.OLD_RE.search(row["name"])
    from norway_company_agent.identity import _is_business_sports_club
    assert _is_business_sports_club(row) is True


def test_corrected_classifier_preserves_plain_bil_with_registry_sports_context():
    row = profile("ACME BIL", activity="Bedriftsidrettslag for ansatte")
    from norway_company_agent.identity import _is_business_sports_club
    assert _is_business_sports_club(row) is True
