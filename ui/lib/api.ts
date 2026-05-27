/**
 * Thin fetch wrappers around the eval-harness FastAPI.
 *
 * Calls flow through Next's rewrite at /api/* (defined in next.config.ts)
 * so local dev and any deploy point to the same code path.
 */

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    ...init,
  });
  if (!res.ok) {
    throw new Error(`API ${res.status} on ${path}`);
  }
  return res.json() as Promise<T>;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    cache: "no-store",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`API ${res.status} on ${path}`);
  }
  return res.json() as Promise<T>;
}

// ── Types mirror api/schemas.py (kept loose so server can evolve faster than UI)

export type EvalRun = {
  id: string;
  example: string;
  dataset: string;
  model: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  total_cost_usd: number;
  total_latency_ms: number;
  notes: string | null;
  trace_count: number;
  pass_count: number;
  fail_count: number;
};

export type Score = {
  scorer_name: string;
  clear_axis: string;
  value: number;
  passed: boolean;
  details: Record<string, unknown>;
};

export type Trace = {
  id: string;
  eval_run_id: string;
  question_id: string;
  status: string;
  cost_usd: number;
  latency_ms: number;
  mlflow_trace_uri: string | null;
  input: Record<string, unknown>;
  output: Record<string, unknown> | null;
  scores: Score[];
};

export type Cluster = {
  id: string;
  eval_run_id: string;
  clear_axis: string;
  label: string;
  size: number;
  sample_trace_ids: string[];
  summary: string | null;
};

export type ParetoCandidate = {
  candidate_id: string;
  label: string;
  parent_id: string | null;
  objectives: Record<string, number>;
  rationale?: string;
};

export type Pareto = {
  opt_run_id: string;
  objectives: string[];
  candidates: ParetoCandidate[];
  frontier_ids: string[];
  winner_id: string;
  baseline_id: string;
  headline_metrics?: Record<string, unknown> | null;
};

export type PromptDiff = {
  opt_run_id: string;
  baseline: Record<string, string | boolean | number>;
  tuned: Record<string, string | boolean | number>;
  rationale: string[];
};

export type OptRun = {
  id: string;
  example: string;
  optimizer: string;
  status: string;
  iter_count: number;
  source_eval_run_id: string;
  started_at: string;
  finished_at: string | null;
  pareto: Pareto | null;
  baseline_prompt_path: string | null;
  winner_prompt_path: string | null;
};

export type PortabilityRow = {
  model: string;
  family: string;
  scores: Record<string, number>;
  notes?: string;
};

export type Portability = {
  opt_run_id: string;
  rows: PortabilityRow[];
};

export const api = {
  health: () => getJson<{ status: string }>("/health"),
  latest: () =>
    getJson<{ latest_run_id: string | null; latest_opt_id: string | null }>("/latest"),

  listRuns: (limit = 50) => getJson<EvalRun[]>(`/runs?limit=${limit}`),
  getRun: (id: string) => getJson<EvalRun>(`/runs/${id}`),
  listTraces: (runId: string) => getJson<Trace[]>(`/runs/${runId}/traces`),
  getTrace: (id: string) => getJson<Trace>(`/traces/${id}`),

  listClusters: (runId: string) => getJson<Cluster[]>(`/clusters/${runId}`),
  buildClusters: (runId: string) => postJson<Cluster[]>(`/clusters/${runId}/build`, {}),

  listOptRuns: () => getJson<OptRun[]>("/opt-runs"),
  getOptRun: (id: string) => getJson<OptRun>(`/opt-runs/${id}`),
  getPareto: (id: string) => getJson<Pareto>(`/pareto/${id}`),
  getPromptDiff: (id: string) => getJson<PromptDiff>(`/prompt-diff/${id}`),
  getPortability: (id: string) => getJson<Portability>(`/portability/${id}`),

  kickoffQuill: (body: {
    golden?: string;
    model?: string;
    use_tuned_prompts?: boolean;
    notes?: string;
  }) => postJson<{ status: string }>("/examples/quill/run", body),
};
