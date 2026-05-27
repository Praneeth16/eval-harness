"""Cluster failing traces by CLEAR axis + failure shape.

Heuristic, no embeddings: we group by `(clear_axis, scorer_name)` and
attach a human-friendly label per known scorer. Each cluster carries up to
N sample trace IDs that the UI surfaces.

The label table here is what shows up on `/clusters/[run_id]` cards.
"""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field

from sqlalchemy import select

from core.store.db import get_session
from core.store.models import Cluster, Score, Trace

# Friendly labels per scorer — used as the cluster card title.
_LABEL: dict[str, str] = {
    "policy_exists": "Phantom policy citations",
    "framework_clause_resolves": "Phantom framework citations",
    "word_count": "Over-long answers (>120 words)",
    "cost_budget": "Per-question cost overshoot",
    "latency_budget": "Per-question latency overshoot",
    "groundedness": "Ungrounded claims",
    "judge_accept": "Reviewer would reject",
    "policy_exists_called_before_cite": "Cited without verifying policy_exists_check",
    "gap_detector_invoked_for_no_policy": "Missed gap escalation",
    "tool_order_sane": "Pipeline-stage skip",
    "prompt_injection_resisted": "Prompt-injection compliance",
    "pii_leak": "PII leak in drafted answer",
    "hallucinated_claim": "Fabricated cert / overclaim",
}


@dataclass
class ClusterDescriptor:
    cluster_id: str
    eval_run_id: str
    clear_axis: str
    label: str
    size: int
    sample_trace_ids: list[str] = field(default_factory=list)
    summary: str = ""


def cluster_run(eval_run_id: str, *, sample_per_cluster: int = 3) -> Sequence[ClusterDescriptor]:
    """Build cluster rows for a finished eval run. Persists + returns them."""
    with get_session() as s:
        # All failed scores joined with their trace.
        stmt = (
            select(Score, Trace)
            .join(Trace, Trace.id == Score.trace_id)
            .where(Trace.eval_run_id == eval_run_id, Score.passed == 0)
        )
        rows = s.execute(stmt).all()
        if not rows:
            return []

        buckets: dict[tuple[str, str], list[str]] = defaultdict(list)
        for score, trace in rows:
            key = (score.clear_axis, score.scorer_name)
            buckets[key].append(trace.id)

        # De-dupe samples while preserving order.
        descriptors: list[ClusterDescriptor] = []
        existing = s.execute(
            select(Cluster).where(Cluster.eval_run_id == eval_run_id)
        ).scalars().all()
        for c in existing:
            s.delete(c)

        for (axis, scorer_name), trace_ids in sorted(buckets.items()):
            uniq: list[str] = []
            for tid in trace_ids:
                if tid not in uniq:
                    uniq.append(tid)
            sample = uniq[:sample_per_cluster]
            label = _LABEL.get(scorer_name, scorer_name)
            cid = f"clu_{uuid.uuid4().hex[:10]}"
            descriptor = ClusterDescriptor(
                cluster_id=cid,
                eval_run_id=eval_run_id,
                clear_axis=axis,
                label=label,
                size=len(uniq),
                sample_trace_ids=sample,
                summary=(
                    f"{len(uniq)} traces failed {scorer_name}. "
                    f"Top sample trace_ids: {', '.join(sample)}."
                ),
            )
            descriptors.append(descriptor)
            s.add(
                Cluster(
                    id=cid,
                    eval_run_id=eval_run_id,
                    clear_axis=axis,
                    label=label,
                    size=len(uniq),
                    sample_trace_ids_json=json.dumps(sample),
                    summary=descriptor.summary,
                )
            )
        return descriptors


__all__ = ["ClusterDescriptor", "cluster_run"]
