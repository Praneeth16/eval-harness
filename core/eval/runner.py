"""Eval runner.

Iterates a golden-set JSONL, runs the example's pipeline per question,
scores every output across all CLEAR-S axes, persists everything to the
SQLite store, and emits MLflow traces.

`run_eval` is the public entry point. CLI calls it through `core.cli`.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.config import settings
from core.scorers import ScoreContext, ScoreResult
from core.scorers.registry import all_scorers
from core.store.db import get_session, init_db
from core.store.models import EvalRun, Score, Trace
from core.tracing import init_mlflow
from core.tracing.mlflow_setup import mlflow_trace_url

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────


def _iter_golden(path: Path) -> Iterable[dict]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def _build_context(row: dict, result: Any) -> ScoreContext:
    return {
        "question": row.get("question", ""),
        "gold_answer": row.get("gold_answer", ""),
        "expected_citations": row.get("expected_citations") or [],
        "axis_focus": row.get("axis_focus") or [],
        "framework": row.get("framework") or "",
        "answer": getattr(result, "answer", ""),
        "citations": getattr(result, "citations", []) or [],
        "retrieved": getattr(result, "retrieved", []) or [],
        "tool_invocations": getattr(result, "tool_invocations", []) or [],
        "latency_ms": getattr(result, "latency_ms", 0),
        "cost_usd": getattr(result, "cost_usd", 0.0),
        "raw_state": getattr(result, "raw_state", {}) or {},
    }


# ─────────────────────────────────────────────────────────────────────────


@dataclass
class EvalRunSummary:
    run_id: str
    example: str
    dataset: str
    model: str
    total: int
    pass_count: int
    fail_count: int
    avg_cost_usd: float
    avg_latency_ms: float
    per_axis_pass_rate: dict[str, float] = field(default_factory=dict)
    score_aggregates: dict[str, float] = field(default_factory=dict)


def _aggregate(scores: list[ScoreResult]) -> dict[str, float]:
    """Mean per scorer (across all traces)."""
    if not scores:
        return {}
    by_name: dict[str, list[float]] = {}
    for s in scores:
        by_name.setdefault(s.scorer_name, []).append(s.value)
    return {k: sum(v) / len(v) for k, v in by_name.items()}


def _axis_pass_rate(scores: list[ScoreResult]) -> dict[str, float]:
    by_axis: dict[str, list[bool]] = {}
    for s in scores:
        by_axis.setdefault(s.clear_axis, []).append(s.passed)
    return {
        axis: (sum(1 for x in vals if x) / len(vals)) if vals else 0.0
        for axis, vals in by_axis.items()
    }


def run_eval(
    *,
    example: str,
    golden_path: str | Path,
    model: str | None = None,
    prompts: dict[str, str] | None = None,
    include_judges: bool = True,
    notes: str = "",
    runner_fn: Callable[..., Any] | None = None,
) -> EvalRunSummary:
    """Run the eval. Persists everything; returns aggregate summary.

    `runner_fn` is the example-specific entry point with signature
    `(question_text, question_id, *, model, prompts) -> QuillResult`-like.
    """
    init_mlflow()
    init_db()

    if runner_fn is None:
        if example == "quill":
            from examples.quill.graph import run_question as quill_run

            runner_fn = quill_run
        else:
            raise ValueError(f"unknown example: {example}")

    golden_path = Path(golden_path)
    rows = list(_iter_golden(golden_path))
    if not rows:
        raise ValueError(f"golden set is empty: {golden_path}")

    scorers = all_scorers(include_judges=include_judges)

    run_id = f"run_{uuid.uuid4().hex[:12]}"
    started = time.time()
    log.info("eval start: run_id=%s example=%s n=%d", run_id, example, len(rows))

    all_scores: list[ScoreResult] = []
    per_trace_pass: list[bool] = []
    total_cost = 0.0
    total_latency = 0

    with get_session() as s:
        s.add(
            EvalRun(
                id=run_id,
                example=example,
                dataset=str(golden_path.name),
                model=model or settings.default_model,
                status="running",
                config_json=json.dumps(
                    {
                        "model": model or settings.default_model,
                        "judge_model": settings.judge_model,
                        "include_judges": include_judges,
                        "prompts_keys": sorted((prompts or {}).keys()),
                    }
                ),
                notes=notes,
            )
        )

    for i, row in enumerate(rows, start=1):
        qid = row.get("id") or f"Q{i:03d}"
        log.info("[%d/%d] %s", i, len(rows), qid)
        try:
            result = runner_fn(
                row.get("question", ""),
                qid,
                model=model,
                prompts=prompts or {},
            )
        except Exception:
            log.exception("question failed: %s", qid)
            with get_session() as s:
                s.add(
                    Trace(
                        id=f"trc_{uuid.uuid4().hex[:12]}",
                        eval_run_id=run_id,
                        question_id=qid,
                        input_json=json.dumps(row),
                        output_json=None,
                        status="error",
                    )
                )
            continue

        ctx = _build_context(row, result)
        trace_id = f"trc_{uuid.uuid4().hex[:12]}"

        # Score against all axes.
        per_trace_scores: list[ScoreResult] = []
        for scorer in scorers:
            try:
                sr = scorer(ctx)
            except Exception as e:
                log.exception("scorer %s failed", getattr(scorer, "__name__", "?"))
                sr = ScoreResult(
                    scorer_name=getattr(scorer, "__name__", "?"),
                    clear_axis="correctness",
                    value=0.0,
                    passed=False,
                    details={"error": str(e)},
                )
            per_trace_scores.append(sr)
            all_scores.append(sr)

        trace_passed = all(s.passed for s in per_trace_scores)
        per_trace_pass.append(trace_passed)
        total_cost += float(ctx["cost_usd"])
        total_latency += int(ctx["latency_ms"])

        mlflow_uri = (
            mlflow_trace_url(result.mlflow_trace_id)
            if getattr(result, "mlflow_trace_id", None)
            else None
        )

        with get_session() as s:
            s.add(
                Trace(
                    id=trace_id,
                    eval_run_id=run_id,
                    question_id=qid,
                    input_json=json.dumps(row),
                    output_json=json.dumps(
                        {
                            "answer": result.answer,
                            "citations": result.citations,
                            "category": result.category,
                            "gap_detected": result.gap_detected,
                            "risk_tier": result.risk_tier,
                            "tool_invocations": result.tool_invocations,
                            "retrieved_ids": [
                                r.get("chunk_id") for r in (result.retrieved or [])
                            ],
                        }
                    ),
                    status="ok",
                    mlflow_trace_uri=mlflow_uri,
                    cost_usd=float(ctx["cost_usd"]),
                    latency_ms=int(ctx["latency_ms"]),
                )
            )
            for sr in per_trace_scores:
                s.add(
                    Score(
                        trace_id=trace_id,
                        scorer_name=sr.scorer_name,
                        clear_axis=sr.clear_axis,
                        value=float(sr.value),
                        passed=1 if sr.passed else 0,
                        details_json=json.dumps(sr.details),
                    )
                )

    elapsed = time.time() - started
    pass_count = sum(1 for p in per_trace_pass if p)
    fail_count = len(per_trace_pass) - pass_count
    summary = EvalRunSummary(
        run_id=run_id,
        example=example,
        dataset=str(golden_path.name),
        model=model or settings.default_model,
        total=len(per_trace_pass),
        pass_count=pass_count,
        fail_count=fail_count,
        avg_cost_usd=(total_cost / max(len(per_trace_pass), 1)),
        avg_latency_ms=(total_latency / max(len(per_trace_pass), 1)),
        per_axis_pass_rate=_axis_pass_rate(all_scores),
        score_aggregates=_aggregate(all_scores),
    )

    with get_session() as s:
        run_row = s.get(EvalRun, run_id)
        if run_row is not None:
            run_row.status = "done"
            run_row.total_cost_usd = total_cost
            run_row.total_latency_ms = total_latency

    log.info(
        "eval done: run_id=%s pass=%d/%d cost=$%.4f elapsed=%.1fs",
        run_id,
        pass_count,
        len(per_trace_pass),
        total_cost,
        elapsed,
    )
    return summary


__all__ = ["EvalRunSummary", "run_eval"]
