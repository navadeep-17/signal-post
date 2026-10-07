from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

spec = importlib.util.spec_from_file_location(
    "m13b_builder", ROOT / "scripts" / "build_v9_m13b_replacement_cohort.py"
)
assert spec and spec.loader
m13b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m13b)


def test_builder_pins_public_practice_exclusions() -> None:
    assert m13b.BUILDERR_PUBLIC_PRACTICE_ORGS == {
        "811413682",
        "811730912",
        "883971752",
        "923609016",
    }


def test_builder_reuses_frozen_m13_selector_contract() -> None:
    assert m13b.M13.PR137_GATE_A_SHA256 == (
        "f2177abd0bd0d6202f9fe47fd00b8def06b21c01fdf4c864c1f3b68f80b160d5"
    )
    assert m13b.M13.M10_POSITIVE_CANARIES == {
        "927097532",
        "979943377",
        "999096298",
    }
    assert "828829092" in m13b.M13.M12_RESEARCHED_ORGS
