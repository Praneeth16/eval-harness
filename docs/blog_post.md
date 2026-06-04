# Journey of an Agent: From Demo to Production

**How a security-questionnaire agent that demoed perfectly learned to stop shipping confident lies.**

## Why does a great demo still ship lies?

Question 89 in our SOC 2 questionnaire: *"What is your access-revocation SLA for terminated employees?"* The agent answered: *"Per our policy ACC-007 and Vendor-Mgmt v2, we revoke access within 4 hours of HR notification."*

Policy `ACC-007` exists. The 4-hour SLA exists. *Vendor-Mgmt v2 does not.* It is a phrase laundered out of an old marketing email a sales engineer wrote two years ago, sitting in our corpus as bait. The model turned a phrase from one document into a citation in another.

Question 102: *"Are you PCI-DSS compliant?"* The agent: *"Yes, we are PCI compliant via SAQ-D, certified annually."* We are not. Buried in the corpus is a draft RFP where someone wrote "we are working toward PCI compliance." The agent collapsed *working toward* into *certified*.

Both answers pass a vibe check, cite specific identifiers, and would clear review unless someone had the source documents open in a second window. Both end a security review badly and, in a regulated deal, end the deal.

The agent here is **Quill**: a LangGraph security-questionnaire responder over a 30-policy corpus, traced with MLflow, with a set of prebaked offline evals you can run on a laptop. It demos beautifully on friendly inputs. Everything below is about the gap between that demo and what happens on the inputs you have not seen yet. One question runs underneath all of it:

> How do you know your agent works, on inputs you have not seen, before a customer finds out for you?

**Takeaways**

- **MLflow tracing and a trajectory scorer catch agent hallucinations that string and citation evals miss.** A fabricated SOC 2 citation passes a vibe check and a well-formed-string eval; the proof that it is fake lives in the tool-call ordering, not the final text.
- **CLEAR-S scores the agent on seven axes (correctness, latency, execution, adherence, relevance, safety, cost) and stacks deterministic, trajectory, and LLM-judge scorers, then gates on an unseen ISO 27001 set** so no regression hides in an average. On Databricks the same loop runs on managed MLflow and Unity Catalog, with lineage across traces, golden sets, and scores.
- **DSPy and GEPA reflectively rewrite prompts, but our run found no lift.** The real fix was architectural, a verify-before-cite scaffold, and an honest harness reports that null result instead of manufacturing a Pareto win.

Code, traces, and prebaked artifacts: [github.com/Praneeth16/eval-harness](https://github.com/Praneeth16/eval-harness).

---

## Why does the vibe check fail at scale?

Most teams start the same way: wire up the agent, run five friendly questions, eyeball the answers, ship. That is the correct first move. The trap is that it scales worse than it looks. The vibe check works at five questions because a human reads every output. It breaks at fifty when the human tires, at five hundred when nobody can hold the corpus in their head, and by five thousand it is theater: someone samples a few rows, sees one that reads fine, and calls the run reviewed.

Worse, vibe-checking trains the wrong taste. After a week you have built an eye for *plausibility*, answers that sound right, not *correctness*. And plausibility and correctness diverge exactly where the money is. A confident wrong answer is worse than an honest "I don't know," and the vibe loop rewards confidence.

Ben Hylak's 2026 guide to evaluating agents [1] draws the line that matters: the **benchmark-maxxer** asks *what score justifies shipping?*, the **floor-raiser** asks *what is the worst thing this can do, and can we stop it?* His litmus test: given a choice between 90% and 99% pass rates, benchmark-maxxers pick 99% on sight; floor-raisers ask *which 1% fails?* The 1% that fails is where the business risk concentrates. This harness is a floor-raising tool. Its job is to preserve failures as regression cases you refuse to reintroduce, not to produce a leaderboard.

## Why score the trajectory, not the output?

Cameron Wolfe's guide to agent evaluation [2] draws the distinction the opening turns on. An agent's **output** is the text it returned. Its **outcome** is the state of the world afterward. His example: an agent that declares *"the restaurant is booked!"* without achieving the booking. Swap in "ticket created," "refund processed," "compliance attestation filed." Agents assert completion because their training data ends that way, with no native signal that the side effect actually happened.

So scoring the output is a category error for any agent that touches the world. You have to score the outcome, which means you have to instrument the run, which means evaluation is not something you bolt onto a string. It is part of the architecture. And the path the agent took, its **trajectory**, is diagnostic in a way the final answer is not. If the agent answered correctly but never called retrieval, the correctness was luck and will not generalize. If it called a verification tool *after* writing its answer, the verification was theater. The evidence of the Q89 lie was never in the string, which was well-formed. It was in the ordering of the tool calls.

## How do we score an agent across seven axes?

Aggregate accuracy is a lie agreed upon. Collapse a multi-dimensional system into one scalar and you lose the information that tells you *how* to improve it. So the harness scores on a coordinate system, **CLEAR-S** (correctness, latency, execution, adherence, relevance, safety, with cost as a seventh axis broken out from latency), enough axes that you cannot hide a regression in the average. If correctness climbs because the agent now refuses every borderline question, relevance drops and you see it.

The scorers run in layers, cheapest first, because no single scorer is complete. Three of them carry the load:

- **Deterministic checks.** Is the output well-formed, within the latency and cost budget, and do the citations even look like real IDs? Cheap, fast, and blind to whether the answer is *true*. A well-formed citation to a policy that does not exist sails straight through.
- **Trajectory checks.** Did the agent call the verifier that confirms each cited ID actually resolves in the corpus, and call it *before* it wrote the citation? Answered by walking the MLflow span tree and comparing timestamps. This is the layer that catches the agent that cited a real-looking phantom because it never checked.
- **Judge checks.** Does the cited clause semantically support the claim, or does the answer overstate it ("working toward" into "certified")? This needs a model, and a model judge carries biases (position, verbosity, self-preference) [3], so we keep its questions binary and itemized and calibrate against a small human-labeled set.

None of this is Databricks-specific to build: MLflow, FAISS, and DSPy are all open source and the whole thing runs on a laptop. What Databricks changes is that the pieces stop being a stitch-job. The trace tree, the scorers (`mlflow.genai.evaluate` and Agent Evaluation), the golden sets, and the optimizer's scores live on one governed surface, with Unity Catalog lineage across all of them, the durable trace store as a Delta table, the quarterly optimizer refresh as a Job, and the cross-model sweep on Model Serving. The difference is not price. It is that a regulated team can audit, govern, and operate the loop instead of assembling it from parts.

## How do we stop the agent from citing phantoms?

The naive agent asks the model, in one call, to write the answer *and* its citations. If the model hallucinates a plausible policy ID, the citation looks correct, and both a vibe check and a string eval wave it through, because all the evidence is in the *ordering*, not the string. We ran exactly this for two weeks. It failed precisely the way the opening did.

The fix is **propose, verify, finalize**, three phases in the drafter:

1. **Propose.** The model emits candidate citations as JSON. It does not yet write prose.
2. **Verify.** A deterministic tool checks every candidate against the corpus. Phantom citations die here, and the check emits an MLflow span with a timestamp.
3. **Finalize.** The model writes the answer from the *verified list only*, and a post-check confirms every cited ID is a member of that list.

Now the trajectory scorer can prove, from the span tree, that the verifier fired before the answer was written and that every cited ID was verified first. The numbers: the single-call baseline scored **0.05** on the verify-before-cite axis across 20 SOC 2 questions; propose/verify/finalize scored **1.00**, and **1.00** again on an unseen ISO 27001 framework. The ordering guarantee transfers. What does *not* transfer is semantic correctness: the reviewer-accept judge drops from **0.85** on SOC 2 to **0.68** on ISO 27001. That gap is the honest result, and the only reason we can see it is that ISO 27001 was held out from this comparison.

This is where floor-raising becomes concrete. Three real failures, three eval layers:

| Failure | Vibe check | String / citation eval | This harness |
|---|---|---|---|
| Baseline cites a policy that doesn't exist (the opening Q89/Q102) | reads fine | **1.00** citation strings well-formed | **0.05** verify-before-cite trajectory fails |
| Tuned prompt on an unseen framework | reads fine | citations resolve | **flagged** reviewer-accept 0.85 to 0.68 |
| Same prompt, swapped model (gemini-2.5-flash to gemini-2.0-flash) | n/a | answers read fine | **flagged** execution 1.00 to 0.983 |

The two cheap layers, the ones most teams ship with, are blind to all three. The evidence lives in the trajectory, the unseen-framework judge gap, and the cross-model call ordering, never in the final string.

<!-- FIGURE 6 -->
![Figure 1. The detection contrast. Three real production failures across three eval layers; only the harness column catches all three, because the evidence lives outside the final string.](./figures/06-detection-contrast.png)

> **Image-gen prompt** (replace the placeholder above): "Publication-quality scientific matrix / heatmap-style table figure, clean white background, thin 1px charcoal grid, single muted teal accent (#10b981) reserved for the rightmost column where failures are caught, neutral gray for pass cells, a soft amber for 'flag' cells, no gradients or 3D or drop shadows, flat vector, sans-serif labels, monospace for scores. Three rows (failure scenarios): 'baseline cites a nonexistent policy', 'tuned prompt on an unseen framework', 'same prompt, swapped model'. Three columns: 'Vibe check', 'String / citation eval', 'This harness'. Cells show small status glyphs and scores: row1 = reads-fine / 1.00 / caught 0.05; row2 = reads-fine / citations resolve / flag 0.85 to 0.68; row3 = n-a / reads fine / flag 1.00 to 0.983. The harness column visibly highlighted teal. Caption styled like a journal figure. 16:9."

The pattern generalizes: wherever you can write a deterministic verifier, write one and hand it to the model as a tool [4]. The model is creative but inconsistent; the verifier is rigid but reliable; the loop gives you creativity bounded by correctness.

## Will your prompt survive GEPA and a model swap?

**GEPA did not improve this agent. That is the point.**

GEPA is a reflective prompt optimizer: it reads failing traces, writes a textual diagnosis, proposes a prompt patch, grades it against your scorers, keeps the non-dominated candidates, and repeats [5]. Run from this agent's prompt (run `opt_022418865fbf`, 301 metric calls, 5 candidates), it found no lift. The winner ties the seed at **0.78** correctness on the ISO 27001 validation set, with execution and safety holding at **1.00**.

Here is the lesson. GEPA optimizes prompt *text*. The win in this agent was *architectural*, the verify-before-cite scaffold, a change to the graph that no amount of wording mutation can invent. The likely reason GEPA found nothing: by the time it ran, the prompt was already sitting inside a correct graph, with little headroom left in the wording for a text optimizer to find. What the run actually proves is narrower, and it is enough: 301 metric calls, five candidates, none beat the seed. A harness that can run a real optimizer and say "nothing here" is the only kind you can trust when it says "something here." Tools that always render a sweeping frontier are the ones lying.

(One terminology note, because it is easy to get wrong: ISO 27001 was the *held-out framework* for the propose/verify/finalize comparison above, then *reused* as GEPA's Pareto-tracking validation set. The set GEPA never sees at all is a held-out SOC 2 tail.)

<!-- FIGURE 7 -->
![Figure 2. The Pareto view, honest. Candidate prompts on correctness by cost; the five candidates cluster around the seed and the non-dominated frontier collapses to a single point. No sweeping frontier, no GEPA win.](./figures/07-pareto-frontier.png)

> **Image-gen prompt** (replace the placeholder above): "Publication-quality scientific scatter plot, clean white background, thin 1px charcoal axes, single muted teal accent (#10b981) for the lone non-dominated point (the seed), neutral gray for the dominated candidate points, no gradients or 3D or drop shadows, flat vector, sans-serif small-caps axis titles. X axis: cost per question (lower is better, left). Y axis: correctness (higher is better, top). Five candidate points clustered tightly in the upper-left around a labeled 'seed' marker, conveying 'no candidate dominated the seed' - not a long sweeping frontier. No frontier line: the non-dominated set is a single point. Small monospace annotation: 'honest null result - search found no lift'. Caption styled like a journal figure. 16:9."

The model swap is the other half of the gate. The same prompt, moved from `gemini-2.5-flash` to `gemini-2.0-flash` on the unseen set, holds on every axis but one: execution slips from **1.00 to 0.983**. The axis averages the verify-before-cite ordering per citation across the set, so this is one question where the model fired the verifier *after* the answer for one of its citations, not a wholesale collapse. Not a worse model, a minor version bump, and the ordering quietly breaks on a single citation. A string eval would never see it; the citations look fine. Only the ordering check catches it. The lesson is narrow and load-bearing: a prompt that works on one model is a model-specific configuration until a portability sweep proves otherwise.

## What does CI for agent behavior look like?

Trace before you eval, because you cannot grade logic you cannot see. Stack eval layers, deterministic for constraints, trajectory for logic, judge for tone. Optimize the tail, not the mean, because the p95 that fails is what ships. We built CI for code; agents need CI for behavior, and this harness is that CI: trace, score, cluster the failures, attempt to optimize, gate on an unseen set, ship, and feed every production failure back to the front of the loop.

Every piece of it is open source and runs on a laptop. On Databricks it stops being a stitch-job: tracing, eval, governance, the optimizer loop, and the model gateway become one surface with lineage across all of it, which is the difference between a demo harness and one a regulated team can actually run and audit.

The full deep dive (every scorer, the complete CLEAR-S taxonomy, the failure-clustering and production-monitoring chapters, all the numbers) lives in the repository: [github.com/Praneeth16/eval-harness/blob/main/docs/Companion_Article.md](https://github.com/Praneeth16/eval-harness/blob/main/docs/Companion_Article.md).

---

## References

1. Hylak, B. *How to Eval AI Agents, The 2026 Guide*. May 2026. [howtoeval.com](https://www.howtoeval.com/)
2. Wolfe, C. *Agent Evaluation: A Detailed Guide*. Deep (Learning) Focus, May 2026. [cameronrwolfe.substack.com/p/agent-evals](https://cameronrwolfe.substack.com/p/agent-evals)
3. Zheng, L. et al. *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena*. NeurIPS 36, 2023. [arxiv.org/abs/2306.05685](https://arxiv.org/abs/2306.05685)
4. Torres, T. *Behind the Scenes: Building AI-Generated Opportunity Solution Trees*. Product Talk, May 2026. [producttalk.org/behind-the-scenes-ai-osts](https://www.producttalk.org/behind-the-scenes-ai-osts/)
5. DSPy and the GEPA reflective prompt optimizer. [dspy.ai](https://dspy.ai/)
6. Damji, J. *Structuring AI Evaluation and Observability with MLflow*. MLflow Blog, April 2026. [mlflow.org/blog/structured-ai-eval](https://mlflow.org/blog/structured-ai-eval/)

---

*Praneeth Paikray, Bangalore, 2026.*

> **Note on figures.** Figures 1 and 2 are placeholders. Each carries an image-gen prompt in the blockquote beneath it; generate the figure, drop it into `./figures/` under the referenced filename, and delete the prompt blockquote. The two prompts share the deep dive's house style (white background, thin charcoal rules, single muted-teal accent, flat vector) so the set reads as one figure family.
