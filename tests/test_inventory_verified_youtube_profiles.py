from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "inventory_verified_youtube_profiles.py"
spec = importlib.util.spec_from_file_location("inventory_verified_youtube_profiles", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_classify_youtube_urls() -> None:
    kind, direct = module.classify_youtube_url(
        "https://www.youtube.com/channel/UCabcdefghijklmnopqrstuv"
    )
    assert kind == "channel_id"
    assert direct is True

    assert module.classify_youtube_url("https://youtube.com/@company")[0] == "handle"
    assert module.classify_youtube_url("https://youtube.com/user/company")[0] == "legacy_user"
    assert module.classify_youtube_url("https://youtube.com/c/company")[0] == "custom_channel"
    assert module.classify_youtube_url("https://example.no/@company")[0] == "non_youtube"
