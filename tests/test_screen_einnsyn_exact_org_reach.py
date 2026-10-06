from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "screen_einnsyn_exact_org_reach.py"
spec = importlib.util.spec_from_file_location("screen_einnsyn_exact_org_reach", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_exact_org_must_be_in_public_title() -> None:
    assert module.title_has_exact_org(
        {"offentligTittel": "Sak om Equinor ASA org.nr. 923609016"},
        "923609016",
    )
    assert not module.title_has_exact_org(
        {"offentligTittel": "Sak om Equinor ASA"},
        "923609016",
    )
    assert not module.title_has_exact_org(
        {"offentligTittel": "Sak 19236090168"},
        "923609016",
    )


def test_public_date_priority() -> None:
    assert module.public_date({
        "publisertDato": "2026-09-01T10:00:00Z",
        "journaldato": "2026-08-30",
    }) == "2026-09-01T10:00:00Z"
    assert module.public_date({"journaldato": "2026-08-30"}) == "2026-08-30"
    assert module.public_date({}) is None


def test_norm_org() -> None:
    assert module.norm_org("923 609 016") == "923609016"
    assert module.norm_org("123") is None
