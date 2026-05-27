"""FAISS retrieval over Quill's corpus.

Three sub-indices, queried together: frameworks, policies, past_responses.
Each chunk keeps a `kind` field so downstream agents (and the trajectory
scorer) can tell what type of evidence the agent retrieved.

Two deterministic helpers also live here, used by both the Quill agent (as
tools the agent _should_ call before citing) and by the L1 scorers (to
detect when the agent cited something that does not exist):

  * `policy_exists(policy_id)`
  * `framework_clause_resolves(framework, clause_id)`
"""

from __future__ import annotations

# faiss-cpu (OpenMP) + torch (also OpenMP, pulled by sentence-transformers)
# deadlock on macOS arm64 unless thread counts are pinned BEFORE either lib
# loads. Set here at the top of the import graph for this subpackage.
import os as _os

_os.environ.setdefault("OMP_NUM_THREADS", "1")
_os.environ.setdefault("MKL_NUM_THREADS", "1")
_os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import json
import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import faiss
import numpy as np

from core.config import settings
from examples.quill.seed_corpus import CORPUS_DIR, dump_to_disk

log = logging.getLogger(__name__)


INDEX_DIR = Path(settings.faiss_index_dir) / "quill"
INDEX_PATH = INDEX_DIR / "corpus.faiss"
META_PATH = INDEX_DIR / "corpus.meta.jsonl"


@dataclass
class Chunk:
    chunk_id: str
    kind: str  # "framework" | "policy" | "past_response"
    title: str
    text: str
    meta: dict = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────
# Deterministic lookups — these power tools the agent should call, AND the
# L1 scorers that detect hallucinated citations.
# ─────────────────────────────────────────────────────────────────────────

_policy_id_cache: set[str] | None = None
_framework_clause_cache: set[tuple[str, str]] | None = None


def _load_corpus_files() -> None:
    """Make sure corpus jsonl files exist on disk."""
    if not (CORPUS_DIR / "policies.jsonl").exists():
        dump_to_disk()


def _iter_jsonl(path: Path) -> Iterable[dict]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def _load_policy_ids() -> set[str]:
    global _policy_id_cache
    if _policy_id_cache is None:
        _load_corpus_files()
        _policy_id_cache = {
            row["policy_id"] for row in _iter_jsonl(CORPUS_DIR / "policies.jsonl")
        }
    return _policy_id_cache


def _load_framework_clauses() -> set[tuple[str, str]]:
    global _framework_clause_cache
    if _framework_clause_cache is None:
        _load_corpus_files()
        _framework_clause_cache = {
            (row["framework"], row["clause_id"])
            for row in _iter_jsonl(CORPUS_DIR / "frameworks.jsonl")
        }
    return _framework_clause_cache


def policy_exists(policy_id: str) -> bool:
    """True iff `policy_id` is a real policy in the corpus."""
    if not policy_id:
        return False
    return policy_id.strip() in _load_policy_ids()


def framework_clause_resolves(framework: str, clause_id: str) -> bool:
    """True iff `(framework, clause_id)` matches an entry in the framework corpus."""
    if not framework or not clause_id:
        return False
    return (framework.strip(), clause_id.strip()) in _load_framework_clauses()


def list_policies() -> list[dict]:
    _load_corpus_files()
    return list(_iter_jsonl(CORPUS_DIR / "policies.jsonl"))


def list_frameworks() -> list[dict]:
    _load_corpus_files()
    return list(_iter_jsonl(CORPUS_DIR / "frameworks.jsonl"))


def list_past_responses() -> list[dict]:
    _load_corpus_files()
    return list(_iter_jsonl(CORPUS_DIR / "past_responses.jsonl"))


# ─────────────────────────────────────────────────────────────────────────
# FAISS index — single flat IP index over MiniLM embeddings (cosine via
# normalization). Small corpus (~100 chunks) so flat is fine.
# ─────────────────────────────────────────────────────────────────────────

_model = None
_index: faiss.Index | None = None
_chunks: list[Chunk] | None = None


def _get_encoder():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        log.info("loading embed model: %s", settings.embed_model)
        _model = SentenceTransformer(settings.embed_model, device=settings.embed_device)
    return _model


def _embed(texts: list[str]) -> np.ndarray:
    model = _get_encoder()
    vecs = model.encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    ).astype("float32")
    return vecs


def _collect_chunks() -> list[Chunk]:
    """Build the flat chunk list from all three jsonl files."""
    chunks: list[Chunk] = []

    for fw in list_frameworks():
        chunks.append(
            Chunk(
                chunk_id=f"FW::{fw['framework']}::{fw['clause_id']}",
                kind="framework",
                title=f"{fw['framework']} {fw['clause_id']} — {fw['title']}",
                text=fw["text"],
                meta={"framework": fw["framework"], "clause_id": fw["clause_id"]},
            )
        )

    for pol in list_policies():
        chunks.append(
            Chunk(
                chunk_id=f"POL::{pol['policy_id']}",
                kind="policy",
                title=f"{pol['policy_id']} — {pol['title']}",
                text=pol["text"],
                meta={"policy_id": pol["policy_id"]},
            )
        )

    for past in list_past_responses():
        chunks.append(
            Chunk(
                chunk_id=f"PAST::{past['q_id']}",
                kind="past_response",
                title=past["question"],
                text=past["answer"],
                meta={
                    "q_id": past["q_id"],
                    "citations": past.get("citations", []),
                },
            )
        )

    return chunks


def build_index(force: bool = False) -> None:
    """Build (or rebuild) the FAISS index on disk."""
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    if not force and INDEX_PATH.exists() and META_PATH.exists():
        return

    chunks = _collect_chunks()
    texts = [f"{c.title}. {c.text}" for c in chunks]
    vecs = _embed(texts)

    dim = vecs.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vecs)

    faiss.write_index(index, str(INDEX_PATH))
    with META_PATH.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(
                json.dumps(
                    {
                        "chunk_id": c.chunk_id,
                        "kind": c.kind,
                        "title": c.title,
                        "text": c.text,
                        "meta": c.meta,
                    }
                )
                + "\n"
            )

    log.info("built FAISS index: %d chunks → %s", len(chunks), INDEX_PATH)


def _ensure_loaded() -> None:
    global _index, _chunks
    if _index is not None and _chunks is not None:
        return
    if not INDEX_PATH.exists() or not META_PATH.exists():
        build_index()
    _index = faiss.read_index(str(INDEX_PATH))
    _chunks = [Chunk(**row) for row in _iter_meta()]


def _iter_meta() -> Iterable[dict]:
    with META_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            yield {
                "chunk_id": row["chunk_id"],
                "kind": row["kind"],
                "title": row["title"],
                "text": row["text"],
                "meta": row.get("meta", {}),
            }


@dataclass
class Hit:
    chunk: Chunk
    score: float


def search(query: str, k: int = 5, kinds: list[str] | None = None) -> list[Hit]:
    """Top-k retrieval. Optional `kinds` filter to restrict by chunk type."""
    _ensure_loaded()
    assert _index is not None and _chunks is not None

    q = _embed([query])
    # Over-fetch when filtering so we still return k results.
    fetch = k * 3 if kinds else k
    scores, ids = _index.search(q, fetch)
    hits: list[Hit] = []
    for score, idx in zip(scores[0], ids[0], strict=False):
        if idx < 0:
            continue
        chunk = _chunks[idx]
        if kinds and chunk.kind not in kinds:
            continue
        hits.append(Hit(chunk=chunk, score=float(score)))
        if len(hits) >= k:
            break
    return hits


__all__ = [
    "Chunk",
    "Hit",
    "build_index",
    "framework_clause_resolves",
    "list_frameworks",
    "list_past_responses",
    "list_policies",
    "policy_exists",
    "search",
]
