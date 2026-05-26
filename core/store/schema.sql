-- eval-harness local store. Mirror of the SQLAlchemy ORM in core/store/models.py.
-- Source of truth is the ORM (Alembic-free for now — we recreate cleanly on dev).
-- This file exists as documentation + for quick `sqlite3 < schema.sql` bootstrap.

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- ── Eval runs (one per "run evals against dataset" invocation) ──
CREATE TABLE IF NOT EXISTS eval_run (
    id              TEXT PRIMARY KEY,
    example         TEXT    NOT NULL,
    dataset         TEXT    NOT NULL,
    model           TEXT    NOT NULL,
    status          TEXT    NOT NULL,                -- pending|running|done|failed|cancelled
    started_at      TEXT    NOT NULL,
    finished_at     TEXT,
    config_json     TEXT,
    total_cost_usd  REAL    NOT NULL DEFAULT 0,
    total_latency_ms INTEGER NOT NULL DEFAULT 0,
    notes           TEXT
);

-- ── Traces (one per question evaluated within a run) ──
CREATE TABLE IF NOT EXISTS trace (
    id                  TEXT PRIMARY KEY,             -- MLflow trace id
    eval_run_id         TEXT NOT NULL,
    question_id         TEXT NOT NULL,
    input_json          TEXT NOT NULL,
    output_json         TEXT,
    status              TEXT NOT NULL,                -- ok|error
    mlflow_trace_uri    TEXT,                         -- deep link to MLflow UI
    started_at          TEXT NOT NULL,
    finished_at         TEXT,
    cost_usd            REAL NOT NULL DEFAULT 0,
    latency_ms          INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (eval_run_id) REFERENCES eval_run(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_trace_eval_run ON trace(eval_run_id);
CREATE INDEX IF NOT EXISTS idx_trace_question ON trace(question_id);

-- ── Scores (many per trace; one per scorer that fired) ──
CREATE TABLE IF NOT EXISTS score (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id        TEXT    NOT NULL,
    scorer_name     TEXT    NOT NULL,
    clear_axis      TEXT    NOT NULL,                 -- correctness|latency|execution|adherence|relevance|safety|cost
    value           REAL    NOT NULL,                 -- normalized 0-1 (or pass/fail as 0/1)
    passed          INTEGER NOT NULL,                 -- bool 0/1
    details_json    TEXT,
    created_at      TEXT    NOT NULL,
    FOREIGN KEY (trace_id) REFERENCES trace(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_score_trace ON score(trace_id);
CREATE INDEX IF NOT EXISTS idx_score_axis ON score(clear_axis);
CREATE INDEX IF NOT EXISTS idx_score_passed ON score(passed);

-- ── Clusters (CLEAR-axis groupings of failed traces) ──
CREATE TABLE IF NOT EXISTS cluster (
    id                      TEXT PRIMARY KEY,
    eval_run_id             TEXT NOT NULL,
    clear_axis              TEXT NOT NULL,
    label                   TEXT NOT NULL,
    size                    INTEGER NOT NULL,
    sample_trace_ids_json   TEXT NOT NULL,
    summary                 TEXT,
    created_at              TEXT NOT NULL,
    FOREIGN KEY (eval_run_id) REFERENCES eval_run(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_cluster_eval_run ON cluster(eval_run_id);

-- ── Optimizer runs (GEPA invocations, Pareto frontiers) ──
CREATE TABLE IF NOT EXISTS opt_run (
    id                      TEXT PRIMARY KEY,
    source_eval_run_id      TEXT NOT NULL,
    example                 TEXT NOT NULL,
    optimizer               TEXT NOT NULL,            -- "gepa"
    status                  TEXT NOT NULL,
    iter_count              INTEGER NOT NULL DEFAULT 0,
    pareto_json             TEXT,                     -- frontier points
    winner_prompt_path      TEXT,
    baseline_prompt_path    TEXT,
    started_at              TEXT NOT NULL,
    finished_at             TEXT,
    config_json             TEXT,
    FOREIGN KEY (source_eval_run_id) REFERENCES eval_run(id)
);
CREATE INDEX IF NOT EXISTS idx_opt_run_source ON opt_run(source_eval_run_id);
