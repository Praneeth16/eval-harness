import Link from "next/link";
import { api, type OptRun } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function PortabilityIndex() {
  let opts: OptRun[] = [];
  try {
    opts = await api.listOptRuns();
  } catch {}
  return (
    <div className="max-w-[1280px] mx-auto px-10 py-12">
      <header className="border-b border-line pb-6">
        <h1 className="font-display text-display-md tracking-tight">Cross-model portability</h1>
        <p className="mt-2 text-ink-secondary">
          Does the tuned prompt hold up across Llama / Claude / Qwen?
        </p>
      </header>
      <ul className="mt-6 space-y-2">
        {opts.map((o) => (
          <li
            key={o.id}
            className="border border-line rounded-md p-4 hover:bg-canvas-elevated"
          >
            <Link
              href={`/portability/${o.id}`}
              className="font-mono tnum text-improved"
            >
              {o.id}
            </Link>
          </li>
        ))}
        {opts.length === 0 && <li className="text-ink-muted">No optimizations yet.</li>}
      </ul>
    </div>
  );
}
