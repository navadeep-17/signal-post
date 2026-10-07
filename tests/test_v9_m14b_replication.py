from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

spec=importlib.util.spec_from_file_location(
    "m14b_builder", ROOT/"scripts"/"build_v9_m14b_replication_cohort.py"
)
assert spec and spec.loader
m14b=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m14b)


def test_replication_builder_module_loads_and_uses_frozen_m14_builder():
    assert m14b.M14.PR137_GATE_A_SHA256 == (
        "f2177abd0bd0d6202f9fe47fd00b8def06b21c01fdf4c864c1f3b68f80b160d5"
    )
    assert "811413682" in m14b.M14.BUILDERR_PUBLIC_PRACTICE_ORGS
    assert "828829092" in m14b.M14.M12_RESEARCHED_ORGS
