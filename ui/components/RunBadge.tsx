import clsx from "clsx";

const STATUS_MAP: Record<
  string,
  { label: string; dot: string; text: string; bg: string }
> = {
  running:    { label: "running",    dot: "bg-state-info",  text: "text-state-info",  bg: "bg-state-info/10  border-state-info/40" },
  pending:    { label: "pending",    dot: "bg-ink-muted",   text: "text-ink-muted",   bg: "bg-canvas-elevated border-line"          },
  passed:     { label: "passed",     dot: "bg-state-success", text: "text-state-success", bg: "bg-state-success/10 border-state-success/40" },
  partial:    { label: "partial",    dot: "bg-clear-execution", text: "text-clear-execution", bg: "bg-clear-execution/10 border-clear-execution/40" },
  failed:     { label: "failed",     dot: "bg-state-error", text: "text-state-error", bg: "bg-state-error/10 border-state-error/40" },
  optimizing: { label: "optimizing", dot: "bg-improved animate-pulse", text: "text-improved", bg: "bg-improved/10 border-improved/40" },
  cancelled:  { label: "cancelled",  dot: "bg-ink-muted",   text: "text-ink-muted",   bg: "bg-canvas-elevated border-line"          },
};

function resolveStatus(
  status: string,
  passCount?: number,
  traceCount?: number,
): string {
  if (status !== "done") return status;
  if (typeof passCount !== "number" || typeof traceCount !== "number" || traceCount === 0) {
    return "passed";
  }
  if (passCount === traceCount) return "passed";
  if (passCount === 0) return "failed";
  return "partial";
}

export function RunBadge({
  status,
  passCount,
  traceCount,
}: {
  status: string;
  passCount?: number;
  traceCount?: number;
}) {
  const resolved = resolveStatus(status, passCount, traceCount);
  const cfg = STATUS_MAP[resolved] || STATUS_MAP.pending;
  const label =
    resolved === "partial" &&
    typeof passCount === "number" &&
    typeof traceCount === "number"
      ? `${passCount}/${traceCount} passed`
      : cfg.label;
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 font-mono tnum text-ui-sm",
        cfg.bg,
        cfg.text,
      )}
    >
      <span className={clsx("h-1.5 w-1.5 rounded-full", cfg.dot)} />
      <span>{label}</span>
    </span>
  );
}
