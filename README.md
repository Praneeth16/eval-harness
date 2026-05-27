# eval-harness

> **Self-evolving eval harness for production AI agents.**
> Companion repo for the **"Journey of an Agent — From Demo to Production"**
> session at Agent Harness, Bangalore (2026-05-30).

**Memorable thing:** *agents learn from their own failures here.*

A generic eval-harness core (`core/`), a FastAPI backend (`api/`), a
Next.js 15 UI (`ui/`), and a hero example — **Quill**, a multi-agent
RFP / security-questionnaire response system that proves the whole
loop end-to-end.

---

## What's inside

| Layer | Choice |
| --- | --- |
| Agent orchestration | LangGraph |
| Tracing | MLflow 3 Tracing (linked-out UI, not rebuilt) |
| Eval | `mlflow.genai.evaluate` + Ragas + custom CLEAR-S scorers |
| Optimizer | DSPy + **GEPA** (Pareto multi-objective) |
| Retrieval | FAISS + sentence-transformers |
| LLM gateway | **OpenRouter** (`google/gemini-flash-latest` default) |
| Trace store | SQLite via SQLAlchemy |
| API | FastAPI |
| UI | Next.js 15 (app router, RSC) — see `DESIGN.md` |

No proprietary surfaces. Everything runs on a laptop.

---

## Quickstart

```bash
# One-time setup
make install          # uv venv + Python deps + npm deps
make seed             # initializes DB and seeds offline demo data

# Three terminals (or panes)
make api              # FastAPI on :8000
make ui               # Next.js on :3000
make mlflow           # MLflow UI on :5000

# Open
open http://localhost:3000
```

For a real eval run (requires `OPENROUTER_API_KEY` in `.env`):

```bash
cp .env.example .env  # then fill OPENROUTER_API_KEY
make eval-soc2
```

To materialize the full pre-baked demo artifacts (baseline traces,
GEPA-tuned prompts, Pareto JSON, cross-framework holdout numbers):

```bash
make prebake
```

---

## Layout

```
eval-harness/
├── core/                     generic harness — LLM, tracing, scorers, optimizer, store, clusters
│   ├── llm/                  OpenRouter client (OpenAI-compatible) w/ cost tracking + retries
│   ├── tracing/              MLflow setup + span taxonomy
│   ├── store/                SQLAlchemy ORM + sessions + WAL mode
│   ├── scorers/              CLEAR-S in four layers:
│   │     layer1_deterministic, layer2_semantic, layer3_trajectory, layer4_safety
│   ├── clusters/             cluster failures by axis + scorer pattern
│   ├── eval/                 the eval runner (mlflow.genai.evaluate wiring)
│   └── optimizer/            GEPA — reflective prompt mutation + Pareto frontier
├── api/                      FastAPI: runs, traces, clusters, pareto, prompt-diff, portability
├── ui/                       Next.js 15 — landing, runs, clusters, optimize, pareto (HERO), prompt-diff, portability
├── examples/quill/           hero example
│   ├── seed_corpus.py        frameworks (SOC2 / ISO27001 / GDPR / DPDP), policies, past responses, cold-open + injection corpora
│   ├── retrieval.py          FAISS + deterministic lookups (policy_exists, framework_clause_resolves)
│   ├── graph.py              LangGraph 6-node supervisor: parser → classifier → rag → drafter → gap_detector → risk_tierer
│   ├── tools.py              policy / framework verification tools the agent should call before citing
│   ├── golden/               SOC2 train, ISO27001 holdout, prompt-injection adversarial
│   ├── prompts/baseline.py   under-constrained baseline — fails the cold open deliberately
│   ├── prompts/tuned.py      GEPA-target tuned prompts — closes the phantom-policy + PCI overclaim holes
│   └── prebaked/             headline + portability sidecars for the demo (committed for offline reproducibility)
├── scripts/                  seed_demo_data.py (offline) and prebake.py (LLM-backed)
└── docs/                     session plan + transcripts + DESIGN.md
```

---

## The five-act demo path (45 min)

1. **Cold open — The phantom SOC 2 control** (0–3). One question, one trace,
   one fabricated `VendorMgmt-Policy-022`. Open the trace tree in MLflow.
2. **Trace first, eval second** (3–13). Scroll 50 pre-baked traces. Spot the
   recurring failure shapes. Write the eval against observed failures.
3. **The eval stack** (13–28). Build CLEAR-S in four layers, live:
   deterministic → semantic judge → trajectory → safety / red-team.
4. **Closing the loop** (28–42). DSPy + GEPA reflective mutation; Pareto select
   across `{correctness, groundedness, safety, cost, latency}`. The mint
   frontier sweeps in on `/pareto/[id]`. Prompt diff on `/prompt-diff/[id]`.
   Cross-framework holdout (SOC 2 → ISO 27001) on `/portability/[id]`.
5. **Axioms** (42–45). Trace before eval. Eval layers stack. Static prompts
   ship hallucinations; a self-evolving harness compounds away from them.
   Optimize the tail, not the mean. **Agents need CI for behavior. This
   harness is that CI.**

---

## License

Apache-2.0.
