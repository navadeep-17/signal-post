from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_retained_hiring_signals.py"
spec = importlib.util.spec_from_file_location("audit_retained_hiring_signals", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_vi_soker_with_role_context_is_strong_hiring_signal() -> None:
    text = (
        "Ser du etter nye utfordringer? Vi søker etter talentfulle kuldeteknikere "
        "og mekanikere, samt administrativt personell."
    )
    result = module.hiring_match(text)
    assert result is not None
    assert result["match_type"] == "no_vi_soker"


def test_vi_soker_non_people_object_is_rejected() -> None:
    assert module.hiring_match("Vi søker etter nye leverandører av reservedeler.") is None


def test_negative_openings_are_rejected() -> None:
    assert module.hiring_match("Vi har ingen ledige stillinger akkurat nå.") is None
    assert module.hiring_match("We are not hiring at the moment.") is None


def test_generic_careers_navigation_is_not_active_hiring() -> None:
    assert module.hiring_match("Jobb hos oss") is None
    assert module.hiring_match("Careers") is None


def test_open_positions_is_accepted_without_role_hint() -> None:
    result = module.hiring_match("See our open positions and apply today.")
    assert result is not None
    assert result["match_type"] == "en_open_positions"
