import os
from typing import List, Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from loguru import logger

from sentinel.db_models import SentinelRun, SentinelValidation
from sentinel.models import SentinelRunMetadata, ValidationResult

# Initialize Database connection
DB_URL = os.environ.get("DATABASE_URL", "sqlite:///./sentinel.db")
try:
    engine = create_engine(DB_URL, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info(f"Database engine initialized for {DB_URL}")
except Exception as e:
    logger.error(f"Failed to initialize database engine: {e}")
    raise

def _build_validation_models(run_id: str, validations: List[ValidationResult]) -> List[SentinelValidation]:
    records = []
    for val in validations:
        args_dump = {p.parameter_name: p.parameter_value for p in val.parameter_results}
        evidence_dump = {p.parameter_name: p.evidence_reference for p in val.parameter_results if p.evidence_reference}
        
        records.append(SentinelValidation(
            run_id=run_id,
            tool_name=val.tool_name,
            proposed_args=args_dump,
            verdict="allowed" if val.allowed else ("escalated" if val.policy_triggered else "blocked"),
            confidence=val.confidence,
            blocking_reason=val.blocking_reason,
            retry_feedback=val.retry_feedback,
            policy_triggered=str(val.policy_triggered) if val.policy_triggered else None,
            evidence_used=evidence_dump,
            latency_ms=val.latency_ms
        ))
    return records

def save_run(metadata: SentinelRunMetadata, validations: List[ValidationResult]) -> None:
    """Persists a complete agent run and its associated validation intercepts."""
    logger.info(f"Saving run {metadata.run_id} to database...")
    db = SessionLocal()
    try:
        total_blocked = sum(1 for v in validations if not v.allowed and v.blocking_reason != "Requires human approval")
        total_escalated = sum(1 for v in validations if getattr(v, "policy_triggered", None) == "Requires human approval" or v.blocking_reason == "Requires human approval")
        
        db.add(SentinelRun(
            run_id=metadata.run_id,
            agent_name=metadata.agent_name,
            started_at=metadata.started_at,
            completed_at=metadata.completed_at,
            shadow_mode=metadata.shadow_mode,
            prompt_hash=metadata.prompt_hash,
            total_tool_calls=len(validations),
            total_blocked=total_blocked,
            total_escalated=total_escalated
        ))
        
        for val_record in _build_validation_models(metadata.run_id, validations):
            db.add(val_record)
            
        db.commit()
        logger.success(f"Successfully saved run {metadata.run_id} with {len(validations)} validations.")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error saving run {metadata.run_id}: {e}")
        raise
    finally:
        db.close()

def get_runs(limit: int = 50, min_calls: int = 1) -> List[Dict[str, Any]]:
    """Retrieves recent runs and aggregate statistics."""
    logger.debug(f"Fetching up to {limit} recent runs with >= {min_calls} calls")
    db = SessionLocal()
    try:
        query = db.query(SentinelRun)
        if min_calls > 0:
            query = query.filter(SentinelRun.total_tool_calls >= min_calls)
        runs = query.order_by(SentinelRun.started_at.desc()).limit(limit).all()
        results = []
        for r in runs:
            block_rate = (r.total_blocked / r.total_tool_calls * 100) if r.total_tool_calls > 0 else 0
            results.append({
                "run_id": r.run_id,
                "agent_name": r.agent_name,
                "started_at": r.started_at,
                "completed_at": r.completed_at,
                "shadow_mode": r.shadow_mode,
                "total_tool_calls": r.total_tool_calls,
                "total_blocked": r.total_blocked,
                "total_escalated": r.total_escalated,
                "block_rate_pct": round(block_rate, 2)
            })
        return results
    except Exception as e:
        logger.error(f"Error fetching runs: {e}")
        return []
    finally:
        db.close()

def get_run_detail(run_id: str) -> Dict[str, Any]:
    """Retrieves full run metadata and chronological validation intercepts."""
    logger.debug(f"Fetching detail for run {run_id}")
    db = SessionLocal()
    try:
        run = db.query(SentinelRun).filter(SentinelRun.run_id == run_id).first()
        if not run:
            logger.warning(f"Run {run_id} not found.")
            return {}
            
        validations = db.query(SentinelValidation).filter(SentinelValidation.run_id == run_id).order_by(SentinelValidation.timestamp.asc()).all()
        
        return {
            "metadata": {
                "run_id": run.run_id,
                "agent_name": run.agent_name,
                "started_at": run.started_at,
                "completed_at": run.completed_at,
                "shadow_mode": run.shadow_mode,
                "prompt_hash": run.prompt_hash,
                "total_tool_calls": run.total_tool_calls,
                "total_blocked": run.total_blocked,
                "total_escalated": run.total_escalated
            },
            "validations": [
                {
                    "id": v.id,
                    "timestamp": v.timestamp,
                    "tool_name": v.tool_name,
                    "proposed_args": v.proposed_args,
                    "verdict": v.verdict,
                    "confidence": v.confidence,
                    "blocking_reason": v.blocking_reason,
                    "retry_feedback": v.retry_feedback,
                    "policy_triggered": v.policy_triggered,
                    "evidence_used": v.evidence_used,
                    "latency_ms": v.latency_ms
                } for v in validations
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching detail for run {run_id}: {e}")
        return {}
    finally:
        db.close()
