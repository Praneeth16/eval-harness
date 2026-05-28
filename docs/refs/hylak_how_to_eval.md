# How to Eval AI Agents — The 2026 Guide

**Source:** https://www.howtoeval.com/
**Author:** Ben Hylak
**Published:** May 2026

---

## Foreword

A year ago, agents were barely present. Now they operate across banking, engineering, medicine and additional sectors.

The author previously disliked the term "agent" but recognized its necessity. Agents represent entities navigating their environment, deploying available tools and discovering creative solutions beyond their creators' imagination.

The author notes a critical gap: while agent technology has advanced dramatically, evaluation methodologies largely remain unchanged from the chatbot and RAG era. Companies selling evaluation tools often propose "increasingly absurd and over-complicated strategies" disconnected from what actually works at leading AI companies.

The guide emphasizes: "it is not that complicated." The author works at a company building agents and collaborates with leading AI firms including Framer, Clay, Vercel, and GC.AI.

**Important caveat:** This guide addresses agent evaluation specifically. Evaluating classifiers, RAG pipelines, and other AI systems requires different approaches.

---

## Benchmark-maxxer or floor-raiser?

Before implementing evaluations, teams must choose their evaluation philosophy:

### Two Paths

**Benchmark-maxxing:** Optimizing for abstract test suite performance and high benchmark scores.

**Floor-raising:** Ensuring reliability where it matters most—in actual workflows users run, moments where mistakes prove expensive, cases that would prevent shipping.

The author contends most product teams should pursue floor-raising.

### Floor-raising is error analysis

Floor-raising resembles error analysis more than benchmark design. Rather than starting with abstract test suites, teams conduct detective work: reviewing user messages, agent responses, and decision trajectories.

The methodology:
- Review traces using AI to scale analysis
- Filter, cluster, summarize interactions
- Ask: What was the last successful step? What was the first real failure? Did retrieval miss? Did the agent ignore context? Did tool calls fail? Did the final answer overstate known information?
- Fix patterns, not isolated incidents
- Only then add evaluations—targeted, grounded in real failures

A floor-raising evaluation suite functions as "a memory of bugs you refuse to reintroduce."

### The litmus test

If given the choice between 90% and 99% pass rates, benchmark-maxxers choose 99% immediately. Floor-raisers ask first: "which 1% fails?"

### Teaching refusal

One high-impact floor-raising technique involves teaching agents to decline uncertain tasks. When confidence drops below thresholds, agents should state "I don't know" rather than guess.

Benchmark-maxxers resist this—it lowers pass rates. Floor-raisers recognize that "a confident wrong answer is worse than an honest 'I don't know.'"

---

## Know your agent before you ship

### Golden cases

Select 5-10 cases representing critical paths. Begin simply: a single common user question the agent should always handle correctly. If the agent fails golden cases, do not ship.

### Understand your agent locally

For golden cases, inspect full trajectories: user message, tool calls, retrieved context, reasoning chains. The path matters as much as the answer.

Raindrop Workshop enables local trace capture, tool call inspection, and scenario replay.

### Pro tip: asking your agent

A valuable but underutilized practice: ask your agent directly about its performance.

Reconstruct the exact run passed to the agent, including the latest response, and request explanation. Reasoning traces are often opaque; returning them to the model leverages available trace, context, and prior messages as evidence.

Ask prompts like: "You were wrong. The answer was X. What would I need to have changed for you to get this right?"

While agents may not always answer truthfully, their responses function as diagnostic clues revealing where the system misinterprets or overindexes on specific prompt sections.

---

## Offline evals

### Code-aware evaluation is essential

Testing prompts in isolation makes no sense once agents become entangled with code, tools, retrieval, permissions, and product state. Behavior lives in the whole system, not the prompt string alone.

Offline evaluations resemble ordinary software testing (Vitest, pytest, jest) rather than prompt scoring. A strong offline evaluation accepts input, runs the real agent path, and asserts on results: output, tool calls, files changed, structured data, or final state.

### Example pattern

Sentry's harness-backed approach uses `describeEval(...)`, app-local harness, explicit `run(...)`, normal `expect(...)` assertions, and tool-call checks.

OpenAI's "macro evals" approach similarly drives the real agent loop on representative inputs, grading full trajectory including tool calls, intermediate state, and final answer.

### Code example

```typescript
// evals/refund_agent.eval.ts

import { expect } from 'vitest'
import { describeEval, toolCalls } from 'vitest-evals'
import { refundAgentHarness } from '../harness'

describeEval('refund agent', { harness: refundAgentHarness() }, (it) => {
  it('approves refundable invoice', async ({ run }) => {
    const result = await run('Refund invoice inv_123')
    expect(result.output.status).toBe('approved')
    expect(toolCalls(result.session).map((c) => c.name)).toEqual(
      ['lookupInvoice', 'createRefund']
    )
  })
})
```

### Dashboard pitfalls

The author recommends against hosted eval dashboards for agent testing. While report UIs are easy to build, they should couple tightly with products. Begin with local HTML viewers displaying pass/fail results.

---

## Learning from production

Post-launch, users reveal where products confuse, break, or remain underspecified.

### Start with raw logs

Begin by reading raw interactions: user messages, agent responses, tool calls, moments where expectations diverged from outcomes. Continue until saturation appears—patterns repeat.

As Hamel Husain states: "Error analysis [is] the single most valuable activity in AI development and consistently the highest-ROI activity."

This tedious work builds the mental models necessary for subsequent automation. Skipping it leads to automating wrong metrics.

### Scaling with volume

Workflows should scale with traffic. At 10 daily runs, read everything. At 10,000, systems must flag what deserves attention.

**1-100 runs/day: Stumbles**
Use raw logs as the firehose. Look for confusion, frustration, near-misses, repeated prompts. The goal is developing taste and taxonomy.

**100-1,000 runs/day: Issues**
When stumbles recur, convert into Issues—emerging problems the team discusses, reproduces, and decides whether to fix.

**1,000+ runs/day: Signals**
Track behaviors over long horizons: aesthetic complaints, refusal quality, ignored tool errors, context loss, user frustration.

**5,000+ runs/day: Experiments**
Once understanding Issues, ship fixes behind feature flags and compare affected Issues and Signals. Production determines whether changes helped.

### Self diagnostics

Raindrop can inject hidden tools enabling agents to report problems. When agents detect missing context, capability gaps, broken tools, or task failures, they call the reporting tool, which records signals on the same event.

In AI SDK integration, this requires essentially one line:

```typescript
const { generateText } = raindrop.wrap(ai, { selfDiagnostics: { enabled: true } })
```

The hidden tool conceptually looks like:

```
__raindrop_report({
  category: 'missing_context',
  summary: 'I could not find the refund policy for enterprise plans.',
  severity: 'medium',
})
```

The author notes this proved less useful than initially expected. Treat self-diagnostics like Stumbles—a firehose where interesting patterns emerge, but requiring real work to calibrate sensitivity and create useful signals.

---

## Making fixes and changes

### Direct fixes

Some problems require obvious, immediate solutions: broken tool calls, missing system prompt instructions, stale retrieval data. Fix, ship, move forward.

The challenge involves distinguishing direct fixes from symptomatic bandages. Quick fixes addressing symptoms rather than causes create weirder bugs later. Adding special-case handling for specific phrases suggests treating symptoms.

### Repro, then fix

For non-trivial issues, reproduction comes first. If failures cannot be reliably recreated, understanding remains incomplete. Return to traces and find additional examples.

Once reproducible, add the case as a golden case before fixing. This prevents regression. Pattern: find in production → reproduce locally → add to evals → fix → verify eval passes → ship.

### Eval case pruning

A trap: adding every discovered bug to the evaluation suite. After six months, 500 cases exist, 400 representing weird edge cases never occurring in production. CI takes 20 minutes. Teams ignore eval failures.

Not every bug deserves an eval case. Ask: Is this a critical path? Could it regress? Is it representative of failure classes, or truly one-off?

Be ruthless. 20 high-signal cases outperform 200 low-signal ones.

Heuristic: If an eval case has not failed in three months, either it does not test something important or the agent genuinely improved. Question whether retention serves purposes.

### Production experimentation

For many changes, only real users reveal effectiveness. Compare models, prompts, tool configurations. Run A/B tests on actual traffic measuring genuine outcomes.

Production monitoring becomes essential: Did the new model reduce hallucinations? Did the new prompt increase satisfaction? Offline evaluations confirm non-regression; production reveals actual helpfulness.

**Example:**
```
A/B test: GPT-5.3 vs Claude 4.5 Sonnet

Treatment: 88% task completion rate (up 12%)
Control: 76% task completion rate

Statistical significance: p<0.001

Promote treatment to 100% traffic
```

---

## Rinse, wash, repeat

The complete loop: ship → watch → understand failures → fix important ones → retain useful lessons as regression tests.

Each iteration marginally reduces agent embarrassment and grounds evaluation suites in reality. The goal does not involve front-loading all possible test cases. Instead, build systems learning from production without forgetting prior lessons.

Evaluation work remains ongoing, not a completed checklist. When loops stop, suites stale and confidence becomes theatrical.

### The commitment

Plan for 10-20% of agent development time devoted to evaluation and monitoring—not just case writing, but trace reading, signal tuning, and issue investigation. This represents the cost of reliable AI systems. Teams skipping this pay in production incidents.

---

## Looking forward

### The collapse of harnesses

The current model of "agent SDKs calling models" shows cracks. As models become more capable and agentic, distinctions between "the model" and "the agent" blur. Examples include Claude Code, Cursor CLI, and emerging Cursor Agent SDK.

What does evaluation look like when agents are just prompts and models? When framework code to instrument disappears? When explicit tool loops vanish from inspection?

Monitoring changes. Today, tool calls get traced by necessity. Tomorrow, perhaps only input/output pairs record, with models explaining actions. Intermediate steps become opaque—like asking humans their thoughts. Verification becomes harder.

This emphasizes end-to-end evaluation importance. Unable to inspect internals means trusting (and verifying) outputs. Golden cases and production monitoring—already recommended—become primary evaluation methods.

### What stays constant

Despite changes:

- Contact with real user behavior remains essential. Synthetic evals diverge from reality.
- Trajectory matters. Whether explicit (tool calls) or implicit (reasoning), the path is diagnostic.
- Golden cases work. Small high-signal test sets beat large low-signal ones.
- Production monitoring is essential. Failure modes cannot all be anticipated.
- Evaluation is ongoing work, not one-time setup.

Tools, frameworks, and models change. The fundamental challenge—verifying autonomous systems work as intended—persists.

---

## The short version

**Key takeaways:**

- **Pick the right frame:** Benchmark-maxxing augments experts. Floor-raising replaces human judgment.
- **Floor-raising is error analysis:** Read real interactions, find patterns that matter, fix the system behind them.
- **Use code-aware offline evals:** Test running agent paths: tools, state, files, structured output, side effects.
- **Scale production review with volume:** Start with Stumbles, let recurring patterns become Issues, track long-term Signals, validate fixes with Experiments.
- **Keep the loop tight:** Real failures become targeted regressions, not speculative eval suites.

---

## Tools mentioned

- **Raindrop Workshop:** Local trace capture, trajectory inspection, replay for agent evaluation
- **Raindrop:** Production monitoring scaling with teams
- **vitest-evals:** Sentry's harness-backed evaluation examples

---

## Further reading referenced

- "Evals are Dead" / Ben Hylak
- "Your AI Product Needs Evals" / Hamel Husain
- "Eval Awareness in Claude Opus 4.6" / Anthropic
- "How We Monitor Internal Coding Agents" / OpenAI
- "Macro Evals for Agentic Systems" / OpenAI Cookbook
- Raindrop documentation
