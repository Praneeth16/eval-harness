import Link from "next/link";
import { api, type EvalRun } from "@/lib/api";
import { RunBadge } from "@/components/RunBadge";
import { fmtCostUSD, fmtMs, fmtPercent, relativeTime } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function RunsPage() {
  let runs: EvalRun[] = [];
  let err: string | null = null;
  try {
    runs = await api.listRuns(100);
  } catch (e) {
    err = (e as Error).message;
  }

  return (
    <div className="max-w-[1280px] mx-auto px-10 py-12">
      <header className="flex items-baseline justify-between border-b border-line pb-6">
        <div>
          <div className="font-mono tnum text-ui-sm text-ink-muted uppercase tracking-widest">
            section
          </div>
          <h1 className="mt-1 font-display text-display-md tracking-tight">Eval runs</h1>
          <p className="mt-2 text-ink-secondary text-ui">
            Every golden-set pass. Failures cluster by CLEAR axis.
          </p>
        </div>
        <span className="font-mono tnum text-ui text-ink-muted">{runs.length} runs</span>
      </header>

      {err && (
        <div className="mt-6 rounded-md border border-state-error/40 bg-state-error/10 px-4 py-3 text-ui text-state-error">
          {err}
        </div>
      )}

      <div className="mt-6 overflow-x-auto rounded-md border border-line bg-canvas-surface/40">
        <table className="w-full text-ui tnum">
          <thead>
            <tr className="text-ui-sm text-ink-muted uppercase tracking-widest">
              <Th>run</Th>
              <Th>example</Th>
              <Th>dataset</Th>
              <Th>model</Th>
              <Th align="right">pass</Th>
              <Th align="right">cost</Th>
              <Th align="right">latency</Th>
              <Th>status</Th>
              <Th align="right">started</Th>
            </tr>
          </thead>
          <tbody>
            {runs.length === 0 && !err && (
              <tr>
                <td colSpan={9} className="py-12 text-center text-ink-muted">
                  No runs yet. Kick off Quill from <code>/optimize</code>.
                </td>
              </tr>
            )}
            {runs.map((r) => (
              <tr key={r.id} className="border-t border-line hover:bg-canvas-elevated/60">
                <Td>
                  <Link href={`/runs/${r.id}`} className="font-mono text-improved hover:underline">
                    {r.id}
                  </Link>
                </Td>
                <Td className="text-ink-secondary">{r.example}</Td>
                <Td className="text-ink-muted font-mono">{r.dataset}</Td>
                <Td className="text-ink-muted font-mono">{r.model}</Td>
                <Td align="right" className="font-mono">
                  {r.trace_count > 0 ? fmtPercent(r.pass_count / r.trace_count) : "—"}
                  <span className="ml-1 text-ink-muted">({r.pass_count}/{r.trace_count})</span>
                </Td>
                <Td align="right" className="font-mono">{fmtCostUSD(r.total_cost_usd)}</Td>
                <Td align="right" className="font-mono">{fmtMs(r.total_latency_ms)}</Td>
                <Td><RunBadge status={r.status} /></Td>
                <Td align="right" className="text-ink-muted">{relativeTime(r.started_at)}</Td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Th({ children, align }: { children: React.ReactNode; align?: "right" }) {
  return (
    <th
      className={`px-4 py-3 text-${align ?? "left"} font-medium text-ui-sm text-ink-muted uppercase tracking-widest`}
    >
      {children}
    </th>
  );
}

function Td({
  children,
  align,
  className = "",
}: {
  children: React.ReactNode;
  align?: "right";
  className?: string;
}) {
  return (
    <td className={`px-4 py-3 text-${align ?? "left"} ${className}`}>{children}</td>
  );
}
