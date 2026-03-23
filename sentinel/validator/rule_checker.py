from typing import Any, Dict, List, Optional
from sentinel.models import ProposedAction, EvidenceCache, ParameterGroundingResult

def _find_exact_match(value: Any, entries: List[Any], current_entry_id: str) -> Optional[str]:
    """Recursively search entries for an exact value match, returning the entry_id if found."""
    for entry in entries:
        outputs = entry.tool_output
        if _recursive_value_search(value, outputs):
            return entry.entry_id
    return None

def _recursive_value_search(value_to_find: Any, structure: Any) -> bool:
    if isinstance(structure, dict):
        for v in structure.values():
            if _recursive_value_search(value_to_find, v):
                return True
    elif isinstance(structure, list):
        for item in structure:
            if _recursive_value_search(value_to_find, item):
                return True
    else:
        # Same type and exact match
        if type(structure) is type(value_to_find) and structure == value_to_find:
            return True
    return False

def _find_range_plausibility(value: Any, entries: List[Any]) -> bool:
    """If numeric, checks if it's within the min/max of prior observed numerics."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
        
    numerics = []
    def _extract_numerics(data: Any):
        if isinstance(data, dict):
            for v in data.values():
                _extract_numerics(v)
        elif isinstance(data, list):
            for item in data:
                _extract_numerics(item)
        elif isinstance(data, (int, float)) and not isinstance(data, bool):
            numerics.append(data)
            
    for entry in entries:
        _extract_numerics(entry.tool_output)
        
    if not numerics:
        return False
        
    return min(numerics) <= value <= max(numerics)

def check_rules(action: ProposedAction, cache: EvidenceCache) -> Dict[str, Optional[ParameterGroundingResult]]:
    """
    Evaluates each parameter deterministically.
    Returns None for parameters it legitimately cannot determine.
    """
    from loguru import logger
    results = {}
    
    for param_name, param_value in action.tool_args.items():
        if isinstance(param_value, str):
            injection_markers = [";", "'", '"', "--", "/*"]
            if any(marker in param_value for marker in injection_markers):
                logger.warning(f"Potential injection attempt detected in parameter '{param_name}': {param_value}")
        match_id = _find_exact_match(param_value, cache.entries, "")
        if match_id:
            results[param_name] = ParameterGroundingResult(
                parameter_name=param_name,
                parameter_value=param_value,
                is_grounded=True,
                confidence=1.0,
                evidence_reference=match_id,
                check_method="rule"
            )
            continue
        if _find_range_plausibility(param_value, cache.entries):
            results[param_name] = ParameterGroundingResult(
                parameter_name=param_name,
                parameter_value=param_value,
                is_grounded=True,
                confidence=0.7,
                check_method="rule"
            )
            continue
        results[param_name] = ParameterGroundingResult(
            parameter_name=param_name,
            parameter_value=param_value,
            is_grounded=False,
            confidence=1.0,
            check_method="rule"
        )
            
    return results
