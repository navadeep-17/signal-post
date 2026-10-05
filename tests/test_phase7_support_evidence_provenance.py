from norway_company_agent.support_contract import project_support_award_observations


def test_support_projection_retains_row_and_snapshot_provenance() -> None:
    org = "917403376"
    observation = {
        "id": "support-award-test",
        "organisation_number": org,
        "platform": "brreg",
        "signal_type": "official_support_award",
        "source_class": "official_support_registry",
        "source_url": "https://stotte.brreg.no/nb/oppslag/stoettetildeling/totalbestand/csv",
        "retrieved_at": "2026-10-05T00:00:00Z",
        "content_sha256": "a" * 64,
        "source_snapshot_sha256": "b" * 64,
        "source_row_number": 42,
        "source_row_key": "measure-42",
        "exact_entity": True,
        "identity_proof": f"Støtteregisteret primary recipient organisation number equals target {org}",
        "acquisition_mode": "official_dataset",
        "rights_status": "approved",
        "rights_basis": "NLOD",
        "evidence_span": f"recipient org: {org}; award date: 05.10.2026; awarded amount: 1000 NOK",
        "effective_at": "2026-10-05",
        "event": {
            "kind": "support_award",
            "awarded_at": "2026-10-05",
            "amount": "1000",
            "currency": "NOK",
            "amount_interval_from": None,
            "amount_interval_to": None,
            "amount_interval_currency": None,
            "support_measure_number": "measure-42",
            "support_measure_type": "Tilskudd",
            "recipient_name": "HOV AS",
            "specified_recipient_organisation_number": None,
            "granting_authority_org": None,
            "granting_authority_name": None,
            "status": "Registrert",
        },
    }
    contract = {"organisation_number": org, "claims": [], "evidence": []}
    profile = {"organisation_number": org, "external_observations": [observation]}

    projected = project_support_award_observations(contract, profile)

    assert len(projected["claims"]) == 1
    assert len(projected["evidence"]) == 1
    evidence = projected["evidence"][0]
    assert evidence["content_sha256"] == "a" * 64
    assert evidence["source_snapshot_sha256"] == "b" * 64
    assert evidence["source_row_number"] == 42
    assert evidence["source_row_key"] == "measure-42"
    assert evidence["retrieved_at"] == "2026-10-05T00:00:00Z"
    assert f"recipient org: {org}" in evidence["claim_span"]
