import Link from "next/link";
import { api, type Portability } from "@/lib/api";

export const dynamic = "force-dynamic";

const AXIS_ORDER = [
  "correctness",
  "relevance",
  "execution",
  "safety",
  "adherence",
  "cost",
  "latency",
];

export default async function PortabilityPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let data: Portability | null = null;
  let err: string | null = null;
  try {
    data = await api.getPortability(id);
  } catch (e) {
    err = (e as Error).message;
  }

  return (
    <div className="max-w-[1280px] mx-auto px-10 py-12">
      <header className="border-b border-line pb-6">
        <Link
          href={`/pareto/${id}`}
          className="text-ui-sm text-ink-muted hover:text-ink-primary"
        >
          ← Pareto {id}
        </Link>
        <h1 className="mt-2 font-display text-display-md tracking-tight">
          Cross-model portability
        </h1>
        <p className="mt-2 text-ink-secondary max-w-[60ch]">
          The tuned prompt re-evaluated against Llama-3.3 70B,
          Claude-Sonnet-4-6, and Qwen-2.5 72B on the ISO 27001 holdout. A
          regression on <code>policy_exists_called_before_cite</code> blocks
          deploy.
        </p>
      </header>

      {err && (
        <div className="mt-6 rounded-md border border-state-error/40 bg-state-error/10 px-4 py-3 text-state-error">
          {err}
        </div>
      )}

      {data && (
        <section className="mt-8 overflow-x-auto rounded-md border border-line bg-canvas-surface/40">
          <table className="w-full text-ui tnum">
            <thead>
              <tr className="text-ui-sm text-ink-muted uppercase tracking-widest">
                <th className="px-4 py-3 text-left">model</th>
                <th className="px-4 py-3 text-left">family</th>
                {AXIS_ORDER.map((a) => (
                  <th key={a} className="px-4 py-3 text-right">
                    {a}
                  </th>
                ))}
                <th className="px-4 py-3 text-left">notes</th>
              </tr>
            </thead>
            <tbody>
              {data.rows.map((r) => (
                <tr key={r.model} className="border-t border-line">
                  <td className="px-4 py-3 font-mono">{r.model}</td>
                  <td className="px-4 py-3 text-ink-muted font-mono">{r.family}</td>
                  {AXIS_ORDER.map((a) => {
                    const v = r.scores?.[a];
                    const ok = typeof v === "number" && v >= 0.8;
                    return (
                      <td
                        key={a}
                        className={`px-4 py-3 text-right font-mono ${
                          ok ? "text-improved" : "text-ink-secondary"
                        }`}
                      >
                        {typeof v === "number" ? v.toFixed(2) : "—"}
                      </td>
                    );
                  })}
                  <td className="px-4 py-3 text-ink-muted">{r.notes ?? ""}</td>
                </tr>
              ))}
              {data.rows.length === 0 && (
                <tr>
                  <td colSpan={AXIS_ORDER.length + 3} className="py-8 text-center text-ink-muted">
                    No portability data — run the prebake script.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
