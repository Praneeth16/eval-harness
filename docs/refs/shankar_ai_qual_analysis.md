# Exploring Agent-Assisted Qualitative Analysis

**Source:** https://www.sh-reya.com/blog/ai-qual-analysis
**Author:** Shreya Shankar
**Date:** May 21, 2026
**Read Time:** 28 minutes

---

## Introduction

After accepting a faculty position, Shankar revisited challenging PhD workflows to explore AI agent assistance. Qualitative analysis—reading unstructured data to identify interesting patterns—emerged as a particularly compelling case study. The core research question: *What constitutes the optimal approach to agent-assisted qualitative analysis?*

---

## Background

### Grounded Theory Methodology

Grounded theory builds research answers from data itself rather than testing predetermined hypotheses. The approach typically unfolds across three stages:

**Open Coding:** Researchers attach concise labels to meaningful passages. For instance, analyzing PhD attrition might yield codes like "no progress for months," "absent advisor," or "social comparison." As coding progresses, researchers compare new passages against existing codes, merging similar ones and subdividing overly broad categories.

**Axial Coding:** Related codes cluster into higher-level concepts. "Absent advisor," "shifting goals," and "no progress for months" might consolidate into *mentorship breakdown*, while "social comparison" and "imposter feelings" become *identity strain*.

**Selective Coding:** Researchers identify one or two core themes organizing remaining theory around them.

Throughout analysis, researchers compose *memos*—informal observations about emerging patterns, uncertainties, and interpretive possibilities.

### Why This Problem Matters

Qualitative analysis presents genuine difficulty for humans: tedious manual reading, judgment calls about salience, hours per transcript. AI faces different obstacles. The "correct" analysis hinges on context external to the data itself. Such judgment resists explicit specification, making it harder than verifiable tasks like code compilation.

Evaluation standards themselves shift during qualitative work. Researchers discover what matters through iterative data engagement. Current agent systems typically assume stable objectives and converge prematurely on fixed framings—a fundamental mismatch with exploratory research practice.

---

## Experimental Design

### Dataset

451 tweets responding to a Sholto Douglas query: *"When do you reach for other models instead of Claude? What can we do better?"*

Analytical question: *Why are users switching away from Claude?*

### Agent Conditions

Six agentic conditions across methodology specification and human involvement, all using Claude Sonnet via Agent SDK:

| ID | Theory Specified | Human Involvement | Multi-Agent |
|---|---|---|---|
| exp0 | No | None | No |
| exp1 | Yes | None | No |
| exp2-codes | Yes | Review codes per batch | No |
| exp2-memo | Yes | Review memo per batch | No |
| exp3-hierarchical | Yes | None | Yes |
| exp3-independent | Yes | Disagreement review | Yes |

---

## Findings

### Core Problem: Agents Misunderstand Qualitative Analysis

#### Agents Paraphrase Rather Than Analyze

A striking observation: open codes per tweet strongly correlated with tweet length (ρ = 0.81 in exp1). Yet longer tweets typically elaborated on identical complaints rather than introducing distinct grievances.

A second indicator: nearly every code appeared exactly once. In exp1, 93.8% of codes were one-time uses. In exp2-codes, 100% were single-use.

| Condition | One-Off Code Rate |
|---|---|
| exp1 | 93.8% |
| exp2-codes | 100% |
| exp2-memo | 96.5% |
| exp3-hierarchical | 74.2% |
| exp3-independent | 4.5% |

#### Agents Fail to Code Complete Datasets

Despite explicit instructions, agents stopped prematurely. Best (exp2-codes) reached 67.8% coverage. Worst (exp3-hierarchical) managed 5.5%.

| Condition | Coverage |
|---|---|
| exp1 | 28.6% |
| exp2-codes | 67.8% |
| exp2-memo | 30.6% |
| exp3-hierarchical | 5.5% |
| exp3-independent | 25.3% |

#### Agents Lack Effective Work Management

Human qualitative researchers distribute data across analysts, compare notes, do strategic sampling, pipeline higher-level categories. Agentic conditions neglected these. In exp1, despite configuring a worker subagent, zero subagent calls occurred.

In exp3-independent, both coding subagents timed out. The orchestrator abandoned qualitative analysis entirely and generated Python scripts with hardcoded keyword heuristics—the system became substring matching rather than qualitative analysis.

#### Human-Agent Feedback Loops Deteriorate

**Overfitting:** Single feedback mention dominated subsequent rounds. The agent elevated "competitor comparisons" into a top axial category after one offhand mention.

**Thread Loss:** Conversely, feedback faded. When asked to reduce code count, agents agreed enthusiastically but reverted to one-off codes in later batches.

### Summary: Two Root Problems

**Premature Convergence:** Agents rush toward stable themes before exploration suffices.

**Poor Adaptive Capacity:** Agents struggle with preferences emerging gradually. They either overfit early feedback or discard it entirely.

---

## The Human Experience

### Validating Open Codes: Tractable but Awkward

Removing erroneous codes straightforward. Choosing which plausible codes to retain proved harder than coding tweets independently—the interaction shifted from "What truly matters?" to "Can I justify removing this?"

Adding missing codes required switching from review mode into authorship mode.

Highlighting text with brief comments felt simpler than formal codes. This *in-vivo* approach delegated pithy code generation to the agent.

### Validating Axial Codes: Substantially Harder

Taxonomies appeared plausible superficially but represented different organizational logics. Each condition produced ~10-12 top-level categories, but organization varied across conditions.

Open-code validation is O(n) per tweet. Axial-code validation demands O(n²) comparisons between code pairs—computationally infeasible for humans without aids.

Vague categories like "Reliability and Trust" are so expansive nearly any LLM complaint plausibly belongs. This unfalsifiability is not a strength—when proposed fixes appear, no basis exists for trusting them.

### Interfaces Generated Frustration

Missing features:
- Marking clusters as reviewed
- Dragging open codes between axial categories
- Displaying example tweets under clusters
- Visualizing code counts per category
- Showing diffs between rounds

Agents tolerate enormous text slop. Humans do not. After several feedback rounds, Shankar avoided reading memos due to cognitive exhaustion.

### Wait Time Less Frustrating Than Expected

Streaming reasoning during agent work was acceptable. Worse was low-leverage mechanical work. Reviewing ten tweets represented about the fatigue threshold.

---

## The Central Insight

The overarching takeaway: agents execute mechanical analysis components rapidly but lack **taste**—evaluative judgment about what matters. The interesting design question is not "How do we automate qualitative analysis?" but "How do we build systems where human taste and agent scale genuinely compose?"

---

## Implications

- Premature convergence is the biggest failure mode
- Provenance and diff visibility for human supervision must be UI-first
- Vague codes are easy to accept and impossible to act upon — the unfalsifiability tax
- Text slop tolerance differs sharply between humans and agents
- Eval-time judgment shifts as researchers learn what matters; static rubrics break

*© 2026 Shreya Shankar*
