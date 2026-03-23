from langchain_core.messages import AIMessage
from sentinel.state import SentinelState
from sentinel.models import ProposedAction, EvidenceCache
from sentinel.validator.validator import run_validation
from sentinel.policy.policy_loader import PolicyLoader

import os

_policy_path = os.environ.get("POLICY_PATH", "demo/policies/customer_support.yaml")
global_policy_loader = PolicyLoader(_policy_path)

def _validate_state_integrity(state: SentinelState) -> None:
    retry_count = state.get("retry_count", 0)
    hitl_pending = state.get("hitl_pending", False)
    hitl_decision = state.get("hitl_decision")
    
    if retry_count < 0:
        raise ValueError(f"Corrupt state: retry_count cannot be negative (got {retry_count})")
        
    if hitl_pending and hitl_decision is not None:
        raise ValueError("Corrupt state: hitl_pending cannot be True while hitl_decision is already set")
        
    if retry_count >= 3 and not hitl_pending:
        raise ValueError("Corrupt state: retry_count >= 3 but hitl_pending is False. Engine must route to HITL.")

def validator_node(state: SentinelState) -> dict:
    _validate_state_integrity(state)
    
    if state.get("retry_count", 0) >= 3:
        return {"hitl_pending": True}
        
    messages = state.get("messages", [])
    if not messages:
        return {}

    last_msg = messages[-1]
    if not isinstance(last_msg, AIMessage) or not last_msg.tool_calls:
        return {}

    from sentinel.models import ValidationResult
    cache = state.get("evidence_cache")
    if not cache:
        cache = EvidenceCache(run_id="default")
        
    all_results = []
    any_blocked = False
    blocking_reasons = []
    hitl_escalated = False

    for tool_call in last_msg.tool_calls:
        action = ProposedAction(
            tool_name=tool_call["name"],
            tool_args=tool_call["args"],
            turn_number=len(cache.entries) + 1
        )
        result = run_validation(action, cache, global_policy_loader)
        all_results.append(result)

        if not result.allowed:
            any_blocked = True
            blocking_reasons.append(f"[{result.tool_name}] {result.blocking_reason}")
            if result.policy_triggered == "Requires human approval":
                hitl_escalated = True

    try:
        if len(all_results) == 1:
            overall_result = all_results[0]
        else:
            all_params = []
            for r in all_results:
                all_params.extend(r.parameter_results)
                
            if any_blocked:
                combined_reason = " | ".join(blocking_reasons)
                overall_result = ValidationResult(
                    tool_name="multi_tool_call",
                    allowed=False,
                    confidence=1.0,
                    parameter_results=all_params,
                    blocking_reason=combined_reason,
                    retry_feedback="One or more parallel tool calls were blocked. See reasons.",
                    policy_triggered="Requires human approval" if hitl_escalated else None,
                    latency_ms=sum(r.latency_ms for r in all_results),
                    check_layers_used=list(set(layer for r in all_results for layer in r.check_layers_used))
                )
            else:
                overall_result = ValidationResult(
                    tool_name="multi_tool_call",
                    allowed=True,
                    confidence=1.0,
                    parameter_results=all_params,
                    latency_ms=sum(r.latency_ms for r in all_results),
                    check_layers_used=list(set(layer for r in all_results for layer in r.check_layers_used))
                )
    except Exception as e:
        overall_result = ValidationResult(
            tool_name="multi_tool_call",
            allowed=False,
            confidence=1.0,
            parameter_results=[],
            blocking_reason=f"ValidationResult schema initialization failure: {e}",
            latency_ms=0,
            check_layers_used=["fallback"]
        )

    updates = {
        "last_validation": overall_result,
        "blocked_actions": all_results
    }
    
    if any_blocked and hitl_escalated:
         updates["hitl_pending"] = True
         
    return updates
