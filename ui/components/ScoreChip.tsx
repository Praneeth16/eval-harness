import clsx from "clsx";

const AXIS_COLOR: Record<string, string> = {
  correctness: "text-clear-correctness border-clear-correctness/40 bg-clear-correctness/10",
  latency:     "text-clear-latency     border-clear-latency/40     bg-clear-latency/10",
  execution:   "text-clear-execution   border-clear-execution/40   bg-clear-execution/10",
  adherence:   "text-clear-adherence   border-clear-adherence/40   bg-clear-adherence/10",
  relevance:   "text-clear-relevance   border-clear-relevance/40   bg-clear-relevance/10",
  safety:      "text-clear-safety      border-clear-safety/40      bg-clear-safety/10",
  cost:        "text-clear-cost        border-clear-cost/40        bg-clear-cost/10",
};

const AXIS_LETTER: Record<string, string> = {
  correctness: "C",
  latency: "L",
  execution: "E",
  adherence: "A",
  relevance: "R",
  safety: "S",
  cost: "$",
};

type Props = {
  axis: string;
  value: number;
  passed?: boolean;
  label?: string;
  size?: "sm" | "md";
};

export function ScoreChip({ axis, value, passed, label, size = "sm" }: Props) {
  const cls = AXIS_COLOR[axis] || "text-ink-secondary border-line bg-canvas-surface";
  const padding = size === "sm" ? "px-1.5 py-0.5" : "px-2 py-1";
  const text = size === "sm" ? "text-ui-sm" : "text-ui";
  const showFailRing = passed === false;
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 rounded-sm border font-mono tnum",
        padding,
        text,
        cls,
        showFailRing && "ring-1 ring-state-error/60",
      )}
      title={label}
    >
      <span className="opacity-70">{AXIS_LETTER[axis] ?? "?"}</span>
      <span>{value.toFixed(2)}</span>
    </span>
  );
}

type DeltaProps = { value: number; improved?: boolean };

export function DeltaChip({ value, improved }: DeltaProps) {
  const arrow = value > 0 ? "▲" : value < 0 ? "▼" : "·";
  const sign = value > 0 ? "+" : "";
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 rounded-sm border px-1.5 py-0.5 font-mono tnum text-ui-sm",
        improved
          ? "text-improved border-improved/40 bg-improved/10"
          : "text-state-error border-state-error/40 bg-state-error/10",
      )}
    >
      <span>{arrow}</span>
      <span>{sign}{Math.abs(value).toFixed(2)}</span>
    </span>
  );
}
