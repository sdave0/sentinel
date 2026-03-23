import os
import sys
import time
import uuid
import hashlib
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from demo.agent import build_guarded_agent, system_prompt
from demo.tools import demo_tools
from sentinel.llm_factory import get_llm
from sentinel.graph.builder import build_sentinel_graph
from sentinel.models import EvidenceCache, SentinelRunMetadata
from sentinel.storage.run_store import save_run

# Load .env for API keys
load_dotenv()

if "GOOGLE_API_KEY" not in os.environ and "ANTHROPIC_API_KEY" not in os.environ:
    print("Please set an API key in the `.env` or environment first.")
    sys.exit(1)

def print_break(title: str):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")

def run_scenario(scenario_name: str, app, prompt: str, shadow_mode: bool = False, agent_name: str = "CustomerSupportAgent"):
    print_break(scenario_name)
    print(f"USER PROMPT: '{prompt}'\n")
    
    run_id = str(uuid.uuid4())
    state_input = {
        "messages": [HumanMessage(content=prompt)],
        "evidence_cache": EvidenceCache(run_id=run_id),
        "run_metadata": SentinelRunMetadata(
            run_id=run_id,
            agent_name=agent_name if not shadow_mode else f"{agent_name}-Shadow",
            shadow_mode=shadow_mode,
            prompt_hash=hashlib.sha256(system_prompt.encode('utf-8')).hexdigest(),
            started_at=datetime.utcnow()
        ),
        "retry_count": 0
    }
    
    validations_ran = []
    original_shadow = os.environ.get("SHADOW_MODE", "false")
    os.environ["SHADOW_MODE"] = "true" if shadow_mode else "false"
    
    try:
        for state_snapshot in app.stream(state_input, stream_mode="updates"):
            for node_name, updates in state_snapshot.items():
                if "last_validation" in updates and updates["last_validation"]:
                    validations_ran.append(updates["last_validation"])
    finally:
        os.environ["SHADOW_MODE"] = original_shadow
        
    print("\n[SCENARIO COMPLETE]")
    
    state_input["run_metadata"].completed_at = datetime.utcnow()
    save_run(state_input["run_metadata"], validations_ran)

if __name__ == "__main__":
    
    WAIT_TIME = 20
    guarded_app = build_guarded_agent()

    # =========================================================================
    # SCENARIO D: The Confident Hallucinator
    # =========================================================================
    run_scenario(
        "SCENARIO D — The Confident Hallucinator",
        guarded_app,
        "Process a refund of $299.99 for order ORD-001 for customer john@example.com.",
        agent_name="BillingSupportAgent"
    )
    
    # Respecting Gemini API rate limits...
    time.sleep(WAIT_TIME)

    # =========================================================================
    # SCENARIO E: The Cascading Dependency (Correct)
    # =========================================================================
    run_scenario(
        "SCENARIO E — The Cascading Dependency (Correct)",
        guarded_app,
        "Look up order ORD-001, then find the customer, then send them a confirmation email.",
        agent_name="CustomerCareAgent"
    )
    
    # Wait for rate limit
    time.sleep(WAIT_TIME)

    # =========================================================================
    # SCENARIO E (Bad): The Cascading Dependency (Skipped Step)
    # =========================================================================
    llm = get_llm(temperature=0, advanced_model=True).bind_tools(demo_tools)
    bad_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a customer support agent. Look up the order, but skip looking up the customer. Proceed directly to sending the email."),
        ("placeholder", "{messages}")
    ])
    bad_agent = build_sentinel_graph(bad_prompt | llm, demo_tools)
    
    run_scenario(
        "SCENARIO E — The Cascading Dependency (Skipped Step)",
        bad_agent,
        "Look up order ORD-001 and then directly send them a confirmation email.",
        agent_name="CustomerCareAgent"
    )
    
    # Wait for rate limit
    time.sleep(WAIT_TIME)

    # =========================================================================
    # SCENARIO F: The Shadow Mode Audit
    # =========================================================================
    run_scenario(
        "SCENARIO F — The Shadow Mode Audit",
        guarded_app,
        "Process a refund of $299.99 for order ORD-001 for customer john@example.com.",
        shadow_mode=True,
        agent_name="BillingSupportAgent"
    )
    
    # Wait for rate limit
    time.sleep(WAIT_TIME)

    # =========================================================================
    # SCENARIO G: The Partial Success
    # =========================================================================
    run_scenario(
        "SCENARIO G — The Partial Success",
        guarded_app,
        "Look up order ORD-001 and then process a refund, but use order ORD-003 for the refund.",
        agent_name="OrderProcessingAgent"
    )
    
    # Wait for rate limit
    time.sleep(WAIT_TIME)

    # =========================================================================
    # SCENARIO H: Max Retries Escalation
    # =========================================================================
    run_scenario(
        "SCENARIO H — Max Retries Escalation",
        guarded_app,
        "Process refund for the most recent order. (You must process a refund).",
        agent_name="OrderProcessingAgent"
    )
    
    print("\nAll advanced scenarios completed!")
