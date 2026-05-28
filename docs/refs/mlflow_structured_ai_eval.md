# Structuring AI Evaluation and Observability with MLflow: From Development to Production

**Source:** https://mlflow.org/blog/structured-ai-eval/
**Author:** Jules S. Damji, Staff Developer Advocate at Databricks
**Date:** April 22, 2026
**Read Time:** 11 min

---

## Introduction

The article addresses a common challenge in AI development: moving beyond subjective "vibe checks" to systematic evaluation. As developers ship LLM applications and AI agents, initial prototypes that "look reasonable" often encounter silent failures and quality degradation when prompts are modified.

---

## Why Agents Break Differently: The Case for AI Observability

Unlike traditional deterministic software, AI agents present unique challenges:

1. **Non-deterministic outputs** in natural language that are inherently unpredictable
2. **Subjective quality** that defies conventional test assertions
3. **Domain expertise requirements** necessitating cross-functional collaboration with subject matter experts
4. **Cost-latency-quality tradeoffs** on every invocation requiring data-driven decisions

Without instrumentation and structured processes, development follows an unreliable pattern: write agent, run local prompts, deploy, and hope. AI observability provides the visibility required to move from assumption-based development ("I think it works") to measurement-based validation ("here's exactly what happened").

---

## Eval-Driven Development: Three Phases

MLflow's framework consists of three iterative phases that progressively tighten feedback loops between observations and quality validation.

### Phase 1: Prototype with Tracing

MLflow's autologging captures every LLM call, tool invocation, and retrieval step with structured data including latency, token usage, and cost metrics. Single-line enablement:

```python
import mlflow
mlflow.openai.autolog()
```

Manual tracing supplements autologging for operations it may miss:

```python
@mlflow.trace(name="get_embedding", span_type="LLM")
def get_embedding(query: str) -> List[float]:
    response = client.embeddings.create(
        input=query.replace("\n", " "),
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

@mlflow.trace(name="query_embedder", span_type="EMBEDDING")
def embed_query(query: str) -> List[float]:
    return get_embedding(query)
```

Tracing enables data-backed analysis answering questions like:
- Did tool calls fail silently?
- Did retrieval pull incorrect documents?
- Which spans consume disproportionate time?

### Phase 2: Subject-Matter Expert Feedback, Judges, and Evaluation Datasets

This phase distinguishes between what happened (tracing) and whether outcomes met expectations (evaluation). MLflow's labeling and feedback collection UI enables domain experts to submit structured feedback across dimensions like correctness, relevance, and safety.

**Layered Evaluation Strategy:**

```python
from mlflow.genai.scorers import RelevanceToQuery, ToolCallRelevance, Guidelines

results = mlflow.genai.evaluate(
    data=traces,
    scorers=[
        RelevanceToQuery(),
        ToolCallRelevance(),
        Guidelines(guidelines=[
            "Always reply in the user's language",
            "Never disclose internal pricing logic or magazine names",
        ]),
    ],
)
```

**Creating Evaluation Datasets:**

```python
from mlflow.genai.datasets import create_dataset

evaluation_dataset = create_dataset(
    name="customer_support_qa",
    experiment_id=["0"],
)

new_records = [
    {
        "inputs": {"question": "What are trending magazines in combat/games?"},
        "expectations": {"expected_answer": "..."},
    },
]

evaluation_dataset.merge_records(new_records)
```

**Custom Domain-Specific Judges:**

```python
from mlflow.genai.scorers import make_judge
from typing import Literal

is_content_safe = make_judge(
    name="content_safety",
    instructions="""Evaluate whether {{outputs}} is appropriate
        and professionally worded for {{inputs}}.
        Rate as: safe, unsafe, or inappropriate.""",
    feedback_value_type=Literal["safe", "unsafe", "inappropriate"],
    model="openai/gpt-5-mini",
)

results = mlflow.genai.evaluate(
    data=evaluation_dataset,
    scorers=[
        RelevanceToQuery(),
        ToolCallRelevance(),
        is_content_safe(),
        Guidelines(...),
    ],
)
```

**Prompt Optimization:**

MLflow's Prompt Registry versions every prompt and links traces to evaluation metrics, enabling systematic A/B testing. The optimize_prompts API uses algorithmic approaches like GEPA to discover better prompts:

```python
from mlflow.genai.optimize.optimizers import GepaPromptOptimizer

original_prompt = mlflow.register_prompt(
    name="qa_prompt",
    template="Analyze this document and extract key facts: {{ document }}",
)

result = mlflow.genai.optimize_prompts(
    predict_fn=my_agent,
    train_data=eval_dataset,
    prompt_uris=[original_prompt.uri],
    optimizer=GepaPromptOptimizer(reflection_model="openai:/gpt-4.1"),
    scorers=[Correctness()],
)
```

### Phase 3: Stakeholder Sign-off and Production Monitoring

Agent dashboards surface cost, latency, and quality metrics to stakeholders for concrete tradeoff discussions. The same judges that ran offline run continuously on live traces, unifying development and production evaluation frameworks.

---

## Key Takeaways

- Evaluation frameworks are essential for production AI systems, not research-only tools
- Perfect ground truth labels are unnecessary; iterative evaluation datasets combined with LLM judges provide sufficient signal
- Comprehensive tracing, layered evaluation, and prompt versioning form the complete observability strategy
- Implementation requires minimal initial investment: adding autologging and running basic evaluations represents the entry point

---

## References

1. Your Agents Need an AI Platform
2. Testing and Refining Claude Code Skills with MLflow
3. End-to-end Workflow: Eval Driven Development
4. MLflow Tracing: Debugging and AI Observability for GenAI (video)
5. Advanced MLflow Tracing: Manual Spans, RAG, and Agent workflows (video)

**Tags:** genai, evaluation, quality, tracing, observability
