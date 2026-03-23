from typing import Annotated, Optional, List
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

from sentinel.models import (
    EvidenceCache,
    ProposedAction,
    ValidationResult,
    SentinelRunMetadata
)

def reduce_evidence_cache(left: Optional[EvidenceCache], right: Optional[EvidenceCache]) -> EvidenceCache:
    """Explicitly merges cache entries protecting LangGraph cyclic states."""
    if not left: 
        return right if right else EvidenceCache(run_id="default")
    if not right: 
        return left
    # Preserve immutability bounds by returning the appended list safely
    merged_entries = left.entries.copy()
    existing_ids = {e.entry_id for e in left.entries}
    for e in right.entries:
        if e.entry_id not in existing_ids:
            merged_entries.append(e)
    # The run_id generally aligns between left and right safely in V1
    new_cache = EvidenceCache(run_id=left.run_id)
    new_cache.entries = merged_entries
    return new_cache

class SentinelState(TypedDict):
    messages: Annotated[list, add_messages]
    evidence_cache: Annotated[EvidenceCache, reduce_evidence_cache]
    pending_action: Optional[ProposedAction]
    last_validation: Optional[ValidationResult]
    hitl_pending: bool
    hitl_decision: Optional[str] # "approved" or "rejected"
    retry_count: int
    run_metadata: SentinelRunMetadata
    blocked_actions: List[ValidationResult]
