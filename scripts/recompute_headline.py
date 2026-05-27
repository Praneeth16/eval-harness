"""Recompute headline.json + portability.json from the latest prebake runs
in SQLite without re-running any LLM calls.

Useful when scorer aggregation logic changes and the existing prebaked
runs are still valid — just need fresh headline numbers.
"""

from __future__ import annotations

import json
import logging

from sqlalchemy import desc, select

from core.config import REPO_ROOT, settings
from core.eval.runner import EvalRunSummary, _aggregate, _axis_pass_rate
from core.scorers import ScoreResult
from core.store.db import get_session
from core.store.models import EvalRun, Score, Trace
from scripts.prebake import _headline_from_summaries, _portability_row

log = logging.getLogger(__name__)


def _summary_for(run_notes_pattern: str) -> EvalRunSummary | None:
    """Build an EvalRunSummary from the latest run matching the notes pattern."""
    with get_session() as s:
        run = s.execute(
            select(EvalRun)
            .where(EvalRun.notes.like(f"%{run_notes_pattern}%"))
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
        # Pass per trace: no failing score for that trace.
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


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    baseline = _summary_for("prebake:baseline:soc2")
    tuned = _summary_for("prebake:tuned:soc2")
    holdout = _summary_for("prebake:tuned:iso27001-holdout")

    if baseline is None or tuned is None:
        raise SystemExit(
            "missing baseline or tuned run — run scripts.prebake first."
        )

    headline = _headline_from_summaries(baseline, tuned, holdout)
    prebaked = REPO_ROOT / "examples/quill/prebaked"
    prebaked.mkdir(parents=True, exist_ok=True)
    (prebaked / "headline.json").write_text(json.dumps(headline, indent=2))
    log.info("headline.json updated (baseline=%s tuned=%s)", baseline.run_id, tuned.run_id)

    # Portability rows from any prebake:portability:* runs that exist.
    rows: list[dict] = []
    if holdout is not None:
        rows.append(
            _portability_row(
                settings.default_model, "gemini", holdout,
                notes="primary model on cross-framework holdout",
            )
        )
    for model in settings.portability_model_list:
        if model == settings.default_model:
            continue
        summary = _summary_for(f"prebake:portability:{model}")
        if summary is None:
            continue
        family = model.split("/")[0] if "/" in model else model.split("-")[0]
        notes = ""
        if summary.score_aggregates.get("policy_exists_called_before_cite", 1.0) < 0.95:
            notes = "regression on policy_exists_called_before_cite — blocks deploy"
        elif summary.per_axis_pass_rate.get("correctness", 0.0) < 0.80:
            notes = "below ship threshold on correctness"
        rows.append(_portability_row(model, family, summary, notes=notes))

    if rows:
        (prebaked / "portability.json").write_text(
            json.dumps({"rows": rows}, indent=2)
        )
        log.info("portability.json updated (rows=%d)", len(rows))
    else:
        log.info("no portability rows to write")


if __name__ == "__main__":
    main()
