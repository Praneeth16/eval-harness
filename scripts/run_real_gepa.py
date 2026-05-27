"""Run a live GEPA loop against the current baseline.

Use after `scripts.prebake` has produced a real baseline + tuned. This
runs the actual reflective-mutation algorithm in `core.optimizer.gepa`:

  * pulls failed traces from the baseline run
  * asks the judge LLM for a textual diagnosis + prompt patch
  * evaluates each candidate against a small held-out sample
  * Pareto-selects across the configured objectives
  * persists candidates + rationale into a new `OptRun.pareto_json`

Default settings keep the loop under ~5 minutes / ~$0.10:

  * `n_iters=4`        — four mutations
  * `sample_size=5`    — five-question slice of soc2.jsonl

For longer runs pass `--iters` / `--sample` flags.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from sqlalchemy import desc, select

from core.config import REPO_ROOT
from core.eval.runner import EvalRunSummary, _aggregate, _axis_pass_rate
from core.optimizer.gepa import run_gepa
from core.scorers import ScoreResult
from core.store.db import get_session, init_db
from core.store.models import EvalRun, Score, Trace
from core.tracing import init_mlflow

log = logging.getLogger(__name__)


def _summary_for_notes(pattern: str) -> EvalRunSummary | None:
    import json

    with get_session() as s:
        run = s.execute(
            select(EvalRun)
            .where(EvalRun.notes.like(f"%{pattern}%"))
            .order_by(desc(EvalRun.started_at))
            .limit(1)
        ).scalar_one_or_none()
        if run is None:
            return None
        traces = s.execute(
            select(Trace).where(Trace.eval_run_id == run.id)
        ).scalars().all()
        if not traces:
            return None
        trace_ids = [t.id for t in traces]
        score_rows = s.execute(
            select(Score).where(Score.trace_id.in_(trace_ids))
        ).scalars().all()
        scores = [
            ScoreResult(
                scorer_name=sr.scorer_name,
                clear_axis=sr.clear_axis,
                value=float(sr.value),
                passed=bool(sr.passed),
                details=json.loads(sr.details_json) if sr.details_json else {},
            )
            for sr in score_rows
        ]
        fail_ids = {sr.trace_id for sr in score_rows if not sr.passed}
        pass_count = sum(1 for t in traces if t.id not in fail_ids)
        total_cost = sum(t.cost_usd for t in traces)
        total_latency = sum(t.latency_ms for t in traces)
        return EvalRunSummary(
            run_id=run.id,
            example=run.example,
            dataset=run.dataset,
            model=run.model,
            total=len(traces),
            pass_count=pass_count,
            fail_count=len(traces) - pass_count,
            avg_cost_usd=total_cost / len(traces),
            avg_latency_ms=total_latency / len(traces),
            per_axis_pass_rate=_axis_pass_rate(scores),
            score_aggregates=_aggregate(scores),
        )


def _subset_golden(src: Path, out: Path, n: int) -> Path:
    rows: list[str] = []
    with src.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= n:
                break
            rows.append(line)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(rows))
    return out


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--iters", type=int, default=4)
    parser.add_argument("--sample", type=int, default=5)
    args = parser.parse_args()

    init_mlflow()
    init_db()

    baseline_summary = _summary_for_notes("prebake:baseline:soc2")
    if baseline_summary is None:
        raise SystemExit(
            "no baseline run found — run `make prebake` (or "
            "`python -m scripts.prebake --mode fast`) first."
        )

    # Use a small subset so 4-8 GEPA iterations stay quick + cheap.
    full_golden = REPO_ROOT / "examples/quill/golden/soc2.jsonl"
    subset_path = REPO_ROOT / ".data" / "gepa-subset.jsonl"
    _subset_golden(full_golden, subset_path, args.sample)

    log.info(
        "running real GEPA loop: iters=%d sample=%d baseline=%s",
        args.iters, args.sample, baseline_summary.run_id,
    )

    result = run_gepa(
        baseline_prompts={},  # baseline defaults from prompts/baseline.py
        source_eval_run_id=baseline_summary.run_id,
        source_summary=baseline_summary,
        example="quill",
        golden_path=subset_path,
        max_iters=args.iters,
        seeded_winner=None,  # ← real mutation loop, no shortcut
    )

    print(f"\nGEPA done.")
    print(f"  opt_run_id: {result.opt_run_id}")
    print(f"  winner:     {result.winner.candidate_id}")
    print(f"  rationale:  {result.winner.mutation_rationale[:200]}")
    print(f"\nOpen: http://localhost:3000/pareto/{result.opt_run_id}\n")


if __name__ == "__main__":
    main()
