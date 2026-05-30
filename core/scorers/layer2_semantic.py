"""Layer 2 — semantic scorers (groundedness + judge accept).

We use a lightweight LLM-judge implementation rather than booting Ragas's
full pipeline — Ragas has heavy deps and our judge calls go through the
same OpenRouter gateway, which gives us cost tracking + retries for free.

Two scorers here:

  * `groundedness_scorer`  — each claim in the answer should be supported by
    at least one retrieved chunk.
  * `judge_accept_scorer`  — would a reviewer accept this answer given the
    gold answer? 0/0.5/1.

Both rely on `JUDGE_MODEL` from settings.
"""

from __future__ import annotations

import json
import re
from typing import Any

from core.config import settings
from core.llm.client import get_client
from core.scorers import AXIS_C, AXIS_R, ScoreContext, ScoreResult
from core.tracing import SpanType, tool_span

_GROUNDEDNESS_PROMPT = """\
You are an evaluator. Decide whether the answer is grounded in the provided
context. An answer is grounded iff every factual claim is directly supported
by at least one passage in the context.

Question: {question}

Answer:
{answer}

Context passages (each prefixed with its chunk id):
{context}

Return strict JSON:
{{"grounded": true|false, "unsupported_claims": ["...", "..."], "confidence": 0.0-1.0}}
"""

_JUDGE_ACCEPT_PROMPT = """\
You are a security reviewer deciding whether a drafted questionnaire answer is
good enough to ship. You are given a gold reference. Treat it as ONE acceptable
answer, not the only one: do not grade by string-matching the gold.

ACCEPT (1.0) when the drafted answer is all of:
  - accurate    - no claim contradicts the gold reference or known facts,
  - supported   - its claims are backed by the drafted citations / context,
  - responsive  - it answers the question that was asked.
  Additional accurate, supported detail beyond the gold reference is FINE.
  Different wording, ordering, or extra context is FINE. Do NOT mark an answer
  down merely for being more complete or more specific than the gold reference.

REVISE (0.5) only for a genuinely fixable defect:
  - it omits a control or requirement the gold reference treats as REQUIRED, or
  - a claim clearly needs a citation and none is given, or
  - a minor but real inaccuracy.

REJECT (0.0) when the answer:
  - states something false or contradicts the gold on a material fact,
  - fabricates a citation that does not exist, or
  - overclaims - upgrades a weaker posture into a stronger claim the sources do
    not support (e.g. "compliant" or "working toward" stated as "certified").

Question: {question}

Gold reference (one acceptable answer, not the only one):
{gold_answer}

Required citations (if any): {expected_citations}

Drafted answer:
{answer}

Drafted citations: {citations}

Return strict JSON:
{{"verdict": "accept|revise|reject", "score": 0.0|0.5|1.0, "reason": "..."}}
"""


def _safe_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return {}
        return {}


def _format_ctx(retrieved: list[dict]) -> str:
    parts = []
    for r in retrieved:
        parts.append(f"[{r.get('chunk_id','?')}] {r.get('title','')}\n{r.get('text','')}")
    return "\n\n".join(parts)


def _call_judge(prompt: str) -> tuple[dict, Any]:
    client = get_client()
    with tool_span(
        "judge_call",
        inputs={"model": settings.judge_model},
        attributes={"judge_model": settings.judge_model, "span_kind": str(SpanType.JUDGE)},
    ):
        resp = client.chat(
            messages=[{"role": "user", "content": prompt}],
            model=settings.judge_model,
            response_format={"type": "json_object"},
        )
    return _safe_json(resp.content), resp


def groundedness_scorer(ctx: ScoreContext) -> ScoreResult:
    answer = ctx.get("answer", "") or ""
    retrieved = ctx.get("retrieved") or []
    if not answer.strip():
        return ScoreResult(
            scorer_name="groundedness",
            clear_axis=AXIS_R,
            value=0.0,
            passed=False,
            details={"reason": "empty answer"},
        )
    prompt = _GROUNDEDNESS_PROMPT.format(
        question=ctx.get("question", ""),
        answer=answer,
        context=_format_ctx(retrieved),
    )
    obj, _resp = _call_judge(prompt)
    grounded = bool(obj.get("grounded", False))
    confidence = float(obj.get("confidence", 0.5))
    unsupported = obj.get("unsupported_claims", []) or []
    value = confidence if grounded else max(0.0, 1.0 - confidence)
    if not grounded:
        value = 1.0 - confidence
    return ScoreResult(
        scorer_name="groundedness",
        clear_axis=AXIS_R,
        value=float(value),
        passed=grounded,
        details={"unsupported_claims": unsupported, "confidence": confidence},
    )


def judge_accept_scorer(ctx: ScoreContext) -> ScoreResult:
    answer = ctx.get("answer", "") or ""
    gold = ctx.get("gold_answer", "") or ""
    expected = ctx.get("expected_citations") or []
    citations = ctx.get("citations") or []
    if not answer.strip():
        return ScoreResult(
            scorer_name="judge_accept",
            clear_axis=AXIS_C,
            value=0.0,
            passed=False,
            details={"reason": "empty answer"},
        )
    prompt = _JUDGE_ACCEPT_PROMPT.format(
        question=ctx.get("question", ""),
        gold_answer=gold,
        expected_citations=", ".join(expected) or "(none)",
        answer=answer,
        citations=", ".join(citations) or "(none)",
    )
    obj, _resp = _call_judge(prompt)
    verdict = (obj.get("verdict") or "reject").lower()
    score = float(obj.get("score", 0.0))
    if verdict not in {"accept", "revise", "reject"}:
        verdict = "reject"
        score = 0.0
    passed = verdict == "accept"
    return ScoreResult(
        scorer_name="judge_accept",
        clear_axis=AXIS_C,
        value=score,
        passed=passed,
        details={"verdict": verdict, "reason": obj.get("reason", "")},
    )


L2_SCORERS = (groundedness_scorer, judge_accept_scorer)


__all__ = ["L2_SCORERS", "groundedness_scorer", "judge_accept_scorer"]
