# Journey of an Agent: From Demo to Production

**The agent passed every demo. It was also confidently making things up.**

**Takeaways**

- **A correct-looking answer is not proof the agent worked.** On a real run over the NIST SP 800-53 control catalog, the broken agent's citations all resolved and read well to an LLM judge, yet it verified none of them. Only an MLflow trace-tree scorer caught that the process was reckless.
- **Score behavior, not wording.** CLEAR-S grades the agent across seven axes (correctness, latency, execution, adherence, relevance, safety, and cost) in cheap-to-expensive layers: deterministic checks, then trajectory checks over the trace, then an LLM judge, so a regression cannot hide in the average.
- **Self-improvement is not magic.** DSPy and GEPA rewrote the prompts and found no lift; the real win was architectural, forcing the agent to verify evidence before citing it. The whole loop runs on a laptop, or end to end on Databricks with Unity Catalog, Mosaic AI Vector Search, Foundation Model APIs, and managed MLflow.

## Why does a great demo still ship lies?

Question 89 in our SOC 2 questionnaire: *"What is your access-revocation SLA for terminated employees?"* The agent answered: *"Per our policy ACC-007 and Vendor-Mgmt v2, we revoke access within 4 hours of HR notification."*

Policy `ACC-007` exists. The 4-hour SLA exists. *Vendor-Mgmt v2 does not.* It is a phrase laundered out of an old marketing email a sales engineer wrote two years ago, sitting in our corpus as bait. The model turned a phrase from one document into a citation in another.

Question 102: *"Are you PCI-DSS compliant?"* The agent: *"Yes, we are PCI compliant via SAQ-D, certified annually."* We are not. Buried in the corpus is a draft RFP where someone wrote "we are working toward PCI compliance." The agent collapsed *working toward* into *certified*.

Both answers pass a vibe check, cite specific identifiers, and would clear review unless someone had the source documents open in a second window. Both end a security review badly and, in a regulated deal, end the deal.

The agent here is **Quill**: a LangGraph security-questionnaire responder over a policy corpus, traced with MLflow. It demos beautifully on friendly inputs. Everything below is about the gap between that demo and what happens on the inputs you have not seen yet. One question runs underneath all of it:

> How do you know your agent works, on inputs you have not seen, before a customer finds out for you?

To answer that honestly, we did two things. We built the harness so it runs on a laptop with open-source parts, and we then ran it end to end on Databricks against a real, public control catalog, **NIST SP 800-53 Rev5**, so the numbers below are measured on a real standard, not a toy. Every figure in this article comes from that run, and where it matters, the managed Databricks service doing the work (Mosaic AI Vector Search, Unity Catalog, managed MLflow) is named as it comes up.

---

## Why does the vibe check fail at scale?

Most teams start the same way: wire up the agent, run five friendly questions, eyeball the answers, ship. That is the correct first move. The trap is that it scales worse than it looks. The vibe check works at five questions because a human reads every output. It breaks at fifty when the human tires, at five hundred when nobody can hold the corpus in their head, and by five thousand it is theater: someone samples a few rows, sees one that reads fine, and calls the run reviewed.

Worse, vibe-checking trains the wrong taste. After a week you have built an eye for *plausibility*, answers that sound right, not *correctness*. And plausibility and correctness diverge exactly where the money is. A confident wrong answer is worse than an honest "I don't know," and the vibe loop rewards confidence. The NIST run makes this literal: the agent that never checked its citations read *better* to a quick reviewer than the one that did.

Ben Hylak's 2026 guide to evaluating agents [\[1\]](#references) draws the line that matters: the **benchmark-maxxer** asks *what score justifies shipping?*, the **floor-raiser** asks *what is the worst thing this can do, and can we stop it?* His litmus test: given a choice between 90% and 99% pass rates, benchmark-maxxers pick 99% on sight; floor-raisers ask *which 1% fails?* The 1% that fails is where the business risk concentrates. This harness is a floor-raising tool. Its job is to preserve failures as regression cases you refuse to reintroduce, not to produce a leaderboard.

## Why score the trajectory, not the output?

Cameron Wolfe's guide to agent evaluation [\[2\]](#references) draws the distinction the opening turns on. An agent's **output** is the text it returned. Its **outcome** is the state of the world afterward. His example: an agent that declares *"the restaurant is booked!"* without achieving the booking. Swap in "ticket created," "refund processed," "compliance attestation filed." Agents assert completion because their training data ends that way, with no native signal that the side effect actually happened.

So scoring the output is a category error for any agent that touches the world. You have to score the outcome, which means you have to instrument the run, which means evaluation is not something you bolt onto a string. It is part of the architecture. And the path the agent took, its **trajectory**, is diagnostic in a way the final answer is not. If the agent answered correctly but never called retrieval, the correctness was luck and will not generalize. If it called a verification tool *after* writing its answer, the verification was theater. The evidence of the Q89 lie was never in the string, which was well-formed. It was in the ordering of the tool calls.

<!-- FIGURE 1 (rendered: docs/figures/make_figures.py) -->
![Figure 1. One question, two trajectories. The same vendor-risk question produces two traces. The baseline drafts and cites with no verify span, so the trajectory scorer reads 0.00. The fix proposes, verifies with a timestamped tool call, then finalizes, so the verifier provably precedes the citation and the trajectory scorer reads 0.97. The final answers look alike; the traces do not.](./figures/fig1_two_traces.png)

## How do we score an agent across seven axes?

Aggregate accuracy is a lie agreed upon. Collapse a multi-dimensional system into one scalar and you lose the information that tells you *how* to improve it. So the harness scores on a coordinate system, **CLEAR-S** (correctness, latency, execution, adherence, relevance, safety, with cost as a seventh axis broken out from latency), enough axes that you cannot hide a regression in the average. If correctness climbs because the agent now refuses every borderline question, relevance drops and you see it.

The scorers run in layers, cheapest first, because no single scorer is complete. Three of them carry the load:

- **Deterministic checks.** Is the output well-formed, within the latency and cost budget, and does each cited ID actually resolve in the corpus? Cheap, fast, and blind to whether the answer is *true*. On the NIST run this layer gave both the broken and the fixed agent a perfect 1.00, because every control they cited really exists in NIST 800-53. The citations were real. That is exactly why this layer cannot be the whole story.
- **Trajectory checks.** Did the agent call the verifier that confirms each cited ID before it wrote the citation? Answered by walking the MLflow span tree and comparing timestamps. This is the layer that separates an agent that *knew* its citation was good from one that *guessed* and got lucky.
- **Judge checks.** Does the cited control semantically support the claim, or does the answer overstate it ("working toward" into "certified")? This needs a model, and a model judge carries biases (position, verbosity, self-preference) [\[3\]](#references), so we keep its questions binary and itemized and calibrate against a small human-labeled set.

<!-- FIGURE 2 (rendered: docs/figures/make_figures.py) -->
![Figure 2. CLEAR-S across the six axes scored on the NIST run, baseline against the propose/verify/finalize fix. The two agents look comparable on most axes, but the baseline collapses on execution, the verify-before-cite axis, from 0.93 down to 0.50. Average the axes and that regression disappears; keep them separate and it is the first thing you see.](./figures/fig2_clears_radar.png)

We ran all of this on Databricks. The corpus and golden sets live as Unity Catalog Delta tables. Retrieval is Mosaic AI Vector Search with managed `databricks-gte-large-en` embeddings, so the same governance that decides who can read a control decides what the agent is allowed to retrieve. The agent calls Foundation Model API endpoints (`databricks-gemini-2-5-flash` for drafting, a second endpoint for the judge). Every trace, score, and golden set sits on managed MLflow, with Unity Catalog lineage tying each score back to the exact trace and corpus version that produced it, and the whole notebook runs as a Job. None of the pieces are Databricks-only to build: MLflow, FAISS, and DSPy are open source and the laptop version uses them directly. What Databricks changes is that the pieces stop being a stitch-job and become one governed loop a regulated team can scale, audit, and operate without having to assemble and re-secure it from individual parts.

## How do we stop the agent from citing phantoms?

The naive agent asks the model, in one call, to write the answer *and* its citations. If the model invents a plausible ID, the citation looks correct, and both a vibe check and a string eval wave it through, because all the evidence is in the *ordering*, not the string. We ran exactly this for two weeks. It failed precisely the way the opening did.

The fix is **propose, verify, finalize**, three phases in the drafter:

1. **Propose.** The model emits candidate citations as JSON. It does not yet write prose.
2. **Verify.** A deterministic tool checks every candidate against the corpus. Unverifiable citations die here, and the check emits an MLflow span with a timestamp.
3. **Finalize.** The model writes the answer from the *verified list only*, and a post-check confirms every cited ID is a member of that list.

Now the trajectory scorer can prove, from the span tree, that the verifier fired before the answer was written. Here are the measured numbers on the NIST run, 20 questions, scored 0 to 1:

| CLEAR-S signal | Baseline (single call) | Fixed (propose/verify/finalize) |
|---|---|---|
| Verify-before-cite (trajectory) | **0.00** | **0.97** |
| Citation resolves (deterministic) | 1.00 | 1.00 |
| Reviewer-accept (judge) | 0.58 | 0.43 |
| Execution axis | 0.50 | 0.93 |
| Safety axis | 1.00 | 1.00 |

Read the first three rows together, because they are the whole argument. The broken agent cited real controls, so the deterministic layer handed it a clean 1.00, and it read perfectly well to a quick reviewer, so the judge gave it 0.58. Yet it ran the verification step on none of its citations, and the trajectory axis says so at 0.00. It was right by luck, with a reckless process underneath. The fixed agent verifies every citation first, 0.97 here, every question but one, and because it now refuses to overstate what a control actually says, it reads slightly worse to the same naive judge at 0.43. Score either agent on its output and you ship the dangerous one. Only the trajectory axis tells you which of the two did the work.

There is a second lesson hiding in the judge row, and it is about your data, not your agent. Both judge scores are low (0.4 to 0.6) because a generic government catalog like NIST 800-53 does not contain Acme's specific evidence: the exact encryption, the 90-day key rotation, the named on-call process. The gold answers do. So no answer fully matches, and the judge marks everyone down. That is a real finding the harness surfaces instead of hiding: *a retrieval corpus has to actually contain your evidence,* and when it does not, the judge axis is the one that tells you.

<!-- FIGURE 3 -->
![Figure 3. The scorers run cheapest first, and each layer is blind to a different failure. An unverified citation passes the deterministic layer cleanly, because the control it names is real, and dies at the trajectory layer, which sees the verifier never ran. The expensive judge and safety layers never have to be spent on it.](./figures/03-scorer-funnel.png)

> **Image-gen prompt** (replace the placeholder above): "Publication-quality flat vector pipeline diagram, clean white background, thin 1px charcoal rules, single muted teal accent (#10b981) for the layer that catches the failure, neutral gray for passing layers, soft amber for the misleading 'looks fine' signal, no gradients or 3D or drop shadows. All text set in 'Charter' (the Medium article body typeface); identifiers in a monospace face. A four-stage vertical pipeline, cheapest at top: stage 1 'Deterministic checks (milliseconds)', stage 2 'Trajectory checks (the trace)', stage 3 'LLM judge', stage 4 'Safety'. A token labeled in monospace 'cites SC-7, never verified' enters at the top, passes stage 1 with a gray check and the amber note 'well-formed, control resolves', and is stopped at stage 2, drawn in teal with the note 'verifier never ran first', shown not reaching stages 3 and 4 (greyed out). Small monospace caption: 'the unverified citation looks perfect to the cheapest layer; only the trace catches it'. Caption styled like a journal figure. 16:9."

The pattern generalizes: wherever you can write a deterministic verifier, write one and hand it to the model as a tool [\[4\]](#references). The model is creative but inconsistent; the verifier is rigid but reliable; the loop gives you creativity bounded by correctness.

## Does the fix survive an unseen framework?

The verify-before-cite guarantee is structural, so it should hold on a framework the agent never trained on. We trained and measured on SOC 2 questions, then ran the same fixed agent on a held-out ISO 27001 set, re-cited to the same NIST controls.

| CLEAR-S signal | SOC 2 (in-domain) | ISO 27001 (held out) |
|---|---|---|
| Verify-before-cite | 0.97 | **1.00** |
| Reviewer-accept (judge) | 0.43 | 0.38 |

The process transfers cleanly. On a framework it never trained on, the agent verifies before citing just as reliably, a touch better even. What does not transfer for free is semantic quality. The judge slips from 0.43 to 0.38, because the scaffold removes unverified citations but does not teach the agent a framework it has never seen. You can only see that gap because ISO 27001 was held out from this comparison. A structural fix buys you a reliable process everywhere. It does not buy you domain knowledge you never gave the agent.

## Will your prompt survive GEPA and a model swap?

**GEPA did not improve this agent. That is the point.**

GEPA is a reflective prompt optimizer: it reads failing traces, writes a textual diagnosis, proposes a prompt patch, grades it against your scorers, keeps the non-dominated candidates, and repeats [\[5\]](#references). Run from this agent's prompt on the NIST validation set, across 41 metric calls, it produced no candidate that beat the seed. The winner *is* the seed.

Here is the lesson. GEPA optimizes prompt *text*. The win in this agent was *architectural*, the verify-before-cite scaffold, a change to the graph that no amount of wording mutation can invent. The likely reason GEPA found nothing: by the time it ran, the prompt was already sitting inside a correct graph, with little headroom left in the wording for a text optimizer to find. We ran a real optimizer, gave it a real budget, and it reported back that there was nothing left to win by editing words. A harness that can say "nothing here" is the only kind you can trust when it says "something here." Tools that always render a sweeping frontier are the ones lying.

One terminology note, because it is easy to get wrong: ISO 27001 was the *held-out framework* for the transfer comparison above, then *reused* as GEPA's validation set. The set GEPA never sees at all is a held-out SOC 2 tail, which is what we check the winner against at the end.

The model swap is the other half of the gate. A prompt that works on one model is a model-specific configuration until a portability sweep proves otherwise. We took the fixed agent and swapped the drafting model from `databricks-gemini-2-5-flash` to `databricks-claude-sonnet-4-6` on the same questions.

| CLEAR-S signal | gemini-2-5-flash | claude-sonnet-4-6 |
|---|---|---|
| Verify-before-cite | 0.97 | **1.00** |
| Reviewer-accept (judge) | 0.43 | 0.53 |

The sweep confirmed the agent ports cleanly to a different model family. Verify-before-cite held, and the judge even rose. The detail worth pausing on is `gemini-2-5-flash` itself, which scored 0.97 rather than 1.00 because on one of the twenty questions it fired the verifier after writing a citation, not before. A string eval sees none of that, since the citation looks fine. Only the per-citation trajectory check surfaces a single late verification, on one model, on one question. That is the whole reason to run the sweep. Not because the swap always breaks, but because you cannot know whether it did until a process-aware eval tells you.

## What does CI for agent behavior look like?

Trace before you eval, because you cannot grade logic you cannot see. Stack eval layers, deterministic for constraints, trajectory for logic, judge for tone. Optimize the tail, not the mean, because the p95 that fails is what ships. We built CI for code; agents need CI for behavior, and this harness is that CI: trace, score, cluster the failures, attempt to optimize, gate on an unseen set, ship, and feed every production failure back to the front of the loop.

<!-- FIGURE 4 -->
![Figure 4. The loop as one governed surface on Databricks. Each stage maps to a managed service, and the arrow back from monitoring is the point: a production failure re-enters as the next regression case instead of disappearing into a log.](./figures/04-databricks-loop.png)

> **Image-gen prompt** (replace the placeholder above): "Publication-quality flat vector architecture diagram, clean white background, thin 1px charcoal rules, single muted teal accent (#10b981) for the feedback arrow, neutral gray for nodes, no gradients or 3D or drop shadows. All text set in 'Charter' (the Medium article body typeface); service names in a monospace face. A closed clockwise loop of seven nodes: 'trace' to 'score' to 'cluster failures' to 'optimize' to 'gate on an unseen set' to 'ship' to 'monitor', then a teal arrow from 'monitor' back to 'trace'. Beneath each node, a small monospace label naming the managed Databricks service doing the work: trace = managed MLflow tracing; score = mlflow.genai.evaluate over CLEAR-S; the corpus and golden sets = Unity Catalog Delta plus Mosaic AI Vector Search; optimize = DSPy and GEPA on a Job; ship = Model Serving; monitor = inference tables. Label the teal feedback arrow 'production failures become tomorrow's regression cases'. Caption styled like a journal figure. 16:9."

Every piece of it is open source and runs on a laptop. On Databricks it stops being a stitch-job: tracing, eval, governance, the optimizer loop, and the model gateway become one surface with lineage across all of it, which is the difference between a demo harness and one a regulated team can actually run and audit. The full Databricks-native run in this article, data load to retrieval to agent to CLEAR-S to GEPA, is one notebook in the repository.

The full deep dive (every scorer, the complete CLEAR-S taxonomy, the failure-clustering and production-monitoring chapters, all the numbers) lives in the repository: [github.com/Praneeth16/eval-harness](https://github.com/Praneeth16/eval-harness).

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

> **Note on figures.** Figures 1 and 2 are already rendered into `./figures/` from the real run numbers by `docs/figures/make_figures.py`; re-run that script to regenerate them. Figures 3 and 4 are placeholders: each carries an image-gen prompt in the blockquote beneath it, so generate the figure, drop it into `./figures/` under the referenced filename, and delete the prompt blockquote. All four share one house style (white background, thin charcoal rules, single muted-teal accent reserved for the signal that matters, flat vector, and all text set in Charter, the Medium article body typeface) so the set reads as one figure family.
