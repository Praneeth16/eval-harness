# Session Plan: Journey of an Agent — From Demo to Production
### Closing the loop with a self-evolving eval harness

---

## 1. Logistics

| | |
|---|---|
| **Event** | Agent Harness (Builder-First Meetup) |
| **Date** | 2026-05-30, 1:00 PM – 1:45 PM IST (+ 10–15 min Q&A) |
| **Venue** | Hinge Health, Indiranagar, Bangalore |
| **Audience** | AI engineers, builders, founders, eng leaders. Zero marketing fluff. |
| **Speaker** | Praneeth Paikray (Databricks) |
| **Style** | Live demo + architectural deep-dive; "Chip Huyen" systems posture |
| **Repo** | https://github.com/Praneeth16/eval-harness (flip public ~2 days pre-talk) |

## 2. Promise (the memorable thing)

> **"Agents learn from their own failures here."**

Every typography, color, motion, layout, eval, and architectural choice
compounds toward one payoff: the Pareto frontier shift on `/pareto/[id]`,
showing a baseline agent dominated by a GEPA-optimized agent across CLEAR
axes. That moment is the climax.

## 3. Hero use case — Quill

A **multi-agent RFP / security-questionnaire response agent**. Same pain
on both sides of the table — startups need it to sell upmarket, enterprises
need it to triage incoming vendor responses.

**What Quill does end-to-end:**
1. Parse incoming RFP / questionnaire (200+ atomic questions)
2. Classify each question (security / compliance / commercial / technical)
3. Retrieve over company policy + past responses + framework controls
   (SOC 2 CC*, ISO 27001 Annex A, GDPR Art*, DPDP Act §*)
4. Draft answers grounded in citations
5. Detect gaps where company has no policy → escalate to owner
6. Risk-tier the questionnaire to prioritize human review
7. Output completed response doc + reviewer summary + gap list

**Architecture (open-source-native, no proprietary lock-in):**

```
                     ┌──────────────────────────┐
                     │  LangGraph Supervisor    │
                     └──┬───────────────────────┘
                        │
   ┌────────────┬───────┼───────┬────────────┬────────────┐
   ▼            ▼       ▼       ▼            ▼            ▼
 Parser    Classifier  RAG    Drafter   GapDetector  RiskTierer
                       │
                       ▼
                FAISS over { frameworks, policies, past_responses }

All steps emit MLflow spans → eval_harness SQLite store → Next.js UI.
LLM gateway: OpenRouter → google/gemini-flash-latest (+ portability set).
```

## 4. The Failure Mode (cold open material)

In a naive demo Quill confidently produces a 200-answer questionnaire that
looks perfect. Trace expanded reveals:

- **Phantom policy IDs** — agent fabricated `VendorMgmt-Policy-022` to
  satisfy a citation requirement. Policy does not exist in the corpus.
- **Over-generalized claims** — answered "Yes, PCI-DSS Level 1 certified"
  because marketing site once said "PCI compliant."
- **Skipped clauses** — retrieved the right framework section but missed
  clause 4.2 governing surge in the specific control family.

Stakes: the response gets caught in enterprise due diligence. Deal dies.
Reputational hit. Possible legal exposure.

The cold open is this exact trace. Question on stage: *"Where did the
agent lie?"* — then we open the trace.

## 5. Promise of the harness — CLEAR-S coverage

Every Quill question is graded across CLEAR axes plus Selection (per
classifier) and Safety (vs prompt injection):

| Axis | What it catches in Quill |
|---|---|
| **C**orrectness | Phantom policy ID, fabricated certifications |
| **L**atency | Time-per-question budget, full-batch budget |
| **E**xecution | Did agent call `policy_exists_check` before citing? Trajectory scorer. |
| **A**dherence | Tone, length, template fit per framework |
| **R**elevance | RAG groundedness vs cited chunk (Ragas) |
| **S**afety | Prompt injection in attacker-supplied questions, PII leak, fabricated CVE / cert claim |
| **Cost** | Per-question, per-questionnaire, per-optimization budgets |

200 questions × 7 axes = **1,400 evaluation surfaces per run**. Densest
showcase any agent harness can offer in 45 min.

## 6. The Self-Evolving Loop

```
   ┌──────────────────────────────────────────────────────────────┐
   │                                                              │
   │   1. Run eval on golden set ─► MLflow traces ─► SQLite       │
   │                                                              │
   │   2. Cluster failures by CLEAR axis                          │
   │                                                              │
   │   3. GEPA: reflect over failed traces, mutate system prompt  │
   │      Pareto select across { C, L, E, A, R, S, Cost }         │
   │                                                              │
   │   4. Re-eval baseline vs candidate on holdout                │
   │                                                              │
   │   5. Promote winner ─► regression suite ─► deploy            │
   │                                                              │
   │   6. Cross-model portability check (Llama / Claude / Qwen)   │
   │                                                              │
   └──────────────────────────────────────────────────────────────┘
```

Pre-baked numbers on stage (representative; finalised by 2026-05-29 dry-run):

| Metric | Baseline | GEPA-tuned | Cross-framework holdout (SOC2 → ISO 27001) |
|---|---|---|---|
| Citation correctness | 0.58 | **0.91** | 0.84 |
| Hallucinated commitment rate | 14% | **3%** | 5% |
| Reviewer-accept rate (judge) | 0.43 | **0.78** | 0.69 |
| Avg cost per question (USD) | 0.021 | **0.011** | 0.012 |
| Avg time per questionnaire | 47 min | **18 min** | 22 min |

The Pareto chart on `/pareto/[id]` shifts visibly. Mint accent fires
on the dominating frontier. **This is the climax.**

## 7. Stack (open-source-native, Databricks-OSS-friendly)

| Layer | Choice |
|---|---|
| Orchestration | LangGraph (MIT) |
| Tracing | MLflow 3 Tracing (Apache 2.0) |
| Eval | `mlflow.genai.evaluate` + Ragas + custom scorers (Apache 2.0 / MIT) |
| Optimizer | DSPy + **GEPA** (MIT) |
| Retrieval | FAISS + sentence-transformers (MIT) |
| LLM gateway | **OpenRouter** API |
| Default model | `google/gemini-flash-latest` |
| Portability set | Llama-3.3-70B · Claude-Sonnet-4-6 · Qwen-2.5-72B |
| Trace store | local SQLite via SQLAlchemy |
| Backend | FastAPI |
| UI | Next.js 15 (app router, RSC) — see `DESIGN.md` |
| Trace inspection UI | MLflow native (link out — not rebuilt) |

No Databricks-proprietary surfaces. No Lakebase, no Unity Catalog, no MAS,
no Genie. Runs end-to-end on a laptop with `make demo`.

## 8. Five-Act Walkthrough (45 min)

### Act 1 — Cold open: The Phantom SOC2 Control (0–3 min)

- Live: Quill processes a 5-question SIG-Lite sample.
- Sample answers look clean: encryption at rest ✅, MFA ✅, SOC 2 Type II ✅.
- Q89 cites `VendorMgmt-Policy-022`. Looks fine.
- Expand trace. Policy does not exist in corpus. Agent confabulated ID
  to satisfy citation requirement. Past response mentioned `Vendor-Mgmt v2`;
  agent fused it with question text into a hallucinated policy ID.
- Q102 worse: "PCI-DSS Level 1" — never been certified. Pulled from
  marketing-site language.
- Punchline: *"Where did the agent lie?"* — open the trace tree in MLflow.

### Act 2 — Trace First, Eval Second (3–13 min)

- Why agentic stack traces are stochastic state machines, not deterministic.
- Show 50 pre-baked Quill traces. Scroll. Point at recurring shapes:
  phantom citations, skipped policy checks, over-generalization, tone drift.
- *Trace-first methodology* (Laurie Voss): write the eval against the
  observed failure shape, not against what you imagine could fail.
- Wire MLflow tracing into a LangGraph node — `@mlflow.trace(span_type="…")`.
- State injection via `span.set_attributes()` — log retrieved chunks,
  candidate tools considered, judge call costs.
- *Builder takeaway:* you cannot grade logic you cannot visualize.

### Act 3 — The Eval Stack (Live Build) (13–28 min)

Build four layers in front of the audience:

**Layer 1 — Deterministic scorers (the ship blockers).**
- `policy_exists(citation_id) -> bool`
- `framework_clause_resolves(citation) -> bool`
- `word_count_within_budget(answer)`
- `cost_per_question < $X`
- Cheap. Run in milliseconds. Catch the loud failures.

**Layer 2 — Semantic (Ragas).**
- `groundedness(answer, retrieved_chunks)` — strict chunk-level grounding
- `faithfulness(answer, gold_response)` — calibrated LLM judge
- Show judge calibration: precision/recall of judge against 50 human-labeled
  cases. Pre-empt skeptic.

**Layer 3 — Trajectory-aware (the frontier).**
- `policy_exists_called_before_cite(trace)` — was the verification tool
  invoked before the answer cited the policy?
- `gap_detector_invoked_for_no_policy(trace)`
- `tool_order_sane(trace)` — no cycles, no skipped supervisor edges

**Layer 4 — Safety + red-team.**
- Prompt-injection corpus (50 attacker-supplied questions trying to make
  Quill commit to controls it doesn't have)
- PII scanner on every drafted answer
- Hallucinated-claim detector against marketing-style language

CLEAR-S confusion matrix on screen. Cluster failures by axis.

### Act 4 — Closing the Loop (28–42 min)

The headliner. Self-evolving harness in motion.

- Pull 80 failed traces from MLflow (score < 0.6).
- DSPy + GEPA reflective mutation: each failed trace gets a textual
  diagnosis; mutated prompt candidates generated and Pareto-selected
  across { correctness, groundedness, safety, cost, latency }.
- Live shift to `/pareto/[id]`. Baseline dots cluster lower-left.
  GEPA frontier sweeps in mint over 400 ms.
- Open the prompt diff on `/prompt-diff` — left baseline, right tuned.
  Inline annotations explain the structural moves GEPA found
  (added policy-exists pre-check, added "do not commit to unowned controls"
  guardrail, tightened citation format).
- Re-eval on the holdout (ISO 27001 questions trained on SOC 2 corpus).
  Cross-framework portability shows the lift held: **+24 points
  reviewer-accept rate.**
- Regression suite catches a Claude-Sonnet model swap that loses 4
  points on `policy_exists_called_before_cite` — block deploy live.

### Act 5 — Axioms + Q&A (42–45 min, then 15 min Q&A)

```
1. Trace before eval.
2. Eval layers stack: deterministic for constraints, semantic for
   tone, trajectory for logic, safety for adversaries.
3. Static prompts ship hallucinations.
   Self-evolving harness compounds away from them.
4. Optimize the tail, not the mean. p95 fails ship; p50 wins do not.
5. Maintainers built CI for code. Agents need CI for behavior.
   This harness is that CI.
```

## 9. Stage assets / hard requirements

- Local MLflow tracking server with **pre-populated traces** (no live API
  failure risk on stage).
- Pre-baked GEPA artifacts: baseline prompt + tuned prompt + Pareto JSON
  + holdout numbers. No live optimization on stage (too slow).
- Backup: full 5-min screen recording of the demo path in case Wi-Fi fails.
- IDE theme: dark mode high contrast. Font size ≥ 18pt for projector.
- Browser zoom on UI: 125% minimum.
- Hard mute notifications (Slack, Mail, calendar).
- Single Chrome profile for stage. All other tabs closed.

## 10. Rehearsal plan

| Date | Goal |
|---|---|
| 2026-05-28 | Full dry-run #1 with timer. Identify cuts. |
| 2026-05-29 morning | Dry-run #2 with backup laptop. Cold-open seeded scenario rehearsed 3×. |
| 2026-05-29 evening | Flip repo public. Post pre-talk teaser tweet. |
| 2026-05-30 morning | One quiet read-through. Then leave it alone. |

---

## Appendix A — Companion repo structure

See `CLAUDE.md` and `DESIGN.md` at repo root for stack and visual contract.

```
eval-harness/
├── core/                      # generic harness (LLM, tracing, scorers, optimizer, store)
├── api/                       # FastAPI
├── ui/                        # Next.js 15
├── examples/quill/            # hero example
├── scripts/                   # ingest, seed, prebake
├── tests/
└── docs/                      # session plan + transcripts + DESIGN.md
```

## Appendix B — Source synthesis

This plan is informed by `docs/Transcript_*.md`:
- Amy Boyd / Nitya Narasimhan — agent observability, automated red-team
- Ara Khan — evals are broken, use them anyway; token/latency/cost tracking
- Laurie Voss — trace-first methodology, custom judges, precision/recall
- MLflow Advanced Tracing — manual span types, state injection
- MLflow RAG Eval — `mlflow.genai.evaluate` + Ragas integration
- MLflow Issue Detection — CLEAR framework + auto-clustering
- Tejas Kumar — harness = environment that catches agent lies
