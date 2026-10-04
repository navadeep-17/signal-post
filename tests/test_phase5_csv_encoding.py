from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "normalize_phase5_csv_encoding.py"
spec = importlib.util.spec_from_file_location("normalize_phase5_csv_encoding", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

detect_encoding = module.detect_encoding
normalize_csv = module.normalize_csv


def test_detects_and_normalizes_utf16le_export(tmp_path: Path):
    source = tmp_path / "source.csv"
    target = tmp_path / "normalized.csv"
    text = 'Støttetiltaksnummer;"Organisasjonsnummer støttemottaker"\n100;974760673\n'
    source.write_bytes(text.encode("utf-16-le"))

    assert detect_encoding(source.read_bytes()) == "utf-16-le"
    used = normalize_csv(source, target)

    assert used == "utf-16-le"
    assert target.read_text(encoding="utf-8") == text


def test_utf8_export_is_left_semantically_unchanged(tmp_path: Path):
    source = tmp_path / "source.csv"
    target = tmp_path / "normalized.csv"
    text = "organisation_number,value\n974760673,1\n"
    source.write_text(text, encoding="utf-8")

    assert detect_encoding(source.read_bytes()) == "utf-8-sig"
    normalize_csv(source, target)
    assert target.read_text(encoding="utf-8") == text
