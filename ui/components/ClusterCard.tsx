import clsx from "clsx";
import type { Cluster } from "@/lib/api";

const AXIS_BORDER: Record<string, string> = {
  correctness: "border-l-clear-correctness",
  latency:     "border-l-clear-latency",
  execution:   "border-l-clear-execution",
  adherence:   "border-l-clear-adherence",
  relevance:   "border-l-clear-relevance",
  safety:      "border-l-clear-safety",
  cost:        "border-l-clear-cost",
};

export function ClusterCard({ cluster }: { cluster: Cluster }) {
  return (
    <article
      className={clsx(
        "border-l-4 border border-line rounded-md bg-canvas-elevated/40 p-5 transition-colors duration-micro hover:bg-canvas-elevated",
        AXIS_BORDER[cluster.clear_axis] || "border-l-line-strong",
      )}
    >
      <div className="flex items-baseline justify-between gap-4">
        <div>
          <h3 className="font-display text-body-lg leading-snug">
            {cluster.label}
          </h3>
          <div className="mt-1 text-ui-sm text-ink-muted font-mono tnum">
            CLEAR axis: <span className="text-ink-secondary">{cluster.clear_axis}</span>
          </div>
        </div>
        <div className="font-mono tnum text-display-md text-ink-primary">
          {cluster.size}
        </div>
      </div>
      {cluster.summary && (
        <p className="mt-3 text-ui text-ink-secondary">{cluster.summary}</p>
      )}
      <div className="mt-4 flex flex-wrap gap-1.5">
        {cluster.sample_trace_ids.map((tid) => (
          <span
            key={tid}
            className="font-mono tnum text-ui-sm px-1.5 py-0.5 rounded-xs bg-canvas-surface border border-line text-ink-muted"
          >
            {tid}
          </span>
        ))}
      </div>
    </article>
  );
}
