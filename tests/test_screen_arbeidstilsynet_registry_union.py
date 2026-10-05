from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "screen_arbeidstilsynet_registry_union.py"
spec = importlib.util.spec_from_file_location("screen_arbeidstilsynet_registry_union", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _write_registry(path: Path) -> None:
    path.write_text(
        """<?xml version=\"1.0\" encoding=\"utf-8\"?>
<Register>
  <Metadata><RegisterXSD>RegisterXML6.xsd</RegisterXSD><DatoTidGenerert>2026-10-05T01:00:00+02:00</DatoTidGenerert></Metadata>
  <Registernavn>TEST</Registernavn>
  <Virksomhet>
    <Hovedenhet>
      <Organisasjonsnummer>123456789</Organisasjonsnummer>
      <Navn>TARGET AS</Navn>
    </Hovedenhet>
    <Godkjenningsstatus>Godkjent</Godkjenningsstatus>
    <Kontaktinformasjon>
      <Telefon>11111111</Telefon>
      <Mobil>99999999</Mobil>
      <Webadresse>https://target.example</Webadresse>
      <Epost>post@target.example</Epost>
    </Kontaktinformasjon>
    <Underenheter>
      <Avdeling><Organisasjonsnummer>987654321</Organisasjonsnummer><Navn>TARGET AVD</Navn></Avdeling>
    </Underenheter>
  </Virksomhet>
  <Virksomhet>
    <Hovedenhet>
      <Organisasjonsnummer>555555555</Organisasjonsnummer>
      <Navn>OTHER AS</Navn>
    </Hovedenhet>
    <Godkjenningsstatus>Under behandling</Godkjenningsstatus>
    <Kontaktinformasjon><Webadresse /></Kontaktinformasjon>
    <Underenheter />
  </Virksomhet>
</Register>
""",
        encoding="utf-8",
    )


def test_parse_registry_keeps_main_identity_separate_from_subunits(tmp_path: Path) -> None:
    source = tmp_path / "registry.xml"
    _write_registry(source)
    parsed = module.parse_registry(source, "test")
    assert parsed["source_virksomheter"] == 2
    assert parsed["unique_main_orgs"] == 2
    assert parsed["mains"]["123456789"]["name"] == "TARGET AS"
    assert parsed["mains"]["123456789"]["status"] == "Godkjent"
    assert parsed["mains"]["123456789"]["websites"] == ["https://target.example"]
    assert parsed["mains"]["123456789"]["emails"] == ["post@target.example"]
    assert parsed["mains"]["123456789"]["phones"] == ["11111111", "99999999"]
    assert "987654321" in parsed["subunit_orgs"]
    assert "987654321" not in parsed["mains"]


def test_cohort_metrics_does_not_promote_subunit_only_match(tmp_path: Path) -> None:
    source = tmp_path / "registry.xml"
    _write_registry(source)
    parsed = module.parse_registry(source, "test")
    companies = {
        "123456789": {"organisation_number": "123456789"},
        "987654321": {"organisation_number": "987654321"},
        "111111111": {"organisation_number": "111111111"},
    }
    metrics, union = module.cohort_metrics(companies, [parsed])
    assert metrics["exact_main_union_hits"] == 1
    assert metrics["website_candidate_companies"] == 1
    assert metrics["email_candidate_companies"] == 1
    assert metrics["phone_candidate_companies"] == 1
    assert metrics["subunit_only_target_matches_not_counted"] == 1
    assert metrics["subunit_only_orgs_not_counted"] == ["987654321"]
    assert set(union) == {"123456789"}


def test_read_companies_rejects_non_nine_digit_ids(tmp_path: Path) -> None:
    path = tmp_path / "companies.jsonl"
    path.write_text(json.dumps({"organisation_number": "123"}) + "\n", encoding="utf-8")
    try:
        module.read_companies(path)
    except ValueError as exc:
        assert "exact 9-digit" in str(exc)
    else:
        raise AssertionError("expected invalid organisation number to fail")
