import Link from "next/link";
import { api, type Pareto } from "@/lib/api";
import { ParetoChart } from "@/components/ParetoChart";
import { AxisBars } from "@/components/AxisBars";

export const dynamic = "force-dynamic";

/**
 * THE CLIMAX.
 *
 * Editorial-asymmetric layout — oversized chart on the right, literary
 * caption + headline-metrics column on the left. The Pareto frontier
 * sweeps in mint over 400ms with `ease-hero`, dots ring-pulse, the page
 * exists to be screenshot-able and remembered.
 *
 * Headline metrics table below the chart references the session-plan
 * numbers: citation correctness 0.58 → 0.91, hallucinated commitment
 * rate 14% → 3%, reviewer-accept 0.43 → 0.78, cost per question
 * $0.021 → $0.011, avg time per questionnaire 47 min → 18 min.
 */
export default async function ParetoHero({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let pareto: Pareto | null = null;
  let err: string | null = null;
  try {
    pareto = await api.getPareto(id);
  } catch (e) {
    err = (e as Error).message;
  }

  const headline =
    (pareto?.headline_metrics as
      | {
          rows?: { metric: string; baseline: string; tuned: string; holdout?: string }[];
        }
      | undefined) || undefined;

  return (
    <div className="bg-hairline min-h-screen">
      <div className="max-w-[1440px] mx-auto px-10 pt-12 pb-24">
        <Link
          href="/optimize"
          className="text-ui-sm text-ink-muted hover:text-ink-primary"
        >
          ← optimize
        </Link>

        <div className="mt-4 grid grid-cols-12 gap-10 items-start">
          <header className="col-span-12 lg:col-span-4 sticky top-8">
            <div className="font-mono tnum text-ui-sm text-improved uppercase tracking-widest">
              the climax
            </div>
            <h1 className="mt-3 font-display text-display-lg leading-[1.05] tracking-tight">
              The baseline ships hallucinations.
              <br />
              <span className="text-improved">GEPA-tuned</span> dominates it.
            </h1>
            <p className="mt-6 font-display text-body-lg text-ink-secondary">
              Each dot is a prompt candidate. Hollow rings are dominated.
              Mint dots are non-dominated — they sit on the frontier no
              competitor beats on every axis. Baseline is the dim graphite
              ring on the lower-left.
            </p>

            <dl className="mt-8 space-y-3 text-ui">
              <Row label="opt run" value={id} mono />
              <Row label="objectives" value={(pareto?.objectives || []).join(" · ")} />
              <Row label="frontier size" value={String(pareto?.frontier_ids.length || 0)} />
              <Row label="winner" value={pareto?.winner_id || "—"} mono />
            </dl>

            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href={`/prompt-diff/${id}`}
                className="font-mono tnum px-3 py-1.5 rounded-sm border border-improved/40 text-improved hover:bg-improved/10"
              >
                prompt diff →
              </Link>
              <Link
                href={`/portability/${id}`}
                className="font-mono tnum px-3 py-1.5 rounded-sm border border-line text-ink-secondary hover:bg-canvas-elevated"
              >
                cross-model holdout →
              </Link>
            </div>
          </header>

          <section className="col-span-12 lg:col-span-8">
            {err && (
              <div className="rounded-md border border-state-error/40 bg-state-error/10 px-4 py-3 text-state-error">
                {err}
              </div>
            )}
            {pareto && (
              <div className="rounded-xl border border-line bg-canvas-surface/40 p-6">
                <ParetoChart pareto={pareto} xAxis="cost" yAxis="correctness" />

                <p className="mt-6 font-display text-body-lg text-ink-secondary max-w-[64ch]">
                  The mint frontier sweeps from origin in 400ms, ease-hero.
                  Every frontier dot ring-pulses on arrival. The only
                  choreographed motion in the app. It only fires when the
                  agent has visibly learned.
                </p>
              </div>
            )}

            {pareto && (
              <div className="mt-6">
                <AxisBars pareto={pareto} />
              </div>
            )}

            {headline?.rows && (
              <div className="mt-8 rounded-xl border border-line bg-canvas-surface/40 p-6">
                <div className="font-mono tnum text-ui-sm text-ink-muted uppercase tracking-widest">
                  Headline metrics
                </div>
                <table className="mt-4 w-full text-ui tnum">
                  <thead>
                    <tr className="text-ui-sm text-ink-muted uppercase tracking-widest">
                      <th className="text-left py-2">metric</th>
                      <th className="text-right py-2">baseline</th>
                      <th className="text-right py-2 text-improved">GEPA-tuned</th>
                      <th className="text-right py-2">holdout</th>
                    </tr>
                  </thead>
                  <tbody>
                    {headline.rows.map((r) => (
                      <tr key={r.metric} className="border-t border-line">
                        <td className="py-3 text-ink-secondary">{r.metric}</td>
                        <td className="py-3 text-right text-ink-muted font-mono">
                          {r.baseline}
                        </td>
                        <td className="py-3 text-right text-improved font-mono">
                          {r.tuned}
                        </td>
                        <td className="py-3 text-right text-ink-secondary font-mono">
                          {r.holdout ?? "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

function Row({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-baseline justify-between border-b border-line pb-2">
      <dt className="font-mono tnum text-ui-sm text-ink-muted uppercase tracking-widest">
        {label}
      </dt>
      <dd className={mono ? "font-mono tnum text-ink-primary" : "text-ink-primary"}>
        {value}
      </dd>
    </div>
  );
}
