from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "replay_jsonld_phone_recovery.py"
spec = importlib.util.spec_from_file_location("replay_jsonld_phone_recovery", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_any_phone_coverage_includes_registry_and_external() -> None:
    assert module.any_phone_coverage({
        "claims": [{"field": "registered_phone", "availability": "available", "value": "22334455"}]
    })
    assert module.any_phone_coverage({
        "claims": [{"field": "registered_mobile", "availability": "available", "value": "99887766"}]
    })
    assert module.any_phone_coverage({
        "claims": [{"field": "external.contact_phone", "availability": "available", "value": "+4799887766"}]
    })
    assert not module.any_phone_coverage({"claims": []})
