"""Run a real ``dspy.GEPA`` optimization of the Quill drafter + classifier.

This is the genuine article: reflective prompt evolution with instance-level
Pareto candidate selection (Agrawal et al., arXiv:2507.19457), driven by the
feedback metric in ``examples/quill/gepa_metric.py``. It starts from the
deliberately-broken baseline instructions so a healthy run has to *rediscover*
the verify-before-cite / no-overclaim discipline.

Everything routes through Google AI Studio on the existing ``GEMINI_API_KEY``
(the harness's primary provider; OpenRouter is only the cross-family
portability path):

  * task LM        — cheap, runs every rollout         (default gemini-2.5-flash)
  * reflection LM  — stronger, proposes prompt mutations (default gemini-2.5-pro)
  * judge          — the harness CLEAR-S judge          (settings.judge_model)

Data split (only ~40 non-injection golden questions exist):

  * trainset (reflection)      = soc2[:16]
  * valset   (Pareto tracking) = iso27001 (20)  → selects for cross-framework
                                                    generalization by construction
  * holdout  (honesty check)   = soc2[16:20]    → never seen by GEPA

Modes:
  --smoke   tiny budget, no judges, 3/3 split — proves the pipeline (~cents)
  (default) paid run — needs --yes; bounded by --max-metric-calls
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path

from core.config import REPO_ROOT, settings
from core.eval.runner import run_eval
from core.optimizer.gepa import build_opt_run
from core.store.db import init_db
from core.tracing import init_mlflow

log = logging.getLogger(__name__)

GOLDEN = REPO_ROOT / "examples/quill/golden"


def _load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _examples(rows: list[dict]):
    import dspy

    return [dspy.Example(**r).with_inputs("question") for r in rows]


def _ensure_gemini_key() -> None:
    """The harness primary provider is Google AI Studio. Export the key so
    litellm (DSPy's backend) and the harness client both pick it up."""
    key = settings.gemini_api_key
    if not key:
        raise SystemExit(
            "GEMINI_API_KEY is empty. Add it to .env before running GEPA:\n"
            "  echo 'GEMINI_API_KEY=...' >> .env"
        )
    os.environ.setdefault("GEMINI_API_KEY", key)
    os.environ.setdefault("GOOGLE_API_KEY", key)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser()
    # DSPy LMs use litellm's native Gemini provider (reads GEMINI_API_KEY).
    # `reasoning_effort=disable` turns off thinking on the task model to keep
    # per-rollout latency / cost down.
    p.add_argument("--task-model", default="gemini/gemini-2.5-flash")
    p.add_argument("--reflection-model", default="gemini/gemini-2.5-pro")
    p.add_argument("--max-metric-calls", type=int, default=300)
    p.add_argument("--minibatch", type=int, default=3)
    p.add_argument("--threads", type=int, default=8)
    p.add_argument("--rescore-n", type=int, default=12,
                   help="val rows used to re-score frontier candidates (cost control)")
    p.add_argument("--no-judges", action="store_true",
                   help="deterministic-only metric + rescore (cheap)")
    p.add_argument("--smoke", action="store_true",
                   help="tiny budget pipeline check (~cents)")
    p.add_argument("--yes", action="store_true", help="confirm the paid run")
    args = p.parse_args()

    import dspy

    init_mlflow()
    init_db()
    _ensure_gemini_key()

    include_judges = not args.no_judges

    train_rows = _load_rows(GOLDEN / "soc2.jsonl")[:16]
    val_rows = _load_rows(GOLDEN / "iso27001_holdout.jsonl")
    holdout_rows = _load_rows(GOLDEN / "soc2.jsonl")[16:20]

    if args.smoke:
        args.max_metric_calls = min(args.max_metric_calls, 12)
        train_rows, val_rows = train_rows[:3], val_rows[:3]
        args.rescore_n = min(args.rescore_n, 3)
        include_judges = False
        log.info("SMOKE MODE: max_metric_calls=%d, no judges, 3/3 split", args.max_metric_calls)
    elif not args.yes:
        raise SystemExit(
            f"Paid run (~budget cap ${settings.cost_budget_per_opt_usd:.0f}, hard stop "
            f"${settings.cost_hard_stop_usd:.0f}). Re-run with --yes to confirm, or "
            "--smoke for a cheap pipeline check."
        )

    # Configure DSPy LMs via litellm's native Gemini provider.
    import litellm

    litellm.drop_params = True  # silently drop any param a model alias rejects
    task_lm = dspy.LM(
        args.task_model,
        api_key=settings.gemini_api_key,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        reasoning_effort="disable",
    )
    reflection_lm = dspy.LM(
        args.reflection_model,
        api_key=settings.gemini_api_key,
        temperature=1.0,
        max_tokens=16000,
    )
    dspy.configure(lm=task_lm, track_usage=True)

    # 1. Baseline graph eval → honest baseline numbers + OptRun source FK.
    log.info("baseline graph eval on %d val rows ...", len(val_rows))
    val_path = REPO_ROOT / ".data" / "gepa_val.jsonl"
    val_path.parent.mkdir(parents=True, exist_ok=True)
    val_path.write_text("\n".join(json.dumps(r) for r in val_rows))
    baseline_summary = run_eval(
        example="quill",
        golden_path=val_path,
        model=None,  # harness default (gemini-2.5-flash via AI Studio)
        prompts={},  # baseline.py defaults — no verification scaffold
        include_judges=include_judges,
        notes="gepa:baseline:val",
    )

    # 2. Real GEPA.
    from examples.quill.dspy_program import QuillProgram
    from examples.quill.gepa_metric import make_metric

    metric = make_metric(include_judges=include_judges)
    gepa = dspy.GEPA(
        metric=metric,
        reflection_lm=reflection_lm,
        max_metric_calls=args.max_metric_calls,
        reflection_minibatch_size=args.minibatch,
        candidate_selection_strategy="pareto",
        use_merge=True,
        track_stats=True,
        track_best_outputs=True,
        num_threads=args.threads,
        seed=0,
    )
    log.info(
        "GEPA compile: budget=%d minibatch=%d train=%d val=%d",
        args.max_metric_calls, args.minibatch, len(train_rows), len(val_rows),
    )
    optimized = gepa.compile(
        QuillProgram(),
        trainset=_examples(train_rows),
        valset=_examples(val_rows),
    )
    detailed = optimized.detailed_results

    # 3. Bridge → OptRun + real multi-objective frontier.
    result = build_opt_run(
        detailed=detailed,
        source_eval_run_id=baseline_summary.run_id,
        example="quill",
        valset_rows=val_rows,
        model_slug=args.task_model,
        rescore_n=args.rescore_n,
        rescore_include_judges=include_judges,
        config_extra={
            "task_model": args.task_model,
            "reflection_model": args.reflection_model,
            "max_metric_calls": args.max_metric_calls,
            "train_size": len(train_rows),
            "val_size": len(val_rows),
        },
    )

    # 4. Honest held-out check: winner instructions through the graph on
    #    questions GEPA never saw.
    from core.optimizer.gepa import winner_prompts_dict

    holdout_path = REPO_ROOT / ".data" / "gepa_holdout.jsonl"
    holdout_path.write_text("\n".join(json.dumps(r) for r in holdout_rows))
    holdout_summary = run_eval(
        example="quill",
        golden_path=holdout_path,
        model=None,
        prompts=winner_prompts_dict(result.winner.prompts),
        include_judges=include_judges,
        notes=f"gepa:holdout:{result.opt_run_id}",
    )

    meta = result.pareto_json["meta"]
    print("\n" + "=" * 60)
    print("GEPA run complete")
    print("=" * 60)
    print(f"  opt_run_id            : {result.opt_run_id}")
    print(f"  total metric calls    : {meta['total_metric_calls']}")
    print(f"  candidates (total)    : {meta['num_candidates_total']}")
    print(f"  candidates (scored)   : {meta['num_candidates_scored']}")
    print(f"  frontier size         : {len(result.pareto_json['frontier_ids'])}")
    print(f"  winner                : {result.winner.candidate_id} ({result.winner.label})")
    print(f"  winner beats baseline : {meta['winner_beats_baseline']}")
    print(f"  baseline objectives   : {result.baseline.objectives}")
    print(f"  winner   objectives   : {result.winner.objectives}")
    print(f"  holdout pass rate     : {holdout_summary.per_axis_pass_rate}")
    print("  winner prompts        : examples/quill/prompts/tuned_gepa.py")
    print(f"\n  open: http://localhost:3000/pareto/{result.opt_run_id}\n")


if __name__ == "__main__":
    main()
