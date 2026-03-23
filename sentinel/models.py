from typing import Any, Dict, List, Literal, Optional
from datetime import datetime
import uuid
from pydantic import BaseModel, Field, model_validator

class EvidenceEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str
    tool_input: Dict[str, Any]
    tool_output: Dict[str, Any]
    turn_number: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class EvidenceCache(BaseModel):
    run_id: str
    entries: List[EvidenceEntry] = Field(default_factory=list)

    def add_entry(self, entry: EvidenceEntry):
        self.entries.append(entry)

    def get_by_tool(self, tool_name: str) -> List[EvidenceEntry]:
        return [e for e in self.entries if e.tool_name == tool_name]

    def to_context_string(self) -> str:
        """Serializes cache to a human-readable string for the LLM."""
        if not self.entries:
            return "No previous tool observations."
        
        lines = ["--- EVIDENCE CACHE ---"]
        for e in sorted(self.entries, key=lambda x: x.turn_number):
            lines.append(f"Turn {e.turn_number} - Tool: {e.tool_name}")
            lines.append(f"Inputs: {e.tool_input}")
            lines.append(f"Outputs: {e.tool_output}")
            lines.append("---")
        return "\n".join(lines)

class ProposedAction(BaseModel):
    tool_name: str
    tool_args: Dict[str, Any]
    turn_number: int

class ParameterGroundingResult(BaseModel):
    parameter_name: str
    parameter_value: Any
    is_grounded: bool
    confidence: float
    evidence_reference: Optional[str] = None
    check_method: Literal["rule", "llm", "policy"]

class ValidationResult(BaseModel):
    tool_name: str
    allowed: bool
    confidence: float
    parameter_results: List[ParameterGroundingResult]
    blocking_reason: Optional[str] = None
    retry_feedback: Optional[str] = None
    policy_triggered: Optional[str] = None
    latency_ms: int
    check_layers_used: List[str]

    @model_validator(mode='after')
    def validate_block_state(self) -> 'ValidationResult':
        if self.allowed and self.blocking_reason is not None:
            if not self.blocking_reason.startswith("[SHADOW BLOCKED]"):
                raise ValueError("ValidationResult cannot be allowed=True while having a blocking_reason.")
        if not self.allowed and self.blocking_reason is None:
            raise ValueError("ValidationResult cannot be allowed=False without a specified blocking_reason.")
        return self

class PolicyRule(BaseModel):
    tool: str
    requires_prior_tool: Optional[str] = None
    hitl_required: bool = False
    condition: Optional[str] = None
    reason: Optional[str] = None

class PolicyViolation(BaseModel):
    is_violation: bool
    is_hitl_escalation: bool
    reason: str

class SentinelRunMetadata(BaseModel):
    run_id: str
    agent_name: str
    shadow_mode: bool
    prompt_hash: str
    started_at: datetime
    completed_at: Optional[datetime] = None

class HITLEscalation(BaseModel):
    run_id: str
    proposed_action: ProposedAction
    evidence_snapshot: EvidenceCache
    policy_that_triggered: str
    escalated_at: datetime
