import os
import pytest
from sentinel.models import EvidenceCache, EvidenceEntry
from sentinel.validator.llm_checker import check_llm

@pytest.mark.skipif("ANTHROPIC_API_KEY" not in os.environ, reason="Needs Anthropic API key")
def test_llm_checker_semantic_match():
    cache = EvidenceCache(run_id="run-1")
    cache.add_entry(EvidenceEntry(
        tool_name="get_policy",
        tool_input={},
        tool_output={"policy": "Refunds are processed strictly within 30 days of purchase."},
        turn_number=1
    ))
    
    # Value is semantically equivalent but not an exact string match
    result = check_llm(
        param_name="policy_summary",
        param_value="30 days",
        cache_context=cache.to_context_string()
    )
    
    assert result.is_grounded is True
    assert result.check_method == "llm"
    assert result.confidence >= 0.7

@pytest.mark.skipif("ANTHROPIC_API_KEY" not in os.environ, reason="Needs Anthropic API key")
def test_llm_checker_ungrounded():
    cache = EvidenceCache(run_id="run-2")
    cache.add_entry(EvidenceEntry(
        tool_name="get_policy",
        tool_input={},
        tool_output={"policy": "Refunds are processed within 30 days."},
        turn_number=1
    ))
    
    # Value is a hallucination
    result = check_llm(
        param_name="policy_summary",
        param_value="We offer a 90-day return policy for premium members.",
        cache_context=cache.to_context_string()
    )
    
    assert result.is_grounded is False
    assert result.check_method == "llm"
