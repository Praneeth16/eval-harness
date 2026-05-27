import Link from "next/link";
import { api, type Cluster } from "@/lib/api";
import { ClusterCard } from "@/components/ClusterCard";

export const dynamic = "force-dynamic";

export default async function ClustersForRun({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;
  let clusters: Cluster[] = [];
  let err: string | null = null;
  try {
    clusters = await api.listClusters(runId);
    if (clusters.length === 0) {
      // build on demand
      clusters = await api.buildClusters(runId);
    }
  } catch (e) {
    err = (e as Error).message;
  }

  // Group by axis
  const grouped: Record<string, Cluster[]> = {};
  for (const c of clusters) {
    (grouped[c.clear_axis] = grouped[c.clear_axis] || []).push(c);
  }

  return (
    <div className="max-w-[1280px] mx-auto px-10 py-12">
      <header className="border-b border-line pb-6">
        <Link href={`/runs/${runId}`} className="text-ui-sm text-ink-muted hover:text-ink-primary">
          ← run {runId}
        </Link>
        <h1 className="mt-2 font-display text-display-md tracking-tight">Failure clusters</h1>
        <p className="mt-2 text-ink-secondary">
          Grouped by CLEAR-S axis + scorer pattern. Each card carries up to three
          sample trace IDs you can drop into MLflow.
        </p>
      </header>

      {err && (
        <div className="mt-6 rounded-md border border-state-error/40 bg-state-error/10 px-4 py-3 text-state-error">
          {err}
        </div>
      )}

      <section className="mt-10 space-y-12">
        {Object.entries(grouped).map(([axis, list]) => (
          <div key={axis}>
            <div className="font-mono tnum text-ui-sm text-ink-muted uppercase tracking-widest">
              {axis}
            </div>
            <div className="mt-3 grid grid-cols-1 lg:grid-cols-2 gap-4">
              {list.map((c) => (
                <ClusterCard key={c.id} cluster={c} />
              ))}
            </div>
          </div>
        ))}
        {clusters.length === 0 && !err && (
          <p className="text-ink-muted">No failure clusters — clean run.</p>
        )}
      </section>
    </div>
  );
}
