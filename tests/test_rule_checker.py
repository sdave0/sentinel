from sentinel.models import EvidenceEntry, EvidenceCache, ProposedAction
from sentinel.validator.rule_checker import check_rules

def test_exact_match():
    cache = EvidenceCache(run_id="test")
    cache.add_entry(EvidenceEntry(
        tool_name="lookup_order",
        tool_input={},
        tool_output={"order_id": "ORD-123", "details": {"status": "shipped"}},
        turn_number=1
    ))
    
    action = ProposedAction(
        tool_name="process_refund",
        tool_args={"order_id": "ORD-123"},
        turn_number=2
    )
    
    results = check_rules(action, cache)
    assert results["order_id"] is not None
    assert results["order_id"].is_grounded
    assert results["order_id"].confidence == 1.0

def test_plausible_numeric_range():
    cache = EvidenceCache(run_id="test")
    cache.add_entry(EvidenceEntry(
        tool_name="lookup_prices",
        tool_input={},
        tool_output={"past_prices": [10.0, 50.0, 100.0]},
        turn_number=1
    ))
    
    action = ProposedAction(
        tool_name="apply_discount",
        tool_args={"amount": 45.0},
        turn_number=2
    )
    
    results = check_rules(action, cache)
    assert results["amount"] is not None
    assert results["amount"].is_grounded
    assert results["amount"].confidence == 0.7

def test_unknown_parameter_fails():
    cache = EvidenceCache(run_id="test")
    cache.add_entry(EvidenceEntry(
        tool_name="lookup",
        tool_input={},
        tool_output={"valid_ids": ["A", "B"]},
        turn_number=1
    ))
    
    action = ProposedAction(
        tool_name="process",
        tool_args={"id": "C"},
        turn_number=2
    )
    
    results = check_rules(action, cache)
    assert results["id"] is not None
    assert not results["id"].is_grounded
    assert results["id"].confidence == 1.0

def test_long_string_fails_grounding():
    cache = EvidenceCache(run_id="test")
    action = ProposedAction(
        tool_name="summarize",
        tool_args={"summary": "This is a longer string that we cannot deterministically match so we block it."},
        turn_number=1
    )
    
    results = check_rules(action, cache)
    assert results["summary"] is not None
    assert not results["summary"].is_grounded
    assert results["summary"].confidence == 1.0

def test_recursive_exact_match_in_list_of_dicts():
    cache = EvidenceCache(run_id="test")
    cache.add_entry(EvidenceEntry(
        tool_name="lookup_all_orders",
        tool_input={},
        tool_output={"status": "success", "data": [{"order_id": "ORD-111", "amount": 10}, {"order_id": "ORD-222", "amount": 20}]},
        turn_number=1
    ))
    
    action = ProposedAction(
        tool_name="process_refund",
        tool_args={"order_id": "ORD-222"},
        turn_number=2
    )
    
    results = check_rules(action, cache)
    assert results["order_id"] is not None
    assert results["order_id"].is_grounded
    assert results["order_id"].confidence == 1.0
