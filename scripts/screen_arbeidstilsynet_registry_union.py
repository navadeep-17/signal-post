#!/usr/bin/env python3
"""Screen Arbeidstilsynet open registries as an exact-org research union.

Research-only source qualification. The parser intentionally counts a target
company only when its 9-digit organisation number is the `Hovedenhet` of a
`Virksomhet` record. `Underenheter`/`Avdeling` organisation numbers are audited
but never promoted to legal-entity hits.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Any

ORG_RE = re.compile(r"^\d{9}$")


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def normalize_org(value: Any) -> str | None:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits if ORG_RE.fullmatch(digits) else None


def company_org(row: dict[str, Any]) -> str:
    for key in ("organisation_number", "organization_number", "orgnr", "org_number"):
        org = normalize_org(row.get(key))
        if org:
            return org
    raise ValueError(f"company row has no exact 9-digit organisation number: {row!r}")


def read_companies(path: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError("company JSONL rows must be objects")
        org = company_org(row)
        if org in result:
            raise ValueError(f"duplicate company orgnr {org}")
        result[org] = row
    if not result:
        raise ValueError("empty company cohort")
    return result


def direct_child(parent: ET.Element | None, name: str) -> ET.Element | None:
    if parent is None:
        return None
    for child in list(parent):
        if local(child.tag) == name:
            return child
    return None


def direct_text(parent: ET.Element | None, name: str) -> str | None:
    child = direct_child(parent, name)
    if child is None or child.text is None:
        return None
    value = child.text.strip()
    return value or None


def collect_contact(contact: ET.Element | None) -> dict[str, list[str]]:
    values: dict[str, set[str]] = {
        "websites": set(),
        "emails": set(),
        "phones": set(),
    }
    if contact is None:
        return {key: [] for key in values}

    for elem in contact.iter():
        if elem is contact or elem.text is None:
            continue
        text = elem.text.strip()
        if not text:
            continue
        tag = local(elem.tag).lower().replace("-", "").replace("_", "")
        if "web" in tag or tag in {"url", "nettside", "hjemmeside"}:
            values["websites"].add(text)
        elif "epost" in tag or "email" in tag or "mailadresse" in tag:
            values["emails"].add(text)
        elif "telefon" in tag or "mobil" in tag or tag in {"phone", "tel"}:
            values["phones"].add(text)

    return {key: sorted(items) for key, items in values.items()}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_registry(path: Path, registry_name: str) -> dict[str, Any]:
    root = ET.parse(path).getroot()
    metadata = direct_child(root, "Metadata")
    generated_at = direct_text(metadata, "DatoTidGenerert")
    register_label = direct_text(root, "Registernavn") or registry_name

    mains: dict[str, dict[str, Any]] = {}
    malformed_main_orgs = 0
    subunit_orgs: set[str] = set()
    source_virksomheter = 0

    for virksomhet in list(root):
        if local(virksomhet.tag) != "Virksomhet":
            continue
        source_virksomheter += 1
        hovedenhet = direct_child(virksomhet, "Hovedenhet")
        org = normalize_org(direct_text(hovedenhet, "Organisasjonsnummer"))
        if org is None:
            malformed_main_orgs += 1
            continue

        contact = collect_contact(direct_child(virksomhet, "Kontaktinformasjon"))
        record = {
            "organisation_number": org,
            "name": direct_text(hovedenhet, "Navn"),
            "status": direct_text(virksomhet, "Godkjenningsstatus"),
            "websites": contact["websites"],
            "emails": contact["emails"],
            "phones": contact["phones"],
            "registry": registry_name,
            "register_label": register_label,
            "generated_at": generated_at,
        }
        if org in mains:
            # Duplicate main records are merged conservatively; conflicting text
            # fields are retained as lists in the audit output rather than used as
            # extra identity evidence.
            old = mains[org]
            old["websites"] = sorted(set(old["websites"]) | set(record["websites"]))
            old["emails"] = sorted(set(old["emails"]) | set(record["emails"]))
            old["phones"] = sorted(set(old["phones"]) | set(record["phones"]))
        else:
            mains[org] = record

        underenheter = direct_child(virksomhet, "Underenheter")
        if underenheter is not None:
            for avdeling in list(underenheter):
                if local(avdeling.tag) != "Avdeling":
                    continue
                sub_org = normalize_org(direct_text(avdeling, "Organisasjonsnummer"))
                if sub_org:
                    subunit_orgs.add(sub_org)

    return {
        "registry": registry_name,
        "register_label": register_label,
        "generated_at": generated_at,
        "source_bytes": path.stat().st_size,
        "source_sha256": sha256_file(path),
        "source_virksomheter": source_virksomheter,
        "unique_main_orgs": len(mains),
        "unique_subunit_orgs": len(subunit_orgs),
        "malformed_main_orgs": malformed_main_orgs,
        "mains": mains,
        "subunit_orgs": subunit_orgs,
    }


def cohort_metrics(
    companies: dict[str, dict[str, Any]],
    registries: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    target_orgs = set(companies)
    union: dict[str, dict[str, Any]] = {}
    per_registry: dict[str, Any] = {}
    subunit_only: set[str] = set()

    for registry in registries:
        mains: dict[str, dict[str, Any]] = registry["mains"]
        hit_orgs = target_orgs & set(mains)
        for org in sorted(hit_orgs):
            source_record = mains[org]
            entry = union.setdefault(
                org,
                {
                    "organisation_number": org,
                    "registries": [],
                    "statuses": [],
                    "websites": [],
                    "emails": [],
                    "phones": [],
                },
            )
            entry["registries"].append(registry["registry"])
            if source_record.get("status"):
                entry["statuses"].append(
                    {"registry": registry["registry"], "status": source_record["status"]}
                )
            entry["websites"] = sorted(set(entry["websites"]) | set(source_record["websites"]))
            entry["emails"] = sorted(set(entry["emails"]) | set(source_record["emails"]))
            entry["phones"] = sorted(set(entry["phones"]) | set(source_record["phones"]))

        main_set = set(mains)
        subunit_only |= (target_orgs & registry["subunit_orgs"]) - main_set
        hit_rows = [mains[org] for org in hit_orgs]
        per_registry[registry["registry"]] = {
            "exact_main_company_hits": len(hit_orgs),
            "reach": round(len(hit_orgs) / len(target_orgs), 6),
            "website_candidate_companies": sum(bool(row["websites"]) for row in hit_rows),
            "email_candidate_companies": sum(bool(row["emails"]) for row in hit_rows),
            "phone_candidate_companies": sum(bool(row["phones"]) for row in hit_rows),
        }

    union_rows = list(union.values())
    metrics = {
        "companies": len(target_orgs),
        "exact_main_union_hits": len(union_rows),
        "union_reach": round(len(union_rows) / len(target_orgs), 6),
        "website_candidate_companies": sum(bool(row["websites"]) for row in union_rows),
        "email_candidate_companies": sum(bool(row["emails"]) for row in union_rows),
        "phone_candidate_companies": sum(bool(row["phones"]) for row in union_rows),
        "subunit_only_target_matches_not_counted": len(subunit_only),
        "subunit_only_orgs_not_counted": sorted(subunit_only),
        "per_registry": per_registry,
    }
    return metrics, union


def parse_registry_args(values: list[str]) -> list[tuple[str, Path]]:
    result: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for value in values:
        if "=" not in value:
            raise ValueError("--registry must be NAME=PATH")
        name, path = value.split("=", 1)
        name = name.strip()
        if not name or name in seen:
            raise ValueError(f"invalid or duplicate registry name: {name!r}")
        seen.add(name)
        result.append((name, Path(path)))
    if not result:
        raise ValueError("at least one --registry is required")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", action="append", default=[], help="NAME=PATH; repeatable")
    parser.add_argument("--companies-100", required=True, type=Path)
    parser.add_argument("--companies-1000", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    companies_100 = read_companies(args.companies_100)
    companies_1000 = read_companies(args.companies_1000)
    if not set(companies_100).issubset(companies_1000):
        raise SystemExit("consumed 100 must be a subset of consumed 1000")

    registry_specs = parse_registry_args(args.registry)
    registries = [parse_registry(path, name) for name, path in registry_specs]
    metrics_100, union_100 = cohort_metrics(companies_100, registries)
    metrics_1000, union_1000 = cohort_metrics(companies_1000, registries)

    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    with (output / "matched-companies-1000.jsonl").open("w", encoding="utf-8") as handle:
        for org in sorted(union_1000):
            handle.write(json.dumps(union_1000[org], ensure_ascii=False, sort_keys=True) + "\n")

    report_registries = []
    for registry in registries:
        report_registries.append(
            {
                key: registry[key]
                for key in (
                    "registry",
                    "register_label",
                    "generated_at",
                    "source_bytes",
                    "source_sha256",
                    "source_virksomheter",
                    "unique_main_orgs",
                    "unique_subunit_orgs",
                    "malformed_main_orgs",
                )
            }
        )

    report = {
        "source_family": "Arbeidstilsynet open registries",
        "screen_type": "exact_hovedenhet_org_registry_union",
        "registries": report_registries,
        "cohorts": {
            "consumed_100": metrics_100,
            "consumed_1000": metrics_1000,
        },
        "external_requests": len(registry_specs),
        "reuse_rights_status": "NLOD_FOR_SCREENED_XML_DISTRIBUTIONS",
        "production_publication_enabled": False,
        "notes": [
            "Only exact 9-digit Hovedenhet organisation numbers count as legal-entity hits.",
            "Underenhet/Avdeling organisation numbers are audited but explicitly not counted.",
            "Official contact values remain research candidates until Signalpost publication policy is decided.",
            "This screen does not mutate production code or consume a fresh evaluator cohort.",
        ],
    }
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
