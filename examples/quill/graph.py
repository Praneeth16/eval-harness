"""Quill multi-agent graph — LangGraph supervisor + 6 nodes.

Pipeline:

    parser → classifier → rag → drafter → gap_detector → risk_tierer

Each node emits an MLflow span. The drafter additionally calls (or omits
calling) the `policy_exists_check` and `framework_clause_check` tools —
the trajectory scorer asserts on whether those tool spans appear before
the cited policy IDs in the draft span.

The graph runs both baseline and GEPA-tuned variants — variant is
selected via the `prompts` argument in `run_question`.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import TypedDict

from langgraph.graph import END, StateGraph

from core.llm.client import LLMResponse, get_client
from core.tracing import SpanType, add_attributes, init_mlflow, trace
from examples.quill.prompts import baseline as bp
from examples.quill.retrieval import Hit, search
from examples.quill.tools import (
    call_framework_clause_check,
    call_policy_exists_check,
)

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────
# State
# ─────────────────────────────────────────────────────────────────────────


class QuillState(TypedDict, total=False):
    question_id: str
    question_text: str
    parsed_question: str
    category: str
    classification_confidence: float
    retrieved: list[dict]  # serialized Hit
    answer: str
    citations: list[str]
    gap_detected: bool
    gap_reason: str
    risk_tier: str
    risk_reason: str
    tool_invocations: list[dict]  # for trajectory scorer
    total_cost_usd: float
    total_latency_ms: int
    model: str
    prompts: dict[str, str]


# ─────────────────────────────────────────────────────────────────────────
# JSON-safe LLM call helper
# ─────────────────────────────────────────────────────────────────────────


def _llm_json(prompt: str, *, model: str | None = None) -> tuple[dict, LLMResponse]:
    """Call the LLM, force JSON, parse safely. Returns ({}, resp) on parse fail."""
    client = get_client()
    resp = client.chat(
        messages=[{"role": "user", "content": prompt}],
        model=model,
        response_format={"type": "json_object"},
    )
    text = resp.content.strip()
    try:
        return json.loads(text), resp
    except json.JSONDecodeError:
        # Salvage: try to find first {...} blob
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0)), resp
            except json.JSONDecodeError:
                pass
        return {}, resp


def _accumulate(state: QuillState, resp: LLMResponse) -> dict:
    """Return the incremented cost/latency for inclusion in the node's return.

    LangGraph merges returned dicts into state but does NOT preserve direct
    mutations — so each LLM-calling node must thread these counters via its
    own return value.
    """
    return {
        "total_cost_usd": state.get("total_cost_usd", 0.0) + resp.usage.cost_usd,
        "total_latency_ms": state.get("total_latency_ms", 0) + resp.usage.latency_ms,
    }


# ─────────────────────────────────────────────────────────────────────────
# Nodes
# ─────────────────────────────────────────────────────────────────────────


@trace(span_type=SpanType.PARSER, name="parser")
def parser_node(state: QuillState) -> QuillState:
    """Cleanup the raw question; trim noise."""
    q = state["question_text"].strip()
    # Light normalization. Keep simple — we want raw input pressure on downstream.
    parsed = re.sub(r"\s+", " ", q)
    add_attributes({"question_id": state.get("question_id", ""), "len_chars": len(parsed)})
    return {"parsed_question": parsed}


@trace(span_type=SpanType.CHAIN, name="classifier")
def classifier_node(state: QuillState) -> QuillState:
    prompts = state.get("prompts") or {}
    template = prompts.get("classifier", bp.CLASSIFIER_PROMPT)
    prompt = template.format(question=state["parsed_question"])
    obj, resp = _llm_json(prompt, model=state.get("model"))
    category = obj.get("category", "security")
    conf = float(obj.get("confidence", 0.5))
    add_attributes({"category": category, "confidence": conf})
    return {"category": category, "classification_confidence": conf, **_accumulate(state, resp)}


@trace(span_type=SpanType.RETRIEVER, name="rag")
def rag_node(state: QuillState) -> QuillState:
    q = state["parsed_question"]
    hits: list[Hit] = search(q, k=5)
    retrieved = [
        {
            "chunk_id": h.chunk.chunk_id,
            "kind": h.chunk.kind,
            "title": h.chunk.title,
            "text": h.chunk.text,
            "score": h.score,
            "meta": h.chunk.meta,
        }
        for h in hits
    ]
    add_attributes(
        {
            "retrieved_count": len(retrieved),
            "retrieved_kinds": json.dumps([r["kind"] for r in retrieved]),
            "retrieved_chunk_ids": json.dumps([r["chunk_id"] for r in retrieved]),
        }
    )
    return {"retrieved": retrieved}


def _format_context(retrieved: list[dict]) -> str:
    parts = []
    for r in retrieved:
        parts.append(f"[{r['kind']} · {r['chunk_id']}] {r['title']}\n{r['text']}")
    return "\n\n".join(parts)


@trace(span_type=SpanType.AGENT, name="drafter")
def drafter_node(state: QuillState) -> QuillState:
    prompts = state.get("prompts") or {}
    template = prompts.get("drafter", bp.DRAFTER_PROMPT)
    prompt = template.format(
        question=state["parsed_question"],
        context=_format_context(state.get("retrieved", [])),
    )
    obj, resp = _llm_json(prompt, model=state.get("model"))
    drafter_acc = _accumulate(state, resp)

    answer = (obj.get("answer") or "").strip()
    citations = obj.get("citations") or []
    if isinstance(citations, str):
        citations = [citations]
    citations = [str(c).strip() for c in citations if c]

    # If the tuned prompt instructs the drafter to verify, the GEPA-tuned
    # variant calls verification tools below — pre-cite. Baseline does not.
    use_verification = bool(prompts.get("use_verification_tools", False))
    tool_invocations: list[dict] = list(state.get("tool_invocations") or [])
    if use_verification:
        for cite in citations:
            # Normalize the citation: strip POL: / FW: prefixes (single or
            # double colon — both formats appear in the wild).
            raw = cite.strip()
            if raw.upper().startswith(("FW:", "FW::")):
                body = re.split(r":+", raw, 1)[1]
                parts = re.split(r"[\s:]+", body)
                parts = [p for p in parts if p]
                if len(parts) >= 2:
                    framework, clause_id = parts[0], parts[1]
                    ok = call_framework_clause_check(framework, clause_id)
                    tool_invocations.append(
                        {
                            "tool": "framework_clause_check",
                            "args": {"framework": framework, "clause_id": clause_id},
                            "result": ok,
                        }
                    )
                continue
            if raw.upper().startswith(("POL:", "POL::")):
                pid = re.split(r":+", raw, 1)[1].strip()
                ok = call_policy_exists_check(pid)
                tool_invocations.append(
                    {
                        "tool": "policy_exists_check",
                        "args": {"policy_id": pid},
                        "result": ok,
                    }
                )
                continue
            # Bare token: framework if matches `XXX <clause>`, else policy.
            parts = raw.replace(",", " ").split()
            if len(parts) >= 2 and parts[0].isalpha() and parts[0].isupper():
                framework, clause_id = parts[0], parts[1]
                ok = call_framework_clause_check(framework, clause_id)
                tool_invocations.append(
                    {
                        "tool": "framework_clause_check",
                        "args": {"framework": framework, "clause_id": clause_id},
                        "result": ok,
                    }
                )
            else:
                ok = call_policy_exists_check(raw)
                tool_invocations.append(
                    {
                        "tool": "policy_exists_check",
                        "args": {"policy_id": raw},
                        "result": ok,
                    }
                )

    add_attributes(
        {
            "answer_len_words": len(answer.split()),
            "citation_count": len(citations),
            "citations": json.dumps(citations),
            "verification_used": use_verification,
        }
    )
    return {
        "answer": answer,
        "citations": citations,
        "tool_invocations": tool_invocations,
        **drafter_acc,
    }


@trace(span_type=SpanType.CHAIN, name="gap_detector")
def gap_detector_node(state: QuillState) -> QuillState:
    prompts = state.get("prompts") or {}
    template = prompts.get("gap_detector", bp.GAP_DETECTOR_PROMPT)
    prompt = template.format(
        question=state["parsed_question"],
        answer=state.get("answer", ""),
        citations=", ".join(state.get("citations") or []) or "(none)",
    )
    obj, resp = _llm_json(prompt, model=state.get("model"))
    is_gap = bool(obj.get("is_gap", False))
    reason = obj.get("reason", "")
    add_attributes({"gap_detected": is_gap})
    return {"gap_detected": is_gap, "gap_reason": reason, **_accumulate(state, resp)}


@trace(span_type=SpanType.CHAIN, name="risk_tierer")
def risk_tierer_node(state: QuillState) -> QuillState:
    prompts = state.get("prompts") or {}
    template = prompts.get("risk_tierer", bp.RISK_TIERER_PROMPT)
    prompt = template.format(
        question=state["parsed_question"],
        answer=state.get("answer", ""),
        category=state.get("category", "security"),
    )
    obj, resp = _llm_json(prompt, model=state.get("model"))
    tier = obj.get("tier", "medium")
    reason = obj.get("reason", "")
    add_attributes({"risk_tier": tier})
    return {"risk_tier": tier, "risk_reason": reason, **_accumulate(state, resp)}


# ─────────────────────────────────────────────────────────────────────────
# Graph builder
# ─────────────────────────────────────────────────────────────────────────


def build_graph():
    g = StateGraph(QuillState)
    g.add_node("parser", parser_node)
    g.add_node("classifier", classifier_node)
    g.add_node("rag", rag_node)
    g.add_node("drafter", drafter_node)
    g.add_node("gap_detector", gap_detector_node)
    g.add_node("risk_tierer", risk_tierer_node)

    g.set_entry_point("parser")
    g.add_edge("parser", "classifier")
    g.add_edge("classifier", "rag")
    g.add_edge("rag", "drafter")
    g.add_edge("drafter", "gap_detector")
    g.add_edge("gap_detector", "risk_tierer")
    g.add_edge("risk_tierer", END)

    return g.compile()


# ─────────────────────────────────────────────────────────────────────────
# Public runner — used by eval driver, prebake script, and API
# ─────────────────────────────────────────────────────────────────────────


@dataclass
class QuillResult:
    question_id: str
    question_text: str
    category: str
    answer: str
    citations: list[str]
    gap_detected: bool
    risk_tier: str
    retrieved: list[dict]
    tool_invocations: list[dict]
    cost_usd: float
    latency_ms: int
    model: str
    mlflow_trace_id: str | None = None
    raw_state: dict = field(default_factory=dict)


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


@trace(span_type=SpanType.AGENT, name="quill_run")
def run_question(
    question_text: str,
    question_id: str = "",
    *,
    model: str | None = None,
    prompts: dict[str, str] | None = None,
) -> QuillResult:
    """Run the Quill pipeline on a single question. Emits one MLflow trace."""
    init_mlflow()
    t0 = time.perf_counter()

    initial: QuillState = {
        "question_id": question_id,
        "question_text": question_text,
        "model": model or "",
        "prompts": prompts or {},
        "tool_invocations": [],
        "total_cost_usd": 0.0,
        "total_latency_ms": 0,
    }
    final_state = get_graph().invoke(initial)
    latency = int((time.perf_counter() - t0) * 1000)

    # Pull current MLflow trace id (best-effort)
    trace_id = None
    try:
        import mlflow

        last = mlflow.get_last_active_trace_id()
        trace_id = last
    except Exception:
        pass

    return QuillResult(
        question_id=question_id,
        question_text=question_text,
        category=final_state.get("category", "security"),
        answer=final_state.get("answer", ""),
        citations=list(final_state.get("citations") or []),
        gap_detected=bool(final_state.get("gap_detected", False)),
        risk_tier=final_state.get("risk_tier", "medium"),
        retrieved=list(final_state.get("retrieved") or []),
        tool_invocations=list(final_state.get("tool_invocations") or []),
        cost_usd=float(final_state.get("total_cost_usd", 0.0)),
        latency_ms=latency,
        model=model or "",
        mlflow_trace_id=trace_id,
        raw_state=dict(final_state),
    )


__all__ = ["QuillResult", "build_graph", "get_graph", "run_question"]
