"""GEPA bridge — turn a real ``dspy.GEPA`` run into the harness's artifacts.

The optimization itself is run by ``dspy.GEPA`` (reflective prompt evolution
with instance-level Pareto candidate selection) in ``scripts/run_real_gepa.py``.
This module's job is the *bridge*: take the ``DspyGEPAResult`` and

  1. re-score a bounded set of candidates (baseline seed, the per-instance
     Pareto frontier, and the winner) on the validation set with the **same**
     CLEAR-S scorers the rest of the harness uses, producing real 7-axis
     objectives + measured cost / latency;
  2. compute the multi-objective Pareto frontier over those 7 axes (the chart
     on ``/pareto/[id]`` and the deploy gate use all seven, not a scalar);
  3. persist an ``OptRun`` whose ``pareto_json`` matches the shape the API and
     UI already render;
  4. write the winner's evolved instructions to disk.

The Pareto math (`_dominates`, `pareto_frontier`) is unchanged — it was always
real; only the candidate *source* changed from a hand-rolled mutation loop to
genuine GEPA.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.config import settings
from core.eval.runner import EvalRunSummary, _aggregate, _axis_pass_rate, _build_context
from core.llm.models import estimate_cost_usd
from core.scorers import AXIS_C, AXIS_R, AXIS_S, ScoreResult
from core.scorers.registry import all_scorers
from core.store.db import get_session
from core.store.models import OptRun

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────


@dataclass
class GepaCandidate:
    candidate_id: str
    label: str  # "baseline" | "candidate-3" | "winner" | ...
    prompts: dict
    objectives: dict[str, float] = field(default_factory=dict)
    parent_id: str | None = None
    mutation_rationale: str = ""
    summary: EvalRunSummary | None = None

    def to_point(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "label": self.label,
            "parent_id": self.parent_id,
            "objectives": self.objectives,
            "rationale": self.mutation_rationale,
        }


# ─────────────────────────────────────────────────────────────────────────
# Pareto math (unchanged — minimization axes are sign-flipped in
# `_normalize_objectives` so higher is always better)
# ─────────────────────────────────────────────────────────────────────────


def _dominates(a: dict[str, float], b: dict[str, float], objectives: list[str]) -> bool:
    """A dominates B iff a >= b on every objective and a > b on at least one."""
    strictly_better = False
    for k in objectives:
        av = a.get(k, 0.0)
        bv = b.get(k, 0.0)
        if av < bv:
            return False
        if av > bv:
            strictly_better = True
    return strictly_better


def pareto_frontier(
    candidates: list[GepaCandidate], objectives: list[str]
) -> list[GepaCandidate]:
    frontier: list[GepaCandidate] = []
    for c in candidates:
        if any(
            _dominates(o.objectives, c.objectives, objectives)
            for o in candidates
            if o is not c
        ):
            continue
        frontier.append(c)
    return frontier


def _normalize_objectives(summary: EvalRunSummary) -> dict[str, float]:
    """Flip cost / latency so higher = better (single domination test)."""
    axis = summary.per_axis_pass_rate
    out = {
        "correctness": axis.get(AXIS_C, 0.0),
        "relevance": axis.get(AXIS_R, 0.0),
        "execution": axis.get("execution", 0.0),
        "safety": axis.get(AXIS_S, 0.0),
        "adherence": axis.get("adherence", 0.0),
    }
    budget = max(settings.cost_budget_per_eval_usd, 1e-9)
    total_cost = summary.avg_cost_usd * summary.total
    out["cost"] = max(0.0, 1.0 - (total_cost / budget))
    budget_ms = 8000.0
    out["latency"] = max(0.0, 1.0 - (summary.avg_latency_ms / budget_ms))
    return out


# ─────────────────────────────────────────────────────────────────────────
# DSPy candidate handling
# ─────────────────────────────────────────────────────────────────────────


def _candidate_instructions(cand: Any) -> dict[str, str]:
    """Normalize a GEPA candidate (a component_name -> instruction-text mapping,
    or a Module) into a plain ``{predictor_name: instruction}`` dict."""
    if isinstance(cand, dict):
        return {k: str(v) for k, v in cand.items()}
    # Module: read instructions off its named predictors.
    out: dict[str, str] = {}
    for name, pred in cand.named_predictors():
        out[name] = pred.signature.instructions
    return out


def program_from_instructions(instructions: dict[str, str]):
    """Rebuild a ``QuillProgram`` with the given per-predictor instructions."""
    from examples.quill.dspy_program import QuillProgram

    prog = QuillProgram()
    for name, pred in prog.named_predictors():
        if name in instructions:
            pred.signature = pred.signature.with_instructions(instructions[name])
    return prog


def _normalized_model_slug(model: str | None) -> str:
    """Strip litellm provider prefixes so the slug hits the cost registry."""
    if not model:
        return settings.default_model
    for prefix in ("openrouter/", "openai/", "gemini/", "google/"):
        if model.startswith(prefix) and prefix != "google/":
            return model[len(prefix):]
    return model


def rescore_program(
    program,
    rows: list[dict],
    *,
    model_slug: str | None,
    include_judges: bool = True,
    label: str = "candidate",
) -> EvalRunSummary:
    """Run a (rebuilt) DSPy program over golden rows with the real CLEAR-S
    scorers, measuring wall-clock latency and token cost. Returns a summary
    whose ``per_axis_pass_rate`` feeds ``_normalize_objectives``."""

    scorers = all_scorers(include_judges=include_judges)
    all_scores: list[ScoreResult] = []
    per_trace_pass: list[bool] = []
    total_cost = 0.0
    total_latency = 0
    slug = _normalized_model_slug(model_slug)

    for row in rows:
        t0 = time.perf_counter()
        try:
            pred = program(question=row.get("question", ""))
        except Exception:
            log.exception("rescore: program failed on %s", row.get("id"))
            continue
        latency_ms = int((time.perf_counter() - t0) * 1000)

        cost = 0.0
        try:
            usage = pred.get_lm_usage() or {}
            for _model, u in usage.items():
                cost += estimate_cost_usd(
                    slug,
                    int(u.get("prompt_tokens", 0) or 0),
                    int(u.get("completion_tokens", 0) or 0),
                )
        except Exception:
            pass

        ctx = _build_context(row, pred)
        ctx["cost_usd"] = cost
        ctx["latency_ms"] = latency_ms

        trace_scores: list[ScoreResult] = []
        for sc in scorers:
            try:
                trace_scores.append(sc(ctx))
            except Exception as e:
                trace_scores.append(
                    ScoreResult(
                        scorer_name=getattr(sc, "__name__", "?"),
                        clear_axis="correctness",
                        value=0.0,
                        passed=False,
                        details={"error": str(e)},
                    )
                )
        all_scores.extend(trace_scores)
        per_trace_pass.append(all(s.passed for s in trace_scores))
        total_cost += cost
        total_latency += latency_ms

    n = max(len(per_trace_pass), 1)
    pass_count = sum(1 for p in per_trace_pass if p)
    return EvalRunSummary(
        run_id=f"rescore_{label}",
        example="quill",
        dataset="gepa-rescore",
        model=slug,
        total=len(per_trace_pass),
        pass_count=pass_count,
        fail_count=len(per_trace_pass) - pass_count,
        avg_cost_usd=total_cost / n,
        avg_latency_ms=total_latency / n,
        per_axis_pass_rate=_axis_pass_rate(all_scores),
        score_aggregates=_aggregate(all_scores),
    )


def _select_indices(detailed, max_candidates: int) -> list[int]:
    """Baseline seed (0), the per-instance Pareto frontier, and the winner —
    deduped and capped so re-scoring stays affordable."""
    idxs: list[int] = [0, detailed.best_idx]
    for s in getattr(detailed, "per_val_instance_best_candidates", []) or []:
        # Element is a set of tying candidate indices, or a single int.
        if isinstance(s, int):
            idxs.append(s)
        else:
            idxs.extend(sorted(s))
    seen: set[int] = set()
    ordered: list[int] = []
    for i in idxs:
        if i not in seen and 0 <= i < len(detailed.candidates):
            seen.add(i)
            ordered.append(i)
    # Keep baseline + winner always; fill the rest up to the cap by val score.
    must = {0, detailed.best_idx}
    rest = [i for i in ordered if i not in must]
    rest.sort(key=lambda i: detailed.val_aggregate_scores[i], reverse=True)
    keep = list(must) + rest
    return keep[: max(max_candidates, len(must))]


# ─────────────────────────────────────────────────────────────────────────
# Winner prompt serialization (instructions → graph-compatible templates)
# ─────────────────────────────────────────────────────────────────────────


def winner_prompts_dict(instructions: dict[str, str]) -> dict:
    """Map evolved DSPy instructions into the LangGraph ``prompts`` dict so the
    winner can ship into the existing graph (prompt-diff / portability pages).
    Keeps the deterministic verify scaffold (``use_verification_tools``)."""
    from examples.quill.prompts import tuned as tp

    classify_instr = instructions.get("classify", "")
    draft_instr = instructions.get("draft", "")
    classifier_tpl = (
        f"{classify_instr}\n\nQuestion: {{question}}\n\n"
        'Return strict JSON: {{"category": "...", "confidence": 0.0-1.0}}'
    )
    drafter_final_tpl = (
        f"{draft_instr}\n\nQuestion:\n{{question}}\n\n"
        "Verified references (cite ONLY these):\n{verified_refs}\n\n"
        "Retrieved context (for content; do not cite anything outside the "
        "verified list):\n{context}\n\n"
        'Return strict JSON: {{"answer": "...", "citations": ["POL:ENC-001", ...]}}'
    )
    return {
        "classifier": classifier_tpl,
        "drafter_propose": tp.DRAFTER_PROPOSE_PROMPT,
        "drafter_final": drafter_final_tpl,
        "gap_detector": tp.GAP_DETECTOR_PROMPT,
        "risk_tierer": tp.RISK_TIERER_PROMPT,
        "use_verification_tools": True,
    }


def write_winner_prompts(instructions: dict[str, str], path: str | Path) -> Path:
    """Persist the winner's evolved instructions as an importable prompts module."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = (
        '"""GEPA-evolved Quill prompts — written by scripts/run_real_gepa.py.\n\n'
        "Auto-generated. The CLASSIFY / DRAFT instructions are what GEPA's\n"
        "reflective mutation converged on, seeded from the broken baseline.\n"
        '"""\n\n'
        "from __future__ import annotations\n\n"
        f"CLASSIFY_INSTRUCTION = {instructions.get('classify', '')!r}\n\n"
        f"DRAFT_INSTRUCTION = {instructions.get('draft', '')!r}\n"
    )
    path.write_text(body, encoding="utf-8")
    return path


# ─────────────────────────────────────────────────────────────────────────
# Public bridge
# ─────────────────────────────────────────────────────────────────────────


@dataclass
class GepaResult:
    opt_run_id: str
    source_eval_run_id: str
    pareto_json: dict
    baseline: GepaCandidate
    winner: GepaCandidate
    iteration_log: list[dict] = field(default_factory=list)


def build_opt_run(
    *,
    detailed,
    source_eval_run_id: str,
    example: str,
    valset_rows: list[dict],
    model_slug: str | None,
    objectives: list[str] | None = None,
    max_candidates: int = 8,
    rescore_n: int | None = None,
    rescore_include_judges: bool = True,
    winner_prompt_path: str = "examples/quill/prompts/tuned_gepa.py",
    baseline_prompt_path: str = "examples/quill/prompts/baseline.py",
    config_extra: dict | None = None,
) -> GepaResult:
    """Turn a ``DspyGEPAResult`` into a persisted ``OptRun`` with a real
    multi-objective Pareto frontier."""
    objectives = objectives or settings.gepa_objective_list or [
        "correctness", "relevance", "execution", "safety", "cost", "latency"
    ]
    if "adherence" not in objectives:
        objectives = [*objectives, "adherence"]

    rows = valset_rows[:rescore_n] if rescore_n else valset_rows
    opt_run_id = f"opt_{uuid.uuid4().hex[:12]}"
    started = time.time()

    keep = _select_indices(detailed, max_candidates)
    log.info(
        "gepa bridge: opt=%s rescoring %d/%d candidates on %d val rows (judges=%s)",
        opt_run_id, len(keep), len(detailed.candidates), len(rows), rescore_include_judges,
    )

    candidates: list[GepaCandidate] = []
    by_index: dict[int, GepaCandidate] = {}
    iteration_log: list[dict] = []
    for idx in keep:
        instructions = _candidate_instructions(detailed.candidates[idx])
        prog = program_from_instructions(instructions)
        summary = rescore_program(
            prog,
            rows,
            model_slug=model_slug,
            include_judges=rescore_include_judges,
            label=str(idx),
        )
        label = "baseline" if idx == 0 else f"candidate-{idx}"
        parents = detailed.parents[idx] if idx < len(detailed.parents) else None
        parent_idx = next((p for p in (parents or []) if p is not None), None)
        cand = GepaCandidate(
            candidate_id=f"cand_{idx:03d}",
            label=label,
            prompts=instructions,
            objectives=_normalize_objectives(summary),
            parent_id=(f"cand_{parent_idx:03d}" if parent_idx is not None else None),
            mutation_rationale=(
                f"GEPA candidate #{idx} · val_agg={detailed.val_aggregate_scores[idx]:.3f} · "
                f"discovered at {detailed.discovery_eval_counts[idx]} metric calls"
            ),
            summary=summary,
        )
        candidates.append(cand)
        by_index[idx] = cand
        iteration_log.append(
            {
                "idx": idx,
                "label": label,
                "val_aggregate": detailed.val_aggregate_scores[idx],
                "objectives": cand.objectives,
            }
        )

    baseline = by_index[0]
    front = pareto_frontier(candidates, objectives)

    def _rank(c: GepaCandidate) -> tuple:
        objs = c.objectives or {}
        total = sum(objs.get(k, 0.0) for k in objectives)
        return (
            total + 0.25 * objs.get("execution", 0.0),
            objs.get("correctness", 0.0),
            objs.get("safety", 0.0),
            objs.get("cost", 0.0),
        )

    # GEPA's own winner is best_idx; cross-check against our multi-axis rank but
    # keep best_idx as the labeled winner for narrative consistency.
    gepa_winner = by_index[detailed.best_idx]
    rank_winner = max(front, key=_rank)
    winner = gepa_winner if gepa_winner in front else rank_winner
    # Label follows the selected winner so the UI's label and winner_id agree.
    if winner.label != "baseline":
        winner.label = "winner"

    pareto_json = {
        "objectives": objectives,
        "candidates": [c.to_point() for c in candidates],
        "frontier_ids": [c.candidate_id for c in front],
        "winner_id": winner.candidate_id,
        "baseline_id": baseline.candidate_id,
        "meta": {
            "total_metric_calls": detailed.total_metric_calls,
            "num_candidates_total": len(detailed.candidates),
            "num_candidates_scored": len(candidates),
            "best_idx": detailed.best_idx,
            "rescore_rows": len(rows),
            "rescore_include_judges": rescore_include_judges,
            "winner_beats_baseline": _rank(winner) > _rank(baseline),
        },
    }

    winner_path = write_winner_prompts(winner.prompts, winner_prompt_path)

    with get_session() as s:
        s.add(
            OptRun(
                id=opt_run_id,
                source_eval_run_id=source_eval_run_id,
                example=example,
                optimizer="gepa",
                status="done",
                iter_count=len(detailed.candidates) - 1,
                pareto_json=json.dumps(pareto_json),
                baseline_prompt_path=baseline_prompt_path,
                winner_prompt_path=str(winner_path),
                config_json=json.dumps(
                    {
                        "objectives": objectives,
                        "total_metric_calls": detailed.total_metric_calls,
                        "model": _normalized_model_slug(model_slug),
                        **(config_extra or {}),
                    }
                ),
            )
        )

    log.info(
        "gepa bridge done: opt=%s winner=%s |frontier|=%d winner_beats_baseline=%s elapsed=%.1fs",
        opt_run_id, winner.candidate_id, len(front),
        pareto_json["meta"]["winner_beats_baseline"], time.time() - started,
    )
    return GepaResult(
        opt_run_id=opt_run_id,
        source_eval_run_id=source_eval_run_id,
        pareto_json=pareto_json,
        baseline=baseline,
        winner=winner,
        iteration_log=iteration_log,
    )


__all__ = [
    "GepaCandidate",
    "GepaResult",
    "build_opt_run",
    "pareto_frontier",
    "program_from_instructions",
    "rescore_program",
    "winner_prompts_dict",
    "write_winner_prompts",
]
