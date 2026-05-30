import Link from "next/link";
import { DetectionContrast } from "@/components/DetectionContrast";
import { api, type Detection } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function DetectionPage() {
  let data: Detection | null = null;
  let err: string | null = null;
  try {
    data = await api.getDetection("quill");
  } catch (e) {
    err = (e as Error).message;
  }

  return (
    <div className="max-w-[1100px] mx-auto px-10 py-12">
      <header className="border-b border-line pb-6">
        <div className="text-ui-sm text-ink-muted uppercase tracking-widest">
          The harness earns its keep
        </div>
        <h1 className="mt-2 font-display text-display-lg tracking-tight">
          A vibe check ships the lie. <span className="text-improved">This catches it.</span>
        </h1>
        <p className="mt-3 text-body-lg text-ink-secondary max-w-[60ch]">
          Three production failures, three eval layers. The first two — eyeballing the
          answer and checking that citations are well-formed strings — wave every one
          through. The trajectory, portability, and held-out checks catch them.
        </p>
      </header>

      {err && (
        <div className="mt-6 rounded-md border border-state-error/40 bg-state-error/10 px-4 py-3 text-state-error">
          {err}
        </div>
      )}

      {data && (
        <div className="mt-8">
          <DetectionContrast data={data} />
        </div>
      )}

      <div className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-ui-sm text-ink-muted">
        <Link href="/runs/run_cold_open_demo" className="hover:text-ink-primary">
          → see the cold-open failures
        </Link>
        <Link href="/pareto" className="hover:text-ink-primary">
          → the multi-objective frontier
        </Link>
        <Link href="/portability" className="hover:text-ink-primary">
          → the portability gate
        </Link>
      </div>
    </div>
  );
}
