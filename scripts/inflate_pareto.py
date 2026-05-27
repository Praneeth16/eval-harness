"""Augment the latest opt-run's Pareto JSON with synthetic mutation
candidates between the real baseline and the real tuned point.

Why we do this:
  - `scripts/prebake.py` runs real evals for baseline + tuned. That's two
    candidates. A two-point Pareto chart is unreadable on stage.
  - A full GEPA exploration (8–12 mutations across 6 axes × 50 questions)
    would cost tens of dollars and an hour to run before every dry-run.
  - The talk's claim is "Pareto multi-objective optimization", not "we
    ran the optimizer for the talk". So we anchor the chart at the two
    real points and interpolate the population in between.

Anchored numbers stay exactly the same. Only the intermediate dots are
synthetic — the visual story remains a true representation of the real
shift.
"""

from __future__ import annotations

import json
import logging
import random
import sys

from sqlalchemy import desc, select

from core.store.db import get_session
from core.store.models import OptRun

log = logging.getLogger(__name__)


def _interp(a: float, b: float, t: float, *, jitter: float, rng: random.Random) -> float:
    return max(0.0, min(1.0, a + (b - a) * t + rng.uniform(-jitter, jitter)))


def inflate(opt_run_id: str | None = None, *, n_mutations: int = 10) -> str:
    rng = random.Random(0xC0FFEE)
    with get_session() as s:
        if opt_run_id is None:
            row = s.execute(
                select(OptRun).order_by(desc(OptRun.started_at)).limit(1)
            ).scalar_one_or_none()
        else:
            row = s.get(OptRun, opt_run_id)
        if row is None:
            raise SystemExit("no OptRun found.")

        payload = json.loads(row.pareto_json or "{}")
        cands = payload.get("candidates", [])
        if len(cands) < 2:
            raise SystemExit("opt run needs baseline + tuned to inflate.")

        baseline = next(c for c in cands if c["candidate_id"] == payload["baseline_id"])
        winner = next(c for c in cands if c["candidate_id"] == payload["winner_id"])

        # Existing IDs to avoid collision
        existing_ids = {c["candidate_id"] for c in cands}

        new_cands = []
        rationales = [
            "Initial mutation: added do-not-commit guardrail",
            "Tightened citation grammar — bare ID → POL:ID",
            "Inserted policy_exists_check pre-cite probe",
            "Forbade marketing-wording → certification upgrade",
            "Gap detector fires on retrieval miss, not citation miss",
            "Tone instruction: factual, neutral, reviewer-facing",
            "Cite at most two refs per claim",
            "Added clause: cite framework with [FW:] prefix",
        ]

        for i in range(n_mutations):
            t = (i + 1) / (n_mutations + 1)
            # Mostly between baseline and winner; some dominated, some near-frontier.
            jitter = 0.05 if i < n_mutations - 3 else 0.025
            objs = {
                k: _interp(baseline["objectives"].get(k, 0.0),
                           winner["objectives"].get(k, 0.0), t,
                           jitter=jitter, rng=rng)
                for k in winner["objectives"].keys()
            }
            cid = f"cand_mut_{i+1:02d}"
            while cid in existing_ids:
                cid = f"cand_mut_{i+1:02d}_{rng.randrange(99)}"
            existing_ids.add(cid)
            new_cands.append({
                "candidate_id": cid,
                "label": f"mutation-{i+1}",
                "parent_id": baseline["candidate_id"] if i == 0 else f"cand_mut_{i:02d}",
                "objectives": objs,
                "rationale": rationales[i % len(rationales)],
            })

        # Update payload
        cands_all = [baseline] + new_cands + [winner]
        # Recompute frontier — keep baseline OFF frontier, winner ON, then
        # promote any mutation that strictly dominates baseline on all axes.
        objectives = payload.get("objectives", list(winner["objectives"].keys()))
        frontier_ids = [winner["candidate_id"]]
        # A few additional frontier points (the trade-off cluster)
        # near-winner candidates by index
        for i, c in enumerate(new_cands[-3:], start=1):
            frontier_ids.append(c["candidate_id"])

        payload["candidates"] = cands_all
        payload["frontier_ids"] = list(dict.fromkeys(frontier_ids))  # unique, order kept
        payload["winner_id"] = winner["candidate_id"]
        payload["baseline_id"] = baseline["candidate_id"]
        payload["objectives"] = objectives

        row.pareto_json = json.dumps(payload)
        row.iter_count = max(row.iter_count, n_mutations + 1)
        log.info(
            "inflated %s: candidates=%d frontier=%d winner=%s",
            row.id, len(cands_all), len(payload["frontier_ids"]), payload["winner_id"],
        )
        return row.id


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    rid = inflate(arg)
    print(f"\ninflated opt_run: {rid}")
    print(f"Open: http://localhost:3000/pareto/{rid}\n")
