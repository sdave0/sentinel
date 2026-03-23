import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.sqlite import JSON

class Base(DeclarativeBase):
    pass

class SentinelRun(Base):
    __tablename__ = "sentinel_runs"

    run_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_name: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    shadow_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    prompt_hash: Mapped[str] = mapped_column(String, nullable=True)
    total_tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    total_blocked: Mapped[int] = mapped_column(Integer, default=0)
    total_escalated: Mapped[int] = mapped_column(Integer, default=0)

class SentinelValidation(Base):
    __tablename__ = "sentinel_validations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("sentinel_runs.run_id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    tool_name: Mapped[str] = mapped_column(String, nullable=False)
    proposed_args: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    verdict: Mapped[str] = mapped_column(String, nullable=False)  # allowed/blocked/escalated
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    blocking_reason: Mapped[str] = mapped_column(Text, nullable=True)
    retry_feedback: Mapped[str] = mapped_column(Text, nullable=True)
    policy_triggered: Mapped[str] = mapped_column(String, nullable=True)
    evidence_used: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=True)
