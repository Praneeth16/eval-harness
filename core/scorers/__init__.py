"""CLEAR-S scorers.

Four layers, one module each:

    layer1_deterministic   — millisecond constraint checks
    layer2_semantic        — Ragas / LLM judge for groundedness + accept
    layer3_trajectory      — span analysis over MLflow trace
    layer4_safety          — adversarial / PII / hallucinated-claim

Each scorer returns a `ScoreResult`. The eval runner persists these to the
`score` table keyed by trace + scorer name.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

# CLEAR-S axis vocabulary, used as `score.clear_axis`.
AXIS_C = "correctness"
AXIS_L = "latency"
AXIS_E = "execution"
AXIS_A = "adherence"
AXIS_R = "relevance"
AXIS_S = "safety"
AXIS_COST = "cost"

ALL_AXES = (AXIS_C, AXIS_L, AXIS_E, AXIS_A, AXIS_R, AXIS_S, AXIS_COST)


@dataclass
class ScoreResult:
    scorer_name: str
    clear_axis: str
    value: float
    passed: bool
    details: dict = field(default_factory=dict)


# Scorers are simple callables: (context) -> ScoreResult
# The context dict is built by the eval runner and carries: question,
# gold_answer, expected_citations, axis_focus, retrieved, answer, citations,
# tool_invocations, latency_ms, cost_usd, raw_state.
ScoreContext = dict[str, Any]
Scorer = Callable[[ScoreContext], ScoreResult]


__all__ = [
    "ALL_AXES",
    "AXIS_A",
    "AXIS_C",
    "AXIS_COST",
    "AXIS_E",
    "AXIS_L",
    "AXIS_R",
    "AXIS_S",
    "ScoreContext",
    "ScoreResult",
    "Scorer",
]
