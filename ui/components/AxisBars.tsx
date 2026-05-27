"use client";

import type { Pareto } from "@/lib/api";

/**
 * Baseline vs Tuned grouped-bar chart across all CLEAR-S axes.
 *
 * Lives directly beside the Pareto chart on `/pareto/[id]`. The Pareto
 * chart only shows two axes (cost × correctness by default); the bars
 * here back up the narration's "dominates across many axes" claim with
 * a side-by-side per-axis comparison.
 *
 * Tuned bars are mint; baseline bars are graphite. Each axis row also
 * shows the absolute delta in mono numerals.
 */
export function AxisBars({ pareto }: { pareto: Pareto }) {
  const baseline = pareto.candidates.find(
    (c) => c.candidate_id === pareto.baseline_id,
  );
  const winner = pareto.candidates.find(
    (c) => c.candidate_id === pareto.winner_id,
  );
  if (!baseline || !winner) return null;

  // Canonical axis order from the design language.
  const AXES = [
    "correctness",
    "relevance",
    "execution",
    "safety",
    "adherence",
    "cost",
    "latency",
  ] as const;

  const rows = AXES.map((axis) => {
    const b = baseline.objectives?.[axis] ?? 0;
    const t = winner.objectives?.[axis] ?? 0;
    return { axis, b, t, delta: t - b };
  });

  return (
    <div className="rounded-md border border-line bg-canvas-surface/40 p-5">
      <header className="flex items-baseline justify-between mb-4">
        <div>
          <div className="font-mono tnum text-ui-sm text-ink-muted uppercase tracking-widest">
            multi-axis proof
          </div>
          <div className="mt-1 font-display text-title">
            baseline → <span className="text-improved">tuned</span>, all axes
          </div>
        </div>
        <div className="font-mono tnum text-ui-sm text-ink-muted">
          higher = better
        </div>
      </header>

      <div className="space-y-3">
        {rows.map((r) => (
          <div key={r.axis} className="grid grid-cols-12 gap-3 items-center">
            <div className="col-span-3 text-ui font-mono tnum text-ink-secondary">
              {r.axis}
            </div>

            <div className="col-span-7 space-y-1.5">
              <Bar label="baseline" value={r.b} accent={false} />
              <Bar label="tuned" value={r.t} accent={true} />
            </div>

            <div className="col-span-2 text-right font-mono tnum text-ui-sm">
              <span
                className={
                  r.delta > 0.01
                    ? "text-improved"
                    : r.delta < -0.01
                      ? "text-state-error"
                      : "text-ink-muted"
                }
              >
                {r.delta > 0 ? "▲ +" : r.delta < 0 ? "▼ " : "· "}
                {Math.abs(r.delta).toFixed(2)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Bar({
  label,
  value,
  accent,
}: {
  label: string;
  value: number;
  accent: boolean;
}) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  return (
    <div className="flex items-center gap-2">
      <span className="font-mono tnum text-ui-sm text-ink-muted w-16">
        {label}
      </span>
      <div className="flex-1 h-4 bg-canvas-elevated rounded-xs overflow-hidden">
        <div
          className={
            accent
              ? "h-full bg-improved transition-all duration-hero ease-out-soft"
              : "h-full bg-ink-muted/40 transition-all duration-short"
          }
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="font-mono tnum text-ui-sm text-ink-secondary w-12 text-right">
        {value.toFixed(2)}
      </span>
    </div>
  );
}
