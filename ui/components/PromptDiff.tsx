"use client";

import { useMemo } from "react";

/**
 * Side-by-side prompt diff. Geist Mono code. Mint additions, red removals.
 * Inline rationale callouts are rendered in Fraunces 14px from
 * `pareto.candidates[*].rationale`.
 */
export function PromptDiff({
  baseline,
  tuned,
  rationale,
}: {
  baseline: Record<string, string | number | boolean>;
  tuned: Record<string, string | number | boolean>;
  rationale: string[];
}) {
  const keys = useMemo(() => {
    const set = new Set([...Object.keys(baseline), ...Object.keys(tuned)]);
    // Show drafter first — most important, most changed.
    const order = [
      "DRAFTER_PROMPT",
      "drafter",
      "CLASSIFIER_PROMPT",
      "classifier",
      "GAP_DETECTOR_PROMPT",
      "gap_detector",
      "RISK_TIERER_PROMPT",
      "risk_tierer",
      "USE_VERIFICATION_TOOLS",
      "use_verification_tools",
    ];
    return [
      ...order.filter((k) => set.has(k)),
      ...[...set].filter((k) => !order.includes(k)),
    ];
  }, [baseline, tuned]);

  return (
    <div className="space-y-12">
      {rationale.length > 0 && (
        <aside className="rounded-lg border border-line bg-canvas-surface/40 p-5">
          <div className="font-mono tnum text-ui-sm text-ink-muted uppercase tracking-wider">
            What GEPA changed
          </div>
          <ul className="mt-3 space-y-2 font-display text-body-lg leading-snug">
            {rationale.map((r, i) => (
              <li key={i} className="flex gap-3">
                <span className="text-improved font-mono tnum">{String(i + 1).padStart(2, "0")}</span>
                <span>{r}</span>
              </li>
            ))}
          </ul>
        </aside>
      )}

      {keys.map((k) => {
        const left = String(baseline[k] ?? "");
        const right = String(tuned[k] ?? "");
        if (!left && !right) return null;
        if (left === right) return null;
        return (
          <section key={k}>
            <header className="flex items-baseline justify-between border-b border-line pb-2">
              <h3 className="font-display text-title">{prettyKey(k)}</h3>
              <span className="font-mono tnum text-ui-sm text-ink-muted">
                {wordCount(left)} → {wordCount(right)} words
              </span>
            </header>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-3">
              <DiffSide title="baseline" body={left} side="left" />
              <DiffSide title="tuned" body={right} side="right" />
            </div>
          </section>
        );
      })}
    </div>
  );
}

function DiffSide({
  title,
  body,
  side,
}: {
  title: string;
  body: string;
  side: "left" | "right";
}) {
  const accent =
    side === "right"
      ? "border-improved/40 bg-improved/[0.04]"
      : "border-line bg-canvas-surface";
  return (
    <div className={`rounded-md border ${accent} overflow-hidden`}>
      <div className="flex items-center justify-between px-4 py-2 border-b border-line bg-canvas-elevated/30">
        <span className="font-mono tnum text-ui-sm text-ink-muted uppercase tracking-wider">
          {title}
        </span>
        <span
          className={
            side === "right"
              ? "font-mono tnum text-ui-sm text-improved"
              : "font-mono tnum text-ui-sm text-ink-muted"
          }
        >
          {side === "right" ? "GEPA-tuned" : "before"}
        </span>
      </div>
      <pre className="code-pane p-4 whitespace-pre-wrap break-words text-ink-secondary">
        {body || <span className="text-ink-muted">(no value)</span>}
      </pre>
    </div>
  );
}

function prettyKey(k: string): string {
  return k
    .replace(/_PROMPT$/, "")
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function wordCount(s: string): number {
  return s ? s.trim().split(/\s+/).length : 0;
}
