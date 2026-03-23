from typing import Any
import json
from langchain_core.prompts import ChatPromptTemplate
from sentinel.models import ParameterGroundingResult
from sentinel.llm_factory import get_llm

SYSTEM_PROMPT = """You are a strict validation guardrail for an AI agent. 
The agent is attempting to call a tool with a specific parameter. 
Your job is to determine if the parameter's value is grounded in the agent's prior observations (the Evidence Cache).

Are the semantics of this value supported by prior evidence? 
For example, if the cache says a price is '$59.99' and the agent passes `59.99`, or if the cache says 'Return policy is 30 days' and the agent summarizes it as '30 days', it is grounded.

You must return a JSON structure matching the ParameterGroundingResult schema. Set check_method to "llm"."""

def check_llm(param_name: str, param_value: Any, cache_context: str) -> ParameterGroundingResult:
    """Uses Claude Haiku with structured output to semantically evaluate grounding."""
    try:
        # Pydantic BaseModels can be passed directly to with_structured_output
        llm = get_llm(temperature=0).with_structured_output(ParameterGroundingResult)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("user", "Evidence Cache:\n{cache_context}\n\nParameter Name: {param_name}\nParameter Value: {param_value}\n\nIs this parameter grounded?")
        ])
        
        chain = prompt | llm
        
        val_str = param_value if isinstance(param_value, str) else json.dumps(param_value)
        result = chain.invoke({
            "cache_context": cache_context,
            "param_name": param_name,
            "param_value": val_str
        })
        
        # Ensure method is set correctly
        if isinstance(result, ParameterGroundingResult):
            result.check_method = "llm"
            return result
        else:
            raise ValueError("Output did not match expected Pydantic schema structure")
            
    except Exception as e:
        from loguru import logger
        logger.error(f"LLM Validator extraction error mapping structured schema: {e}")
        return ParameterGroundingResult(
            parameter_name=param_name,
            parameter_value=param_value,
            is_grounded=False,
            confidence=0.5,
            check_method="llm"
        )
