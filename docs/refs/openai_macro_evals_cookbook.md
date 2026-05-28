# Macro Evals for Agentic Systems: Full Cookbook Content

**Source:** https://developers.openai.com/cookbook/examples/partners/macro_evals_for_agentic_systems/macro_evals_for_agentic_systems
**Authors:** Shikhar Kwatra (OpenAI), Will Thieme, Bradley Strauss
**Publication Date:** May 19, 2026

---

## Executive Summary

This cookbook demonstrates how to evaluate multi-agent systems at population scale. Rather than inspecting individual traces, macro evals discover recurring behavior patterns across hundreds of agent runs, then diagnose where to inspect first.

The core thesis: "When an agentic system fails, the problem is often larger than a single bad response."

---

## 1. Core Problem: Why Macro Evals Matter

### The Challenge with Multi-Agent Systems

Traditional evals grade single model outputs. Multi-agent systems require different thinking:

- A handoff may occur too late
- A specialist agent may miss the same signal repeatedly
- Review processes may trigger for wrong case types
- Problems emerge as patterns across many traces, not isolated errors

### Two-Level Evaluation Strategy

**Lower-level evals** grade individual agents, tool calls, and handoffs using rubrics like:
- final_decision_quality
- policy_compliance_correctness
- routing_specialist_activation
- market_drift_awareness
- review_appropriateness

**Macro evals** aggregate these signals to discover:
- Which kinds of problems repeat
- Where they concentrate in the population
- Which part of the workflow deserves inspection first

### Key Public Labels

| Label | Meaning |
|-------|---------|
| `case_type` | Generated business scenario (e.g., clean_simple, pricing_exception_compound) |
| `run_outcome` | How the run ended (completed, awaiting_review, blocked, failed) |
| `eval_finding` | Local signal from lower-level rubric |
| `behavior_pattern` | Discovered recurring pattern across many traces (emerges after clustering) |

---

## 2. System Architecture

### End-to-End Agentic System Map

```
Scenario inputs
    ↓
Orchestrated specialist swarm (agents, handoffs, tools)
    ↓
Runtime traces (events, spans)
    ↓
Lower-level evals (Promptfoo labels on completed runs)
    ↓
Normalized traces + eval labels
    ↓
Trace documents (compressed workflow evidence)
    ↓
BERTopic-style clustering → behavior patterns
    ↓
AgentTrace-style diagnosis → root-cause suspects
```

### Evidence captured per run (bundle):
- `run`: Run ID, trace ID, terminal state, batch metadata, order context
- `events`: Normalized event log (status updates, handoffs, tool calls, responses, findings)
- `spans`: OpenAI Agents SDK trace spans for execution structure
- `environment_events`: Dated world state (tariffs, incentives, stockouts, promotions, competitor pressure, launches, schedule/capacity signals)
- `review_packet`: Simulated review artifact with findings, recommended action, allowed actions, review status
- `snapshots`: Optional inventory, capacity, environment snapshots

---

## 3. Lower-Level Eval Layer: Promptfoo Rubrics

### Five Core Rubrics

```python
PROMPTFOO_RUBRICS = [
    ("final_decision_quality",
     "Final decision is supported by active issues, terminal state, and agent outputs."),
    ("policy_compliance_correctness",
     "Policy, tariff, incentive, and regional compliance context is handled correctly."),
    ("routing_specialist_activation",
     "Specialist routing matches the issues present in the bundle."),
    ("market_drift_awareness",
     "Changing market conditions and dated environment signals are noticed."),
    ("review_appropriateness",
     "Review and escalation behavior is proportionate to the case risk."),
]
```

### Expected Results Pattern

In a balanced dataset:
- ~60-75% of traces pass all rubrics
- ~25-40% fail at least one rubric
- `final_decision_quality` failures appear most frequently
- `review_appropriateness` and `market_drift_awareness` failures indicate pattern-level issues

---

## 4. BERTopic-Style Discovery Process

### Mathematical Framework

**Step 1: Document Embedding**

For each trace document $d_i$:
$$e_i = f(d_i)$$
where $f$ is an embedding model (e.g., Sentence-BERT, OpenAI embedding API).

**Step 2: Dimensionality Reduction (UMAP)**
- `n_neighbors`: min(30, max(2, population_size - 1))
- `min_dist`: 0.0
- `metric`: "cosine"

**Step 3: Density Clustering (HDBSCAN)**
- `min_cluster_size`: min(24, max(2, population_size // 4))
- `prediction_data`: True

Clusters with fewer than min_cluster_size traces are marked as noise (topic_id = -1).

**Step 4: Topic Representation** — class-aware TF-IDF for distinctive terms

**Step 5: Impact Scoring**

$$\text{impact\_score}(k) = \text{prevalence\_share}(k) \times \text{severity\_weighted\_prevalence}(k)$$

---

## 5. Comparative Analysis: Slice Lift

$$\text{lift} = \frac{\text{slice\_pattern\_share}}{\text{overall\_pattern\_share}}$$

- lift = 1.0: Pattern appears in slice at overall rate
- lift > 1.0: Pattern is concentrated in this scenario slice
- lift < 1.0: Pattern is less common in this slice

---

## 6. AgentTrace-Style Diagnosis

### Root Cause Suspect Scoring

From a focus event (anchor), walk backward and score upstream suspects:

$$\text{suspect\_score} = 0.4 \times \text{proximity} + 0.3 \times \text{frequency} + 0.2 \times \text{bridge} + 0.1 \times \text{role}$$

### Focus Event Types

| Signal | Meaning |
|---|---|
| review finding | Review/validation surface recorded an issue |
| review required / awaiting_review | Simulated business process paused for review |
| failed / blocked | Run ended in degraded terminal state |
| triage route / reroute | Workflow changed ownership or path |
| tool warning / policy marker | Structured tool exposed risk or policy context |

---

## 7. Key Takeaways for AI Teams

### When to Use Macro Evals

- Your system has **multiple specialized agents** with handoffs
- You want to understand **repeated behavior patterns** across hundreds of runs
- Lower-level evals or Promptfoo already grade individual traces
- You need to **prioritize inspection** across a large failure population

### What Macro Evals Answer

| Question | Method |
|----------|--------|
| Which behavior patterns repeat across my traces? | BERTopic-style discovery |
| Where do patterns concentrate (by case type, agent version, market condition)? | Slice lift analysis |
| Which parts of my workflow should I inspect for a pattern? | AgentTrace-style diagnosis |
| How do discovered patterns relate to lower-level eval findings? | Sankey flow diagrams |

### Implementation Workflow

1. **Collect traces** from your agent system with event-level detail (agent names, tool calls, handoffs)
2. **Grade with lower-level evals** (use Promptfoo, OpenAI evals, or custom rubrics)
3. **Normalize and document** each trace into a comparable format
4. **Cluster on documents** using BERTopic or similar embedder + UMAP + HDBSCAN
5. **Analyze and compare** behavior patterns across metadata slices
6. **Diagnose suspects** by walking backward from focus events in sample traces
7. **Share results** with engineering and product teams

### Common Pitfalls

- **Poor document construction**: If your trace documents omit routing decisions or environment signals, clustering will miss behavior that matters for macro evals
- **Too much focus on noise**: Topics with only 2–5 traces are exploratory. Focus on patterns with at least 10–20 traces before diagnosing
- **Confusing correlation with causation**: Suspect scores are triage hints, not root-cause proofs. Always inspect the actual traces
- **Ignoring metadata slices**: A behavior pattern looks different in a clean case vs. a supplier-substitution case. Use slice lift to find where it's truly unexpected
