# Session Plan: Journey of an Agent: From Demo to Production

## 1. Session Logistics & Vibe
* **Event:** Agent Harness (Builder-First Session)
* **Date & Time:** May 30th, 2026 | 1:00 PM - 1:45 PM (45 mins + 10-15 mins Q&A)
* **Location:** Hinge Health, Indiranagar, Bangalore
* **Target Audience:** Hardcore AI engineers, builders, and developers. Zero marketing fluff.
* **Speaker Persona / Presentation Style:** "Chip Huyen" systems-engineering approach. Deeply analytical, data-driven, highlighting real-world constraints (cost, latency, non-determinism). Emphasize math, telemetry, and strict engineering over "magic" or "vibes."
* **Tech Stack Focus:** Open Source Native — LangGraph, FAISS, DSPy, MLflow (with Lakebase acting as the scalable backend trace store).

---

## 2. The Core Use Case: Dynamic Supply Chain & Logistics Resolution Agent
To prove the necessity of a harness, we avoid simple chat/RAG use cases. We use a high-stakes scenario.

* **The Scenario:** A B2B logistics escalation. 
    * *Input:* "Temperature-sensitive pharma shipment SKU-9902 from Amsterdam to Bangalore is delayed in Frankfurt due to strikes. Cold-chain threshold is 72 hours; 24 hours elapsed. Re-route, recalculate duty thresholds, and issue a compliance variance certificate."
* **The Architecture:** * **Orchestrator:** LangGraph (State graph managing the workflow).
    * **Retrieval:** FAISS (For querying compliance/variance rules).
    * **Tools:** External mock APIs (`search_flight_routes`, `calculate_eu_tariffs`).
* **The Failure Mode (Why it needs an eval):** In a naive demo, the agent might successfully reroute the package via a maritime route taking 96 hours—ruining the cold-chain pharma cargo. The final output *looks* confident and well-formatted, but is functionally disastrous. 

---

## 3. Minute-by-Minute Walkthrough (45 Minutes)

### Phase 1: The "Vibes" Problem & The Swiss Cheese Model (0–5 Mins)
*Objective: Hook the audience by validating the pain of productionizing agents.*
* **The Paradigm Shift:** Software engineering relies on deterministic stack traces. Agentic workflows introduce stochastic state machines. If a LangGraph node fails, the agent might silently hallucinate a workaround, loop infinitely to retry an API, or confidently return a fatal error wrapped in perfect markdown.
* **Chip's Axiom:** "If you evaluate only the final output, you pass lucky guessers. Lucky guessers break production."
* **The Swiss Cheese Model of Evaluation:** Introduce the layers of defense. No single eval catches everything. You need:
    1.  **Deterministic Unit Tests** (Syntax, Tool Triggers, Hard Constraints).
    2.  **Semantic Output Judges** (Tone, Groundedness, Hallucination).
    3.  **Trajectory/Execution Judges** (Efficiency, Logic paths).

### Phase 2: Instrumenting the Black Box with MLflow (5–15 Mins)
*Objective: Shift to the architecture. Evaluation requires deep visibility.*
* **Live Whiteboarding/Code:** Show the LangGraph architecture for the Logistics Agent.
* **Beyond `autolog`:** Explain why `mlflow.openai.autolog()` falls short for agents. It captures the LLM calls but loses the context of the workflow.
* **Manual Span Trees:** Show how to instrument nodes. 
    * Demonstrate wrapping Python functions with `@mlflow.trace(span_type="tool")` and `@mlflow.trace(span_type="retriever")`.
* **State Injection:** Show the critical step of using `span.set_attributes()`. If the flight API returns 5 routes, inject that raw array into the span *before* the LLM decides. 
* **Storage Scale:** Briefly note that as tracing scales across concurrent agent runs, backing MLflow with a robust data layer like Lakebase ensures traces remain highly searchable and durable for downstream analysis.
* **The UI Reveal:** Switch to the MLflow UI. Show a fully expanded nested execution graph: `Goal -> Plan -> FAISS Retrieve -> Tool Call -> Synthesis`. Emphasize: *You cannot grade logic until you visualize the trajectory.*

### Phase 3: Building the Eval Harness (Live Code) (15–30 Mins)
*Objective: Write the tests that catch the agent's failure.*
* **Layer 1: Deterministic Code Evals (The Ship Blockers)**
    * *Concept:* Don't use an expensive LLM to check math or constraints. 
    * *Live Code:* Write a custom Python `@scorer` in MLflow that intercepts the trace. It asserts that `new_route_duration < remaining_cold_chain_hours (48h)`. If `False`, the execution is flagged as a catastrophic failure. Costs $0, runs in 2ms.
* **Layer 2: RAG & Output Judges (Semantic Checks)**
    * *Concept:* The agent issued the "Compliance Variance Certificate." Is it legally accurate based on the retrieved FAISS documents?
    * *Live Demo:* Integrate OSS frameworks (like Ragas or Arize Phoenix metrics) directly into the `mlflow.genai.evaluate()` pipeline. Show a `Groundedness` check evaluating the LLM output *strictly* against the retrieved FAISS chunks.
* **Layer 3: Trace-Aware Trajectory Evals (The Frontier)**
    * *Concept:* Did the agent waste tool calls? 
    * *Live Demo:* Show a custom judge reading the *sequence* of the MLflow trace. Did it query flight schedules *before* looking up cold-chain constraints? If yes, fail the trajectory for poor logical planning.

### Phase 4: The Data Flywheel & DSPy Optimization (30–40 Mins)
*Objective: Close the loop. Evals aren't just dashboards; they are optimization engines.*
* **Mining Traces for Golden Data:** Demos break because user inputs shift. Show a script running `mlflow.search_traces(filter_string="tags.ExecutionEfficiency < 0.5")` to pull up failing trajectories.
* **Capability vs. Regression:** Explain the lifecycle. When you add a new API to the agent, write a *Capability Eval*. Once passed, it permanently joins the test suite as a *Regression Eval*.
* **Algorithmic Prompt Optimization:** * *The Pitch:* Stop manual prompt engineering. It is fragile and unscientific. 
    * *The Architecture:* Take the golden dataset of failed-but-corrected traces from MLflow. Feed this dataset into **DSPy**. Use DSPy's teleprompter (e.g., MIPRO) to mathematically compile and optimize the agent's internal system instructions, maximizing the pass rate against your deterministic and semantic judges.

### Phase 5: Synthesis & Q&A (40–45 Mins)
* **Summary Axioms:**
    1. Traces are your foundation.
    2. Stack your evals: Code for constraints, LLMs for semantics, Trajectory for logic.
    3. Use the flywheel: Traces -> Datasets -> DSPy compilation.
* **Open Floor for Builders.**

---

## 4. Hardware / AV Checklist
* Light/Dark mode IDE themes tested for projector contrast at Hinge Health.
* Local MLflow tracking server spun up with pre-populated traces to avoid live API latency/failures.
* Postman/cURL examples ready to demonstrate raw inputs to the LangGraph endpoint.
