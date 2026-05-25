# eval-harness — instructions for Claude Code sessions

Companion repo for the **"Journey of an Agent: From Demo to Production"**
session at Agent Harness, Bangalore (2026-05-30).

## What this repo is

A self-evolving eval harness for production AI agents. Generic core (`core/`),
FastAPI backend (`api/`), Next.js 15 UI (`ui/`), and a hero example
(`examples/quill/` — an RFP / security questionnaire response agent) that
proves the harness works end-to-end. **MLflow handles trace storage and
trace-tree inspection** — we link out to it rather than rebuild it.

## Stack (open-source-native)

- LangGraph (agent orchestration)
- MLflow 3 Tracing + `mlflow.genai.evaluate` (tracing + eval)
- FAISS + sentence-transformers (retrieval)
- DSPy + GEPA (self-evolving prompt optimization, Pareto multi-objective)
- Ragas (semantic / groundedness scorers)
- OpenRouter API (LLM gateway — default model: `google/gemini-flash-latest`)
- FastAPI + SQLite + SQLAlchemy (backend + store)
- Next.js 15 app router + RSC + Tailwind (UI)

## Design System

**Always read `DESIGN.md` before making any visual or UI decisions.**
All font choices, colors, spacing, motion, and aesthetic direction live there.
Do not deviate without explicit user approval. In QA mode, flag any code that
does not match `DESIGN.md`.

Memorable thing the UI must drive home: **"Agents learn from their own failures
here."** Every UI choice compounds toward the self-evolving payoff (Pareto
frontier as hero moment).

## Working style

- Plan mode for any change touching >1 file.
- Run linters / formatters before declaring done.
- Verify visually before claiming done on UI changes — start dev server,
  click through the affected flow, check console.
- Write commit messages explaining **why**, not what.
- One logical change per PR.
- Don't add comments, docstrings, or type annotations to code you didn't change.
- Don't add error handling for impossible scenarios. Validate at system
  boundaries only.

## Talk-specific guardrails

- The repo will be flipped public ~2 days before the talk for momentum.
  No secrets, no real customer data, no proprietary frameworks committed.
- Demo path must be fully reproducible offline (pre-baked traces, pre-baked
  GEPA artifacts) — no live OpenRouter calls required during the talk.
- The Pareto chart on `/pareto/[id]` is the climax visual. Treat it like a
  hero asset.
