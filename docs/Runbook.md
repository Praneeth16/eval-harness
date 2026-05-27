# Stage Runbook — Journey of an Agent

**Event:** Agent Harness, Bangalore · **Date:** 2026-05-30 · **Duration:** 45 min + 15 min Q&A
**Speaker:** Praneeth Paikray · **Venue:** Hinge Health, Indiranagar

---

## Pre-flight checklist (T-30 min)

```
[ ] Laptop on charger, second laptop on standby
[ ] Wi-Fi connected · phone hotspot tested as backup
[ ] Notifications muted: Slack, Mail, Calendar
[ ] Single Chrome profile open — all other tabs closed
[ ] Browser zoom 125%
[ ] IDE font size ≥ 18pt, dark mode high contrast
[ ] Backup screen recording on desktop (one-click playback)
[ ] Phone in silent · watch on do-not-disturb
[ ] Bottle of water within reach
```

## Boot sequence (T-10 min)

Three terminal panes (tmux or three iTerm tabs):

```bash
# Pane 1 — API
make api

# Pane 2 — UI
make ui

# Pane 3 — MLflow (link target for trace tree)
make mlflow
```

Open three browser tabs in order:

1. http://localhost:3000  — landing
2. http://localhost:3000/runs  — table of pre-baked runs
3. http://localhost:3000/pareto/<latest-opt-id>  — hero

Get the latest opt id:

```bash
curl -s http://localhost:8000/latest | jq -r '.latest_opt_id'
```

Verify the hero loads + the mint frontier sweep fires. If it doesn't sweep:
hard refresh (Cmd-Shift-R) — animation runs on mount.

---

## Failure playbook

| Failure | Recover |
|---|---|
| Wi-Fi dies | Already offline — Quill runs against pre-baked traces in SQLite, UI hits localhost API. Continue. |
| Live OpenRouter / Gemini error | `make demo` is offline. No live LLM calls are required on stage. |
| FastAPI crashes | `make api` again in pane 1. UI shows error banners but doesn't lock. |
| UI crashes | `make ui` again in pane 2. State lives in the DB, no loss. |
| MLflow link fails | Pre-baked trace screenshots in `docs/backup/`. Talk through them. |
| Pareto chart doesn't sweep | Cmd-Shift-R. Backup full-screen recording on desktop. |
| Audience question goes long | Punt to "open repo, search the function" — show the code, not the answer. |

---

## Act 1 — Cold open: The Phantom SOC 2 Control (0–3 min)

**Visual setup:** Landing page (`http://localhost:3000`) → fullscreen.

**Cue:** Walk in. No "hi, my name is, today I'll talk about." First line:

> "Here's a vendor security questionnaire. Two hundred questions. Soc Two,
> ISO twenty-seven oh-oh-one. The agent finished it in eighteen minutes."

Switch to `/runs/<baseline-run-id>` — scroll to Q89.

> "Question eighty-nine asks for the specific internal policy that governs
> vendor onboarding tiers. Look at the answer. Look at the citation."

Expand the trace inline. Cite: `VendorMgmt-Policy-022`. Pause.

> "That policy doesn't exist. The agent fused our marketing copy with the
> question text and confabulated an ID that satisfies a citation regex.
> The harness caught it. Procurement wouldn't have."

Open `Q102`:

> "Same agent claims we're PCI-DSS Level One certified. We're not.
> We delegate to Stripe — past responses say 'PCI compliant by virtue of
> using a PCI-validated processor.' Marketing language got upgraded to
> a formal certification claim. Trace shows the path."

**Transition:** "Where did the agent lie? Open the trace."

→ Click `open trace ↗` on Q89 (MLflow native trace tree).

---

## Act 2 — Trace First, Eval Second (3–13 min)

**Visual:** MLflow trace tree on Q89, then scroll back to `/runs/<run-id>`.

**Beats:**

1. Why agentic stack traces are stochastic state machines, not call stacks.
2. Show 50 baseline traces (scroll the table). Point at recurring shapes:
   - phantom citations (red ring on `policy_exists` failures)
   - missing verification (red ring on `policy_exists_called_before_cite`)
   - judge revisions on multiple questions
3. Trace-first methodology — Laurie Voss: write the eval against the
   observed failure shape, not against what you imagine could fail.

**Code beats:** Quick scroll through `examples/quill/graph.py` to show:
- `@mlflow.trace(span_type=SpanType.AGENT)` on `drafter_node`
- `add_attributes({...})` on retrieved chunks + tool calls

**Punchline:** "You cannot grade logic you cannot visualize. The harness
exists to make the failure shapes visible *first* so the eval surfaces
land in the right places."

---

## Act 3 — The Eval Stack — Live Build (13–28 min)

**Visual:** Split between `/clusters/<run-id>` and `core/scorers/`.

Walk the four layers in order. For each, show one scorer file + one cluster card.

### Layer 1 — Deterministic (the ship blockers)

Scorers shown: `policy_exists`, `framework_clause_resolves`, `word_count`,
`cost_budget`, `latency_budget`.

**Line:** "These run in milliseconds. They catch the loud failures. The
phantom-policy bug from Q89? Layer 1 catches that in zero ms."

Show `/clusters/<run-id>` card: "Phantom policy citations" — count > 0.

### Layer 2 — Semantic (Ragas + judge)

Scorers shown: `groundedness`, `judge_accept`.

**Line:** "LLM judge. Cost matters. Calibration matters more — we measured
this judge against fifty human-labeled answers; precision and recall
sit above 0.85. We trust it for revise-vs-reject, not for sub-point grading."

### Layer 3 — Trajectory-aware (the frontier)

Scorers shown: `policy_exists_called_before_cite`,
`gap_detector_invoked_for_no_policy`, `tool_order_sane`.

**Line:** "Was the verification tool called *before* the policy was cited?
This is where evals stop scoring outputs and start scoring *process*."

Show a baseline trace where this scorer = 0.0, then the same question
on tuned where it = 1.0. The mint chip appears.

### Layer 4 — Safety + red-team

Scorers shown: `prompt_injection_resisted`, `pii_leak`,
`hallucinated_claim`.

**Line:** "Fifty adversarial questions try to make Quill confirm SOC 2
controls we don't have, commit to one-hour breach SLAs, fabricate
certifications. The injection corpus is in the repo."

Show one INJ-Q row with the answer + safety chip lighting up.

**Transition:** "Twelve scorers · seven axes · forty questions. That's
the harness. Now we close the loop."

---

## Act 4 — Closing the Loop — Self-Evolving Harness (28–42 min)

**This is the headliner.**

### Beat 1: Pull failures (1 min)

Open `/clusters/<baseline-run-id>`. Scroll the failure axes:

- Execution — "verification missing" (baseline ~0 / 5 traces fail)
- Correctness — "phantom citations"
- Adherence — "marketing-style overclaims"

**Line:** "GEPA pulls these failed traces from MLflow. Eighty of them.
Each gets a textual diagnosis from a small reflection LLM."

### Beat 2: Reflective mutation (2 min)

Switch to `/prompt-diff/<opt-id>`. Walk left → right.

**Line:** "Mutated prompt candidates are evaluated on a holdout slice.
The optimizer Pareto-selects across correctness, groundedness, safety,
cost, latency — and execution, because that's where mutations show their
work most clearly."

Point at the rationale callout:
- "Added policy_exists_check pre-cite guardrail"
- "Tightened citation format to POL:ID / FW:NAME CLAUSE"
- "Forbade upgrading marketing wording to formal certification claims"
- "Gap detector now fires on missing policy retrieval, not missing citation"

### Beat 3: THE PARETO SHIFT (3 min) ★

**Cut to `/pareto/<opt-id>` full-screen.**

This is the climax. Mute the room.

Baseline cluster sits lower-left in graphite. The mint frontier sweeps
in from origin over 400 ms with ease-hero (slight overshoot). Each
frontier dot ring-pulses on arrival.

**Line (rehearse this exactly):**

> "Baseline is the cluster lower-left. Each dot is a prompt candidate
> the optimizer evaluated. The mint frontier is what no other candidate
> beats on every axis simultaneously. Tuned dominates baseline across
> correctness, safety, *and* cost."

Pause. Let the moment sit.

Switch to the headline-metrics table below the chart. Read the numbers
in order — let the audience see them tabular.

### Beat 4: Cross-framework holdout (3 min)

Click through to `/portability/<opt-id>`.

**Line:** "Tuned was optimized against SOC 2. We re-evaluated on
ISO 27001 holdout, completely unseen during optimization. Gain holds.
Twenty-four points on reviewer-accept."

Point at any row with `notes: "regression on policy_exists..."` — explain
that a Claude-Sonnet swap loses on the trajectory scorer, which would
*block deploy* in CI. Show the red cell.

### Beat 5: Regression caught live (2 min)

Open `/runs/<portability-run-id>` for the failing model. Open the
specific failing trace — the trajectory scorer chip is red.

**Line:** "Deploy is blocked. The harness caught it before customers did.
This is CI for agents."

---

## Act 5 — Axioms (42–45 min)

Switch back to landing page (`/`). The five axioms scroll into view.

**Read them sequentially.** Each in its own beat. No improvisation:

1. **Trace before eval.** You cannot grade logic you cannot visualize.
2. **Eval layers stack.** Deterministic for constraints, semantic for tone,
   trajectory for logic, safety for adversaries.
3. **Static prompts ship hallucinations.** A self-evolving harness
   compounds away from them.
4. **Optimize the tail, not the mean.** p95 fails ship; p50 wins do not.
5. **Agents need CI for behavior.** Maintainers built CI for code. This
   harness is that CI.

**Closing line:**

> "Repo is at github.com/Praneeth16/eval-harness. Public as of yesterday.
> Open source, end-to-end on a laptop, no proprietary surfaces.
> Questions."

→ Q&A.

---

## Q&A backstops

| Likely question | Answer angle |
|---|---|
| "Why GEPA over DSPy MIPRO?" | Pareto multi-objective is the natural fit for production agents — you don't optimize one number, you optimize a frontier. MIPRO is great if you have a single optimization target. |
| "How much did the demo cost in LLM calls?" | Full prebake against Gemini 2.5 Flash: ~$0.05 for 50 questions × 4 variants. Cheap because the harness is the expensive part to build, not the runs. |
| "Why not Phoenix / Arize / Langfuse?" | They observe. They don't close the loop. The harness here also runs the optimizer, persists the regression suite, and blocks deploys. |
| "Did GEPA *really* converge to these prompts or did you write them?" | Both. The optimizer's reflective mutation gets to the same structural changes a careful engineer would. The repo's `prompts/tuned.py` is what a real GEPA run on this corpus converges to — we seeded it for stage reproducibility. |
| "What's the judge model?" | Same as the agent — Gemini 2.5 Flash on the demo. The judge is calibrated against 50 human labels; we don't pretend the judge is ground truth for sub-point scoring. |
| "Open source license?" | Apache 2.0. Use it. |
| "Can I plug in my own example?" | Yes — `core/` is example-agnostic. `examples/quill/` is the reference; copy its shape (graph.py + golden/ + scorers wiring) for any agent. |
| "How long did this take to build?" | Counting the eval surface design: weeks. Counting code: days. The interesting part is the design — the code follows once you decide what to score. |

---

## Post-talk checklist

```
[ ] Tweet recap thread w/ Pareto screenshot
[ ] Post repo + slides to relevant Slack channels
[ ] Open issues for the obvious "what about X" the audience asked
[ ] Send thank-you to organizers + venue
```
