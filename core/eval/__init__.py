"""Eval driver — orchestrates golden-set runs, scoring, and persistence."""

from core.eval.runner import EvalRunSummary, run_eval

__all__ = ["EvalRunSummary", "run_eval"]
