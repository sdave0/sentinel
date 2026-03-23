from typing import Callable, Sequence, Any
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from sentinel.state import SentinelState
from sentinel.nodes.evidence_collector import evidence_collector_node
from sentinel.nodes.validator_node import validator_node
from sentinel.nodes.retry_node import retry_node
from sentinel.hitl.checkpoint import hitl_checkpoint_node

def build_sentinel_graph(agent_runnable: Callable, tools: Sequence[Any]) -> StateGraph:
    """
    Compiles the Sentinel workflow graph encapsulating an agent and its tools.
    """
    workflow = StateGraph(SentinelState)
    
    # 1. Define raw agent wrapper
    def call_model(state: SentinelState):
        msgs = state.get("messages", [])
        response = agent_runnable.invoke({"messages": msgs})
        return {"messages": [response]}
        
    # 2. Add structural nodes
    workflow.add_node("agent_node", call_model)
    workflow.add_node("validator_node", validator_node)
    workflow.add_node("tool_node", ToolNode(tools))
    workflow.add_node("evidence_collector_node", evidence_collector_node)
    workflow.add_node("retry_node", retry_node)
    workflow.add_node("hitl_node", hitl_checkpoint_node)
    
    # 3. Define Conditional Edges
    def after_agent(state: SentinelState) -> str:
        last_msg = state["messages"][-1]
        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
            return "validator_node"
        return END

    def after_validator(state: SentinelState) -> str:
        validation = state.get("last_validation")
        # Ensure we block first
        if state.get("hitl_pending", False) or validation.blocking_reason == "Requires human approval":
            return "hitl_node"
            
        if not validation.allowed:
            return "retry_node"
        
        return "tool_node"

    def after_retry(state: SentinelState) -> str:
        if state.get("retry_count", 0) >= 3:
            return "hitl_node"
        return "agent_node"

    def after_hitl(state: SentinelState) -> str:
        decision = state.get("hitl_decision")
        if decision == "approved":
            # Resume exactly where it was paused -- the tool node
            return "tool_node"
        else:
            return "agent_node" # Return rejection toolMsg back to agent

    # 4. Compose Edges
    workflow.add_edge(START, "agent_node")
    workflow.add_conditional_edges("agent_node", after_agent)
    
    workflow.add_conditional_edges("validator_node", after_validator)
    
    workflow.add_edge("tool_node", "evidence_collector_node")
    workflow.add_edge("evidence_collector_node", "agent_node")
    
    workflow.add_conditional_edges("retry_node", after_retry)
    workflow.add_conditional_edges("hitl_node", after_hitl)
    
    return workflow.compile()
