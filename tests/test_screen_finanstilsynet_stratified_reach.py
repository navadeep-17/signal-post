import importlib.util
from datetime import date
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "screen_finanstilsynet_stratified_reach.py"
spec = importlib.util.spec_from_file_location("screen_finanstilsynet", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def write_page(path: Path, rows: list[dict], page: int = 1, total_pages: int = 10, total: int = 10000) -> None:
    import json

    path.write_text(
        json.dumps({"page": page, "totalPages": total_pages, "total": total, "hitsReturned": len(rows), "data": rows}),
        encoding="utf-8",
    )


def entity(org: str, name: str = "Target", provider_type: str = "Licensed") -> dict:
    return {
        "legalEntityNumber": org,
        "legalEntityName": name,
        "finanstilsynetId": "FT1",
        "serviceProviderType": provider_type,
    }


def licence(code: str = "REGS", registered: str = "2026-01-01T00:00:00") -> dict:
    return {
        "licenceTypeCode": code,
        "licenceTypeName": {"norwegian": "Regnskapsselskap", "english": "External accounting firm"},
        "registeredDate": registered,
    }


def test_counts_only_exact_service_provider_and_not_owner_only(tmp_path: Path) -> None:
    target = "999999999"
    rows = [
        {"licenceOwner": entity(target, "Owner only"), "serviceProvider": entity("888888888", "Other"), "licence": licence()},
        {"licenceOwner": entity("777777777", "Owner"), "serviceProvider": entity(target, "Target", "Agent"), "licence": licence("AGENT")},
    ]
    page = tmp_path / "page-1.json"
    write_page(page, rows)

    report, matches = module.screen_pages([page], {target}, today=date(2026, 10, 5))

    assert report["exact_target_company_hits"] == 1
    assert report["owner_only_target_matches_not_counted"] == 1
    assert matches[0]["organisation_number"] == target
    assert matches[0]["observations"][0]["service_provider_type"] == "Agent"


def test_rejects_malformed_provider_org_and_deduplicates_rows(tmp_path: Path) -> None:
    target = "999999999"
    valid = {"licenceOwner": entity(target), "serviceProvider": entity(target), "licence": licence()}
    malformed = {"licenceOwner": entity("777777777"), "serviceProvider": entity("NO-ABC"), "licence": licence("BAD")}
    page = tmp_path / "page-1.json"
    write_page(page, [valid, valid, malformed])

    report, matches = module.screen_pages([page], {target}, today=date(2026, 10, 5))

    assert report["malformed_provider_numbers"] == 1
    assert report["exact_target_company_hits"] == 1
    assert matches[0]["observation_count"] == 1


def test_recent_registration_and_projection(tmp_path: Path) -> None:
    target = "999999999"
    page1 = tmp_path / "page-1.json"
    page5 = tmp_path / "page-5.json"
    write_page(page1, [{"licenceOwner": entity(target), "serviceProvider": entity(target), "licence": licence(registered="2026-09-01T00:00:00")}], page=1, total_pages=10)
    write_page(page5, [], page=5, total_pages=10)

    report, matches = module.screen_pages([page1, page5], {target}, today=date(2026, 10, 5))

    assert report["recent_registration_companies"] == 1
    assert report["observed_hits_per_request"] == 0.5
    assert report["naive_projected_full_hits"] == 5
    assert matches[0]["has_recent_registration"] is True
