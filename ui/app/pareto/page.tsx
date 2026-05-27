import Link from "next/link";
import { api, type OptRun } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ParetoIndex() {
  let opts: OptRun[] = [];
  try {
    opts = await api.listOptRuns();
  } catch {}
  return (
    <div className="max-w-[1280px] mx-auto px-10 py-12">
      <header className="border-b border-line pb-6">
        <h1 className="font-display text-display-md tracking-tight">Pareto frontier</h1>
        <p className="mt-2 text-ink-secondary">
          Pick an optimization run to see the frontier shift.
        </p>
      </header>
      <ul className="mt-6 space-y-2">
        {opts.map((o) => (
          <li key={o.id} className="border border-line rounded-md p-4 hover:bg-canvas-elevated">
            <Link href={`/pareto/${o.id}`} className="flex items-baseline justify-between">
              <span className="font-mono tnum text-improved">{o.id}</span>
              <span className="font-mono tnum text-ui-sm text-ink-muted">
                {o.example} · {o.iter_count} iters
              </span>
            </Link>
          </li>
        ))}
        {opts.length === 0 && <li className="text-ink-muted">No optimizations yet.</li>}
      </ul>
    </div>
  );
}
