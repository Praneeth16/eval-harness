"""Layer 3 — trajectory scorers. Inspect the tool-call sequence to decide
whether the agent's *process* was sound, independent of whether the final
answer happened to look right.

Each scorer reads `ctx["tool_invocations"]` (list of dicts with `tool`,
`args`, `result`) and `ctx["citations"]` / `ctx["raw_state"]`.
"""

from __future__ import annotations

from core.scorers import AXIS_E, ScoreContext, ScoreResult


def _tool_calls(ctx: ScoreContext, name: str) -> list[dict]:
    return [t for t in (ctx.get("tool_invocations") or []) if t.get("tool") == name]


def policy_exists_called_before_cite(ctx: ScoreContext) -> ScoreResult:
    """For every policy ID cited, the agent must have called
    `policy_exists_check` on it (and got True back)."""
    citations = ctx.get("citations") or []
    answer = ctx.get("answer", "") or ""

    import re

    from core.scorers.layer1_deterministic import _is_known_prefix

    pol_pat = re.compile(r"\b([A-Z]{2,6}-\d{3})\b")
    past_strip = re.compile(r"\bPAST:{1,2}[A-Z]+-\d+\b", re.IGNORECASE)
    phantom_pat = re.compile(r"\b[A-Z][A-Za-z]+-?[A-Z][A-Za-z]*-Policy-\d+\b")
    cited: set[str] = set()
    for c in [*list(citations), answer]:
        cleaned = past_strip.sub(" ", c)
        for m in pol_pat.finditer(cleaned):
            pid = m.group(1)
            if _is_known_prefix(pid):
                cited.add(pid)
        cited.update(m.group(0) for m in phantom_pat.finditer(c))

    if not cited:
        return ScoreResult(
            scorer_name="policy_exists_called_before_cite",
            clear_axis=AXIS_E,
            value=1.0,
            passed=True,
            details={"cited": [], "verified": []},
        )

    verified = {
        t["args"]["policy_id"]
        for t in _tool_calls(ctx, "policy_exists_check")
        if t.get("result") is True and "policy_id" in t.get("args", {})
    }
    missing = sorted(cited - verified)
    passed = len(missing) == 0
    value = 1.0 - (len(missing) / max(len(cited), 1))
    return ScoreResult(
        scorer_name="policy_exists_called_before_cite",
        clear_axis=AXIS_E,
        value=value,
        passed=passed,
        details={"cited": sorted(cited), "verified": sorted(verified), "missing": missing},
    )


def gap_detector_invoked_for_no_policy(ctx: ScoreContext) -> ScoreResult:
    """If no policy / framework was retrieved that matches, gap detector
    should fire (`gap_detected == True`)."""
    retrieved = ctx.get("retrieved") or []
    policy_or_framework_hits = [
        r for r in retrieved if r.get("kind") in ("policy", "framework") and r.get("score", 0.0) > 0.40
    ]
    raw_state = ctx.get("raw_state") or {}
    gap_detected = bool(raw_state.get("gap_detected", False))

    if not policy_or_framework_hits:
        passed = gap_detected
        value = 1.0 if passed else 0.0
        details = {
            "expected_gap": True,
            "gap_detected": gap_detected,
            "policy_hits": 0,
        }
    else:
        passed = True
        value = 1.0
        details = {"expected_gap": False, "policy_hits": len(policy_or_framework_hits)}

    return ScoreResult(
        scorer_name="gap_detector_invoked_for_no_policy",
        clear_axis=AXIS_E,
        value=value,
        passed=passed,
        details=details,
    )


def tool_order_sane(ctx: ScoreContext) -> ScoreResult:
    """The pipeline must run parser → classifier → rag → drafter → gap → risk,
    with no skipped node. We approximate via raw_state presence."""
    raw = ctx.get("raw_state") or {}
    required = (
        "parsed_question",
        "category",
        "retrieved",
        "answer",
    )
    missing = [k for k in required if not raw.get(k)]
    passed = not missing
    value = 1.0 if passed else max(0.0, 1.0 - len(missing) / len(required))
    return ScoreResult(
        scorer_name="tool_order_sane",
        clear_axis=AXIS_E,
        value=value,
        passed=passed,
        details={"missing_stages": missing},
    )


L3_SCORERS = (
    policy_exists_called_before_cite,
    gap_detector_invoked_for_no_policy,
    tool_order_sane,
)


__all__ = [
    "L3_SCORERS",
    "gap_detector_invoked_for_no_policy",
    "policy_exists_called_before_cite",
    "tool_order_sane",
]
