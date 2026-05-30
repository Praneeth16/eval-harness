"""Quill as a DSPy program — the GEPA optimization target.

Two optimizable predictors (the "drafter + classifier" optimization decision):

  * ``classify`` : question -> category, confidence
  * ``draft``    : question, context, verified_refs -> answer, citations

Between them sits a *deterministic* propose→verify scaffold: candidate
references are pulled from the retrieved policy / framework chunks and each is
checked with the same tools the LangGraph agent uses
(``call_policy_exists_check``, ``call_framework_clause_check``). This guarantees
the verify-before-cite trajectory invariant by construction and populates
``tool_invocations`` exactly as ``layer3_trajectory`` expects — so GEPA's job is
to evolve the *drafting discipline* (cite only verified refs, never overclaim),
not to discover the scaffold.

Instructions are seeded from the deliberately under-constrained baseline so a
healthy GEPA run has to *rediscover* the no-phantom-citation / no-overclaim
rules that the hand-tuned prompts encode. That rediscovery is the demo payoff.
"""

from __future__ import annotations

import dspy

from examples.quill.retrieval import Hit, search
from examples.quill.tools import (
    call_framework_clause_check,
    call_policy_exists_check,
)

# ── Seed instructions distilled from prompts/baseline.py (under-constrained) ──

CLASSIFY_SEED = (
    "Classify a vendor security questionnaire question into exactly one "
    "category: security, compliance, commercial, or technical."
)

DRAFT_SEED = (
    "Draft a response to a vendor security questionnaire on behalf of Acme "
    "Corp. Be concise, professional, and factual. Always include at least one "
    "citation. Keep the answer under 120 words. Use a confident tone."
)


class Classify(dspy.Signature):
    """Classify the questionnaire question into one category."""

    question: str = dspy.InputField()
    category: str = dspy.OutputField(
        desc="one of: security, compliance, commercial, technical"
    )
    confidence: float = dspy.OutputField(desc="0.0-1.0")


class Draft(dspy.Signature):
    """Write the final questionnaire answer."""

    question: str = dspy.InputField()
    context: str = dspy.InputField(
        desc="retrieved policy / framework / past-response chunks"
    )
    verified_refs: str = dspy.InputField(
        desc="the ONLY references that may be cited (one per line)"
    )
    answer: str = dspy.OutputField()
    citations: list[str] = dspy.OutputField(
        desc="subset of verified_refs, e.g. ['POL:ENC-001', 'FW:SOC2 CC6.1']"
    )


def _format_context(hits: list[Hit]) -> str:
    parts = []
    for h in hits:
        c = h.chunk
        parts.append(f"[{c.kind} · {c.chunk_id}] {c.title}\n{c.text}")
    return "\n\n".join(parts)


def _serialize_hits(hits: list[Hit]) -> list[dict]:
    return [
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


def _propose_and_verify(hits: list[Hit]) -> tuple[list[str], list[dict]]:
    """Deterministic propose→verify: every retrieved policy / framework chunk is
    a citation candidate; each is checked with the real tool. Returns the
    verified-ref strings and the ordered ``tool_invocations`` list."""
    verified: list[str] = []
    tool_invocations: list[dict] = []
    seen: set[str] = set()
    for h in hits:
        c = h.chunk
        if c.kind == "policy":
            pid = c.meta.get("policy_id", "")
            raw = f"POL:{pid}"
            if not pid or raw in seen:
                continue
            seen.add(raw)
            ok = call_policy_exists_check(pid)
            tool_invocations.append(
                {
                    "tool": "policy_exists_check",
                    "args": {"policy_id": pid},
                    "result": ok,
                    "raw": raw,
                }
            )
            if ok:
                verified.append(raw)
        elif c.kind == "framework":
            fw = c.meta.get("framework", "")
            clause = c.meta.get("clause_id", "")
            raw = f"FW:{fw} {clause}"
            if not fw or not clause or raw in seen:
                continue
            seen.add(raw)
            ok = call_framework_clause_check(fw, clause)
            tool_invocations.append(
                {
                    "tool": "framework_clause_check",
                    "args": {"framework": fw, "clause_id": clause},
                    "result": ok,
                    "raw": raw,
                }
            )
            if ok:
                verified.append(raw)
    return verified, tool_invocations


def _coerce_citations(raw: object) -> list[str]:
    if isinstance(raw, str):
        return [raw.strip()] if raw.strip() else []
    if isinstance(raw, list):
        return [str(c).strip() for c in raw if str(c).strip()]
    return []


class QuillProgram(dspy.Module):
    """The GEPA-optimizable Quill pipeline.

    ``forward`` returns a ``dspy.Prediction`` carrying exactly the attributes
    ``core.eval.runner._build_context`` reads (answer, citations, retrieved,
    tool_invocations, latency_ms, cost_usd, raw_state), so the existing CLEAR-S
    scorers grade it unchanged.
    """

    def __init__(self) -> None:
        super().__init__()
        self.classify = dspy.Predict(Classify)
        self.draft = dspy.Predict(Draft)
        # Seed from the broken baseline so GEPA has to earn the discipline.
        self.classify.signature = self.classify.signature.with_instructions(CLASSIFY_SEED)
        self.draft.signature = self.draft.signature.with_instructions(DRAFT_SEED)

    def forward(self, question: str, k: int = 5) -> dspy.Prediction:
        hits = search(question, k=k)
        context = _format_context(hits)
        retrieved = _serialize_hits(hits)

        verified, tool_invocations = _propose_and_verify(hits)
        verified_block = "\n".join(f"- {v}" for v in verified) or "(none)"

        cls = self.classify(question=question)
        out = self.draft(
            question=question,
            context=context,
            verified_refs=verified_block,
        )
        citations = _coerce_citations(getattr(out, "citations", []))
        answer = (getattr(out, "answer", "") or "").strip()

        gap_detected = len(verified) == 0
        return dspy.Prediction(
            answer=answer,
            citations=citations,
            category=getattr(cls, "category", "security"),
            gap_detected=gap_detected,
            retrieved=retrieved,
            tool_invocations=tool_invocations,
            # Cost / latency are model-choice axes, not prompt axes: GEPA does
            # not optimize them. They are measured for real in the bridge's
            # re-score (core/optimizer/gepa.py), so we leave them neutral here.
            cost_usd=0.0,
            latency_ms=0,
            raw_state={
                "parsed_question": question,
                "category": getattr(cls, "category", "security"),
                "retrieved": retrieved,
                "answer": answer,
                "gap_detected": gap_detected,
            },
        )


__all__ = [
    "CLASSIFY_SEED",
    "DRAFT_SEED",
    "Classify",
    "Draft",
    "QuillProgram",
]
