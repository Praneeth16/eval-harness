# eval-harness

> **A self-evolving eval harness for production AI agents.**
> Companion repo for the talk **"Journey of an Agent: From Demo to Production"**
> (Agent Harness, Bangalore, 2026-05-30).

**The memorable thing:** *agents learn from their own failures here.*

An agent that demos perfectly will still ship confident, fluent lies in
production: asserting an outcome it never achieved, citing a policy that does
not exist, overstating "compliant" into "certified." Those failures pass a vibe
check and a string/citation eval. The evidence of the lie is not in the final
text, it is in **what the agent did** (the trajectory) and **the state of the
world afterward** (the outcome).

This harness catches that, then closes the loop: trace every step, score across
seven axes, cluster the failures, optimize the prompt, gate on a held-out set,
ship. It is **CI for agent behavior**.

It ships with a hero example, **Quill**, a security-questionnaire / RFP response
agent, but the harness is the reusable part: swap in any agent that retrieves,
cites, and acts.

---

## Slides

The talk deck and a one-per-page PDF live in [`docs/deck/`](docs/deck/):

- **PDF:** [`docs/deck/journey-of-an-agent.pdf`](docs/deck/journey-of-an-agent.pdf)
- **Interactive HTML:** [`docs/deck/journey-of-an-agent.html`](docs/deck/journey-of-an-agent.html) (open in any browser; arrows / space to navigate, `F` fullscreen, `O` overview)

---

## What's inside

| Layer | Choice |
| --- | --- |
| Agent orchestration | LangGraph |
| Tracing | MLflow 3 Tracing (we link out to its trace UI, not rebuilt) |
| Scoring | Custom **CLEAR-S** scorers in four layers (deterministic, trajectory, LLM-judge, safety) |
| Optimizer | DSPy + **GEPA** (reflective prompt mutation, Pareto multi-objective) |
| Retrieval | FAISS + **gemini-embedding-001** (sentence-transformers fallback for offline) |
| LLM gateway | **Google AI Studio** (`gemini-2.5-flash` default); OpenRouter optional for the cross-provider sweep |
| Trace store | SQLite via SQLAlchemy |
| API | FastAPI |
| UI | Next.js 15 (app router, RSC) — see `DESIGN.md` |

Open-source, no proprietary surfaces, runs end-to-end on a laptop.

---

## CLEAR-S — scoring as a coordinate system

Seven axes so you cannot hide a regression in the average. Each is a named
scorer that can be falsified, not a vague `quality: 4/5`:

| Axis | Catches |
| --- | --- |
| **C**orrectness | cited ID does not exist in the corpus |
| **L**atency | p95 over the budget |
| **E**xecution | the verifier fired *after* the draft (trajectory) |
| **A**dherence | answer omits a required statement |
| **R**elevance | answer addresses an adjacent question |
| **S**afety | a past-response phrase laundered into a citation |
| **Cost** | per-question spend over the tier budget |

The four scorer layers run in order (deterministic → trajectory → judge →
safety) so a malformed output never reaches the expensive judge.

---

## Quickstart

```bash
# One-time setup
make install          # uv venv + Python deps + npm deps
make seed             # init DB + seed offline demo data + build the FAISS index

# Three terminals (or panes)
make api              # FastAPI on :8000
make ui               # Next.js on :3000
make mlflow           # MLflow UI on :5000

open http://localhost:3000
```

Set up a model gateway for live runs (`cp .env.example .env`, then add your
`GEMINI_API_KEY`). Then:

```bash
make eval-soc2        # baseline Quill eval on the SOC 2 golden set
```

The UI has a **live Compare tab** (`/compare`): pick a question, and the
baseline and tuned agents run side by side so you can watch the
verify-before-cite trajectory the baseline never has.

---

## The agent eval flywheel

```
   trace ─▶ score (CLEAR-S, 4 layers) ─▶ cluster failures ─▶ optimize (GEPA)
     ▲                                                              │
     └──────── ship + monitor ◀── gate on held-out ◀───────────────┘
```

Every production failure re-enters at `trace`. The same scorers that gate the
offline run also run on live traffic, so leadership and engineering argue from
one scoreboard, not two.

---

## Layout

```
eval-harness/
├── core/                     generic harness — LLM, tracing, scorers, optimizer, store, clusters
│   ├── llm/                  OpenAI-compatible client (Google AI Studio / OpenRouter) w/ cost tracking + retries
│   ├── tracing/              MLflow setup + span taxonomy
│   ├── store/                SQLAlchemy ORM + sessions
│   ├── scorers/              CLEAR-S — layer1_deterministic, layer2_semantic (judge), layer3_trajectory, layer4_safety
│   ├── clusters/             group failures by (axis, scorer)
│   ├── eval/                 the eval runner
│   └── optimizer/            GEPA — reflective prompt mutation + Pareto selection
├── api/                      FastAPI: runs, traces, clusters, pareto, prompt-diff, portability, compare
├── ui/                       Next.js 15 — overview, runs, compare, clusters, optimize, pareto, prompts
├── examples/quill/           hero example
│   ├── seed_corpus.py        policies, framework clauses, past responses, cold-open + injection corpora
│   ├── retrieval.py          FAISS + deterministic lookups (policy_exists, framework_clause_resolves)
│   ├── graph.py              LangGraph: parser → classifier → rag → drafter → gap_detector → risk_tierer
│   ├── golden/               SOC 2, ISO 27001 holdout, prompt-injection adversarial
│   └── prompts/              baseline (single-call) + tuned (propose / verify / finalize)
├── scripts/                  seed_demo_data.py (offline) and prebake.py (LLM-backed)
└── docs/                     the slide deck (docs/deck/) + companion article
```

---

## Five axioms

1. Trace before you eval. You cannot grade logic you cannot see.
2. Eval layers stack: deterministic for constraints, judge for tone, trajectory for logic.
3. Static prompts ship hallucinations. A self-evolving harness compounds away from them.
4. Optimize the tail, not the mean. The p95 that fails ships; the p50 win does not.
5. We built CI for code. Agents need CI for behavior. This harness is that CI.

---

## License

Apache-2.0.
