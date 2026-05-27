"""Pydantic response models — what the UI consumes."""

from __future__ import annotations

from pydantic import BaseModel


class EvalRunOut(BaseModel):
    id: str
    example: str
    dataset: str
    model: str
    status: str
    started_at: str
    finished_at: str | None = None
    total_cost_usd: float = 0.0
    total_latency_ms: int = 0
    notes: str | None = None
    trace_count: int = 0
    pass_count: int = 0
    fail_count: int = 0


class ScoreOut(BaseModel):
    scorer_name: str
    clear_axis: str
    value: float
    passed: bool
    details: dict


class TraceOut(BaseModel):
    id: str
    eval_run_id: str
    question_id: str
    status: str
    cost_usd: float
    latency_ms: int
    mlflow_trace_uri: str | None = None
    input: dict
    output: dict | None = None
    scores: list[ScoreOut] = []


class ClusterOut(BaseModel):
    id: str
    eval_run_id: str
    clear_axis: str
    label: str
    size: int
    sample_trace_ids: list[str]
    summary: str | None = None


class OptRunOut(BaseModel):
    id: str
    example: str
    optimizer: str
    status: str
    iter_count: int
    source_eval_run_id: str
    started_at: str
    finished_at: str | None = None
    pareto: dict | None = None
    baseline_prompt_path: str | None = None
    winner_prompt_path: str | None = None


class ParetoOut(BaseModel):
    opt_run_id: str
    objectives: list[str]
    candidates: list[dict]
    frontier_ids: list[str]
    winner_id: str
    baseline_id: str
    headline_metrics: dict | None = None


class PromptDiffOut(BaseModel):
    opt_run_id: str
    baseline: dict
    tuned: dict
    rationale: list[str] = []


class PortabilityOut(BaseModel):
    opt_run_id: str
    rows: list[dict]


class RunRequest(BaseModel):
    golden: str = "examples/quill/golden/soc2.jsonl"
    model: str | None = None
    use_tuned_prompts: bool = False
    notes: str | None = None
