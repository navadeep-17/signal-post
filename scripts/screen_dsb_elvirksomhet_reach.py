#!/usr/bin/env python3
"""Research-only DSB Elvirksomhetsregister exact-legal-entity reach screen.

The DSB workbook contains both Foretaksnr (legal entity) and Bedriftsnr
(subunit). Signalpost target identity is established only by an exact 9-digit
Foretaksnr. Subunit contact fields are retained as observations only and are
never promoted as company-wide contact candidates by this screen.
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ORG_RE = re.compile(r"^\d{9}$")
MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"m": MAIN_NS, "r": REL_NS}


def normalize_org(value: Any) -> str | None:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits if ORG_RE.fullmatch(digits) else None


def load_targets(path: Path) -> set[str]:
    targets: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        org = normalize_org(row.get("organisation_number"))
        if org:
            targets.add(org)
    return targets


def _column_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha()).upper()
    if not letters:
        raise ValueError(f"invalid cell reference: {cell_ref!r}")
    index = 0
    for ch in letters:
        index = index * 26 + (ord(ch) - ord("A") + 1)
    return index - 1


def read_first_sheet_rows(path: Path) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        shared: list[str] = []
        if "xl/sharedStrings.xml" in names:
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for si in root.findall("m:si", NS):
                shared.append("".join(t.text or "" for t in si.iter(f"{{{MAIN_NS}}}t")))

        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        first_sheet = workbook.find(".//m:sheets/m:sheet", NS)
        if first_sheet is None:
            raise ValueError("workbook has no sheets")
        relationship_id = first_sheet.attrib.get(f"{{{REL_NS}}}id")
        if not relationship_id:
            raise ValueError("first sheet has no relationship id")

        relroot = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {rel.attrib["Id"]: rel.attrib["Target"] for rel in relroot}
        raw_target = targets.get(relationship_id)
        if not raw_target:
            raise ValueError("first sheet relationship target missing")
        sheet_path = raw_target.lstrip("/")
        if not sheet_path.startswith("xl/"):
            sheet_path = "xl/" + sheet_path

        sheet = ET.fromstring(archive.read(sheet_path))
        xml_rows = sheet.findall(".//m:sheetData/m:row", NS)
        if not xml_rows:
            return []

        def cell_value(cell: ET.Element) -> str:
            typ = cell.attrib.get("t")
            if typ == "inlineStr":
                return "".join(t.text or "" for t in cell.iter(f"{{{MAIN_NS}}}t"))
            value = cell.find("m:v", NS)
            if value is None:
                return ""
            raw = value.text or ""
            if typ == "s":
                try:
                    return shared[int(raw)]
                except (ValueError, IndexError):
                    return raw
            return raw

        def row_values(row: ET.Element) -> dict[int, str]:
            result: dict[int, str] = {}
            for cell in row.findall("m:c", NS):
                ref = cell.attrib.get("r") or ""
                result[_column_index(ref)] = cell_value(cell).strip()
            return result

        header_values = row_values(xml_rows[0])
        headers = {idx: value for idx, value in header_values.items() if value}
        required = {"Status", "Foretaks-/bedriftsnavn", "Foretaksnr", "Bedriftsnr"}
        missing = required - set(headers.values())
        if missing:
            raise ValueError(f"missing required workbook headers: {sorted(missing)}")

        rows: list[dict[str, str]] = []
        for xml_row in xml_rows[1:]:
            values = row_values(xml_row)
            row = {header: values.get(idx, "") for idx, header in headers.items()}
            if any(value for value in row.values()):
                rows.append(row)
        return rows


def _split_semicolon(value: Any) -> list[str]:
    return sorted({part.strip() for part in str(value or "").split(";") if part.strip()})


def screen(rows: list[dict[str, str]], targets: set[str]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    by_company: dict[str, list[dict[str, str]]] = {}
    all_company_orgs: set[str] = set()
    all_subunit_orgs: set[str] = set()
    malformed_company_numbers = 0
    malformed_subunit_numbers = 0

    for row in rows:
        company_org = normalize_org(row.get("Foretaksnr"))
        if company_org is None:
            malformed_company_numbers += 1
        else:
            all_company_orgs.add(company_org)
            if company_org in targets:
                by_company.setdefault(company_org, []).append(row)

        raw_subunit = row.get("Bedriftsnr")
        if str(raw_subunit or "").strip():
            subunit_org = normalize_org(raw_subunit)
            if subunit_org is None:
                malformed_subunit_numbers += 1
            else:
                all_subunit_orgs.add(subunit_org)

    matched: list[dict[str, Any]] = []
    active_companies = 0
    companies_with_tasks = 0
    companies_with_scope = 0
    companies_with_email_observations = 0
    companies_with_phone_observations = 0

    for org in sorted(by_company):
        company_rows = by_company[org]
        statuses = sorted({
            str(row.get("Status") or "").strip()
            for row in company_rows
            if str(row.get("Status") or "").strip()
        })
        active = any(status.casefold() == "aktiv" for status in statuses)
        if active:
            active_companies += 1

        names = sorted({
            str(row.get("Foretaks-/bedriftsnavn") or "").strip()
            for row in company_rows
            if str(row.get("Foretaks-/bedriftsnavn") or "").strip()
        })
        subunits = sorted({
            normalized
            for row in company_rows
            if (normalized := normalize_org(row.get("Bedriftsnr"))) is not None
        })
        tasks = sorted({
            item
            for row in company_rows
            for item in _split_semicolon(row.get("Arbeidsoppgaver"))
        })
        scope = sorted({
            item
            for row in company_rows
            for item in _split_semicolon(row.get("Anlegg- og utstyrstyper"))
        })
        emails = sorted({
            str(row.get("E-post") or "").strip().lower()
            for row in company_rows
            if "@" in str(row.get("E-post") or "")
            and " " not in str(row.get("E-post") or "").strip()
        })
        phones = sorted({
            str(row.get("Telefon") or "").strip()
            for row in company_rows
            if str(row.get("Telefon") or "").strip()
        })
        responsible_dle = sorted({
            str(row.get("Ansvarlig DLE") or "").strip()
            for row in company_rows
            if str(row.get("Ansvarlig DLE") or "").strip()
        })
        worker_bands = sorted({
            str(row.get("Antall elektrofagarbeidere") or "").strip()
            for row in company_rows
            if str(row.get("Antall elektrofagarbeidere") or "").strip()
        })

        if tasks:
            companies_with_tasks += 1
        if scope:
            companies_with_scope += 1
        if emails:
            companies_with_email_observations += 1
        if phones:
            companies_with_phone_observations += 1

        matched.append(
            {
                "organisation_number": org,
                "dsb_registry_rows": len(company_rows),
                "active_registration": active,
                "statuses": statuses,
                "registered_unit_names": names,
                "subunit_organisation_numbers": subunits,
                "work_tasks": tasks,
                "facility_equipment_types": scope,
                "responsible_dle_observations": responsible_dle,
                "electrical_worker_band_observations": worker_bands,
                "subunit_email_observations": emails,
                "subunit_phone_observations": phones,
            }
        )

    report = {
        "source": "DSB Elvirksomhetsregisteret bulk Excel export",
        "screen_type": "exact_legal_entity_foretaksnr_registry_screen",
        "production_publication_enabled": False,
        "api_access_status": "OPEN_FREE_NO_REGISTRATION_OBSERVED",
        "reuse_rights_status": "UNRESOLVED_FOR_PERSISTENT_REUSE",
        "source_rows": len(rows),
        "unique_legal_entity_orgs_in_source": len(all_company_orgs),
        "unique_subunit_orgs_in_source": len(all_subunit_orgs),
        "malformed_foretaksnr_values": malformed_company_numbers,
        "malformed_bedriftsnr_values": malformed_subunit_numbers,
        "target_companies": len(targets),
        "exact_target_company_hits": len(matched),
        "exact_target_reach": len(matched) / len(targets) if targets else 0.0,
        "active_registration_companies": active_companies,
        "companies_with_work_tasks": companies_with_tasks,
        "companies_with_facility_equipment_scope": companies_with_scope,
        "companies_with_subunit_email_observations": companies_with_email_observations,
        "companies_with_subunit_phone_observations": companies_with_phone_observations,
        "external_requests": 1,
        "notes": [
            "Only exact 9-digit Foretaksnr establishes target legal-entity identity.",
            "Bedriftsnr is retained as subunit evidence and never used to match a target company.",
            "Subunit email and phone values are observations only; they are not emitted as company-wide contact candidates.",
            "Registry activity and scope are attributed only where the workbook itself carries the exact target Foretaksnr.",
            "The bulk endpoint is publicly reachable without authentication, but persistent/commercial reuse rights remain unresolved.",
            "This research screen does not publish production claims or touch a fresh evaluator cohort.",
        ],
    }
    return report, matched


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-xlsx", type=Path, required=True)
    parser.add_argument("--companies", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    rows = read_first_sheet_rows(args.source_xlsx)
    targets = load_targets(args.companies)
    report, matched = screen(rows, targets)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "matched-companies.jsonl").write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
            for row in matched
        ),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
