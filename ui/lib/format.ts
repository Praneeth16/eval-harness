/**
 * Number / time formatters for the data-dense cells in the app.
 * Everything that renders here is wrapped in `.tnum` somewhere up the tree.
 */

export function fmtPercent(value: number, digits = 0): string {
  if (!Number.isFinite(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

export function fmtCostUSD(value: number): string {
  if (!Number.isFinite(value)) return "—";
  if (value < 0.01) return `$${value.toFixed(4)}`;
  if (value < 1) return `$${value.toFixed(3)}`;
  return `$${value.toFixed(2)}`;
}

export function fmtMs(value: number): string {
  if (!Number.isFinite(value)) return "—";
  if (value < 1000) return `${Math.round(value)} ms`;
  return `${(value / 1000).toFixed(2)} s`;
}

export function fmtDelta(value: number, digits = 1): string {
  if (!Number.isFinite(value)) return "—";
  const arrow = value > 0 ? "▲" : value < 0 ? "▼" : "·";
  const sign = value > 0 ? "+" : value < 0 ? "−" : "";
  return `${arrow} ${sign}${Math.abs(value).toFixed(digits)}`;
}

export function fmtScore(value: number): string {
  if (!Number.isFinite(value)) return "—";
  return value.toFixed(2);
}

export function relativeTime(iso: string): string {
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return iso;
  const diff = (Date.now() - t) / 1000;
  if (diff < 60) return `${Math.round(diff)}s ago`;
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
  if (diff < 86_400) return `${Math.round(diff / 3600)}h ago`;
  return `${Math.round(diff / 86_400)}d ago`;
}
