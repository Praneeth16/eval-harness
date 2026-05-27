"""Registry — pick which scorers to run for a given example / mode."""

from __future__ import annotations

from collections.abc import Sequence

from core.scorers import Scorer
from core.scorers.layer1_deterministic import L1_SCORERS
from core.scorers.layer2_semantic import L2_SCORERS
from core.scorers.layer3_trajectory import L3_SCORERS
from core.scorers.layer4_safety import L4_SCORERS


def all_scorers(*, include_judges: bool = True) -> tuple[Scorer, ...]:
    out: tuple[Scorer, ...] = L1_SCORERS + L3_SCORERS + L4_SCORERS
    if include_judges:
        out = L1_SCORERS + L2_SCORERS + L3_SCORERS + L4_SCORERS
    return out


def deterministic_only() -> Sequence[Scorer]:
    """No-LLM subset — used for fast smoke tests + GEPA proxy fitness."""
    return L1_SCORERS + L3_SCORERS + L4_SCORERS


__all__ = ["all_scorers", "deterministic_only"]
