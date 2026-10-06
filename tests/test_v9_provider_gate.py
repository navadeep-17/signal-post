from norway_company_agent.v9_provider_gate import ProviderContract, evaluate_provider_contract


def contract(**overrides):
    values = {
        "name": "example-search",
        "evaluator_reproducible": True,
        "rights_status": "approved",
        "key_available_to_evaluator": True,
        "cost_per_search_usd": 0.02,
        "max_searches": 20,
    }
    values.update(overrides)
    return ProviderContract.from_mapping(values)


def test_provider_gate_allows_only_bounded_experiment_when_contract_is_complete():
    result = evaluate_provider_contract(contract(), challenge_cost_budget_usd=10.0)

    assert result["allowed_for_live_v9_experiment"] is True
    assert result["allowed_for_production_candidate"] is False
    assert result["projected_provider_cost_usd"] == 0.4
    assert result["reasons"] == []


def test_provider_gate_blocks_unconfirmed_rights():
    result = evaluate_provider_contract(
        contract(rights_status="review_required"),
        challenge_cost_budget_usd=10.0,
    )

    assert result["allowed_for_live_v9_experiment"] is False
    assert "provider_rights_not_confirmed" in result["reasons"]


def test_provider_gate_blocks_non_reproducible_or_missing_evaluator_key():
    result = evaluate_provider_contract(
        contract(evaluator_reproducible=False, key_available_to_evaluator=False),
        challenge_cost_budget_usd=10.0,
    )

    assert result["allowed_for_live_v9_experiment"] is False
    assert "provider_not_evaluator_reproducible" in result["reasons"]
    assert "provider_key_not_available_to_evaluator" in result["reasons"]


def test_provider_gate_blocks_projected_cost_over_budget():
    result = evaluate_provider_contract(
        contract(cost_per_search_usd=0.75, max_searches=20),
        challenge_cost_budget_usd=10.0,
    )

    assert result["allowed_for_live_v9_experiment"] is False
    assert result["projected_provider_cost_usd"] == 15.0
    assert "projected_provider_cost_exceeds_budget" in result["reasons"]


def test_provider_contract_rejects_missing_or_invalid_cost_data():
    try:
        ProviderContract.from_mapping(
            {
                "name": "broken",
                "evaluator_reproducible": True,
                "rights_status": "approved",
                "key_available_to_evaluator": True,
                "cost_per_search_usd": None,
                "max_searches": 1,
            }
        )
    except ValueError as exc:
        assert "cost_per_search_usd" in str(exc)
    else:
        raise AssertionError("missing numeric provider cost must fail")
