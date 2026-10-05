import importlib.util
from pathlib import Path
import sys
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "screen_official_activity_sources.py"
spec = importlib.util.spec_from_file_location("source_screen", MODULE_PATH)
source_screen = importlib.util.module_from_spec(spec)
sys.modules["source_screen"] = source_screen
assert spec.loader is not None
spec.loader.exec_module(source_screen)


class PatentstyretScreenTests(unittest.TestCase):
    def test_exact_org_case_is_kept(self):
        payload = {
            "cases": [
                {
                    "applicationNumber": "202400356",
                    "registrationNumber": "1771018",
                    "caseUrl": "https://services.patentstyret.no/search-details/Trademark/202400356",
                    "applicationDate": "2024-01-11",
                    "holder": {"partyIdentifier": "912355683"},
                }
            ]
        }
        rows = source_screen.extract_patentstyret_cases(payload, "912355683")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["organisation_number"], "912355683")

    def test_conflicting_org_response_is_rejected(self):
        payload = {
            "cases": [
                {
                    "applicationNumber": "202400356",
                    "caseUrl": "https://example.test/case",
                    "holder": {"partyIdentifier": "999999999"},
                }
            ]
        }
        self.assertEqual(source_screen.extract_patentstyret_cases(payload, "912355683"), [])

    def test_case_for_other_org_is_not_inherited(self):
        payload = {
            "cases": [
                {
                    "applicationNumber": "A",
                    "holder": {"partyIdentifier": "912355683"},
                },
                {
                    "applicationNumber": "B",
                    "holder": {"partyIdentifier": "999999999"},
                },
            ]
        }
        rows = source_screen.extract_patentstyret_cases(payload, "912355683")
        self.assertEqual([r["application_number"] for r in rows], ["A"])


class DoffinScreenTests(unittest.TestCase):
    def test_exact_supplier_org_is_kept(self):
        xml = b'''<?xml version="1.0" encoding="UTF-8"?>
        <ContractAwardNotice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
                             xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
          <cbc:ID>2026-100001</cbc:ID>
          <cbc:IssueDate>2026-09-30</cbc:IssueDate>
          <cac:TenderingParty>
            <cac:TendererParty>
              <cac:Party>
                <cac:PartyIdentification><cbc:ID schemeID="NO:ORGNR">912355683</cbc:ID></cac:PartyIdentification>
              </cac:Party>
            </cac:TendererParty>
          </cac:TenderingParty>
        </ContractAwardNotice>'''
        rows = source_screen.extract_doffin_exact_supplier_hits(xml, "912355683")
        self.assertTrue(rows)
        self.assertEqual(rows[0]["organisation_number"], "912355683")

    def test_buyer_or_unscoped_org_is_not_treated_as_supplier(self):
        xml = b'''<?xml version="1.0" encoding="UTF-8"?>
        <ContractAwardNotice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
                             xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
          <cbc:ID>2026-100002</cbc:ID>
          <cac:ContractingParty>
            <cac:Party><cbc:EndpointID schemeID="NO:ORGNR">912355683</cbc:EndpointID></cac:Party>
          </cac:ContractingParty>
        </ContractAwardNotice>'''
        self.assertEqual(source_screen.extract_doffin_exact_supplier_hits(xml, "912355683"), [])

    def test_wrong_supplier_org_is_rejected(self):
        xml = b'''<Notice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
                           xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
          <cac:TendererParty><cbc:ID>999999999</cbc:ID></cac:TendererParty>
        </Notice>'''
        self.assertEqual(source_screen.extract_doffin_exact_supplier_hits(xml, "912355683"), [])


class ValidationTests(unittest.TestCase):
    def test_orgnr_requires_exactly_nine_digits(self):
        self.assertEqual(source_screen.normalize_orgnr("912 355 683"), "912355683")
        with self.assertRaises(ValueError):
            source_screen.normalize_orgnr("1234")


if __name__ == "__main__":
    unittest.main()
