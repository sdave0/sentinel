from langchain_core.messages import ToolMessage, AIMessage
from sentinel.state import SentinelState

def retry_node(state: SentinelState) -> dict:
    """
    Injects retry feedback into the state as ToolMessages so the agent understands
    its tool calls were blocked. Increments retry_count.
    """
    validation = state.get("last_validation")
    if not validation:
        return {}
        
    messages = state.get("messages", [])
    last_msg = messages[-1]
    
    tool_messages = []
    if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
        # Provide feedback for each tool call that was blocked
        for call in last_msg.tool_calls:
            msg = ToolMessage(
                content=f"Error: Action Blocked. Reason: {validation.blocking_reason}\nFeedback: {validation.retry_feedback}",
                tool_call_id=call["id"],
                name=call["name"]
            )
            tool_messages.append(msg)
            
    retry_count = state.get("retry_count", 0) + 1
    return {
        "messages": tool_messages,
        "retry_count": retry_count
    }
