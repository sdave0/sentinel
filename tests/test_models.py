from sentinel.models import EvidenceEntry, EvidenceCache, ProposedAction

def test_evidence_cache_to_context_string():
    # 1. Create EvidenceEntry
    entry_1 = EvidenceEntry(
        tool_name="lookup_order",
        tool_input={"order_id": "123"},
        tool_output={"amount": 42.50, "status": "shipped"},
        turn_number=1
    )
    
    # 2. Add it to EvidenceCache
    cache = EvidenceCache(run_id="run-001")
    cache.add_entry(entry_1)
    
    # 3. Create ProposedAction
    ProposedAction(
        tool_name="process_refund",
        tool_args={"order_id": "123", "amount": 42.50},
        turn_number=2
    )
    
    # 4. Assert cache serialization
    context_str = cache.to_context_string()
    
    assert "lookup_order" in context_str
    assert "123" in context_str
    assert "42.5" in context_str
    assert "Turn 1" in context_str

def test_empty_cache():
    cache = EvidenceCache(run_id="run-002")
    assert cache.to_context_string() == "No previous tool observations."
