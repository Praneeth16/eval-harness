import Link from "next/link";
import { api, type OptRun } from "@/lib/api";
import { RunBadge } from "@/components/RunBadge";
import { relativeTime } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function OptimizePage() {
  let opts: OptRun[] = [];
  let err: string | null = null;
  try {
    opts = await api.listOptRuns();
  } catch (e) {
    err = (e as Error).message;
  }

  return (
    <div className="max-w-[1280px] mx-auto px-10 py-12">
      <header className="border-b border-line pb-6">
        <div className="font-mono tnum text-ui-sm text-ink-muted uppercase tracking-widest">
          loop
        </div>
        <h1 className="mt-1 font-display text-display-md tracking-tight">
          Self-evolving optimizations
        </h1>
        <p className="mt-2 text-ink-secondary text-ui max-w-[60ch]">
          GEPA pulls failed traces, reflects, mutates the prompt set, evaluates
          each candidate, and Pareto-selects across correctness, groundedness,
          safety, cost, and latency. Each run below produced a tuned prompt
          that dominates its baseline.
        </p>
      </header>

      {err && (
        <div className="mt-6 rounded-md border border-state-error/40 bg-state-error/10 px-4 py-3 text-state-error">
          {err}
        </div>
      )}

      <section className="mt-8 space-y-3">
        {opts.length === 0 && !err && (
          <div className="rounded-md border border-dashed border-line p-8 text-center text-ink-muted">
            <div className="font-mono tnum text-ui-sm uppercase tracking-widest">
              No optimizations yet
            </div>
            <p className="mt-2">
              Run <code className="text-improved">scripts/prebake.py</code> to
              materialize baseline + tuned + Pareto artifacts.
            </p>
          </div>
        )}
        {opts.map((o) => (
          <article
            key={o.id}
            className="rounded-md border border-line bg-canvas-surface/40 p-5 hover:bg-canvas-elevated"
          >
            <div className="flex items-baseline justify-between gap-4">
              <div>
                <Link
                  href={`/pareto/${o.id}`}
                  className="font-mono tnum text-improved hover:underline"
                >
                  {o.id}
                </Link>
                <div className="mt-1 font-mono tnum text-ui-sm text-ink-muted">
                  {o.optimizer.toUpperCase()} · {o.example} · {o.iter_count} iters
                </div>
              </div>
              <div className="flex items-center gap-3">
                <RunBadge status={o.status} />
                <span className="font-mono tnum text-ui-sm text-ink-muted">
                  {relativeTime(o.started_at)}
                </span>
              </div>
            </div>
            <div className="mt-4 flex flex-wrap gap-3 text-ui">
              <Link
                href={`/pareto/${o.id}`}
                className="font-mono tnum px-3 py-1 rounded-sm border border-improved/40 text-improved hover:bg-improved/10"
              >
                Pareto →
              </Link>
              <Link
                href={`/prompt-diff/${o.id}`}
                className="font-mono tnum px-3 py-1 rounded-sm border border-line text-ink-secondary hover:bg-canvas-elevated"
              >
                Prompt diff
              </Link>
              <Link
                href={`/portability/${o.id}`}
                className="font-mono tnum px-3 py-1 rounded-sm border border-line text-ink-secondary hover:bg-canvas-elevated"
              >
                Portability
              </Link>
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}
