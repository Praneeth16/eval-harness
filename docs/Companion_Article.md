# Journey of an Agent: From Demo to Production

**A practitioner's guide to building self-evolving eval harnesses**

Companion article for the AI Engineer Bangalore session, 30 May 2026.
Code, traces, and prebaked artifacts: [github.com/Praneeth16/eval-harness](https://github.com/Praneeth16/eval-harness).

---

## 0. Cold open: the moment a demo becomes a liability

Question 89 in our SOC 2 questionnaire: *"What is your access-revocation SLA for terminated employees?"* Our agent (a multi-step LangGraph pipeline retrieving from a 30-document policy corpus) answered: *"Per our policy ACC-007 and Vendor-Mgmt v2, we revoke access within 4 hours of HR notification."*

Policy `ACC-007` exists. The 4-hour SLA exists. *Vendor-Mgmt v2 does not exist.* It appears in one of the past response documents we seeded into the corpus as bait: a marketing-tinged email from a sales engineer two years ago that name-drops a framework the company never adopted. The model laundered a phrase from one document into a citation in another.

Question 102: *"Are you PCI-DSS compliant?"* The agent: *"Yes, we are PCI compliant via SAQ-D self-assessment, certified annually."* We are not PCI compliant. We never claimed to be. Buried in our past-responses corpus is a draft RFP for a retail prospect we never closed, where someone wrote "we are working toward PCI compliance" in a margin note. The agent collapsed *working toward* into *certified*.

Both pass a vibe check, cite specific identifiers, and would clear review unless someone had the source documents open in a second window. Both end a security review badly and, in a regulated context, end a deal.

This is the gap the article is about: an agent that demos well, in front of friendly inputs, with a charitable observer, and *fails in production in a way the demo never surfaced*. Everything that follows (tracing, scoring, judges, clustering, self-evolving prompts, Pareto selection) is in service of one question:

> **How do you know your agent works, on inputs you haven't seen yet, before a customer finds out for you?**

If you have already lived this moment, you can skip the next two sections. If you haven't yet, you will.

---

## 1. The vibe-check trap

Many teams start the same way: wire up an agent in a notebook, run five friendly questions, eyeball the answers, and treat that as evidence. The trap is not that this is wrong. It is the correct first move. The trap is that it scales worse than it looks like it scales.

Jules Damji at Databricks names the four structural reasons in his MLflow piece on structured eval ([mlflow.org, April 2026](https://mlflow.org/blog/structured-ai-eval/)): outputs are non-deterministic; quality is subjective; the people who can judge quality are not the people who can write code; and every invocation forces a cost-latency-quality tradeoff with no obvious knob. None of these are unique to LLMs in isolation. What is unique is having all four at once on every call.

The vibe check works at five questions because a human is in the loop on every output. It breaks at fifty because the human gets tired. It breaks at five hundred because the human can no longer hold the policy corpus in their head while reading each answer. By five thousand, it is performance: someone samples a few rows, sees one that looks reasonable, and calls the run reviewed.

The deeper failure is that *vibe checks teach the wrong thing*. After a week of vibe-checking, your team has built taste for *plausibility* (answers that sound like the answer) rather than taste for *correctness*. Plausibility and correctness diverge exactly where the money is. A confident wrong answer is worse than an honest "I don't know," and the vibe-check loop optimizes for confident answers.

The second-order question, the one most teams skip: *what is the smallest investment that moves us from "looks reasonable" to "here's exactly what happened"?* The honest answer in 2026 is **tracing first, deterministic scorers second, judges third**. Tracing because you cannot debug what you cannot see. Deterministic scorers because they catch the gross failures cheaply. Judges because at agent scale humans cannot review every output, and regex-only evaluation misses the semantic failures that matter most.

We will return to each.

---

## 2. The framing choice: benchmark-maxxer or floor-raiser?

Before any code, there is a fork that determines everything downstream, and most teams take it without noticing. Ben Hylak's *2026 Guide to Evaluating AI Agents* ([howtoeval.com, May 2026](https://www.howtoeval.com/)) draws the line cleanly: **benchmark-maxxer** versus **floor-raiser**.

A benchmark-maxxer asks: *what score on what test set would justify shipping?* A floor-raiser asks: *what is the worst thing this system can do, and can we prevent it?* The first frame optimizes for comparable scores; the second optimizes for reducing specific production risks. Both are legitimate. They are not the same activity, and the artifacts they produce are not interchangeable.

Hylak's litmus test is sharp enough to quote: *"If given the choice between 90% and 99% pass rates, benchmark-maxxers choose 99% immediately. Floor-raisers ask first: which 1% fails?"* This is the entire game in one sentence. The 1% that fails is where the business risk concentrates. The 1% that fails determines whether your agent gets pulled from production. A 99% pass rate where the 1% is uniform random noise is a different system than a 99% pass rate where the 1% is *every* question containing the word "pediatric" or *every* question filed on a Sunday.

Floor-raising is error analysis dressed as evaluation. It begins by reading traces, not by writing test cases. The methodology is detective work: *what was the last successful step? What was the first real failure? Did retrieval miss? Did the agent ignore context? Did tool calls fail? Did the final answer overstate known information?* You find a pattern, you fix the pattern, *then* you write an eval. The eval exists to prevent regression, not to prove that the system is good.

The mental model Hylak lands on: a floor-raising eval suite is *"a memory of bugs you refuse to reintroduce."* This is closer to how senior engineers think about regression tests than how researchers think about benchmarks. It is also why most hosted eval platforms feel uncanny: they are built for benchmark-maxxers, with leaderboards and aggregate scores, when the work that actually moves your agent forward is closer to incident review.

Our session, our harness, and this article are floor-raising tools. If you came looking for a benchmark, the literature in our references will serve you better. If you came looking for the discipline that prevents the cold-open scenario from happening in front of your customer, read on.

---

## 3. Outcomes versus outputs: the trajectory question

Cameron Wolfe's *Agent Evaluation: A Detailed Guide* ([cameronrwolfe.substack.com, May 2026](https://cameronrwolfe.substack.com/p/agent-evals)) draws the second indispensable distinction. An agent's **output** is the text it returned. An agent's **outcome** is the state of the world after the run. These are not the same thing, and the gap between them is where most agent failures hide.

Wolfe's example: *"An agent might declare 'The restaurant is booked!' without actually achieving the booking outcome."* Replace "restaurant booking" with "ticket created in your queue system," "PR merged," "refund processed," "compliance attestation filed." The pattern generalizes brutally. Agents assert completion because successful examples in their training data often end that way, and the model has no native signal that the side effect actually occurred.

The implication for evaluation is that **scoring the output is a category error** for any agent that touches the world. You have to score the outcome, which means you have to instrument the world, which means evaluation is no longer something you bolt onto a string return value. It is something you build into the system architecture.

This is also why **trajectory** is a first-class evaluation signal. Tejas Kumar's *Harnesses in AI: A Deep Dive* (AI Engineer, May 2026): *"an agent harness is everything around the model that gives it grounding in reality."* This sits next to Wolfe's framing. The path the agent took is diagnostic in a way the final answer is not. If the agent answered correctly but never called the retrieval tool, the correctness was a coincidence and will not generalize. If the agent called the right tools in the wrong order, the answer might pass today and fail next week when the corpus shifts. If the agent called a verification tool *after* writing its final answer, then the verification was theater.

Wolfe formalizes this into five tool-call metrics (*invocation, selection, structural, trajectory, outcome* accuracy), and the practical advice is that you want at least two of these grading every run. We pick *trajectory* and *outcome* as the pair our harness relies on. For Quill, the outcome is not a world-changing side effect like booking a restaurant; it is the *content of the response packet that will be sent to the customer's security reviewer*. We decompose it into two layers. The deterministic layer verifies: (a) every cited policy ID exists in the corpus, (b) every cited framework clause resolves to a real clause, and (c) no past-response phrase (`PAST:*` prefix) was laundered into a citation. The judge-graded layer verifies whether the cited clause semantically supports the answer's claim, and whether the answer overstates the clause (e.g. collapses "working toward PCI" into "PCI compliant"). The split matters: semantic overclaim cannot be checked with regex; citation membership cannot be checked with a judge alone. The trajectory check then ensures the deterministic verifiers ran *before* the answer was finalized, not after, not in parallel, not as an afterthought. We return to this in section 8, because it is the single hardest piece of our harness to get right honestly.

---

## 4. Eval-driven development is a loop, not a checklist

If you read one piece of canonical material on eval methodology in 2026, read the MLflow team's *Structuring AI Evaluation and Observability* ([mlflow.org, April 2026](https://mlflow.org/blog/structured-ai-eval/)). The framing they propose, three phases repeated indefinitely, is the cleanest articulation of the practitioner's workflow we have seen:

1. **Prototype with tracing.** Wire tracing on day zero, whether through MLflow autologging for supported clients or explicit `@mlflow.trace` decorators around your LangGraph nodes and provider calls (our stack is OpenRouter + Gemini + LangGraph, so we use manual spans rather than `mlflow.openai.autolog()`). Every LLM call, tool invocation, and retrieval result becomes structured data with latency, tokens, cost. You are not yet evaluating anything; you are buying yourself the option to evaluate later.
2. **SME feedback, judges, and evaluation datasets.** Domain experts label a subset. Their labels train your taste and bootstrap your LLM judges. The dataset grows by accretion; every production failure adds a row. The judges run continuously, not as a one-shot.
3. **Stakeholder sign-off and production monitoring.** The same scorers that gated your offline runs now run on live traffic. Offline and production metrics share definitions, so leadership and engineering are not arguing from different scoreboards. There is one set of metrics, not two.

What makes this a loop and not a checklist is that phase 3 produces the failures that get added back into phase 2's dataset. The system is designed to learn from its own production. Skip phase 1 and you cannot see the failures. Skip phase 2 and you cannot grade them. Skip phase 3 and your offline numbers diverge from your production reality within a quarter.

In our harness, the three phases map cleanly onto the modules: `core/tracing/` is phase 1 (MLflow span types AGENT, CHAIN, TOOL, RETRIEVER, LLM, PARSER attached around the LangGraph nodes that matter for replay and scoring), `core/scorers/` and `core/eval/runner.py` are phase 2 (four scorer layers, 50-question golden set, MLflow `genai.evaluate`-compatible output), and the API + UI + portability gate are phase 3 (the same scorers run against held-out frameworks and against alternative model providers before any prompt change ships).

The detail that matters most, and the one teams skip first: **the evaluation dataset is a living artifact, not a fixed test set**. Damji is explicit about this: *"perfect ground truth labels are unnecessary; iterative evaluation datasets combined with LLM judges provide sufficient signal."* Treating your golden set as fixed is a benchmark-maxxer move. Treating it as a queue of past incidents you refuse to repeat is a floor-raiser move.

It is the one piece of advice everyone gives and almost no one operationalizes, because it requires building the pipeline for converting production traces into golden set entries, and that pipeline is not glamorous to build. For our demo, `scripts/seed_cold_open.py` turns the Q89 and Q102 failures into permanent regression cases, sticky at the demo URL so they cannot quietly drift out of the suite.

---

## 5. CLEAR-S: scoring as a coordinate system

Aggregate accuracy is a lie agreed upon. The moment you collapse a multi-dimensional system into a single scalar, you lose the information that would tell you *how* to improve it. The pass rate went from 73% to 81%. Wonderful. But did latency get worse? Did cost go up? Did the agent start hallucinating in a new way the old scorer doesn't catch? You don't know.

Our harness adopts a 7-axis scoring scheme we call **CLEAR-S** (the acronym covers six axes; *cost* is the seventh, deliberately broken out from "latency" because cost regressions look identical to latency improvements in casual review):

| Axis | Scorer type | Owner | Example failure | Remediation |
|---|---|---|---|---|
| **C**orrectness | deterministic + judge | retrieval / drafter | cited ID does not exist in corpus | tighten verifier; retrain drafter prompt |
| **L**atency | deterministic | infra / model choice | p95 > 20s budget | shorter prompt, smaller model, batched verifier |
| **E**xecution | trajectory | graph topology | verifier fired *after* final draft | reorder DAG; add ordering assertion |
| **A**dherence | deterministic + judge | drafter prompt | answer omits required confidence statement | prompt patch; format check |
| **R**elevance | judge | drafter | answer addresses adjacent question | reranker tuning; judge calibration |
| **S**afety | deterministic + judge | guardrail layer | past-response phrase laundered into citation | prefix filter; injection corpus |
| **Cost** | deterministic | model choice + retrieval | $0.0008/q exceeds tier budget | cheaper model on baseline path; cache hot chunks |

The axes overlap on purpose. *Correctness*, *relevance*, *adherence*, and *safety* can all punish overclaim, and they do so for different reasons. Correctness because the claim is false. Relevance because the claim does not answer the question. Adherence because the format requires hedged language. Safety because the source was a marketing past-response. The overlap means a single failure mode shows up on multiple axes, which is the *point*. If your scorers reach unanimous agreement on every failure, you have one scorer playing seven roles, not seven scorers. We accept the redundancy; we just refuse to double-count in the aggregate by collapsing axes into a scalar.

Seven axes is not a magic number; it is *enough axes that you can no longer hide a regression in the average*. If correctness goes up because the agent is now refusing every borderline question, relevance drops. If cost goes down because you switched to a smaller model, correctness drops. The tradeoffs between axes are the product decisions: refuse more often, spend more tokens, accept higher latency, or ship a weaker answer.

This is also the structural argument for **Pareto selection** later in the article. With one axis, "better" is well-defined. With seven, you have a frontier, not a winner. The frontier is where the interesting choices are: *we accept 5% lower correctness to halve cost, because this agent runs on a budget-constrained customer tier*. A benchmark-maxxer cannot have that conversation because their leaderboard cannot represent it.

A subtler reason for multi-axis scoring is the one Shreya Shankar surfaces in her qualitative analysis piece ([sh-reya.com, May 2026](https://www.sh-reya.com/blog/ai-qual-analysis)): *"vague codes are easy to accept and impossible to act upon."* A scorer named `quality` is a vague code. A scorer named `correctness` is slightly better. A scorer named `cited_policy_exists_in_corpus` is actionable: it tells you exactly which file in `examples/quill/seed_corpus.py` to inspect when it fails. The narrower your axes, the more you can do with a failure.

If your eval reports a single number, you have a thermometer. If your eval reports seven numbers with clearly defined ownership, you have a diagnostic tool. The difference is operationally enormous.

---

## 6. Layered scorers: the Swiss Cheese strategy

No scorer is complete. We use layers because each one fails differently. Deterministic checks miss semantic errors. Judges miss structural errors. Trajectory checks miss content errors. Together they form a sieve dense enough to catch the cases that matter.

Our harness uses four scorer kinds. We describe them below in *runtime order* (which is also the order they appear in `core/eval/runner.py`); the file numbering on disk (`layer1_deterministic`, `layer2_semantic`, `layer3_trajectory`, `layer4_safety`) tracks the historical order they were written, not the execution order. We do not try to make the two match. Renaming files breaks too many things. If you read the code, do not let the filenames confuse you about execution order.

**Deterministic checks (run first).** Regex, format checks, citation prefix validation, latency budget, cost budget. Cheap, fast, and *unreliable as a judgment of correctness*. They tell you whether the output is *well-formed*, not whether it is *true*. Runs first because a malformed output never needs to reach the expensive scorers. The regex that detects bare policy citations (`POL-007`) had to learn the corpus prefix list dynamically (`_known_policy_prefixes()`), so that crypto strings and ISO standard numbers are not mistaken for policy IDs (the failure that cost us — see below).

**Trajectory checks (run second).** Did the agent call `policy_exists_check` before writing its citation? Did it call `framework_clause_resolves` for any framework reference? Were the verification calls *before* the final draft, not after? This is the layer that catches the agent who answers correctly for the wrong reason. The implementation walks the MLflow span tree, asserts ordering, and fails the run if `final_draft.start_time < verification_tool.end_time`. Runs second because the span data is already on disk from the trace; no extra LLM calls needed.

**LLM-judge scoring (run third).** Reviewer-accept score, relevance, adherence-to-style. A model is asked to play the role of a domain reviewer and score the output against the question. Runs third because it is the only layer that costs LLM tokens. Judges are expensive, slow, and have biases. They prefer longer answers. They prefer answers that match their own training distribution. They collapse subtle distinctions. They are also, for many subjective dimensions, the only scalable option. We calibrate ours against a small human-labeled set (about 30 examples) and accept that the calibration is approximate. The judge's job is to be roughly right at scale, not exactly right on every case.

**Post-answer safety scoring (run fourth).** Safety splits into two distinct concerns; only the *post-answer* half is part of the scorer pipeline. *Pre-answer guardrails* run at request-time inside the agent itself: injection detection on the question, refusal-vs-answer routing, prompt-leak detection. These are production checks, not eval scorers. They block before the agent does work. *Post-answer safety scoring* runs against the response after the judge: overclaim detection (the `PAST:` and `FW:` prefix filters that prevent past-response leakage), refusal correctness on the adversarial set, jailbreak success rate. Conflating the two is a common architectural mistake. Adversarial inputs need to be blocked early, not graded late.

The total per-question eval cost is dominated by the judge (roughly $0.0002 in our prebake at current Gemini pricing), which makes the aggregate run cheap enough to gate every PR.

The non-obvious detail: **a scorer with a bug is worse than no scorer at all**, because it produces false confidence. Our `bare_policy_match` regex flagged `AES-256` as a policy citation for two days before we caught it. The scorer was inflating the failure rate, the team distrusted the numbers, and the actual debugging only started when the *direction* of the bug flipped to undercounting. We were lucky. A real production team trusting its scorers would have shipped and been wrong for a quarter.

---

## 7. The LLM-judge problem

LLM-as-judge is the workhorse of modern eval, and it is the single most over-promised tool in the stack. The right mental model is a low-cost reviewer with systematic biases, not an objective grader. Treat it accordingly.

The biases are well-documented now. Zheng et al.'s MT-Bench paper ([NeurIPS 2023](https://arxiv.org/abs/2306.05685)) catalogues: **position bias** (judges prefer the first response in a pairwise comparison), **verbosity bias** (judges prefer longer responses), **self-enhancement bias** (judges prefer outputs that look like their own training distribution), **limited reasoning depth** (judges miss errors that require multi-step verification). Wolfe summarizes the calibration cost in one line: *"itemized rubrics with dozens of individually-assessed criteria improve reliability."*

The practical implication is that **a single 1-5 score from an LLM judge is almost meaningless**. What works in our harness, drawing on the MLflow `make_judge` API and the OpenAI cookbook's macro-eval rubrics, is to decompose the subjective judgment into many binary or low-cardinality questions:

- Does the answer cite at least one policy? (binary)
- Is every cited policy in the corpus? (binary, deterministic, doesn't need a judge)
- Does the answer address the actual question, not a related question? (binary, needs a judge)
- Would a security reviewer approve this for inclusion in the response packet? (4-point ordinal, needs a judge)
- Are there any overclaims in this answer? List them. (extract list, then score)

The second-order point: *judges agree with each other much more than they agree with humans*. This is a real risk. You can build an eval system where two LLM judges, scoring each other's domain, both report 95% pass rate, while the actual ground truth (when you finally hire a human to check) is 60%. The judge ensemble is converging on a shared model artifact, not on reality. The mitigation is to keep a small human-labeled "gold gold" set (fifty examples is a working minimum) and compute judge-human agreement on it every time you change a judge prompt or model. For ordinal labels (1-5 reviewer-accept scores), report Cohen's weighted kappa; for binary failure flags, report precision and recall against the human-labeled positives. Set a deploy-blocking threshold *before* you start tuning: we use weighted κ ≥ 0.6 as the floor for shipping a new judge prompt, and a drop of more than 0.1 from the previous prompt's κ as a regression. Below the floor, the new judge does not ship regardless of how its aggregate scores look. The floor is the contract; the aggregate is just a number.

Shankar's qualitative-analysis piece sharpens this: *"agents execute mechanical analysis components rapidly but lack taste, evaluative judgment about what matters."* Judges have the same problem at lower stakes. They will rate things as good that are technically defensible but missing the point. Our practical check is to manually review a random sample of passing judgments on a fixed cadence; fifty per quarter is a working minimum. If you cannot bring yourself to do this exercise, your judges are probably wrong in ways you don't know about.

---

## 8. Honest trajectories: propose, verify, then finalize

This is the section that took us the longest to get right and the one that almost every public agent demo gets wrong.

The naive RAG-plus-citations agent looks like this:

```python
def drafter(state):
    response = llm.generate(prompt_with_retrieval(state.question, state.chunks))
    return {"answer": response.text, "citations": response.citations}
```

The model is asked, in one call, to produce both the answer and the citations. The citations are whatever the model decided to attach. If the model hallucinates a policy ID that sounds plausible, the citation looks correct. The retrieval step ran *earlier*, the verifier step (if it exists) runs *later*, and the answer was already written before either happened.

We ran this for two weeks. It passed our deterministic scorers (citations are well-formed strings) and it passed our judge scorer (the answer was relevant). It failed in exactly the way the cold open describes: phantom citations that looked exactly like real ones, and our scorers could not tell, because all the evidence was in the *ordering* of the tool calls, not in the final string.

The fix is the **propose / verify / finalize** pattern, which is the same shape Teresa Torres describes in her opportunity-solution-tree piece ([producttalk.org, May 2026](https://www.producttalk.org/behind-the-scenes-ai-osts/)) and which Cameron Wolfe references as the *outcome-driven* style of evaluation. In our LangGraph DAG, the drafter node now has three phases:

1. **Propose.** The LLM generates a list of candidate citations (`{"candidates": [{"policy_id": "ACC-007", "claim": "..."}]}`). It does *not* yet write the answer text. This output is JSON, not prose.
2. **Verify.** A deterministic tool (`policy_exists_check` for policies, `framework_clause_resolves` for frameworks) runs on every candidate. The tool emits an MLflow `TOOL` span with `inputs` (the candidate) and `outputs` (the verified reference object, or `null` for misses). Phantom citations die here, deterministically.
3. **Finalize.** The LLM is called a second time with the question, the original chunks, and *the verified-refs list only*. The prompt explicitly states: *cite only from the verified list*. The unverified candidates are removed from the context, which makes it *unlikely* (not impossible) that the model references them; an over-confident model can still hallucinate an ID that is not in front of it. So a post-finalization deterministic check runs after this step: every citation in the final answer is matched against the verified-refs list, and any citation not in that list fails the run.

The trajectory scorer can now make three load-bearing claims, all verifiable from the MLflow span tree: *the verification tool fired before the final answer was written* (finalize-span `start_time` strictly greater than verify-span `end_time`), *every cited ID in the final answer is a member of the verified-refs list*, and *no citation appears in the final answer that was not in the verified candidate pool*. These three together are the honest version of "the agent verified citation membership before finalization." They do *not* check that the cited clause semantically supports the claim. That is a judge-graded property, not a deterministic one. Any of the three checks in isolation is theater; all three together still leave semantic correctness as a separate axis.

The numbers from our prebake tell the story. The baseline (single-call drafter) scored **0.10** on the `verified_cite_trajectory` axis across 20 SOC 2 questions (avg 1.8 citations/question, 36 citation opportunities). The propose/verify/finalize variant scored **1.00** on the same set, and **1.00** again on the held-out ISO 27001 framework (20 questions, never seen during tuning). State the claim precisely once and never inflate it past that: *the ordering-and-membership constraint — verifier fired before the finalize span, every cited ID present in the verified-refs list — transfers to the held-out framework; the semantic-correctness claim does not.* The reviewer-accept judge, which is the semantic check, drops from **0.78** on SOC 2 to **0.55** on ISO 27001. That gap is the entire reason §12 and §13 exist.

There is a generalization here worth pulling out. Torres' tree-diff problem is structurally identical: the model produces output that is locally plausible (a change set), a deterministic verifier checks it (does this change set produce the claimed tree?), and the loop continues until the verifier passes. She names it the deterministic-verifier-in-the-loop pattern. We call it propose/verify/finalize. They are the same pattern with different domain vocabularies. *Where you can write a deterministic verifier, you should, and you should hand it to the model as a tool.* This is the most reliable single move in production agent design we know about.

The corollary is that if you cannot write a deterministic verifier for your domain, you are doing harder work than you think. Most teams are doing harder work than they think, and discover this the first time they try to write the verifier.

---

## 9. Error analysis is the highest-ROI activity

Hamel Husain has been saying this for two years; Hylak quotes him again in 2026: *"Error analysis is the single most valuable activity in AI development and consistently the highest-ROI activity."* The claim sounds like advice and reads like cliché until you actually do it for a week.

What error analysis *is*, concretely: you take the last 200 failures, you read them, and you build a taxonomy. Not the failures' symptoms (the surface), their *causes* (the structure). You go through one by one, you tag each with a candidate cause, you cluster the tags, and you end up with five to ten clusters that account for 80% of failures. Each cluster is now a project. Each project has a clear definition of done. Prioritization becomes tractable: rank clusters by prevalence, severity, and fix cost.

The reason this is high-ROI is that it cuts the search space from "what could possibly be wrong with our agent" (infinite) to "five things, in this order, that account for most of what's wrong" (finite). It also produces named failure modes that the rest of the team can reason about: *"the agent overclaims when the past-response corpus contains marketing language"* is a sentence anyone can act on; *"correctness is 84%"* is a number that does not tell you what to fix.

At small scale (≤200 failures) you do this by hand. Beyond that, you need machine help, and this is where the OpenAI Cookbook's *Macro Evals for Agentic Systems* ([May 2026](https://developers.openai.com/cookbook/examples/partners/macro_evals_for_agentic_systems/macro_evals_for_agentic_systems)) becomes the right reference. Kwatra, Thieme, and Strauss describe the population-scale version: embed each trace as a document, reduce to 2D with UMAP, cluster with HDBSCAN, label clusters with class-aware TF-IDF, rank clusters by impact (prevalence × severity).

The step they describe and most teams skip is **slice lift**: for each (case_type, behavior_pattern) combination, compute the ratio of slice-pattern-share to overall-pattern-share. Lift > 1 means the failure mode is *concentrated* in this slice. This is the difference between "the agent has a 15% failure rate" (useless) and "the agent has a 60% failure rate on questions tagged `pricing_exception_compound`" (actionable, immediate next step is to inspect that slice).

In our harness, the same idea lives in `core/clusters/cluster.py`. We group failures by `(clear_axis, scorer_name)` and surface the dominant groups in the UI. At our demo scale (50-question golden set, single-digit groups) this is *grouping*, not clustering: there is no embedding, no UMAP, no HDBSCAN, just a sorted dict. The distinction matters because grouping-by-scorer can only surface failure modes the scorers already know to look for, while trace-embedding clustering can discover *novel* behavior patterns the scorers missed. At 50 questions, novel patterns are a luxury; there are not enough traces to cluster. Past about a thousand failures, the OpenAI cookbook's BERTopic + HDBSCAN approach becomes the right tool, and the grouping output transitions from "the dominant failure modes" to "the dominant *known* failure modes, with clustering as a separate signal for the unknown ones."

The deeper move is the AgentTrace-style **suspect scoring** the cookbook describes: from a focus event (the failure), walk backward through the span graph, score each upstream node by `0.4 × proximity + 0.3 × frequency + 0.2 × bridge + 0.1 × role`. The output is a ranked list of *suspects*: nodes in the agent's execution graph that are statistically associated with the failure. This is what production root-cause analysis for agents looks like, and there is no good way to do it without span-level tracing in place from day one. (Phase 1 of MLflow's three phases. The phase you cannot skip.)

---

## 10. Open-coding without losing taste

Shankar's qualitative-analysis piece is not, on its face, an evaluation paper. It is a study of agents trying to do the work qualitative researchers do: open-coding tweets, building taxonomies, writing memos. The findings are directly relevant to eval design and they generalize to LLM-judge eval in particular:

- **Agents paraphrase rather than analyze.** ρ = 0.81 correlation between tweet length and number of codes assigned in her exp1 condition (from Shankar's published correlation table). Longer tweets got more codes because the agent restated the content as codes, not because longer tweets contained more distinct ideas.
- **Agents fail to reuse codes.** 93.8% of codes were used exactly once in exp1, 100% in exp2-codes (Shankar's published rate table). The agent had the full codebook in context and *still invented new codes* for every new tweet instead of reusing existing ones. The taxonomy never consolidated.
- **Agents converge prematurely.** They rush toward neat themes before exploration is done. Qualitative analysis is supposed to maintain ambiguity; agents treat ambiguity as a bug to close.
- **Human-agent feedback loops deteriorate.** One feedback point either dominates everything that follows (overfitting) or vanishes after the next batch (thread loss). There is no in-between.

The reason this matters for eval specifically: *the LLM judges you are using to grade your agent are doing exactly this work*. They are open-coding outputs ("does this answer have these properties?"). They have all the failure modes Shankar documents. The judge will paraphrase the rubric, invent new sub-criteria mid-batch, and converge on a taxonomy that looks plausible but does not match the rubric you actually wrote.

The mitigation is structural, not prompt-engineering: keep judge prompts *short, binary, and itemized*. Every additional axis of judgment doubles the chance the judge drifts. Every additional rubric criterion is another place where the judge will paraphrase the criterion into something subtly different. If your judge prompt is more than a paragraph long, it is probably already doing something other than what you asked.

Shankar's deeper observation, and the one I keep coming back to: *"vague codes are easy to accept and impossible to act upon."* This is the entire problem with most production eval dashboards. A scorer called `quality` reports 87%. Nobody can argue with it because nobody knows what it means. Nobody can improve it because there is no concrete thing to improve. The unfalsifiability is the bug.

In our harness, every scorer name is a sentence that can be falsified. `cited_policy_exists_in_corpus` is either true or false for a given trace, and when it is false, you can point at the trace, name the cited ID, grep the corpus, and confirm the bug in 30 seconds. `quality_score: 4/5` cannot be falsified. We do not allow scorers of that shape in the harness, and the rule has paid for itself.

The second-order point, and this is where the section earns its keep, is that **the agent and the judge are the same kind of system**. They share failure modes. If you are debugging your agent and your eval system is built out of LLM judges, you are debugging *two coupled systems with correlated failure modes*. Shankar's findings are not just about qualitative researchers. They are about the structural limits of LLMs being asked to do open-ended judgment. Plan accordingly.

---

## 11. The deterministic-verifier-in-the-loop pattern

We named this pattern in section 8 and it deserves its own section because it is the single most reliable architectural move we know.

Torres tells the story end-to-end in *Behind the Scenes: Building AI-Generated Opportunity Solution Trees* ([producttalk.org, May 2026](https://www.producttalk.org/behind-the-scenes-ai-osts/)). The setup: she is building a service that updates an opportunity-solution tree based on new customer interviews. The model proposes a change set (splits, merges, adds, deletes); a deterministic function applies the change set to the input tree; the result is supposed to match the output tree the model claimed it produced. Around the 14th interview upload, the system started shipping change sets that didn't actually produce the claimed tree.

She tried to fix the model's mistakes in deterministic code. She couldn't. When the model deleted A and then merged A with B, there was no programmatic way to recover the intent. Eleven days of work, no fix.

The useful insight was structural: *validation should become a tool the model calls in a loop*. The model proposes a change set, the verifier runs, if it fails the verifier returns specific error messages, the model retries. In Torres' reported testing, the loop usually converged in one or two iterations. That does not remove the need for max-turn limits and failure handling. It only means the common case is cheap.

This is not new in the abstract; it is the ReAct loop ([Yao et al. 2022, arXiv:2210.03629](https://arxiv.org/abs/2210.03629)). But Torres' framing is the cleanest case study for *why* it works. The model is creative but inconsistent. The verifier is rigid but reliable. Hand the verifier to the model as a tool, and you get creativity bounded by correctness. The model gets to be wrong, and the loop's job is to make wrongness recoverable.

The pattern shows up everywhere once you have the name for it:

- **Code agents.** The compiler is the verifier. The test suite is the verifier. The type checker is the verifier. Cursor and Claude Code both work because they hand these verifiers to the model and let it iterate.
- **SQL agents.** The query planner is a verifier. The schema is a verifier. Some teams use a sandbox database that runs the query and returns row counts as the verifier.
- **Our Quill agent.** `policy_exists_check` is a verifier. `framework_clause_resolves` is a verifier. The MLflow span ordering check is a *meta-verifier*: it verifies that the verifiers ran in the right order.

The corollary, restated: **wherever you can write a verifier, write one and hand it to the model**. Wherever you cannot, you are doing harder work than you think, and the failure mode will be the cold-open scenario, only on a topic you care more about than security questionnaires.

The second-order question, which the literature has not answered well: *what do you do when the verifier itself is an LLM?* This is the recursive case: your evaluator is an agent, your agent calls a verifier-agent, the verifier-agent is sometimes wrong. We do not have a clean answer. The best we have is "calibrate against humans on a small set, and never let the verifier and the agent share weights." If you find a better answer, please write it up.

---

## 12. Self-evolving prompts: DSPy + GEPA, and why it is qualitatively different

So far the article has been about *evaluating* an agent. This section is about *improving* one, automatically, at the prompt level.

The framing question: if your scorers can rank candidate prompts, can you let the system *generate* candidate prompts and rank them too? The answer, in 2026, is yes. The reason it is interesting is that the resulting search is structurally different from human prompt-tuning.

DSPy ([dspy.ai](https://dspy.ai/)) and the GEPA prompt optimizer (surfaced through MLflow's `optimize_prompts` API; see Damji's MLflow piece for the integration walkthrough; the exact import path moves between MLflow versions, so prefer their current docs over any specific line we cite here) implement what is called **reflective mutation**. The idea: given a current prompt and a set of failed traces, ask an LLM to (a) diagnose what went wrong textually and (b) propose a prompt patch that would fix it. The patched prompt is evaluated against the scorer suite. If it improves on at least one axis without regressing others, it joins the candidate pool. Repeat for N iterations.

This is qualitatively different from "I, the human prompt engineer, will read failures and tweak the prompt" in three ways:

1. **The search space is broader than what a human will explore.** GEPA explores prompt variants humans may avoid because they look awkward, redundant, or off-key. Every variant still has to survive the scorer suite, so weirdness alone does not win, but weirdness is no longer disqualifying.
2. **The scorer suite is in the loop.** A human edit is a hypothesis; a GEPA mutation is a hypothesis *and an experiment*. Every candidate is graded against all 7 axes before it survives to the next round.
3. **The selection is multi-objective.** This is the section's payoff and the next section's subject. A single-objective optimizer would converge on whatever maximizes correctness even if it costs 3x more and runs 2x slower. GEPA, configured for multi-objective Pareto selection, keeps the *frontier*: every prompt that is non-dominated on some combination of axes.

The MLflow integration makes this concrete:

```python
from mlflow.genai.optimize.optimizers import GepaPromptOptimizer

result = mlflow.genai.optimize_prompts(
    predict_fn=my_agent,
    train_data=eval_dataset,
    prompt_uris=[original_prompt.uri],
    optimizer=GepaPromptOptimizer(reflection_model="openai:/gpt-4.1"),
    scorers=[Correctness(), Latency(), Cost(), Adherence()],
)
```

Our harness runs a genuine `dspy.GEPA` loop (`scripts/run_real_gepa.py`; bridge in `core/optimizer/gepa.py`). We seed the `classify` and `draft` predictors with the *deliberately-broken baseline* instructions, then let GEPA evolve them. The contract is the load-bearing detail (§7): the metric returns `dspy.Prediction(score, feedback)` where the **feedback string** — assembled from concrete CLEAR-S scorer details (the phantom IDs, the overclaims, the cited-but-unverified refs) — is the gradient the reflection LM reads. Task rollouts run on a cheap model (Gemini Flash); the reflection LM is a stronger model; the data split is train = SOC 2[:16], Pareto-tracking val = ISO 27001 (20), with a held-out SOC 2 tail GEPA never sees. Budget matters more than people expect: a few hundred metric calls is the floor where reflective mutation beats noise — our run used ~300.

The honest outcome (run `opt_2df16fdc95d4`, 304 metric calls, 8 discovered candidates): **GEPA's winner dominates the baseline.** Seeded from the broken baseline — which scores **0/20** on the ISO 27001 validation set, failing the floor outright — reflective mutation evolved the `classify` and `draft` instructions until the winner improved correctness **0.69 → 0.75** and relevance **0.92 → 1.00** on that held-out framework, with every other axis already at ceiling. On four SOC 2 questions GEPA never saw, the winner held correctness at 0.83 and everything else at 1.00. The winner Pareto-dominates the baseline, so the frontier collapses to a single non-dominated point. We report that honestly: the `/pareto/[id]` scatter plots all eight real candidates GEPA discovered — no synthetic interpolation, no seeded teaching curve — with the baseline shown dominated and the winner on the frontier. On Gemini Flash (task) + Gemini Pro (reflection) the whole run cost under a dollar; the methodology, not the price tag, is the point. The earlier version of this harness ran a hand-rolled five-question mutation loop where the baseline won — that was noise, and the difference is real GEPA at a real budget.

The second-order question, which the literature has not closed on: *does reflective mutation actually generalize, or does it overfit to the scorer suite?* The answer, empirically, is "it overfits aggressively, and the held-out set is the only thing that catches it." Our held-out ISO 27001 framework drops ~23 points from the tuned SOC 2 score (0.78 → 0.55 reviewer-accept), and this is the *honest* result. A GEPA loop without a held-out evaluator will produce candidates that look brilliant on the training golden set and ship broken in production. Plan for this. Build the held-out set first, run GEPA second.

---

## 13. The payoff: catching what naive eval misses — and the Pareto frontier behind it

This is the climax of the talk, and it is not the chart most people expect. Before the Pareto frontier comes a harder-won and simpler result: **the harness catches failures that a vibe check and a string/citation eval both wave through.** That is floor-raising (§2) made concrete. Three production failures, three eval layers:

| Failure | Vibe check | String / citation eval | This harness |
|---|---|---|---|
| Baseline cites a policy that doesn't exist (cold-open Q89/Q102) | ✓ reads fine | ✓ **1.00** — citation strings well-formed | ✗ **0.10** — verify-before-cite trajectory fails |
| Ship Claude — the *most correct* model (0.85) — to production | n/a | ✓ ships | ✗ **blocked** — execution 0.78, verifier called post-hoc |
| Tuned prompt evaluated on an unseen framework | ✓ reads fine | ✓ citations resolve | ▲ **overfit flagged** — reviewer-accept 0.78 → 0.55 |

Every number is a real prebaked score (`headline.json`, `portability.json`, the GEPA held-out set). The pattern is the point: the two cheap layers — the ones most teams actually ship with — are blind to all three, because the evidence lives in the *trajectory*, the *cross-model call ordering*, and the *held-out gap*, never in the final string. This is the demo's `/detection` view, and it is the moment the abstract discipline becomes concrete. It is also counterintuitive enough to stick: the model a string-eval would happily promote — Claude, the most correct of the four — is the one the harness blocks.

The Pareto frontier is the multi-objective *tool* behind the third row of that table: how you choose, among prompts that all pass the floor, which tradeoff to ship.

In a single-objective optimization, you have a winner. In a multi-objective optimization, you have a **Pareto frontier**: the set of points where no other point dominates *on every axis simultaneously*. A point `A` dominates `B` if `A` is at least as good as `B` on every axis and strictly better on at least one. The frontier is everyone who is not dominated.

Why this matters operationally: the frontier is where the *real design choices live*. "More correct but more expensive" is a frontier choice. "Faster but lower adherence" is a frontier choice. The leadership conversation (*"we are willing to spend 2x compute for 5% better correctness on the security-questionnaire tier, but on the marketing-FAQ tier we want the cheaper one"*) is a frontier conversation. You cannot have it with a scalar.

A single scalar collapses the frontier into a single point and loses the information that would let you make those choices. The `/pareto/[id]` visual is a 2D scatter of `correctness × cost` with the frontier highlighted: it gives the audience a *coordinate system to think in*, not a scoreboard to memorize.

The mechanics in our harness: GEPA produces a set of candidate prompts. For each candidate, we evaluate against the full golden set on all 7 CLEAR-S axes. Dominance is computed across all 7 axes (a candidate is dominated only if another candidate is at least as good on every axis and strictly better on at least one). The frontier *as a mathematical object* lives in 7-D. The UI projects it down to a 2D scatter of `correctness × cost` because two-axis charts are readable on a conference stage and seven-axis charts are not. The dominance computation that determined which candidates made the frontier used all seven. Deploy gating uses all seven too: a candidate that dominates on correctness × cost but regresses on safety still does not ship. The 2D view is a presentation projection, not the truth.

We highlight the *winner*, the point that maximizes a configurable weighted sum (we use `correctness + 0.25 × execution`). But the frontier itself is the artifact, not the winner. A different customer with a different cost tolerance picks a different point on the frontier.

The chart animates: 400ms ease-hero sweep traces the frontier from lowest-cost / lowest-correctness to highest-correctness / highest-cost, 200ms ring-pulse highlights the winner after the sweep completes, the baseline is labeled "◂ baseline" and the winner "▸ winner." The sweep is a sort along the frontier. Pareto frontiers do not have an intrinsic "added" order; the order we draw in is a presentation choice. We pick the cost-to-correctness sweep because it makes the tradeoff curve legible on stage: the eye follows from the cheap-but-weaker end to the expensive-but-stronger end, and the winner sits at the inflection where the marginal correctness gain stops paying for itself. If the chart were static, the audience would have to find that inflection unaided; the animation hands it to them in 400ms.

There is no single right answer here, and the harness's job is to not pretend there is.

The detection table is where the talk lands; the frontier is the coordinate system that makes the third row actionable. Two honesty rules govern the chart. First, the frontier is only as trustworthy as the eval budget behind it — a frontier drawn from five noisy questions is a Rorschach test, not evidence, which is why §12 reports our real GEPA run truthfully rather than inflating it. Second, the argument is never *our agent definitively beat the baseline*; it is *the harness tells you, honestly, whether it did, and on which axes*. Self-evolving prompts are not magic; they are a search over a frontier, and the frontier is where production decisions live — once the floor in the table above is already held.

---

## 14. Portability as a deployment gate

A prompt-and-tool contract is not portable until it has been tested across model/provider combinations under the same decoding and tool-calling settings. We did not expect this gate to matter as much as it does; it became one of the most important checks in our deployment flow.

The naive assumption: a good prompt is a good prompt. A prompt tuned to maximize correctness on `gemini-2.5-flash` should also work on `gemini-2.0-flash`, on `anthropic/claude-sonnet-4.6`, on `meta-llama/llama-3.3-70b-instruct`. The assumption is wrong, and the failure mode is asymmetric.

Our portability gate runs the same prompt against four models on the same held-out set and reports per-model CLEAR-S scores. The honest results from our prebaked run:

- `gemini-2.5-flash` — passes all 7 axes, ships
- `gemini-2.0-flash` — passes all 7 axes, ships
- `anthropic/claude-sonnet-4.6` (via OpenRouter, slug as of 2026-05-27): *regresses on the execution axis* (`policy_exists_called_before_cite` drops from 1.00 to 0.78). **Blocks deploy.**
- `meta-llama/llama-3.3-70b-instruct` (via OpenRouter): passes (ships)

The Claude regression is the diagnostic one. The model is more capable than Gemini on most generic benchmarks. On our specific propose/verify/finalize prompt, tuned for Gemini's instruction-following style, the failure pattern is consistent across traces: the model treats the verification tool as a *post-hoc check*, calling it after producing the candidate answer rather than before. In the span tree, this shows up as `finalize_span.start_time < verify_span.start_time` on 22% of runs. The policy-exists tool fires, but it fires too late to constrain the answer. A gate that scored only the final string would not see this; the citations look fine and the answer reads well. Only the ordering check catches it. The lesson is narrow but important: this is one prompt × one model × one provider × one decoding setting on one date. We are not making a general claim about Claude. We are making a specific claim about *this contract* against *this slug*. The portability gate is what makes the difference between a one-line generalization and a specific, dated diagnostic.

The general principle: **prompts overfit to model-specific tool-call quirks more than people expect, and the held-out check should always include a multi-model portability sweep**. If your prompt only works on one model family, you do not have a portable prompt; you have a model-specific configuration, and the cost of switching models later is much higher than you think.

The connection to Hylak's *collapse of harnesses* section is worth flagging. As models become more agentic and the harness collapses into the model, the portability question gets worse, not better. The agent's behavior depends on internal reasoning that is no longer visible. The held-out portability check becomes the only signal you have that the prompt-and-model combination still works.

---

## 15. Production: Stumbles → Issues → Signals → Experiments

Hylak's four-stage model for scaling production review by traffic volume is the cleanest articulation of post-launch eval discipline. We reproduce his vocabulary because his vocabulary is correct:

- **1–100 runs/day: Stumbles.** Read every trace. Look for confusion, frustration, near-misses, repeated prompts. The goal is *developing taste and taxonomy*, not measuring anything. At this scale you do not have enough data for statistical claims. You have enough data to learn.
- **100–1,000 runs/day: Issues.** When the same kind of Stumble recurs, it becomes an Issue. Issues are tracked, reproduced, debated, and explicitly decided on (fix / wontfix / postpone). The system at this stage is closer to an incident-response queue than to a benchmark.
- **1,000+ runs/day: Signals.** Track long-horizon trends: aesthetic complaints, refusal quality, ignored tool errors, context loss. A Signal is something you watch over weeks, not something you fix in a sprint. Signals often surface drift (the model changed, the user population changed, the corpus drifted), and the absence of Signal tracking is how teams get blindsided by quarter-over-quarter quality regressions.
- **5,000+ runs/day: Experiments.** Once you understand your Issues and Signals, ship fixes behind feature flags and run real A/B tests on real traffic. Hylak gives an illustrative example: a two-model production A/B with a 12-point task-completion gap and `p<0.001` driving a clean promote decision. The specific model names and percentages in his post are an example, not a benchmark, and any numbers you reproduce will depend on your traffic. This is the only stage where statistical claims actually carry weight.

The mistake every team makes: jumping to stage 4 before they have done stage 1. They build an A/B testing harness on top of an eval suite they have not validated, and the experiment results are noise. Not because A/B testing doesn't work, but because the dependent variable is wrong. The experiment is only legible when the metric is already trusted.

Hylak's blunter framing: *"Plan for 10–20% of agent development time devoted to evaluation and monitoring."* This is roughly the same fraction good software teams spend on testing and observability. The teams that try to spend 2% and ship faster pay the difference in production incidents, and the production incidents cost more than the eval time would have. This is not a moral claim. It is an arithmetic claim about defect costs.

Our session does not directly cover stages 3 and 4 because our talk is about a pre-production harness. But the architecture supports them: the same MLflow scorers that ran in our offline eval run in production with `mlflow.genai.evaluate(model=...)` against live traces; the same store collects production failures and feeds them into the golden set (SQLite in the demo for portability; in a real production deployment this boundary should be a durable event store, a warehouse table, or a managed trace backend); and the same DSPy + GEPA loop can be re-run on a quarterly cadence to refresh the prompt against the latest production failure distribution.

The right way to think about the architecture: *offline and production are the same pipeline running on different data sources*. Any production-critical scorer should have an offline equivalent, and any offline gate should state whether it is also monitored live. Some offline evals are intentionally expensive, adversarial, or synthetic and should *not* run on live traffic. The architecture should make that decision explicit, not accidental. Anything in production that is not also reproducible in offline is unreviewable.

---

## 16. The collapse of the harness

A note on placement: the detection contrast in §13 — what each eval layer catches — is the article's climax, with the Pareto frontier as the coordinate system behind it. What follows from here, Hylak's closing argument about the harness collapsing into the model, is a second beat, not a louder one. In the talk we will treat §16 as part of the open-questions tail rather than a new act. In the article it earns its own section because it changes what eval will look like in 18 months, and a reader who skips it will be surprised by the next generation of agent systems.

Today, agents are *agent SDKs calling models*. The harness is visible. Tool calls happen at the framework boundary; we can intercept them, log them, score them, replay them. The MLflow span tree exists because the framework code is the thing emitting spans.

Some agent products are moving toward thinner visible harnesses, where more tool policy lives inside the model/provider layer. Claude Code, Cursor CLI, the emerging Cursor Agent SDK: these are systems where the explicit tool loop is partially collapsing into the model itself. The model decides what tools to call, in what order, with what arguments, with less framework-level orchestration imposing structure. Audit-heavy production systems will keep the explicit orchestration for compliance reasons; ergonomics-heavy consumer products will not. The bifurcation matters for eval.

What changes for eval:

- **Outcome evaluation becomes primary.** When you cannot inspect the trajectory, you can only score the result. Wolfe's outcomes-vs-outputs distinction matters in a way it currently does not.
- **Golden cases get more important, not less.** A small, high-signal regression set is the only thing you can ground evaluation in when the path is opaque. Hylak's *5–10 golden cases for critical paths* advice ages well.
- **Self-diagnostics get more important.** The Raindrop pattern Hylak describes (the model has a hidden tool it can use to report its own failures) is one of the few signals you have when the framework is gone.
- **Portability gates get harder.** When you cannot see what the model is doing internally, you cannot tell why a different model behaves differently. The held-out evaluator becomes the only signal.

The harder question, which the field has not answered: *what do you do when the verifier is also a model?* The deterministic-verifier-in-the-loop pattern depends on the verifier being deterministic. If the verifier is itself an LLM (because the domain doesn't admit deterministic verification), the recursive case kicks in: your judge is uncertain about your agent's answer, and you have no ground truth for either. The current best answer is to keep humans calibrated against the judge and the judge calibrated against humans, on a small set, indefinitely. Whether this scales to billion-call production traffic is an open research question.

For our talk and our harness, we are deliberately living in the *current* world: the world where the framework is visible, where MLflow span trees exist, where deterministic verifiers can be written. The patterns we are demonstrating work in that world. They will need to be reframed in the post-collapse world, and the reframing is where the next two years of practitioner literature will live.

---

## 17. Second-order close: what we still don't know

The honest close is the set of questions this harness still does not answer:

**What we know.** Tracing first. Multi-axis scoring. Layered scorers. Honest trajectories via propose/verify/finalize. LLM judges with itemized rubrics and human calibration. Failure clustering and slice lift. Self-evolving prompts via reflective mutation. Pareto selection over weighted sums. Portability gates across model families. Production loops scaled by traffic volume.

**What we suspect but cannot prove.** That the propose/verify/finalize pattern generalizes to most agent domains where a deterministic verifier exists. That GEPA-style reflective mutation will become the default optimization technique in 2027, replacing hand-tuning. That CLEAR-S-style multi-axis scoring will be table stakes within a year, and the teams shipping single-scalar dashboards will look obviously wrong in retrospect.

**What we genuinely do not know.**

- *How do you evaluate an agent whose verifier is also an LLM?* The recursive case. We have heuristics; we do not have a theory.
- *How do you keep judges calibrated against humans at billion-call scale?* The MLflow + DSPy + GEPA stack assumes you can keep re-grounding. The grounding cost grows linearly with judge drift, which grows with model updates, which we do not control.
- *What does the eval suite look like when the harness collapses?* Hylak's open question. We have guesses. Nobody has built the system yet.
- *How do you eval an agent that is supposed to be creative?* All our scorers reward correctness. None of them reward the *interesting* answer. Shankar's piece is the closest treatment, and it is explicitly about why current agents fail at this.
- *How do you handle the political problem of eval, when the team that built the agent is the team grading the agent?* Every piece of published advice assumes good faith. Real production teams have incentives that point the other way. We do not have an institutional answer, and we suspect this is the question that matters most at scale.

---

## Appendix A: References

### Cited primary sources

In order of appearance.

1. Damji, J. *Structuring AI Evaluation and Observability with MLflow: From Development to Production*. MLflow Blog, 22 April 2026. [mlflow.org/blog/structured-ai-eval](https://mlflow.org/blog/structured-ai-eval/)
2. Hylak, B. *How to Eval AI Agents — The 2026 Guide*. May 2026. [howtoeval.com](https://www.howtoeval.com/)
3. Wolfe, C. *Agent Evaluation: A Detailed Guide*. Deep (Learning) Focus, 18 May 2026. [cameronrwolfe.substack.com/p/agent-evals](https://cameronrwolfe.substack.com/p/agent-evals)
4. Kwatra, S., Thieme, W., Strauss, B. *Macro Evals for Agentic Systems*. OpenAI Cookbook, 19 May 2026.
5. Shankar, S. *Exploring Agent-Assisted Qualitative Analysis*. sh-reya.com, 21 May 2026. [sh-reya.com/blog/ai-qual-analysis](https://www.sh-reya.com/blog/ai-qual-analysis)
6. Torres, T. *Behind the Scenes: Building AI-Generated Opportunity Solution Trees*. Product Talk, 13 May 2026. [producttalk.org/behind-the-scenes-ai-osts](https://www.producttalk.org/behind-the-scenes-ai-osts/)
7. Kumar, T. *Harnesses in AI: A Deep Dive*. AI Engineer, 17 May 2026.
8. Yao, S. et al. *ReAct: Synergizing Reasoning and Acting in Language Models*. arXiv:2210.03629, 2022.
9. Zheng, L. et al. *Judging LLM-as-a-judge with MT-Bench and Chatbot Arena*. NeurIPS 36, 2023.

### Further reading (related, not directly cited)

10. Khan, A. *Evals Are Broken. Use Them Anyway*. AI Dev 26 SF, DeepLearningAI, 22 May 2026.
11. Yao, S. et al. *τ-bench: A Benchmark for Tool-Agent-User Interaction*. arXiv:2406.12045, 2024.
12. Barres, V. et al. *τ²-Bench: Evaluating Conversational Agents in a Dual-Control Environment*. arXiv:2506.07982, 2025.
13. Merrill, M. et al. *Terminal-bench: Benchmarking Agents on Hard, Realistic Tasks in Command Line Interfaces*. arXiv:2601.11868, 2026.
14. Anthropic. *Demystifying Evals for AI Agents*. 2026.
15. Anthropic. *Effective Context Engineering for AI Agents*. 2025.
16. Anthropic. *Effective Harnesses for Long-Running Agents*. 2025.
17. OpenAI. *A Practical Guide to Building Agents*. 2025.
18. Husain, H. *Your AI Product Needs Evals*. 2024.

---

## Appendix B: The harness — what to read, where to look

The repository is organized so that each section of this article maps to a directory.

```
core/
  llm/           — gateway, OpenRouter + Gemini dual-provider routing (§4, §14)
  tracing/       — MLflow span types, manual span helpers (§4)
  scorers/       — layer1_deterministic, layer2_semantic (judge), layer3_trajectory, layer4_safety (§5, §6)
  eval/          — runner, EvalRunSummary, golden set loaders (§4)
  clusters/      — failure clustering by (axis, scorer) (§9)
  optimizer/     — DSPy + GEPA reflective mutation, Pareto ranking (§12, §13)
  store/         — SQLite + SQLAlchemy: EvalRun, Trace, Score, Cluster, OptRun (§4, §15)

examples/quill/  — the security-questionnaire agent
  graph.py       — LangGraph DAG, propose/verify/finalize drafter (§8)
  prompts/       — baseline.py (the bad agent), tuned.py (the propose/verify/finalize agent)
  retrieval.py   — FAISS + sentence-transformers (§3)
  tools.py       — policy_exists_check, framework_clause_resolves (§8, §11)
  seed_corpus.py — the 30-policy corpus, the bait past-responses, the injection set
  golden/        — soc2.jsonl (20), iso27001_holdout.jsonl (20), injection.jsonl (10)
  prebaked/      — headline.json, portability.json (§13, §14)

api/             — FastAPI routes: /runs /traces /clusters /detection /pareto /prompt-diff /portability
ui/              — Next.js 15 + Tailwind, DetectionContrast on /detection + ParetoChart on /pareto/[id] (§13)

docs/
  Session_Plan_Journey_of_an_Agent.md  — the talk outline
  Runbook.md                            — stage runbook, sticky demo URLs
  Companion_Article.md                  — this article
  refs/                                 — primary-source scrapes for citations
```

Demo URLs (read-only, prebaked):

- `/detection` — **the climax**: what each eval layer sees (vibe / string / this harness), every cell a real number (§13)
- `/runs/run_cold_open_demo` — Q89 + Q102 with `LiePanel`, and the same detection contrast embedded
- `/pareto/opt_2df16fdc95d4` — the real `dspy.GEPA` run (304 metric calls, 8 candidates; winner Pareto-dominates the baseline — correctness 0.69→0.75, relevance 0.92→1.00 on the ISO held-out — see §12)
- `/portability` — the four-model gate, with Claude blocking deploy

The demo path is fully offline-reproducible. No live LLM calls required.

---

*Praneeth Paikray, Bangalore, May 2026. Companion to "Journey of an Agent: From Demo to Production" at Agent Harness Bangalore, 30 May 2026.*
