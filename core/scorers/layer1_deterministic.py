"""Layer 1 — deterministic scorers. Ship blockers. Run in milliseconds."""

from __future__ import annotations

import re

from core.config import settings
from core.scorers import (
    AXIS_A,
    AXIS_C,
    AXIS_COST,
    AXIS_L,
    ScoreContext,
    ScoreResult,
)
from examples.quill.retrieval import framework_clause_resolves, policy_exists

_FRAMEWORK_CITE_RE = re.compile(
    r"\b(SOC2|ISO27001|GDPR|DPDP)\s+([A-Z]+\.?\d+(?:\.\d+)?)", re.IGNORECASE
)
_POLICY_CITE_RE = re.compile(r"\b([A-Z]{2,6}-\d{3})\b")
_PHANTOM_CITE_RE = re.compile(r"\b[A-Z][A-Za-z]+-?[A-Z][A-Za-z]*-Policy-\d+\b")


def _extract_policy_ids(citations: list[str], answer: str) -> list[str]:
    found: list[str] = []
    for c in citations:
        for m in _POLICY_CITE_RE.finditer(c):
            found.append(m.group(1))
        for m in _PHANTOM_CITE_RE.finditer(c):
            found.append(m.group(0))
    for m in _POLICY_CITE_RE.finditer(answer or ""):
        found.append(m.group(1))
    for m in _PHANTOM_CITE_RE.finditer(answer or ""):
        found.append(m.group(0))
    # dedupe preserving order
    seen: set[str] = set()
    out: list[str] = []
    for x in found:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _extract_framework_clauses(citations: list[str], answer: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for c in [*list(citations), answer or ""]:
        for m in _FRAMEWORK_CITE_RE.finditer(c):
            framework = m.group(1).upper().replace("-", "")
            framework = "ISO27001" if framework == "ISO27001" else framework
            clause = m.group(2)
            found.append((framework, clause))
    return sorted(set(found))


# ─────────────────────────────────────────────────────────────────────────


def policy_exists_scorer(ctx: ScoreContext) -> ScoreResult:
    """Every cited policy ID must resolve in the corpus."""
    citations = ctx.get("citations") or []
    answer = ctx.get("answer", "")
    pids = _extract_policy_ids(citations, answer)
    if not pids:
        return ScoreResult(
            scorer_name="policy_exists",
            clear_axis=AXIS_C,
            value=1.0,
            passed=True,
            details={"checked": [], "missing": []},
        )
    missing = [p for p in pids if not policy_exists(p)]
    passed = len(missing) == 0
    value = 1.0 - (len(missing) / max(len(pids), 1))
    return ScoreResult(
        scorer_name="policy_exists",
        clear_axis=AXIS_C,
        value=value,
        passed=passed,
        details={"checked": pids, "missing": missing},
    )


def framework_clause_scorer(ctx: ScoreContext) -> ScoreResult:
    """Every cited framework clause must resolve."""
    citations = ctx.get("citations") or []
    answer = ctx.get("answer", "")
    pairs = _extract_framework_clauses(citations, answer)
    if not pairs:
        return ScoreResult(
            scorer_name="framework_clause_resolves",
            clear_axis=AXIS_C,
            value=1.0,
            passed=True,
            details={"checked": [], "missing": []},
        )
    missing = [
        f"{fw} {cl}" for fw, cl in pairs if not framework_clause_resolves(fw, cl)
    ]
    passed = len(missing) == 0
    value = 1.0 - (len(missing) / max(len(pairs), 1))
    return ScoreResult(
        scorer_name="framework_clause_resolves",
        clear_axis=AXIS_C,
        value=value,
        passed=passed,
        details={"checked": [f"{fw} {cl}" for fw, cl in pairs], "missing": missing},
    )


def word_count_scorer(ctx: ScoreContext, *, limit: int = 120) -> ScoreResult:
    """Drafted answer must stay within the per-answer word budget."""
    answer = ctx.get("answer", "") or ""
    n = len(answer.split())
    passed = n <= limit
    value = 1.0 if passed else max(0.0, 1.0 - (n - limit) / limit)
    return ScoreResult(
        scorer_name="word_count",
        clear_axis=AXIS_A,
        value=value,
        passed=passed,
        details={"words": n, "limit": limit},
    )


def cost_budget_scorer(ctx: ScoreContext) -> ScoreResult:
    """Per-question cost must stay under the configured budget."""
    cost = float(ctx.get("cost_usd", 0.0))
    # Per-question budget = the per-eval budget divided by a nominal question count
    # so individual answers stay within range. Tunable via env later.
    per_q_budget = settings.cost_budget_per_eval_usd / 50.0
    passed = cost <= per_q_budget
    # Normalize value: 1.0 at zero cost, 0.0 at 2× budget.
    if cost <= per_q_budget:
        value = 1.0 - (cost / max(per_q_budget, 1e-9)) * 0.5
    else:
        over = (cost - per_q_budget) / max(per_q_budget, 1e-9)
        value = max(0.0, 0.5 - over * 0.5)
    return ScoreResult(
        scorer_name="cost_budget",
        clear_axis=AXIS_COST,
        value=value,
        passed=passed,
        details={"cost_usd": cost, "budget_usd": per_q_budget},
    )


def latency_budget_scorer(ctx: ScoreContext, *, limit_ms: int = 8000) -> ScoreResult:
    """Per-question latency budget."""
    lat = int(ctx.get("latency_ms", 0))
    passed = lat <= limit_ms
    value = 1.0 if passed else max(0.0, 1.0 - (lat - limit_ms) / max(limit_ms, 1))
    return ScoreResult(
        scorer_name="latency_budget",
        clear_axis=AXIS_L,
        value=value,
        passed=passed,
        details={"latency_ms": lat, "limit_ms": limit_ms},
    )


L1_SCORERS = (
    policy_exists_scorer,
    framework_clause_scorer,
    word_count_scorer,
    cost_budget_scorer,
    latency_budget_scorer,
)


__all__ = [
    "L1_SCORERS",
    "cost_budget_scorer",
    "framework_clause_scorer",
    "latency_budget_scorer",
    "policy_exists_scorer",
    "word_count_scorer",
]
