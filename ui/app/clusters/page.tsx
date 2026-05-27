import Link from "next/link";
import { api, type EvalRun } from "@/lib/api";
import { relativeTime } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function ClustersIndex() {
  let runs: EvalRun[] = [];
  try {
    runs = await api.listRuns(20);
  } catch {}
  return (
    <div className="max-w-[1280px] mx-auto px-10 py-12">
      <header className="border-b border-line pb-6">
        <h1 className="font-display text-display-md tracking-tight">Failure clusters</h1>
        <p className="mt-2 text-ink-secondary">Pick a run to inspect its clusters.</p>
      </header>
      <ul className="mt-6 space-y-2">
        {runs.map((r) => (
          <li key={r.id} className="border border-line rounded-md p-4 hover:bg-canvas-elevated">
            <Link href={`/clusters/${r.id}`} className="flex items-baseline justify-between">
              <span className="font-mono tnum text-improved">{r.id}</span>
              <span className="font-mono tnum text-ui-sm text-ink-muted">
                {r.example} · {r.dataset} · {relativeTime(r.started_at)}
              </span>
            </Link>
          </li>
        ))}
        {runs.length === 0 && <li className="text-ink-muted">No runs yet.</li>}
      </ul>
    </div>
  );
}
