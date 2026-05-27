import Link from "next/link";
import { api } from "@/lib/api";
import { RunBadge } from "@/components/RunBadge";

const AXIOMS = [
  {
    n: "01",
    title: "Trace before eval.",
    body: "You cannot grade logic you cannot visualize. Agents are stochastic state machines. Watch them run before you score what they did.",
  },
  {
    n: "02",
    title: "Eval layers stack.",
    body: "Deterministic for constraints. Semantic for tone. Trajectory for logic. Safety for adversaries. One layer never catches everything.",
  },
  {
    n: "03",
    title: "Static prompts ship hallucinations.",
    body: "A self-evolving harness compounds away from them. Failures become training data. Pareto frontiers replace single scores.",
  },
  {
    n: "04",
    title: "Optimize the tail, not the mean.",
    body: "p95 failures ship. p50 wins do not. The harness's job is to expose the tail, then close it.",
  },
  {
    n: "05",
    title: "Agents need CI for behavior.",
    body: "Maintainers built CI for code. This harness is that — every commit, every prompt, every model swap regressed against the failure shapes that actually shipped.",
  },
];

export default async function HomePage() {
  let latest: { latest_run_id: string | null; latest_opt_id: string | null } | null = null;
  try {
    latest = await api.latest();
  } catch {
    latest = null;
  }

  return (
    <div className="bg-hairline min-h-screen">
      <section className="max-w-[1280px] mx-auto px-10 pt-24 pb-16">
        <div className="grid grid-cols-12 gap-8 items-start">
          <div className="col-span-12 lg:col-span-8">
            <div className="font-mono tnum text-ui-sm text-improved uppercase tracking-widest">
              v0.1 · Journey of an Agent
            </div>
            <h1 className="mt-4 font-display text-display-xl leading-[1.02] tracking-tight">
              Agents learn from <span className="text-improved">their own</span> failures here.
            </h1>
            <p className="mt-6 font-display text-body-lg text-ink-secondary max-w-[60ch]">
              A self-evolving eval harness for production AI agents. Trace
              every step. Score every output across CLEAR-S. Cluster failures.
              Mutate prompts reflectively. Land on the Pareto frontier — and
              ship the prompt that dominates the baseline across correctness,
              groundedness, safety, cost, and latency.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href={latest?.latest_opt_id ? `/pareto/${latest.latest_opt_id}` : "/pareto"}
                className="inline-flex items-center gap-2 rounded-md bg-improved text-canvas px-4 py-2 font-mono tnum text-ui hover:bg-improved/90 transition-colors duration-micro"
              >
                See the Pareto shift →
              </Link>
              <Link
                href="/runs"
                className="inline-flex items-center gap-2 rounded-md border border-line px-4 py-2 font-mono tnum text-ui text-ink-secondary hover:bg-canvas-elevated transition-colors duration-micro"
              >
                Browse eval runs
              </Link>
            </div>
          </div>

          <aside className="col-span-12 lg:col-span-4 rounded-xl border border-line bg-canvas-surface/60 p-6">
            <div className="font-mono tnum text-ui-sm text-ink-muted uppercase tracking-widest">
              Hero example
            </div>
            <div className="mt-2 font-display text-title">Quill</div>
            <p className="mt-2 text-ui text-ink-secondary">
              A multi-agent RFP / security-questionnaire response system. Parses
              the questionnaire, classifies each question, retrieves over the
              company's policy corpus + framework controls, drafts answers
              grounded in citations, escalates policy gaps to owners, risk-tiers
              the whole thing for human review.
            </p>
            <div className="mt-4 flex flex-wrap gap-1.5">
              {["LangGraph", "MLflow 3", "FAISS", "DSPy + GEPA", "OpenRouter"].map((t) => (
                <span
                  key={t}
                  className="font-mono tnum text-ui-sm px-1.5 py-0.5 rounded-sm border border-line text-ink-muted bg-canvas-elevated"
                >
                  {t}
                </span>
              ))}
            </div>
          </aside>
        </div>
      </section>

      <section className="max-w-[1280px] mx-auto px-10 py-16 border-t border-line">
        <div className="grid grid-cols-12 gap-8">
          <div className="col-span-12 lg:col-span-4">
            <div className="font-mono tnum text-ui-sm text-ink-muted uppercase tracking-widest">
              Axioms
            </div>
            <h2 className="mt-3 font-display text-display-md tracking-tight">
              What we believe about evaluating real agents.
            </h2>
          </div>
          <div className="col-span-12 lg:col-span-8 space-y-6">
            {AXIOMS.map((a) => (
              <article key={a.n} className="grid grid-cols-12 gap-6 border-t border-line pt-6">
                <div className="col-span-2 font-mono tnum text-display-md text-improved">
                  {a.n}
                </div>
                <div className="col-span-10">
                  <h3 className="font-display text-title">{a.title}</h3>
                  <p className="mt-2 text-ink-secondary">{a.body}</p>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="max-w-[1280px] mx-auto px-10 py-12 border-t border-line">
        <div className="flex items-baseline justify-between">
          <div>
            <div className="font-mono tnum text-ui-sm text-ink-muted uppercase tracking-widest">
              status
            </div>
            <div className="mt-1 font-display text-title">Live harness state</div>
          </div>
          <Link href="/runs" className="text-ui text-ink-muted hover:text-ink-primary">
            all runs →
          </Link>
        </div>
        <div className="mt-4 rounded-md border border-line bg-canvas-surface p-5">
          <div className="grid grid-cols-3 gap-6">
            <div>
              <div className="font-mono tnum text-ui-sm text-ink-muted">latest run</div>
              <div className="mt-1 font-mono tnum text-ui">
                {latest?.latest_run_id || "—"}
              </div>
            </div>
            <div>
              <div className="font-mono tnum text-ui-sm text-ink-muted">latest optimization</div>
              <div className="mt-1 font-mono tnum text-ui">
                {latest?.latest_opt_id || "—"}
              </div>
            </div>
            <div>
              <div className="font-mono tnum text-ui-sm text-ink-muted">api</div>
              <div className="mt-1">
                <RunBadge status={latest ? "done" : "pending"} />
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
