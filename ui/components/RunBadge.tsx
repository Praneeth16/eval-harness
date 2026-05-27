import clsx from "clsx";

const STATUS_MAP: Record<
  string,
  { label: string; dot: string; text: string; bg: string }
> = {
  running:    { label: "running",    dot: "bg-state-info",  text: "text-state-info",  bg: "bg-state-info/10  border-state-info/40" },
  pending:    { label: "pending",    dot: "bg-ink-muted",   text: "text-ink-muted",   bg: "bg-canvas-elevated border-line"          },
  done:       { label: "passed",     dot: "bg-state-success", text: "text-state-success", bg: "bg-state-success/10 border-state-success/40" },
  failed:     { label: "failed",     dot: "bg-state-error", text: "text-state-error", bg: "bg-state-error/10 border-state-error/40" },
  optimizing: { label: "optimizing", dot: "bg-improved animate-pulse", text: "text-improved", bg: "bg-improved/10 border-improved/40" },
  cancelled:  { label: "cancelled",  dot: "bg-ink-muted",   text: "text-ink-muted",   bg: "bg-canvas-elevated border-line"          },
};

export function RunBadge({ status }: { status: string }) {
  const cfg = STATUS_MAP[status] || STATUS_MAP.pending;
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 font-mono tnum text-ui-sm",
        cfg.bg,
        cfg.text,
      )}
    >
      <span className={clsx("h-1.5 w-1.5 rounded-full", cfg.dot)} />
      <span>{cfg.label}</span>
    </span>
  );
}
