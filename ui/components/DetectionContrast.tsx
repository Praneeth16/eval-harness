import type { Detection, DetectionCell } from "@/lib/api";

const AXIS_COLOR: Record<string, string> = {
  correctness: "text-clear-correctness",
  latency: "text-clear-latency",
  execution: "text-clear-execution",
  adherence: "text-clear-adherence",
  relevance: "text-clear-relevance",
  safety: "text-clear-safety",
  cost: "text-clear-cost",
};

function CellView({ cell, harness }: { cell: DetectionCell; harness: boolean }) {
  // Naive layers (vibe / string) wave failures through → muted. The harness
  // column is where mint fires: it caught what the others missed.
  const styles: Record<DetectionCell["verdict"], { glyph: string; cls: string }> = {
    pass: { glyph: "○", cls: "text-ink-muted" },
    na: { glyph: "—", cls: "text-ink-muted/60" },
    caught: { glyph: "●", cls: "text-improved" },
    block: { glyph: "●", cls: "text-improved" },
    flag: { glyph: "▲", cls: "text-state-warn" },
  };
  const s = styles[cell.verdict];
  return (
    <div
      className={`h-full px-4 py-3 ${
        harness && (cell.verdict === "caught" || cell.verdict === "block")
          ? "bg-improved-soft"
          : ""
      }`}
    >
      <div className={`flex items-center gap-2 font-mono tnum text-ui ${s.cls}`}>
        <span aria-hidden>{s.glyph}</span>
        <span>{cell.label}</span>
      </div>
      {cell.note && (
        <div className="mt-1 text-ui-sm text-ink-muted leading-snug">{cell.note}</div>
      )}
    </div>
  );
}

export function DetectionContrast({
  data,
  compact = false,
}: {
  data: Detection;
  compact?: boolean;
}) {
  const cols = data.layers.length;
  return (
    <section className="rounded-xl border border-line bg-canvas-surface/40 overflow-hidden">
      {!compact && (
        <header className="px-6 pt-6 pb-4 border-b border-line">
          <h2 className="font-display text-display-md tracking-tight">{data.title}</h2>
          {data.subtitle && (
            <p className="mt-2 text-ink-secondary max-w-[70ch]">{data.subtitle}</p>
          )}
        </header>
      )}

      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="text-ui-sm uppercase tracking-widest">
              <th className="w-[28%] px-4 py-3 text-left font-medium text-ink-muted">
                failure
              </th>
              {data.layers.map((l) => (
                <th
                  key={l.key}
                  className={`px-4 py-3 text-left font-medium ${
                    l.kind === "harness" ? "text-improved" : "text-ink-muted"
                  }`}
                >
                  {l.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row, i) => (
              <tr key={i} className="border-t border-line align-top">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    {row.axis && (
                      <span
                        className={`text-ui-sm font-mono ${
                          AXIS_COLOR[row.axis] ?? "text-ink-muted"
                        }`}
                      >
                        {row.axis}
                      </span>
                    )}
                  </div>
                  <div className="mt-0.5 text-ui text-ink-primary">{row.scenario}</div>
                  {!compact && row.detail && (
                    <div className="mt-1 text-ui-sm text-ink-muted leading-snug max-w-[40ch]">
                      {row.detail}
                    </div>
                  )}
                </td>
                {row.cells.slice(0, cols).map((cell, j) => (
                  <td
                    key={j}
                    className={`p-0 border-l border-line ${
                      data.layers[j]?.kind === "harness" ? "border-l-improved/30" : ""
                    }`}
                  >
                    <CellView cell={cell} harness={data.layers[j]?.kind === "harness"} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {!compact && data.footnote && (
        <footer className="px-6 py-4 border-t border-line text-ui-sm text-ink-muted">
          {data.footnote}
        </footer>
      )}
    </section>
  );
}
