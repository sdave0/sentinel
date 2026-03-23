from langchain_core.messages import ToolMessage, AIMessage, HumanMessage
from sentinel.state import SentinelState

def hitl_checkpoint_node(state: SentinelState) -> dict:
    """
    Terminal input block serving as Human-in-the-Loop.
    Pauses execution and waits for human approval via the console.
    """
    validation = state.get("last_validation")
    messages = state.get("messages", [])
    
    last_msg = messages[-1]
    is_dangling = isinstance(last_msg, AIMessage) and getattr(last_msg, "tool_calls", None)
    
    print("\n" + "="*50)
    print("🚨 HITL ESCALATION REQUIRED 🚨")
    print(f"Policy Triggered: {getattr(validation, 'policy_triggered', 'Max Retries Exceeded')}")
    
    if is_dangling:
        print(f"Proposed Action: {last_msg.tool_calls[0].get('name')} -> {last_msg.tool_calls[0].get('args')}")
    else:
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
                print(f"Blocked Action: {msg.tool_calls[0].get('name')} -> {msg.tool_calls[0].get('args')}")
                break
                
    print("="*50)
    
    decision = input("Approve action? [y/n]: ").strip().lower()
    
    if decision in ["y", "yes", "approve"]:
        if is_dangling:
            return {
                "hitl_decision": "approved",
                "hitl_pending": False,
                "retry_count": 0
            }
        else:
            return {
                "messages": [HumanMessage(content="SYSTEM: The human approved the intent, but the parameters remain structurally ungrounded. Halt and ask the user for clarification manually.")],
                "hitl_decision": "rejected", 
                "hitl_pending": False,
                "retry_count": 0
            }
    else:
        if is_dangling:
            tool_msgs = []
            for call in last_msg.tool_calls:
                tool_msgs.append(ToolMessage(
                    content="Action REJECTED by human operator.",
                    tool_call_id=call["id"],
                    name=call["name"]
                ))
            return {
                "messages": tool_msgs,
                "hitl_decision": "rejected",
                "hitl_pending": False,
                "retry_count": 0
            }
        else:
            return {
                "messages": [HumanMessage(content="SYSTEM: The human operator has forcefully rejected this action. Stop attempting to execute this tool and conclude.")],
                "hitl_decision": "rejected",
                "hitl_pending": False,
                "retry_count": 0
            }
