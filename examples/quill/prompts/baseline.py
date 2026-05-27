"""Baseline Quill prompts — what ships before GEPA optimization.

These are deliberately under-constrained so the cold-open failure modes
fire reliably:

  * Drafter does NOT require `policy_exists_check` before citing.
  * Drafter is told to "always include a citation" — pushing toward
    fabricated IDs when retrieval is thin.
  * No "do not commit to unowned controls" guardrail.

GEPA-tuned variants live in `examples/quill/prompts/tuned.py`, generated
during optimization.
"""

from __future__ import annotations

CLASSIFIER_PROMPT = """\
You are classifying a security questionnaire question into one category.

Categories:
- security      (technical controls: encryption, access, network)
- compliance    (certifications, frameworks, audits)
- commercial    (pricing, SLA, contract)
- technical     (architecture, integration, performance)

Question: {question}

Return JSON: {{"category": "...", "confidence": 0.0-1.0}}
"""


DRAFTER_PROMPT = """\
You are drafting a response to a vendor security questionnaire on behalf of
Acme Corp. Be concise, professional, factual.

Question:
{question}

Retrieved context (mix of internal policies, framework clauses, and past
responses):
{context}

Requirements:
- Always include at least one citation in the form [POLICY-ID] or
  [FRAMEWORK CLAUSE-ID].
- Keep the answer under 120 words.
- Use a confident tone — this is going to an enterprise buyer.

Return JSON: {{"answer": "...", "citations": ["...", "..."]}}
"""


GAP_DETECTOR_PROMPT = """\
You decide whether the drafted answer reflects a real policy gap (no
matching policy exists for the question topic).

Question: {question}
Drafted answer: {answer}
Cited policies/frameworks: {citations}

Return JSON: {{"is_gap": true|false, "reason": "..."}}
"""


RISK_TIERER_PROMPT = """\
Tier this question by reviewer-attention required.

Question: {question}
Answer: {answer}
Category: {category}

Tiers:
- low       routine, low scrutiny
- medium    standard reviewer pass
- high      lawyer / security lead must approve

Return JSON: {{"tier": "low|medium|high", "reason": "..."}}
"""
