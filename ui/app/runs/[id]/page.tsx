import Link from "next/link";
import { api, type EvalRun, type Trace } from "@/lib/api";
import { ScoreChip } from "@/components/ScoreChip";
import { RunBadge } from "@/components/RunBadge";
import { LiePanel } from "@/components/LiePanel";
import { fmtCostUSD, fmtMs, fmtPercent, relativeTime } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function RunDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let run: EvalRun | null = null;
  let traces: Trace[] = [];
  let err: string | null = null;
  try {
    run = await api.getRun(id);
    traces = await api.listTraces(id);
  } catch (e) {
    err = (e as Error).message;
  }

  return (
    <div className="max-w-[1280px] mx-auto px-10 py-12">
      <header className="border-b border-line pb-6">
        <Link href="/runs" className="text-ui-sm text-ink-muted hover:text-ink-primary">
          ← runs
        </Link>
        <div className="mt-2 flex items-baseline justify-between">
          <div>
            <h1 className="font-display text-display-md tracking-tight">
              Run <span className="font-mono tnum text-improved">{id}</span>
            </h1>
            {run && (
              <div className="mt-2 flex items-center gap-3 font-mono tnum text-ui text-ink-muted">
                <span>{run.example}</span>
                <span>·</span>
                <span>{run.dataset}</span>
                <span>·</span>
                <span>{run.model}</span>
                <span>·</span>
                <span>{relativeTime(run.started_at)}</span>
                <RunBadge status={run.status} />
              </div>
            )}
          </div>
        </div>
      </header>

      {err && (
        <div className="mt-6 rounded-md border border-state-error/40 bg-state-error/10 px-4 py-3 text-ui text-state-error">
          {err}
        </div>
      )}

      {run && (
        <section className="mt-6 grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Stat label="pass rate"
            value={run.trace_count ? fmtPercent(run.pass_count / run.trace_count) : "—"}
            sub={`${run.pass_count}/${run.trace_count}`}
          />
          <Stat label="total cost" value={fmtCostUSD(run.total_cost_usd)} />
          <Stat label="total latency" value={fmtMs(run.total_latency_ms)} />
          <Stat
            label="avg per trace"
            value={
              run.trace_count
                ? fmtCostUSD(run.total_cost_usd / run.trace_count)
                : "—"
            }
            sub={
              run.trace_count
                ? fmtMs(run.total_latency_ms / run.trace_count)
                : undefined
            }
          />
        </section>
      )}

      <section className="mt-10">
        <h2 className="font-display text-title">Traces</h2>
        <p className="text-ink-secondary text-ui mt-1">
          Each row is a question. Score chips show CLEAR-S axes. Open in MLflow
          for the full trace tree.
        </p>

        <div className="mt-4 space-y-3">
          {traces.length === 0 && (
            <p className="text-ink-muted">No traces in this run.</p>
          )}
          {traces.map((t) => {
            const failed = t.scores.some((s) => !s.passed);
            const out = (t.output as { answer?: string } | null)?.answer ?? "";
            const inp = (t.input as { question?: string }).question ?? "";
            return (
              <article
                key={t.id}
                className={`rounded-md border ${failed ? "border-state-error/30" : "border-line"} bg-canvas-surface/40 p-4`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="font-mono tnum text-ui-sm text-ink-muted">
                      <span className="text-ink-secondary">{t.question_id}</span>
                      <span className="mx-2">·</span>
                      <span>{t.id}</span>
                      <span className="mx-2">·</span>
                      <span>{fmtCostUSD(t.cost_usd)}</span>
                      <span className="mx-2">·</span>
                      <span>{fmtMs(t.latency_ms)}</span>
                    </div>
                    <div className="mt-1 text-ink-primary text-ui">{inp}</div>
                    {out && (
                      <div className="mt-2 code-pane bg-canvas p-3 rounded-sm text-ink-secondary whitespace-pre-wrap">
                        {out}
                      </div>
                    )}
                  </div>
                  {t.mlflow_trace_uri && (
                    <a
                      href={t.mlflow_trace_uri}
                      target="_blank"
                      rel="noreferrer"
                      className="shrink-0 font-mono tnum text-ui-sm text-improved hover:underline"
                    >
                      open trace ↗
                    </a>
                  )}
                </div>

                <div className="mt-3 flex flex-wrap gap-1.5">
                  {t.scores.map((s, i) => (
                    <ScoreChip
                      key={i}
                      axis={s.clear_axis}
                      value={s.value}
                      passed={s.passed}
                      label={s.scorer_name}
                    />
                  ))}
                </div>

                {failed && (
                  <LiePanel
                    scores={t.scores}
                    retrieved={
                      ((t.output as { retrieved?: unknown[] } | null)?.retrieved as
                        | Array<{
                            chunk_id?: string;
                            kind?: string;
                            title?: string;
                            score?: number;
                          }>
                        | undefined) ?? []
                    }
                  />
                )}
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}

function Stat({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="rounded-md border border-line bg-canvas-surface/40 p-4">
      <div className="font-mono tnum text-ui-sm text-ink-muted uppercase tracking-widest">
        {label}
      </div>
      <div className="mt-1 font-mono tnum text-display-md">{value}</div>
      {sub && <div className="font-mono tnum text-ui-sm text-ink-muted mt-1">{sub}</div>}
    </div>
  );
}
