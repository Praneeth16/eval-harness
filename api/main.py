"""FastAPI app — read endpoints over the eval-harness store, plus a kickoff
endpoint for eval runs.

Tracing UI is NOT rebuilt here — `trace.mlflow_trace_uri` is returned and
the Next.js UI links out to MLflow.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc, func, select

from api.schemas import (
    ClusterOut,
    EvalRunOut,
    OptRunOut,
    ParetoOut,
    PortabilityOut,
    PromptDiffOut,
    RunRequest,
    ScoreOut,
    TraceOut,
)
from core.config import REPO_ROOT, settings
from core.store.db import get_session, init_db
from core.store.models import Cluster, EvalRun, OptRun, Score, Trace
from core.tracing import init_mlflow

log = logging.getLogger(__name__)

app = FastAPI(
    title="eval-harness",
    description=(
        "Self-evolving eval harness for production AI agents. "
        "Companion API for the 'Journey of an Agent' session."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api_cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_mlflow()
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# ─────────────────────────────────────────────────────────────────────────
# Eval runs
# ─────────────────────────────────────────────────────────────────────────


def _serialize_eval_run(row: EvalRun, *, trace_count: int = 0, pass_count: int = 0) -> EvalRunOut:
    return EvalRunOut(
        id=row.id,
        example=row.example,
        dataset=row.dataset,
        model=row.model,
        status=row.status,
        started_at=row.started_at,
        finished_at=row.finished_at,
        total_cost_usd=row.total_cost_usd,
        total_latency_ms=row.total_latency_ms,
        notes=row.notes,
        trace_count=trace_count,
        pass_count=pass_count,
        fail_count=max(0, trace_count - pass_count),
    )


@app.get("/runs", response_model=list[EvalRunOut])
def list_runs(limit: int = 50) -> list[EvalRunOut]:
    with get_session() as s:
        rows = s.execute(
            select(EvalRun).order_by(desc(EvalRun.started_at)).limit(limit)
        ).scalars().all()
        out: list[EvalRunOut] = []
        for r in rows:
            tc = s.execute(
                select(func.count(Trace.id)).where(Trace.eval_run_id == r.id)
            ).scalar_one()
            # Pass = no failing scores for the trace.
            fail_trace_ids = s.execute(
                select(Trace.id)
                .join(Score, Score.trace_id == Trace.id)
                .where(Trace.eval_run_id == r.id, Score.passed == 0)
                .distinct()
            ).scalars().all()
            pc = max(0, tc - len(set(fail_trace_ids)))
            out.append(_serialize_eval_run(r, trace_count=tc, pass_count=pc))
        return out


@app.get("/runs/{run_id}", response_model=EvalRunOut)
def get_run(run_id: str) -> EvalRunOut:
    with get_session() as s:
        row = s.get(EvalRun, run_id)
        if row is None:
            raise HTTPException(404, "run not found")
        tc = s.execute(
            select(func.count(Trace.id)).where(Trace.eval_run_id == run_id)
        ).scalar_one()
        fail_trace_ids = s.execute(
            select(Trace.id)
            .join(Score, Score.trace_id == Trace.id)
            .where(Trace.eval_run_id == run_id, Score.passed == 0)
            .distinct()
        ).scalars().all()
        return _serialize_eval_run(row, trace_count=tc, pass_count=max(0, tc - len(set(fail_trace_ids))))


@app.get("/runs/{run_id}/traces", response_model=list[TraceOut])
def list_traces(run_id: str, limit: int = 500) -> list[TraceOut]:
    with get_session() as s:
        traces = s.execute(
            select(Trace).where(Trace.eval_run_id == run_id).limit(limit)
        ).scalars().all()
        if not traces:
            return []
        trace_ids = [t.id for t in traces]
        scores_by_trace: dict[str, list[Score]] = {tid: [] for tid in trace_ids}
        score_rows = s.execute(
            select(Score).where(Score.trace_id.in_(trace_ids))
        ).scalars().all()
        for sc in score_rows:
            scores_by_trace[sc.trace_id].append(sc)

        return [
            TraceOut(
                id=t.id,
                eval_run_id=t.eval_run_id,
                question_id=t.question_id,
                status=t.status,
                cost_usd=t.cost_usd,
                latency_ms=t.latency_ms,
                mlflow_trace_uri=t.mlflow_trace_uri,
                input=json.loads(t.input_json) if t.input_json else {},
                output=json.loads(t.output_json) if t.output_json else None,
                scores=[
                    ScoreOut(
                        scorer_name=sc.scorer_name,
                        clear_axis=sc.clear_axis,
                        value=sc.value,
                        passed=bool(sc.passed),
                        details=json.loads(sc.details_json) if sc.details_json else {},
                    )
                    for sc in scores_by_trace[t.id]
                ],
            )
            for t in traces
        ]


@app.get("/traces/{trace_id}", response_model=TraceOut)
def get_trace(trace_id: str) -> TraceOut:
    with get_session() as s:
        t = s.get(Trace, trace_id)
        if t is None:
            raise HTTPException(404, "trace not found")
        score_rows = s.execute(select(Score).where(Score.trace_id == trace_id)).scalars().all()
        return TraceOut(
            id=t.id,
            eval_run_id=t.eval_run_id,
            question_id=t.question_id,
            status=t.status,
            cost_usd=t.cost_usd,
            latency_ms=t.latency_ms,
            mlflow_trace_uri=t.mlflow_trace_uri,
            input=json.loads(t.input_json) if t.input_json else {},
            output=json.loads(t.output_json) if t.output_json else None,
            scores=[
                ScoreOut(
                    scorer_name=sc.scorer_name,
                    clear_axis=sc.clear_axis,
                    value=sc.value,
                    passed=bool(sc.passed),
                    details=json.loads(sc.details_json) if sc.details_json else {},
                )
                for sc in score_rows
            ],
        )


# ─────────────────────────────────────────────────────────────────────────
# Clusters
# ─────────────────────────────────────────────────────────────────────────


@app.get("/clusters/{run_id}", response_model=list[ClusterOut])
def list_clusters(run_id: str) -> list[ClusterOut]:
    with get_session() as s:
        rows = s.execute(
            select(Cluster).where(Cluster.eval_run_id == run_id).order_by(Cluster.clear_axis)
        ).scalars().all()
        return [
            ClusterOut(
                id=r.id,
                eval_run_id=r.eval_run_id,
                clear_axis=r.clear_axis,
                label=r.label,
                size=r.size,
                sample_trace_ids=json.loads(r.sample_trace_ids_json) if r.sample_trace_ids_json else [],
                summary=r.summary,
            )
            for r in rows
        ]


@app.post("/clusters/{run_id}/build", response_model=list[ClusterOut])
def build_clusters(run_id: str) -> list[ClusterOut]:
    from core.clusters import cluster_run

    descriptors = cluster_run(run_id)
    return [
        ClusterOut(
            id=d.cluster_id,
            eval_run_id=d.eval_run_id,
            clear_axis=d.clear_axis,
            label=d.label,
            size=d.size,
            sample_trace_ids=d.sample_trace_ids,
            summary=d.summary,
        )
        for d in descriptors
    ]


# ─────────────────────────────────────────────────────────────────────────
# Optimization runs (GEPA) + Pareto
# ─────────────────────────────────────────────────────────────────────────


def _opt_to_out(row: OptRun) -> OptRunOut:
    return OptRunOut(
        id=row.id,
        example=row.example,
        optimizer=row.optimizer,
        status=row.status,
        iter_count=row.iter_count,
        source_eval_run_id=row.source_eval_run_id,
        started_at=row.started_at,
        finished_at=row.finished_at,
        pareto=json.loads(row.pareto_json) if row.pareto_json else None,
        baseline_prompt_path=row.baseline_prompt_path,
        winner_prompt_path=row.winner_prompt_path,
    )


@app.get("/opt-runs", response_model=list[OptRunOut])
def list_opt_runs(limit: int = 50) -> list[OptRunOut]:
    with get_session() as s:
        rows = s.execute(
            select(OptRun).order_by(desc(OptRun.started_at)).limit(limit)
        ).scalars().all()
        return [_opt_to_out(r) for r in rows]


@app.get("/opt-runs/{opt_id}", response_model=OptRunOut)
def get_opt_run(opt_id: str) -> OptRunOut:
    with get_session() as s:
        r = s.get(OptRun, opt_id)
        if r is None:
            raise HTTPException(404, "opt run not found")
        return _opt_to_out(r)


@app.get("/pareto/{opt_id}", response_model=ParetoOut)
def get_pareto(opt_id: str) -> ParetoOut:
    with get_session() as s:
        r = s.get(OptRun, opt_id)
        if r is None or not r.pareto_json:
            raise HTTPException(404, "pareto not available")
        payload = json.loads(r.pareto_json)

        # Side-car headline numbers (read from a JSON file written by prebake).
        headline_path = REPO_ROOT / "examples" / r.example / "prebaked" / "headline.json"
        headline = None
        if headline_path.exists():
            try:
                headline = json.loads(headline_path.read_text())
            except json.JSONDecodeError:
                headline = None

        return ParetoOut(
            opt_run_id=opt_id,
            objectives=payload.get("objectives", []),
            candidates=payload.get("candidates", []),
            frontier_ids=payload.get("frontier_ids", []),
            winner_id=payload.get("winner_id", ""),
            baseline_id=payload.get("baseline_id", ""),
            headline_metrics=headline,
        )


def _load_prompt_module(path: str) -> dict:
    """Load a prompt module by path (e.g. examples/quill/prompts/baseline.py)
    and return its public string constants + flags."""
    full = REPO_ROOT / path
    if not full.exists():
        return {}
    import importlib.util

    spec = importlib.util.spec_from_file_location(f"_promptmod_{full.stem}", full)
    if spec is None or spec.loader is None:
        return {}
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out: dict = {}
    for name in dir(mod):
        if name.startswith("_"):
            continue
        val = getattr(mod, name)
        if isinstance(val, (str, bool, int, float)):
            out[name] = val
    return out


@app.get("/prompt-diff/{opt_id}", response_model=PromptDiffOut)
def get_prompt_diff(opt_id: str) -> PromptDiffOut:
    with get_session() as s:
        r = s.get(OptRun, opt_id)
        if r is None:
            raise HTTPException(404, "opt run not found")
        baseline = _load_prompt_module(r.baseline_prompt_path or "")
        tuned = _load_prompt_module(r.winner_prompt_path or "")

        rationale: list[str] = []
        if r.pareto_json:
            try:
                payload = json.loads(r.pareto_json)
                for c in payload.get("candidates", []):
                    if c.get("rationale"):
                        rationale.append(c["rationale"])
            except json.JSONDecodeError:
                pass

        return PromptDiffOut(
            opt_run_id=opt_id, baseline=baseline, tuned=tuned, rationale=rationale
        )


@app.get("/portability/{opt_id}", response_model=PortabilityOut)
def get_portability(opt_id: str) -> PortabilityOut:
    """Cross-model portability table. Read from a sidecar JSON file written
    by the prebake script — keeping the API stateless about portability runs.
    """
    with get_session() as s:
        r = s.get(OptRun, opt_id)
        if r is None:
            raise HTTPException(404, "opt run not found")
    path = REPO_ROOT / "examples" / r.example / "prebaked" / "portability.json"
    rows: list[dict] = []
    if path.exists():
        try:
            rows = json.loads(path.read_text()).get("rows", [])
        except json.JSONDecodeError:
            rows = []
    return PortabilityOut(opt_run_id=opt_id, rows=rows)


# ─────────────────────────────────────────────────────────────────────────
# Kick off an eval run (background)
# ─────────────────────────────────────────────────────────────────────────


@app.post("/examples/quill/run")
def kickoff_quill_run(req: RunRequest, bg: BackgroundTasks) -> dict:
    from core.eval import run_eval

    golden = (REPO_ROOT / req.golden) if not Path(req.golden).is_absolute() else Path(req.golden)
    if not golden.exists():
        raise HTTPException(400, f"golden not found: {golden}")

    prompts: dict = {}
    if req.use_tuned_prompts:
        from examples.quill.prompts.tuned import as_prompts_dict

        prompts = as_prompts_dict()

    def _job() -> None:
        try:
            run_eval(
                example="quill",
                golden_path=golden,
                model=req.model,
                prompts=prompts,
                notes=req.notes or "",
            )
        except Exception:
            log.exception("background eval failed")

    bg.add_task(_job)
    return {"status": "queued", "golden": str(golden), "use_tuned_prompts": req.use_tuned_prompts}


# ─────────────────────────────────────────────────────────────────────────
# Convenience: latest opt run id (so the UI doesn't need to scrape /opt-runs)
# ─────────────────────────────────────────────────────────────────────────


@app.get("/latest")
def latest() -> dict:
    with get_session() as s:
        run = s.execute(select(EvalRun).order_by(desc(EvalRun.started_at)).limit(1)).scalar_one_or_none()
        opt = s.execute(select(OptRun).order_by(desc(OptRun.started_at)).limit(1)).scalar_one_or_none()
        return {
            "latest_run_id": run.id if run else None,
            "latest_opt_id": opt.id if opt else None,
        }


__all__ = ["app"]
