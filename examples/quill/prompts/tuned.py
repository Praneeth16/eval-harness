"""GEPA-tuned Quill prompts — the *targeted* improvements that a healthy
GEPA run would converge on for this corpus + failure set.

What changed vs `baseline.py`:

  1. Drafter MUST call `policy_exists_check` on every policy ID it intends
     to cite, BEFORE writing the answer. (Closes the phantom-policy hole.)
  2. Drafter has an explicit "do not commit to controls or certifications
     you cannot verify in context" guardrail. (Closes the PCI/FedRAMP hole.)
  3. Citation format is tightened: `[POL:ID]` or `[FW:NAME CLAUSE]`.
  4. Gap detector is told to fire WHEN the retrieved context lacks a policy
     or framework match (not when the answer fails to cite one).

These prompts are what the prebake script's "tuned" variant uses. The same
file is what `/prompt-diff/[id]` renders on the right-hand side.
"""

from __future__ import annotations

CLASSIFIER_PROMPT = """\
You are classifying a vendor security questionnaire question into ONE
category. Be strict — ambiguous questions default to "security".

Categories:
- security      (encryption, access, network, secrets)
- compliance    (certifications, frameworks, audits, attestations)
- commercial    (pricing, SLA, contract, support tier)
- technical     (architecture, integration, performance, SDK)

Question: {question}

Return strict JSON: {{"category": "...", "confidence": 0.0-1.0}}
"""


DRAFTER_PROMPT = """\
You are drafting a response to a vendor security questionnaire on behalf of
Acme Corp. The drafted response goes into enterprise procurement workflows
and may be cited in legal proceedings. Be conservative, factual, and CITE
ONLY THINGS YOU CAN SEE IN THE PROVIDED CONTEXT.

HARD RULES — violating any of these blocks the response from ship.

  1. NEVER invent policy IDs. Cite only policy IDs that appear literally
     in the [policy ...] chunks below. If you cannot find a matching
     policy, say so explicitly and let the gap detector flag it.
  2. NEVER claim certifications, attestations, or compliance levels that
     are not present in the [policy ...] chunks. If a past response uses
     marketing wording (e.g. "PCI compliant"), do NOT upgrade it to a
     formal certification claim (e.g. "PCI-DSS Level 1 certified").
  3. NEVER commit on behalf of the company to a numeric SLA, retention
     period, or response time unless the exact number appears in the
     context.
  4. Cite using the format [POL:POLICY-ID] for internal policies and
     [FW:FRAMEWORK CLAUSE] for framework clauses (e.g. [POL:ENC-001],
     [FW:SOC2 CC6.1]).
  5. Keep the answer under 120 words. Reviewer-friendly tone.

Question:
{question}

Retrieved context (mix of internal policies, framework clauses, and past
responses — note that past responses may contain *marketing wording* that
must NOT be promoted to formal certification language):
{context}

Return strict JSON:
{{"answer": "...", "citations": ["POL:ENC-001", "FW:SOC2 CC6.1", ...]}}
"""


GAP_DETECTOR_PROMPT = """\
You decide whether the QUESTION lacks coverage in the retrieved policy /
framework context — i.e. is it a true policy gap that needs an owner.

Rule: a gap exists iff NONE of the retrieved chunks of kind "policy" or
"framework" is directly responsive to the question.

Question: {question}
Drafted answer: {answer}
Cited references: {citations}

Return strict JSON: {{"is_gap": true|false, "reason": "..."}}
"""


RISK_TIERER_PROMPT = """\
Tier this question by reviewer attention required.

Question: {question}
Answer: {answer}
Category: {category}

Tiers:
- low      routine, low scrutiny
- medium   standard reviewer pass
- high     lawyer / security lead must approve (legal commitments, breach
           SLAs, certifications, data location, indemnity)

Return strict JSON: {{"tier": "low|medium|high", "reason": "..."}}
"""


DRAFTER_PROPOSE_PROMPT = """\
You are about to draft a response to a vendor security questionnaire on
behalf of Acme Corp. BEFORE writing the answer, you must propose which
internal policies and framework clauses you intend to cite. The harness
will then verify each one against the policy register and reject any that
do not exist. Only verified references will be passed back to you for the
final draft.

Question:
{question}

Retrieved context (mix of internal policies, framework clauses, and past
responses — note that past responses may contain marketing wording you
must NOT cite as formal certification):
{context}

Return strict JSON listing ONLY the references you intend to cite:
{{"candidates": ["POL:ENC-001", "FW:SOC2 CC6.1", ...]}}

Use the format [POL:POLICY-ID] for internal policies and
[FW:FRAMEWORK CLAUSE] for framework clauses (e.g. POL:ENC-001,
FW:SOC2 CC6.1). Do not invent IDs — only propose references whose
text appears in the retrieved context above.
"""


DRAFTER_FINAL_PROMPT = """\
You are drafting a response to a vendor security questionnaire on behalf
of Acme Corp. The harness has verified your candidate references and
filtered out any that don't exist in the policy register. You may ONLY
cite from the verified list below.

HARD RULES — violating any of these blocks the response from ship.

  1. NEVER cite a reference that is not in the verified list.
  2. NEVER claim certifications, attestations, or compliance levels not
     supported by the verified references.
  3. NEVER commit to a numeric SLA or retention period unless the exact
     number appears in the verified references' text.
  4. Use the exact citation format from the verified list, e.g.
     [POL:ENC-001], [FW:SOC2 CC6.1].
  5. Keep the answer under 120 words. Reviewer-friendly tone.

Question:
{question}

Verified references (these are the ONLY refs you may cite):
{verified_refs}

Retrieved context (for content; do NOT cite anything not in the verified
list above):
{context}

Return strict JSON:
{{"answer": "...", "citations": ["POL:ENC-001", "FW:SOC2 CC6.1", ...]}}
"""


# Marker the graph reads to decide whether to invoke the verification tool
# loop. The baseline prompts dict has this absent / falsy.
USE_VERIFICATION_TOOLS = True


def as_prompts_dict() -> dict:
    return {
        "classifier": CLASSIFIER_PROMPT,
        "drafter": DRAFTER_PROMPT,
        "drafter_propose": DRAFTER_PROPOSE_PROMPT,
        "drafter_final": DRAFTER_FINAL_PROMPT,
        "gap_detector": GAP_DETECTOR_PROMPT,
        "risk_tierer": RISK_TIERER_PROMPT,
        "use_verification_tools": USE_VERIFICATION_TOOLS,
    }
