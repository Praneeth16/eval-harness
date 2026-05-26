"""SQLAlchemy ORM — mirrors `core/store/schema.sql`."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class EvalRun(Base):
    __tablename__ = "eval_run"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    example: Mapped[str] = mapped_column(String, nullable=False)
    dataset: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)  # pending|running|done|failed|cancelled
    started_at: Mapped[str] = mapped_column(String, nullable=False, default=_utcnow_iso)
    finished_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    config_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_cost_usd: Mapped[float] = mapped_column(default=0.0, nullable=False)
    total_latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    traces: Mapped[list[Trace]] = relationship(
        back_populates="eval_run", cascade="all, delete-orphan"
    )
    clusters: Mapped[list[Cluster]] = relationship(
        back_populates="eval_run", cascade="all, delete-orphan"
    )


class Trace(Base):
    __tablename__ = "trace"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    eval_run_id: Mapped[str] = mapped_column(
        ForeignKey("eval_run.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    input_json: Mapped[str] = mapped_column(Text, nullable=False)
    output_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)  # ok|error
    mlflow_trace_uri: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    started_at: Mapped[str] = mapped_column(String, nullable=False, default=_utcnow_iso)
    finished_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    cost_usd: Mapped[float] = mapped_column(default=0.0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    eval_run: Mapped[EvalRun] = relationship(back_populates="traces")
    scores: Mapped[list[Score]] = relationship(
        back_populates="trace", cascade="all, delete-orphan"
    )


class Score(Base):
    __tablename__ = "score"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trace_id: Mapped[str] = mapped_column(
        ForeignKey("trace.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scorer_name: Mapped[str] = mapped_column(String, nullable=False)
    clear_axis: Mapped[str] = mapped_column(String, nullable=False, index=True)
    value: Mapped[float] = mapped_column(nullable=False)
    passed: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 0/1
    details_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=_utcnow_iso)

    trace: Mapped[Trace] = relationship(back_populates="scores")


class Cluster(Base):
    __tablename__ = "cluster"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    eval_run_id: Mapped[str] = mapped_column(
        ForeignKey("eval_run.id", ondelete="CASCADE"), nullable=False, index=True
    )
    clear_axis: Mapped[str] = mapped_column(String, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    sample_trace_ids_json: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=_utcnow_iso)

    eval_run: Mapped[EvalRun] = relationship(back_populates="clusters")


class OptRun(Base):
    __tablename__ = "opt_run"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    source_eval_run_id: Mapped[str] = mapped_column(
        ForeignKey("eval_run.id"), nullable=False, index=True
    )
    example: Mapped[str] = mapped_column(String, nullable=False)
    optimizer: Mapped[str] = mapped_column(String, nullable=False)  # "gepa"
    status: Mapped[str] = mapped_column(String, nullable=False)
    iter_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pareto_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    winner_prompt_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    baseline_prompt_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    started_at: Mapped[str] = mapped_column(String, nullable=False, default=_utcnow_iso)
    finished_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    config_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


__all__ = ["Base", "EvalRun", "Trace", "Score", "Cluster", "OptRun"]
