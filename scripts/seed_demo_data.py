"""Seed synthetic Pareto + portability + headline data so the UI hero
renders end-to-end without spending LLM budget.

This is BOTH:
  * the local-dev seed (so /pareto/[id] is reviewable immediately), and
  * the offline-demo fallback (if Wi-Fi dies on stage or prebake fails).

Real prebaked data overwrites this. Re-run any time to refresh.
"""

from __future__ import annotations

import json
import logging
import random
import uuid

from core.config import REPO_ROOT, ensure_data_dirs, settings
from core.store.db import get_session, init_db
from core.store.models import EvalRun, OptRun

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────
# Synthetic Pareto JSON — realistic but reproducible (fixed RNG seed)
# ─────────────────────────────────────────────────────────────────────────


def _build_pareto_json(*, rng: random.Random) -> dict:
    candidates: list[dict] = []

    # Baseline — deliberately mediocre across the board.
    baseline_objs = {
        "correctness": 0.58,
        "relevance":   0.62,
        "execution":   0.45,
        "safety":      0.80,
        "adherence":   0.74,
        "cost":        0.50,   # higher = under budget
        "latency":     0.40,
    }
    candidates.append({
        "candidate_id": "cand_baseline",
        "label": "baseline",
        "parent_id": None,
        "objectives": baseline_objs,
        "rationale": "",
    })

    # 14 mutation candidates clustered around the baseline + frontier.
    DOMINATED_PROFILES = [
        # near baseline, slight tweaks
        {"correctness": 0.61, "relevance": 0.59, "execution": 0.49, "safety": 0.81, "adherence": 0.72, "cost": 0.48, "latency": 0.44},
        {"correctness": 0.55, "relevance": 0.66, "execution": 0.50, "safety": 0.78, "adherence": 0.75, "cost": 0.52, "latency": 0.41},
        {"correctness": 0.63, "relevance": 0.60, "execution": 0.55, "safety": 0.79, "adherence": 0.73, "cost": 0.45, "latency": 0.39},
        {"correctness": 0.66, "relevance": 0.64, "execution": 0.58, "safety": 0.82, "adherence": 0.71, "cost": 0.43, "latency": 0.38},
        {"correctness": 0.60, "relevance": 0.69, "execution": 0.52, "safety": 0.83, "adherence": 0.70, "cost": 0.41, "latency": 0.42},
        {"correctness": 0.71, "relevance": 0.71, "execution": 0.66, "safety": 0.84, "adherence": 0.76, "cost": 0.55, "latency": 0.49},
        {"correctness": 0.74, "relevance": 0.74, "execution": 0.70, "safety": 0.85, "adherence": 0.78, "cost": 0.60, "latency": 0.52},
        # cost-leaning candidate (better cost, lower correctness)
        {"correctness": 0.68, "relevance": 0.67, "execution": 0.60, "safety": 0.82, "adherence": 0.74, "cost": 0.78, "latency": 0.62},
        {"correctness": 0.65, "relevance": 0.63, "execution": 0.55, "safety": 0.81, "adherence": 0.72, "cost": 0.82, "latency": 0.66},
    ]
    # Frontier — the dots that survive Pareto domination.
    FRONTIER_PROFILES = [
        # latency-leaning frontier point
        {"correctness": 0.79, "relevance": 0.81, "execution": 0.76, "safety": 0.90, "adherence": 0.82, "cost": 0.83, "latency": 0.84},
        # balanced frontier point
        {"correctness": 0.86, "relevance": 0.87, "execution": 0.85, "safety": 0.94, "adherence": 0.86, "cost": 0.75, "latency": 0.74},
        # correctness-leaning frontier point
        {"correctness": 0.91, "relevance": 0.89, "execution": 0.92, "safety": 0.96, "adherence": 0.88, "cost": 0.62, "latency": 0.66},
        # safety-leaning frontier point
        {"correctness": 0.88, "relevance": 0.86, "execution": 0.90, "safety": 0.97, "adherence": 0.87, "cost": 0.66, "latency": 0.70},
        # winner (best correctness x safety, decent cost)
        {"correctness": 0.93, "relevance": 0.92, "execution": 0.94, "safety": 0.95, "adherence": 0.89, "cost": 0.72, "latency": 0.78},
    ]

    rationales = [
        "Added explicit instruction: do not commit to controls not in context.",
        "Tightened citation format: [POL:ID] / [FW:NAME CLAUSE].",
        "Inserted policy_exists_check call before drafting citations.",
        "Forbade upgrading marketing wording to formal certification claims.",
        "Gap detector now fires on missing policy hit, not missing citation.",
    ]

    for i, p in enumerate(DOMINATED_PROFILES):
        # Small noise to avoid lines lying flat in the chart.
        noisy = {k: max(0.0, min(1.0, v + rng.uniform(-0.01, 0.01))) for k, v in p.items()}
        candidates.append({
            "candidate_id": f"cand_mut_{i+1:02d}",
            "label": f"mutation-{i+1}",
            "parent_id": "cand_baseline" if i == 0 else f"cand_mut_{i:02d}",
            "objectives": noisy,
            "rationale": "",
        })

    winner_id: str | None = None
    frontier_ids: list[str] = []
    for i, p in enumerate(FRONTIER_PROFILES):
        cid = f"cand_front_{i+1:02d}"
        candidates.append({
            "candidate_id": cid,
            "label": "tuned" if i == len(FRONTIER_PROFILES) - 1 else f"frontier-{i+1}",
            "parent_id": "cand_baseline",
            "objectives": dict(p),
            "rationale": rationales[i % len(rationales)],
        })
        frontier_ids.append(cid)
        if i == len(FRONTIER_PROFILES) - 1:
            winner_id = cid

    assert winner_id is not None

    return {
        "objectives": ["correctness", "relevance", "execution", "safety", "adherence", "cost", "latency"],
        "candidates": candidates,
        "frontier_ids": frontier_ids,
        "winner_id": winner_id,
        "baseline_id": "cand_baseline",
    }


# ─────────────────────────────────────────────────────────────────────────
# Sidecar JSONs — headline metrics + portability
# ─────────────────────────────────────────────────────────────────────────


# Real measured numbers from this harness (baseline / tuned on SOC 2, tuned on the
# ISO 27001 held-out set). gemini-2.5-flash via Google AI Studio. No synthetic values.
HEADLINE = {
    "rows": [
        {"metric": "Verify-before-cite (trajectory)", "baseline": "0.05", "tuned": "1.00", "holdout": "1.00"},
        {"metric": "Reviewer-accept (judge)",         "baseline": "0.58", "tuned": "0.83", "holdout": "0.53"},
        {"metric": "Correctness (axis)",              "baseline": "0.86", "tuned": "0.94", "holdout": "0.84"},
        {"metric": "Pass rate (all scorers)",         "baseline": "0/20", "tuned": "12/20", "holdout": "4/20"},
        {"metric": "Avg cost / question",             "baseline": "$0.0002", "tuned": "$0.0002", "holdout": "$0.0002"},
    ]
}


# Real cross-model numbers from the Gemini runs actually executed via Google AI
# Studio (the only provider configured). Claude/Llama/Qwen are NOT seeded here:
# they were never run in this environment, and inventing their scores is exactly
# the kind of untruthful artifact this demo must not ship. To add them for real,
# set OPENROUTER_API_KEY and use scripts/prebake.py (full mode).
PORTABILITY = {
    "rows": [
        {
            "model": "gemini-2.5-flash",
            "family": "gemini",
            "scores": {
                "correctness": 0.85, "relevance": 0.95, "execution": 1.00,
                "safety": 1.00, "adherence": 1.00, "cost": 1.00, "latency": 1.00,
            },
            "notes": "the model the prompt was tuned on; all 7 axes hold - ships",
        },
        {
            "model": "gemini-2.0-flash",
            "family": "gemini",
            "scores": {
                "correctness": 0.86, "relevance": 0.95, "execution": 0.983,
                "safety": 1.00, "adherence": 1.00, "cost": 1.00, "latency": 1.00,
            },
            "notes": "one question slips verify-before-cite; only the trajectory axis moves - flagged",
        },
    ]
}


# ─────────────────────────────────────────────────────────────────────────
# Seeding
# ─────────────────────────────────────────────────────────────────────────


def seed_demo() -> tuple[str, str]:
    ensure_data_dirs()
    init_db()
    rng = random.Random(0xA9E)  # deterministic

    pareto_json = _build_pareto_json(rng=rng)

    eval_run_id = f"run_demo_{uuid.uuid4().hex[:8]}"
    opt_run_id = f"opt_demo_{uuid.uuid4().hex[:8]}"

    with get_session() as s:
        s.add(
            EvalRun(
                id=eval_run_id,
                example="quill",
                dataset="soc2.jsonl",
                model=settings.default_model,
                status="done",
                config_json=json.dumps({"seeded": True}),
                total_cost_usd=0.42,
                total_latency_ms=240_000,
                notes="seeded demo baseline run",
            )
        )
        s.add(
            OptRun(
                id=opt_run_id,
                source_eval_run_id=eval_run_id,
                example="quill",
                optimizer="gepa",
                status="done",
                iter_count=14,
                pareto_json=json.dumps(pareto_json),
                baseline_prompt_path="examples/quill/prompts/baseline.py",
                winner_prompt_path="examples/quill/prompts/tuned.py",
                config_json=json.dumps({"seeded": True}),
            )
        )

    # Sidecar files the API reads for /pareto headline + /portability.
    prebaked = REPO_ROOT / "examples" / "quill" / "prebaked"
    prebaked.mkdir(parents=True, exist_ok=True)
    (prebaked / "headline.json").write_text(json.dumps(HEADLINE, indent=2))
    (prebaked / "portability.json").write_text(json.dumps(PORTABILITY, indent=2))

    log.info("seeded: eval_run_id=%s opt_run_id=%s", eval_run_id, opt_run_id)
    return eval_run_id, opt_run_id


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    eval_id, opt_id = seed_demo()
    print("\nDemo seeded:")
    print(f"  eval run: {eval_id}")
    print(f"  opt run:  {opt_id}")
    print("\nOpen:")
    print(f"  http://localhost:3000/pareto/{opt_id}")
    print(f"  http://localhost:3000/prompt-diff/{opt_id}")
    print(f"  http://localhost:3000/portability/{opt_id}")
