import Link from "next/link";
import { api, type PromptDiff as PromptDiffData } from "@/lib/api";
import { PromptDiff } from "@/components/PromptDiff";

export const dynamic = "force-dynamic";

export default async function PromptDiffPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let data: PromptDiffData | null = null;
  let err: string | null = null;
  try {
    data = await api.getPromptDiff(id);
  } catch (e) {
    err = (e as Error).message;
  }

  return (
    <div className="max-w-[1440px] mx-auto px-10 py-12">
      <header className="border-b border-line pb-6">
        <Link
          href={`/pareto/${id}`}
          className="text-ui-sm text-ink-muted hover:text-ink-primary"
        >
          ← Pareto {id}
        </Link>
        <h1 className="mt-2 font-display text-display-md tracking-tight">
          Prompt diff
        </h1>
        <p className="mt-2 text-ink-secondary max-w-[64ch]">
          Left, the under-constrained baseline that ships phantom citations and
          marketing-leaning certification claims. Right, the GEPA-tuned variant
          that adds policy-existence verification, tightens citation format,
          and forbids unverifiable certification commitments.
        </p>
      </header>

      {err && (
        <div className="mt-6 rounded-md border border-state-error/40 bg-state-error/10 px-4 py-3 text-state-error">
          {err}
        </div>
      )}

      {data && (
        <section className="mt-8">
          <PromptDiff
            baseline={data.baseline}
            tuned={data.tuned}
            rationale={data.rationale}
          />
        </section>
      )}
    </div>
  );
}
