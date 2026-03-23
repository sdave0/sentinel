import json
from langchain_core.messages import ToolMessage, AIMessage
from sentinel.state import SentinelState
from sentinel.models import EvidenceEntry

def evidence_collector_node(state: SentinelState) -> dict:
    """Reads the last ToolMessage and its preceding AIMessage to construct an EvidenceEntry."""
    messages = state.get("messages", [])
    if not messages or len(messages) < 2:
        return {}

    # Find the last ToolMessage
    last_msg = messages[-1]
    if not isinstance(last_msg, ToolMessage):
        return {}
        
    # Find the preceding AIMessage that generated this tool call
    ai_msg = None
    for msg in reversed(messages[:-1]):
        if isinstance(msg, AIMessage) and msg.tool_calls:
            ai_msg = msg
            break
            
    if not ai_msg:
        return {}

    # Extract matching tool call
    target_call = next((call for call in ai_msg.tool_calls if call["id"] == last_msg.tool_call_id), None)
    if not target_call:
        return {}

    cache = state.get("evidence_cache")
    if not cache:
        return {}

    turn_number = len(cache.entries) + 1
    
    # Safely parse tool output (ToolNode might stringify JSON)
    output_content = last_msg.content
    try:
        output_data = json.loads(output_content) if isinstance(output_content, str) else output_content
    except (json.JSONDecodeError, TypeError):
        output_data = {"result": output_content}

    entry = EvidenceEntry(
        tool_name=target_call["name"],
        tool_input=target_call["args"],
        tool_output=output_data,
        turn_number=turn_number
    )
    
    cache.add_entry(entry)
    return {"evidence_cache": cache}
