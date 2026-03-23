import yaml
import os
from typing import List, Optional
from sentinel.models import ProposedAction, EvidenceCache, PolicyRule, PolicyViolation
from loguru import logger

def evaluate_condition(condition: str, tool_args: dict) -> bool:
    """Safely evaluates basic operator conditions like 'amount > 500' without using eval()."""
    operators = [">=", "<=", "==", "!=", ">", "<"]
    found_op = None
    
    for op in operators:
        if op in condition:
            found_op = op
            break
            
    if not found_op:
        logger.warning(f"Unsupported condition pattern: '{condition}'")
        return False
        
    parts = condition.split(found_op)
    if len(parts) != 2:
        logger.warning(f"Malformed condition pattern: '{condition}'")
        return False
        
    param_name = parts[0].strip()
    raw_threshold = parts[1].strip()
    
    if param_name not in tool_args:
        return False
        
    param_val = tool_args[param_name]
    
    # Try parsing threshold numerically
    try:
        if "." in raw_threshold:
            threshold = float(raw_threshold)
        else:
            threshold = int(raw_threshold)
    except ValueError:
        # Keep as string
        threshold = raw_threshold.strip("\"'")
        
    try:
        if found_op == ">=": 
            return param_val >= threshold
        if found_op == "<=": 
            return param_val <= threshold
        if found_op == "==": 
            return str(param_val) == str(threshold) if isinstance(threshold, str) else param_val == threshold
        if found_op == "!=": 
            return str(param_val) != str(threshold) if isinstance(threshold, str) else param_val != threshold
        if found_op == ">": 
            return param_val > threshold
        if found_op == "<": 
            return param_val < threshold
    except TypeError:
        logger.warning(f"Type mismatch evaluating '{condition}' against value '{param_val}'")
        return False
        
    return False

class PolicyLoader:
    def __init__(self, policy_path: str):
        self.rules: List[PolicyRule] = []
        if os.path.exists(policy_path):
            with open(policy_path, 'r') as f:
                data = yaml.safe_load(f)
                if data and "rules" in data:
                    for r_dict in data["rules"]:
                        try:
                            rule = PolicyRule(**r_dict)
                            rule.tool = rule.tool.lower()
                            self.rules.append(rule)
                        except Exception as e:
                            logger.error(f"Failed to parse policy rule '{r_dict}': {e}. Skipping malformed rule.")

    def check_policy(self, action: ProposedAction, cache: EvidenceCache) -> Optional[PolicyViolation]:
        """
        Evaluates the proposed action against loaded policy rules.
        
        Returns None if no policy applies or if all policy requirements are met.
        Returns a PolicyViolation with is_violation=True for hard blocks (e.g., missing prior tool).
        Returns a PolicyViolation with is_violation=False and is_hitl_escalation=True for HITL escalations.
        """
        matching_rules = [r for r in self.rules if r.tool.lower() == action.tool_name.lower()]
        
        # 1. Evaluate hard blocks (Prior tool checks) first
        for rule in matching_rules:
            if rule.requires_prior_tool:
                if not any(e.tool_name == rule.requires_prior_tool for e in cache.entries):
                    return PolicyViolation(
                        is_violation=True,
                        is_hitl_escalation=False,
                        reason=f"Policy violation: {action.tool_name} requires {rule.requires_prior_tool} to be called first."
                    )
                    
        # 2. Evaluate HITL escalations
        for rule in matching_rules:
            if rule.hitl_required:
                if rule.condition:
                    if evaluate_condition(rule.condition, action.tool_args):
                        return PolicyViolation(
                            is_violation=False,
                            is_hitl_escalation=True,
                            reason=rule.reason or f"HITL condition met: {rule.condition}"
                        )
                else:
                    return PolicyViolation(
                        is_violation=False,
                        is_hitl_escalation=True,
                        reason=rule.reason or f"HITL required for all calls to {rule.tool}"
                    )
                    
        return None
