"""tuned_v2 - the fix the harness pointed at.

Error analysis of the tuned run's failures (read the judge rationales on the
8 SOC 2 misses and the 16 ISO misses) found ONE failure family, not many:
the agent over-answers. It adds scopes/mechanisms/frameworks the cited clause
does not state (overclaim), omits a control the clause lists, or cites a real
policy instead of the framework clause the question is really about.

propose -> verify -> final already made phantom citations impossible. It did
nothing about citation *sufficiency*. tuned_v2 adds two things on top of the
tuned prompts:

  1. A tightened DRAFTER_FINAL prompt: extractive, complete, cite the
     expected clause.
  2. A `drafter_revise` groundedness pass: after the final draft, rewrite the
     answer to stay within the verified clause text. This is the
     deterministic-verifier-in-the-loop pattern moved one layer up - from
     "does the ID exist?" to "does the cited clause support the claim?".

Everything else is inherited from `tuned.py` unchanged.
"""

from __future__ import annotations

from examples.quill.prompts import tuned as t


DRAFTER_FINAL_PROMPT = """\
You are drafting a response to a vendor security questionnaire on behalf
of Acme Corp. The harness has verified your candidate references and
filtered out any that don't exist. You may ONLY cite from the verified
list below, and you may ONLY state what those references' text supports.

HARD RULES - violating any of these blocks the response from ship.

  1. NEVER cite a reference that is not in the verified list.
  2. GROUND every sentence in the verified references' text. Do NOT add a
     scope, frequency, mechanism, tool, certification, or framework name
     that does not appear in that text. If the clause does not say it,
     do not claim it.
  3. Do NOT OMIT a control or requirement the verified reference text
     lists for this question. Completeness counts.
  4. When the question is about a regulation or framework control (breach
     notification, MFA, access control, encryption), cite the FRAMEWORK
     clause reference, not only the internal policy, when both are
     verified.
  5. NEVER claim certifications or compliance levels not supported by the
     verified references; never upgrade marketing wording ("PCI compliant")
     into a formal certification ("PCI-DSS Level 1 certified").
  6. Keep the answer under 120 words. Reviewer-friendly tone.

Question:
{question}

Verified references (the ONLY refs you may cite, and the ONLY claims you
may make):
{verified_refs}

Retrieved context (for the source text behind those references; do NOT
cite or claim anything not backed by the verified list above):
{context}

Return strict JSON:
{{"answer": "...", "citations": ["POL:ENC-001", "FW:SOC2 CC6.1", ...]}}
"""


DRAFTER_REVISE_PROMPT = """\
You are reviewing a drafted questionnaire answer for FAITHFULNESS to its
cited sources before it ships to an enterprise security reviewer. Your job
is to remove anything the sources do not support and restore anything they
require.

Question:
{question}

Draft answer:
{draft}

Verified references you may cite:
{verified_refs}

Source text behind those references (the answer must stay within this):
{context}

Rewrite the answer so that:
  1. Every claim is directly supported by the source text above. DELETE any
     scope, frequency, mechanism, tool name, certification, or framework
     name that is not present in that text.
  2. You do NOT omit a control or requirement the source text states for
     this question.
  3. You cite the most specific verified reference for each claim - prefer
     the framework clause when the question is about a regulation or
     control.
Do not add new information. If the source text does not support part of the
draft, remove that part. Keep it under 120 words.

Return strict JSON:
{{"answer": "...", "citations": ["POL:ENC-001", "FW:SOC2 CC6.1", ...]}}
"""


def as_prompts_dict() -> dict:
    d = t.as_prompts_dict()
    d["drafter_final"] = DRAFTER_FINAL_PROMPT
    d["drafter_revise"] = DRAFTER_REVISE_PROMPT
    return d
