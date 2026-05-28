# Agent Evaluation: A Detailed Guide

**Source:** https://cameronrwolfe.substack.com/p/agent-evals
**Author:** Cameron R. Wolfe, Ph.D.
**Date:** May 18, 2026
**Publication:** Deep (Learning) Focus Newsletter

---

## Fundamentals of Agent Systems

### Core Characteristics

Agents differ from conventional LLMs through five key capabilities:
- Reasoning
- Tool calling
- Multi-step problem solving
- Error recovery
- Autonomous user-facing actions

An agent: "an LLM that autonomously uses tools in a loop." Unlike standard LLMs, agents assess intermediate results and dynamically recover from errors within an **agentic loop**.

### Components of Agent Systems

1. **The underlying LLM or reasoning model** — cognitive core
2. **Tools for environmental interaction** (APIs, CLIs, MCP servers)
3. **Instructions guiding agent behavior**

#### Tool Calling Metrics

- *Invocation accuracy:* correct decision to call or avoid calling tools
- *Selection accuracy:* calling the correct tools
- *Structural accuracy:* proper tool call formatting
- *Trajectory accuracy:* comparing call sequences against ground truth
- *Outcome-oriented evaluation:* verifying final answer correctness

### The ReAct Framework

Structures the agentic loop into sequential steps: observe environment state, reason about optimal actions, take action based on reasoning.

```
Question: Who was Milhouse named after?
Thought 1: Search for Milhouse information
Action 1: Search[Milhouse]
Observation 1: [Character description]
Thought 2: Need to find naming origin
Action 2: Lookup[named after]
Observation 2: Named after President Richard Nixon
Action 3: Finish[Richard Nixon]
```

### Multi-Agent Systems

Single-agent designs should be optimized before expanding. Indicators to expand:
- Bloated instructions with agent struggling to follow logic
- Incorrect tool selection from oversized tool sets

**Manager Setup:** Central orchestrator delegates to specialists via tool calls.
**Decentralized Setup:** Peer agents hand off tasks based on specialization.

### Context Engineering

"Context engineering refers to the set of strategies for curating and maintaining the optimal set of tokens (information) during LLM inference."

#### Compaction Techniques

- *Summarization:* conversation summaries; reinitialize with compressed context
- *Tool result clearing:* remove older tool call outputs
- *Note-taking:* external notes accessible when needed

### Agent Scaffolds

"An agent harness (or scaffold) is the system that enables a model to act as an agent: it processes inputs, orchestrates tool calls, and returns results. When we evaluate an agent, we're evaluating the harness and the model working together."

Scaffolds control:
- Environment interface
- Prompting strategy
- Available tools and documentation
- System structure (sub-agents)
- Context management

Since scaffolds significantly impact performance, agent evaluation assesses **model-scaffold combinations** rather than isolated capabilities.

---

## Common Patterns in Agent Evaluation

### Evaluation Components

- **Tasks:** Individual test cases with predefined inputs and success criteria
- **Trials:** Individual task-solving attempts (typically multiple per task for consistency)
- **Transcripts:** Complete records of agent outputs, tool calls, reasoning, interactions
- **Outcomes:** Final external environment state after trial completion
- **Graders:** Quality checks on transcripts and/or outcomes

**Outcomes differ from outputs.** An agent might declare "The restaurant is booked!" without actually achieving the booking outcome.

### Grader Types

#### Human Evaluation
Definitive quality standard. Initial: manual inspections, vibe checks, researcher testing. Mature: detailed rubrics, pass/fail or Likert scales.

Evaluation quality depends on calibration. Human evaluators rarely agree without refined annotation guidelines.

#### Automatic Graders

**Code-based graders:** Python functions for deterministic checks
- String matching, assertions
- Math problem verification
- Coding problem test case execution
- Tool call verification in transcripts
- Traditional metrics (ROUGE, BLEU)

Benefits: efficiency, reproducibility, debuggability
Drawbacks: reference-dependent, inflexible

**Model-based graders:** LLM judges for subjective evaluation. Three scoring setups:
- *Pairwise scoring:* Judge selects better of two
- *Direct assessment:* Judge assigns single-response score
- *Reference-guided:* Judge receives golden reference plus candidate

Itemized rubrics with dozens of individually-assessed criteria improve reliability.

#### Multiple Graders Strategy

Combine:
- Human evaluation as calibration baseline
- Model-based graders for efficiency at scale
- Code-based graders for deterministic checks

### Broader Evaluation Categories

- Manual inspection and vibe checks
- Production monitoring (errors, usage metrics, outcomes)
- A/B testing (traffic splitting, metric comparison)
- Explicit user feedback (thumbs up/down, surveys)
- Cost metrics (token usage, spend, speed)

"Swiss Cheese" strategy combines complementary techniques.

---

## Agent Evaluation Case Studies

### τ-Bench Series

**τ-Bench** evaluates agents through dynamic multi-turn conversations in real-world domains (retail, airline). Agents must:
- Interact with users and resolve intent
- Adhere to written policies and rules
- Use tools to retrieve and modify environment

Information unfolds during conversation rather than being provided upfront.

#### Success Measurement

**Pass@K:** Probability agent solves task at least once across K attempts
- 1 - (unsuccessful_trials / total_trials)^K

**Pass^K:** Probability agent succeeds on all K attempts (stricter)
- successful_trials / total_trials, raised to K power

"For real-world agent tasks requiring reliability and consistency like customer service, we propose a new metric – pass^k (pass hat k), defined as the chance that all k i.i.d. task trials are successful, averaged across tasks."

Pass^K declines sharply with increasing K. Most agents perform poorly on Pass^K, even with reasoning models.

#### τ²-Bench Extension

Dual-control: both users and agents access shared external environment via tools. Telecom domain. 2,285 initial tasks reduced to 114 with uniform intent and difficulty distribution.

#### τ³-Bench

τ-banking domain with knowledge base retrieval requirements. Agents search ~700 documents. Performance drops significantly: recent reasoning models achieve only 25.5% Pass@1 on τ-banking vs 80%+ on verified prior domains.

### Terminal-Bench

Tasks exist in Docker containers with:
1. **Instruction** describing task completion requirements
2. **Docker image** providing initialized environment
3. **Test set** executing deterministic outcome verification
4. **Reference solution** demonstrating solvability

"Tests verify that all outcomes described in the instruction have been achieved by testing properties of the final container state; they do not test the agent's commands or console output. Terminal-Bench is an outcome-driven framework where each agent is free to accomplish the task using a variety of approaches."

229 tasks from 93 contributors → 89 final tasks after rigorous review. Three-stage human verification.

Model capabilities drive performance more than scaffold choice. Range: Kimi K2 Thinking 35.7%; GPT-5.2 62.9%.

### Additional Benchmarks

- **GAIA/GAIA-2:** General assistant; web browsing, tool use, multimodal
- **AgentCompany:** Software company simulation
- **WorkArena:** Enterprise software workflows using ServiceNow
- **OSWorld/OfficeBench/MobileBench:** Computer-use
- **MLE-Bench:** Autonomous ML experimentation
- **PaperBench:** AI research paper reproduction
- **SpreadsheetBench:** Excel manipulation
- **HIL-Bench:** Human-in-the-loop evaluation
- **GDPval:** Economically-valuable tasks

---

## Roadmap for Agent Evaluation

### Step 1: Define Success
- **Outcome goals:** Verify outcomes (database entries, reservations)
- **Process goals:** Verify transcript components (specific tool calls)

### Step 2: Collect Small Task Set
10-20 manually-curated tasks reflecting realistic use cases. Continuously add tasks discovered through agent failures.

### Step 3: Create High-Quality Tasks
Tasks must be unambiguous and yield consistent repeated evaluations.

### Step 4: Provide Ground Truth and References
Reference solutions and known-good trajectories proving solvability.

### Step 5: Configure Graders
Start with simple code-based deterministic checks. Progress to model-based graders for subjective criteria.

### Step 6: Build Evaluation Harness
- Realistic controlled agent execution
- Transcript collection (tool calls, intermediate outputs)
- Final outcome capture
- Use production scaffold, tools, and environment
- Start fresh for each trial

### Step 7: Inspect, Iterate, Maintain
Treat evaluation suites as living artifacts. Inspect transcripts post-evaluation verifying failures stem from agent mistakes rather than task quality issues.

---

## Bibliography

[1] Anthropic. "Demystifying evals for AI agents" (2026).
[2] Anthropic. "Effective context engineering for AI agents" (2025).
[3] OpenAI. "A practical guide to building agents" (2025).
[4] Anthropic. "Effective harnesses for long-running agents" (2025).
[5] Yao, Shunyu, et al. "React: Synergizing reasoning and acting in language models." arXiv:2210.03629 (2022).
[6] OpenAI. "Evaluation Best Practices" (2026).
[7] Zheng, Lianmin, et al. "Judging LLM-as-a-judge with MT-bench and chatbot arena." NeurIPS 36 (2023).
[8] Yao, Shunyu, et al. "τ-bench." arXiv:2406.12045 (2024).
[9] Barres, Victor, et al. "τ²-Bench." arXiv:2506.07982 (2025).
[10] Cuadron, Alejandro, et al. "SABER." arXiv:2512.07850 (2025).
[11] Barres, Victor et al. "τ³-Bench" (2026).
[12] Merrill, Mike A., et al. "Terminal-bench." arXiv:2601.11868 (2026).
[13] Anthropic. "How we built our multi-agent research system" (2025).
