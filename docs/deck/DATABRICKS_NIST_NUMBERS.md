# Databricks NIST run — verified numbers (source of truth for the blog article)

These are the numbers used in `docs/blog_post.md`. They come from the
**Databricks-native run** (Foundation Model APIs + Mosaic AI Vector Search +
managed MLflow), NOT the local Google AI Studio + FAISS run documented in
`REAL_NUMBERS.md`. The two runs use different providers and retrieval stacks, so
their numbers differ. Do not cross-check the article against `REAL_NUMBERS.md`;
check it against this file.

- Experiment: `/Users/praneeth.paikray@databricks.com/eval_harness_journey_mlflow`
  (experiment_id `2551904988181616`)
- Provider: Databricks Foundation Model APIs (`<workspace>/serving-endpoints`)
- Task model: `databricks-gemini-2-5-flash`; judge on; n = 20 questions
- Harvested 2026-06-08 via `mlflow.search_runs` against the workspace.

## Baseline vs fixed (SOC 2, NIST corpus, 20 questions)

Runs: baseline `20f057bf475c45a485013a45eef2ffbc`, fixed `4a8836b5aa8d4290a34b2fd19e31f5bc`.

| signal | baseline | fixed | article rounds to |
|---|---|---|---|
| verify_before_cite (trajectory) | 0.0 | 0.9667 | 0.00 / 0.97 |
| framework_clause + policy_exists (deterministic) | 1.0 / 1.0 | 1.0 / 1.0 | 1.00 / 1.00 |
| judge_accept (reviewer-accept) | 0.575 | 0.425 | 0.58 / 0.43 |
| clear_execution (axis) | 0.5 | 0.925 | 0.50 / 0.93 |
| clear_correctness | 0.75 | 0.6833 | radar 0.75 / 0.683 |
| clear_safety | 1.0 | 1.0 | 1.00 |
| pass_rate | 0.0 | 0.05 | — |

## Transfer to held-out ISO 27001 (same fixed agent)

Run: `74a9abe4d6f74bd28115c3dcbbeea596` (dataset iso27001, variant tuned).

| signal | SOC 2 | ISO 27001 | article |
|---|---|---|---|
| verify_before_cite | 0.9667 | 1.0 | 0.97 / 1.00 |
| judge_accept | 0.425 | 0.375 | 0.43 / 0.38 |

## Model portability swap (Claude)

Run: `487f731a24fd419f9cf96389aaf09b29`, `variant=tuned-swap`,
`model=databricks-claude-sonnet-4-6`, dataset soc2, n=20.
(Claude WAS run here on Databricks. `REAL_NUMBERS.md`'s "Claude never run" note
refers only to the local Google AI Studio session, not this run.)

| signal | gemini-2-5-flash | claude-sonnet-4-6 | article |
|---|---|---|---|
| verify_before_cite | 0.9667 | 1.0 | 0.97 / 1.00 |
| judge_accept | 0.425 | 0.525 | 0.43 / 0.53 |
| total_cost_usd / run | 0.0 (free tier) | 0.010119 | — |

## GEPA (real dspy.GEPA on a Job)

Runs: `gepa-full` `5639e2814d0348309c96c31979b51326`
(max_metric_calls 40, train 16, val 20, task `databricks-gemini-2-5-flash`,
reflection `databricks-gemini-2-5-pro`); summary `1c44e2079c224fcc9518d2fe00d5b7b8`.

- total_metric_calls = **41**; candidates_scored = 1; frontier_size = 1
- winner_idx = 0; winner_beats_baseline = 0.0  → the winner IS the seed
- Article claim "~41 metric calls, no candidate beat the seed" is exact.

## Mechanism notes (so prose stays accurate)

- verify-before-cite is scored from the recorded `tool_invocations` list (set
  membership: every cited control must have a verification call that returned
  true). It is NOT a walk of the MLflow span tree comparing timestamps. The
  ordering guarantee is structural: the finalize step writes only from the
  verified list.
- The verify step (`_verify_one`) runs inside the `drafter` span; it does not
  emit its own MLflow span.
- Verified-list membership of final citations is enforced by the trajectory
  scorer, not by a post-check inside the drafter node.
- The NIST corpus in the notebook is a ~37-control subset embedded for offline
  reproducibility, recited against the full catalog's IDs.
