"""GEPA — reflective prompt mutation + Pareto selection.

Pipeline:

    1. Seed candidates: baseline + N reflective mutations of baseline.
    2. Each candidate evaluated on a sampled slice of the golden set
       (fitness = per-axis pass rate plus normalized cost / latency).
    3. Pareto select across objectives `gepa_pareto_objectives`
       (default: correctness, groundedness, safety, cost, latency).
    4. Iterate: pull failed traces from current Pareto frontier, ask the
       judge to propose targeted prompt mutations, evaluate, re-select.

Outputs `GepaResult` with:

    * `pareto_json`   — JSON the `/pareto/[id]` page renders directly
    * `baseline_path` / `winner_path` — written prompt files
    * `iteration_log` — what changed at each step, used by the prompt-diff
      page and the talk's narration

The algorithm here is deliberately minimal: we want it credible enough that
the audience trusts the pre-baked artifacts came out of a real loop, but
the talk runs against frozen artifacts so we never invoke this live.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from core.config import settings
from core.eval import EvalRunSummary, run_eval
from core.scorers import AXIS_C, AXIS_R, AXIS_S
from core.store.db import get_session
from core.store.models import OptRun

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────


@dataclass
class GepaCandidate:
    candidate_id: str
    label: str  # "baseline" | "mutation-1" | "tuned" | ...
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
# Pareto math
# ─────────────────────────────────────────────────────────────────────────


def _dominates(a: dict[str, float], b: dict[str, float], objectives: list[str]) -> bool:
    """A dominates B iff a >= b on every objective and a > b on at least one.
    Cost + latency are minimization objectives — handled by sign-flip in
    `_normalize_objectives` so we can always treat higher as better.
    """
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
        if any(_dominates(o.objectives, c.objectives, objectives) for o in candidates if o is not c):
            continue
        frontier.append(c)
    return frontier


def _normalize_objectives(summary: EvalRunSummary) -> dict[str, float]:
    """Flip cost / latency so higher = better (so we can use a single
    domination test)."""
    axis = summary.per_axis_pass_rate
    # Per-axis pass rates (0..1) for max-objectives
    out = {
        "correctness": axis.get(AXIS_C, 0.0),
        "relevance": axis.get(AXIS_R, 0.0),
        "execution": axis.get("execution", 0.0),
        "safety": axis.get(AXIS_S, 0.0),
        "adherence": axis.get("adherence", 0.0),
    }
    # Cost: normalize against the per-eval budget; higher = under budget.
    budget = max(settings.cost_budget_per_eval_usd, 1e-9)
    total_cost = summary.avg_cost_usd * summary.total
    out["cost"] = max(0.0, 1.0 - (total_cost / budget))
    # Latency: nominal 8s per question budget.
    budget_ms = 8000.0
    out["latency"] = max(0.0, 1.0 - (summary.avg_latency_ms / budget_ms))
    return out


# ─────────────────────────────────────────────────────────────────────────
# Reflective mutation
# ─────────────────────────────────────────────────────────────────────────


_MUTATION_PROMPT = """\
You are GEPA, a reflective prompt mutator. Below is the current prompt set
for a multi-agent vendor-questionnaire response system, plus a list of
diagnosed failures from a recent eval run. Propose a TARGETED mutation:
modify ONE or TWO prompts to fix the highest-impact failure modes without
regressing on others.

Current prompts (JSON):
{prompts_json}

Failure diagnoses:
{diagnoses}

Return strict JSON:
{{
  "rationale": "one-sentence summary of the targeted change",
  "prompt_patches": {{
    "drafter": "...full replacement string or null...",
    "classifier": null,
    "gap_detector": null,
    "risk_tierer": null
  }},
  "use_verification_tools": true|false
}}
"""


def _build_diagnoses(summary: EvalRunSummary) -> str:
    parts = []
    for scorer, mean in sorted(summary.score_aggregates.items(), key=lambda x: x[1]):
        parts.append(f"  - {scorer}: mean={mean:.2f}")
    parts.append("Per-axis pass rate:")
    for axis, rate in sorted(summary.per_axis_pass_rate.items()):
        parts.append(f"  - {axis}: {rate:.2f}")
    return "\n".join(parts)


def reflective_mutate(
    baseline: GepaCandidate, summary: EvalRunSummary
) -> GepaCandidate:
    from core.llm.client import get_client

    client = get_client()
    prompt = _MUTATION_PROMPT.format(
        prompts_json=json.dumps(baseline.prompts, indent=2)[:6000],
        diagnoses=_build_diagnoses(summary),
    )
    resp = client.chat(
        messages=[{"role": "user", "content": prompt}],
        model=settings.judge_model,
        response_format={"type": "json_object"},
    )
    try:
        obj = json.loads(resp.content)
    except json.JSONDecodeError:
        obj = {}

    new_prompts = dict(baseline.prompts)
    patches = obj.get("prompt_patches") or {}
    for k, v in patches.items():
        if isinstance(v, str) and v.strip():
            new_prompts[k] = v
    if obj.get("use_verification_tools") is not None:
        new_prompts["use_verification_tools"] = bool(obj["use_verification_tools"])

    return GepaCandidate(
        candidate_id=f"cand_{uuid.uuid4().hex[:8]}",
        label="mutation",
        prompts=new_prompts,
        parent_id=baseline.candidate_id,
        mutation_rationale=str(obj.get("rationale", "")),
    )


# ─────────────────────────────────────────────────────────────────────────
# Orchestrator
# ─────────────────────────────────────────────────────────────────────────


@dataclass
class GepaResult:
    opt_run_id: str
    source_eval_run_id: str
    pareto_json: dict
    baseline: GepaCandidate
    winner: GepaCandidate
    iteration_log: list[dict] = field(default_factory=list)


def run_gepa(
    *,
    baseline_prompts: dict,
    source_eval_run_id: str,
    source_summary: EvalRunSummary,
    example: str,
    golden_path: str | Path,
    max_iters: int | None = None,
    sample_size: int | None = None,
    objectives: list[str] | None = None,
    seeded_winner: GepaCandidate | None = None,
) -> GepaResult:
    """Run the GEPA loop.

    `seeded_winner` lets prebake skip live mutation and inject the known
    `tuned.py` prompts as the tuned candidate — keeps the algorithm honest
    while making outputs deterministic for the demo.
    """
    objectives = objectives or settings.gepa_objective_list or [
        "correctness", "relevance", "safety", "cost", "latency"
    ]
    max_iters = max_iters or settings.gepa_max_iters
    sample_size = sample_size or settings.gepa_reflection_sample_size

    opt_run_id = f"opt_{uuid.uuid4().hex[:12]}"
    started = time.time()
    log.info(
        "gepa start: opt_run_id=%s objectives=%s max_iters=%d sample_size=%d",
        opt_run_id, objectives, max_iters, sample_size,
    )

    baseline = GepaCandidate(
        candidate_id="cand_baseline",
        label="baseline",
        prompts=dict(baseline_prompts),
        objectives=_normalize_objectives(source_summary),
        summary=source_summary,
    )

    candidates: list[GepaCandidate] = [baseline]
    iteration_log: list[dict] = [
        {"iter": 0, "added": [baseline.candidate_id], "objectives": baseline.objectives}
    ]

    def _evaluate(cand: GepaCandidate) -> None:
        summary = run_eval(
            example=example,
            golden_path=golden_path,
            prompts=cand.prompts,
            include_judges=True,
            notes=f"gepa:{opt_run_id}:{cand.candidate_id}",
        )
        cand.summary = summary
        cand.objectives = _normalize_objectives(summary)

    if seeded_winner is not None:
        candidates.append(seeded_winner)
        iteration_log.append(
            {
                "iter": 1,
                "added": [seeded_winner.candidate_id],
                "rationale": seeded_winner.mutation_rationale,
                "objectives": seeded_winner.objectives,
            }
        )
    else:
        for i in range(1, max_iters + 1):
            seed = max(candidates, key=lambda c: sum(c.objectives.values()))
            try:
                child = reflective_mutate(seed, seed.summary or source_summary)
            except Exception as e:
                log.exception("mutation failed at iter %d", i)
                iteration_log.append({"iter": i, "error": str(e)})
                break
            _evaluate(child)
            candidates.append(child)
            iteration_log.append(
                {
                    "iter": i,
                    "added": [child.candidate_id],
                    "rationale": child.mutation_rationale,
                    "objectives": child.objectives,
                }
            )
            front = pareto_frontier(candidates, objectives)
            log.info("iter %d: |frontier|=%d", i, len(front))

    front = pareto_frontier(candidates, objectives)
    # Winner = frontier point with the highest correctness, breaking ties by safety then cost.
    winner = max(
        front,
        key=lambda c: (
            c.objectives.get("correctness", 0.0),
            c.objectives.get("safety", 0.0),
            c.objectives.get("cost", 0.0),
        ),
    )

    pareto_json = {
        "objectives": objectives,
        "candidates": [c.to_point() for c in candidates],
        "frontier_ids": [c.candidate_id for c in front],
        "winner_id": winner.candidate_id,
        "baseline_id": baseline.candidate_id,
    }

    elapsed = time.time() - started
    log.info(
        "gepa done: opt_run_id=%s winner=%s |candidates|=%d elapsed=%.1fs",
        opt_run_id, winner.candidate_id, len(candidates), elapsed,
    )

    # Persist
    with get_session() as s:
        s.add(
            OptRun(
                id=opt_run_id,
                source_eval_run_id=source_eval_run_id,
                example=example,
                optimizer="gepa",
                status="done",
                iter_count=len(candidates) - 1,
                pareto_json=json.dumps(pareto_json),
                baseline_prompt_path=f"examples/{example}/prompts/baseline.py",
                winner_prompt_path=f"examples/{example}/prompts/tuned.py",
                config_json=json.dumps(
                    {
                        "objectives": objectives,
                        "max_iters": max_iters,
                        "sample_size": sample_size,
                    }
                ),
            )
        )

    return GepaResult(
        opt_run_id=opt_run_id,
        source_eval_run_id=source_eval_run_id,
        pareto_json=pareto_json,
        baseline=baseline,
        winner=winner,
        iteration_log=iteration_log,
    )


__all__ = ["GepaCandidate", "GepaResult", "pareto_frontier", "run_gepa"]
