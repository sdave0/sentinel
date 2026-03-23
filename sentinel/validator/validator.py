import os
import time
from langchain_core.prompts import PromptTemplate
from sentinel.models import ProposedAction, EvidenceCache, ValidationResult, ParameterGroundingResult
from sentinel.policy.policy_loader import PolicyLoader
from sentinel.validator.rule_checker import check_rules
from sentinel.validator.llm_checker import check_llm
from sentinel.llm_factory import get_llm

def generate_retry_feedback(action: ProposedAction, cache: EvidenceCache, ungrounded_params: list[str]) -> str:
    """Uses LLM to suggest the exact tool call needed to obtain missing parameters."""
    llm = get_llm(temperature=0, max_tokens=150)
    prompt = PromptTemplate.from_template(
        "You are an AI assistant helping a LangGraph agent. "
        "The agent tried to call {tool} but parameters {params} were not grounded in prior observations.\n"
        "Evidence cache: {cache_context}\n\n"
        "Your task: Tell the agent in one short sentence exactly which tool it should call next to observe the missing information. DO NOT write code."
    )
    res = llm.invoke(prompt.format(
        tool=action.tool_name, 
        params=", ".join(ungrounded_params),
        cache_context=cache.to_context_string()
    ))
    return res.content if isinstance(res.content, str) else res.content[0]["text"]

def _handle_policy_block(violation, shadow_mode, start_time, action: ProposedAction) -> ValidationResult:
    
    dummy_params = []
    for k, v in action.tool_args.items():
        dummy_params.append(ParameterGroundingResult(
            parameter_name=str(k),
            parameter_value=v,
            is_grounded=False,
            confidence=1.0,
            check_method="policy"
        ))
        
    reason = f"[SHADOW BLOCKED] {violation.reason}" if shadow_mode else violation.reason
    return ValidationResult(
        tool_name=action.tool_name,
        allowed=True if shadow_mode else False,
        confidence=1.0,
        parameter_results=dummy_params,
        blocking_reason=reason,
        retry_feedback="Policy violated. Cannot proceed with this action.",
        policy_triggered=violation.reason,
        latency_ms=int((time.time() - start_time) * 1000),
        check_layers_used=["policy"]
    )

def _evaluate_parameters(action: ProposedAction, cache: EvidenceCache, rule_results: dict, check_layers: set):
    final_params, ungrounded_names = [], []
    for param_name, res in rule_results.items():
        if res is None:
            check_layers.add("llm")
            llm_res = check_llm(param_name, action.tool_args.get(param_name), cache.to_context_string())
            final_params.append(llm_res)
            if not llm_res.is_grounded and llm_res.confidence > 0.8:
                ungrounded_names.append(param_name)
        else:
            final_params.append(res)
            if not res.is_grounded and res.confidence > 0.8:
                ungrounded_names.append(param_name)
    return final_params, ungrounded_names

def run_validation(action: ProposedAction, cache: EvidenceCache, policy: PolicyLoader) -> ValidationResult:
    start_time = time.time()
    shadow_mode = os.environ.get("SHADOW_MODE", "false").lower() == "true"
    violation = policy.check_policy(action, cache)
    if violation and violation.is_violation:
        return _handle_policy_block(violation, shadow_mode, start_time, action)
        
    check_layers = set(["rule"])
    final_params, ungrounded_names = _evaluate_parameters(action, cache, check_rules(action, cache), check_layers)
    min_confidence = min([p.confidence for p in final_params], default=1.0)
    
    if ungrounded_names:
        feedback = generate_retry_feedback(action, cache, ungrounded_names)
        base_reason = f"Parameters ungrounded: {', '.join(ungrounded_names)}"
        reason = f"[SHADOW BLOCKED] {base_reason}" if shadow_mode else base_reason
        return ValidationResult(
            tool_name=action.tool_name,
            allowed=True if shadow_mode else False,
            confidence=min_confidence,
            parameter_results=final_params,
            blocking_reason=reason,
            retry_feedback=feedback,
            latency_ms=int((time.time() - start_time) * 1000),
            check_layers_used=list(check_layers)
        )
    if violation and violation.is_hitl_escalation:
        return ValidationResult(
            tool_name=action.tool_name,
            allowed=False,
            confidence=min_confidence,
            parameter_results=final_params,
            blocking_reason="Requires human approval",
            policy_triggered=violation.reason,
            latency_ms=int((time.time() - start_time) * 1000),
            check_layers_used=list(check_layers)
        )
    return ValidationResult(
        tool_name=action.tool_name,
        allowed=True,
        confidence=min_confidence,
        parameter_results=final_params,
        latency_ms=int((time.time() - start_time) * 1000),
        check_layers_used=list(check_layers)
    )
