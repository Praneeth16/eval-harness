"use client";

import { useState } from "react";

type Citation = { id: string; verified: boolean };
type Side = {
  answer: string;
  citations: Citation[];
  all_verified: boolean;
  has_phantom: boolean;
  verified_before_cite: boolean;
  category: string;
  risk_tier: string;
  gap_detected: boolean;
  cost_usd: number;
  latency_ms: number;
};
type CompareResult = { question: string; baseline: Side; tuned: Side };

const PRESETS: { label: string; q: string }[] = [
  {
    label: "PCI-DSS certification",
    q: "Confirm whether your organization is certified under PCI-DSS and specify the level.",
  },
  {
    label: "Vendor management policy",
    q: "Describe your vendor management program and reference the specific internal policy that governs vendor onboarding tiers.",
  },
  {
    label: "Breach notification SLA",
    q: "What is your breach notification SLA for confirmed personal data breaches?",
  },
  {
    label: "MFA on production",
    q: "Do you enforce MFA on production, and which policy mandates it?",
  },
  {
    label: "SOC 2 Type II",
    q: "Are you SOC 2 Type II certified? Provide the audit period and the controlling policy.",
  },
];

function Verdict({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div className="flex items-center gap-2 font-mono tnum text-ui-sm">
      <span className={ok ? "text-improved" : "text-clear-safety"}>{ok ? "✓" : "✗"}</span>
      <span className="text-ink-secondary">{label}</span>
    </div>
  );
}

function SideCard({ side, data, win }: { side: "baseline" | "tuned"; data: Side; win: boolean }) {
  const isTuned = side === "tuned";
  return (
    <div
      className={`rounded-lg border overflow-hidden ${
        isTuned && win ? "border-improved/45 bg-improved/[0.04]" : "border-line bg-canvas-surface/40"
      }`}
    >
      <div className="flex items-center justify-between px-5 py-3 border-b border-line bg-canvas-elevated/30">
        <span className="font-mono tnum text-ui-sm uppercase tracking-wider text-ink-muted">
          {isTuned ? "Tuned · propose / verify / finalize" : "Baseline · single call"}
        </span>
        <span className={`font-mono tnum text-ui-sm ${isTuned ? "text-improved" : "text-ink-muted"}`}>
          {data.latency_ms} ms · ${data.cost_usd.toFixed(4)}
        </span>
      </div>
      <div className="p-5 space-y-4">
        <p className="text-ink-primary text-ui leading-relaxed whitespace-pre-wrap">{data.answer}</p>

        <div>
          <div className="font-mono tnum text-ui-sm text-ink-muted uppercase tracking-wider mb-2">
            Citations
          </div>
          <div className="flex flex-wrap gap-1.5">
            {data.citations.length === 0 && (
              <span className="text-ink-muted text-ui-sm">none</span>
            )}
            {data.citations.map((c, i) => (
              <span
                key={i}
                className={`font-mono tnum text-ui-sm px-2 py-0.5 rounded-sm border ${
                  c.verified
                    ? "border-improved/40 text-improved bg-improved/10"
                    : "border-clear-safety/50 text-clear-safety bg-clear-safety/10"
                }`}
              >
                {c.id} {c.verified ? "✓" : "✗ phantom"}
              </span>
            ))}
          </div>
        </div>

        <div className="pt-3 border-t border-line space-y-1.5">
          <Verdict ok={data.verified_before_cite} label="verified before citing" />
          <Verdict ok={!data.has_phantom} label="no phantom citation" />
        </div>
      </div>
    </div>
  );
}

export default function ComparePage() {
  const [question, setQuestion] = useState(PRESETS[0].q);
  const [result, setResult] = useState<CompareResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function run() {
    setLoading(true);
    setErr(null);
    setResult(null);
    try {
      const res = await fetch("/api/examples/quill/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setResult(await res.json());
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  // tuned "wins" when it verified before citing and baseline did not, or it avoided a phantom baseline emitted
  const tunedWins =
    !!result &&
    ((result.tuned.verified_before_cite && !result.baseline.verified_before_cite) ||
      (result.baseline.has_phantom && !result.tuned.has_phantom));

  return (
    <div className="max-w-[1280px] mx-auto px-10 py-12">
      <header className="border-b border-line pb-6">
        <div className="font-mono tnum text-ui-sm text-ink-muted uppercase tracking-widest">
          live · baseline vs tuned
        </div>
        <h1 className="mt-1 font-display text-display-md tracking-tight">
          Run both agents on the same question.
        </h1>
        <p className="mt-2 text-ink-secondary text-ui max-w-[70ch]">
          The baseline drafts answer + citations in one call. The tuned agent proposes
          citations, verifies each against the corpus, then writes from the verified list.
          Watch the <span className="text-improved">verify-before-cite</span> trajectory: the
          baseline never has it.
        </p>
      </header>

      <section className="mt-6">
        <div className="flex flex-wrap gap-2">
          {PRESETS.map((p) => (
            <button
              key={p.label}
              onClick={() => setQuestion(p.q)}
              className={`font-mono tnum text-ui-sm px-3 py-1.5 rounded-sm border transition-colors duration-micro ${
                question === p.q
                  ? "border-improved/50 text-improved bg-improved/10"
                  : "border-line text-ink-secondary hover:bg-canvas-elevated"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>

        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          rows={2}
          className="mt-4 w-full rounded-md border border-line bg-canvas-surface px-4 py-3 text-ui text-ink-primary font-sans resize-none focus:outline-none focus:border-improved/50"
        />

        <button
          onClick={run}
          disabled={loading || !question.trim()}
          className="mt-3 inline-flex items-center gap-2 rounded-md bg-improved text-canvas px-4 py-2 font-mono tnum text-ui hover:bg-improved/90 transition-colors duration-micro disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loading ? "Running both agents…" : "Run comparison →"}
        </button>
        {loading && (
          <span className="ml-3 font-mono tnum text-ui-sm text-ink-muted">
            live calls, ~15s
          </span>
        )}
      </section>

      {err && (
        <div className="mt-6 rounded-md border border-state-error/40 bg-state-error/10 px-4 py-3 text-ui text-state-error">
          {err}
        </div>
      )}

      {result && (
        <section className="mt-8">
          {tunedWins && (
            <div className="mb-4 rounded-md border border-improved/40 bg-improved/[0.06] px-4 py-3 text-ui">
              <span className="text-improved font-mono tnum">harness verdict →</span>{" "}
              <span className="text-ink-primary">
                the tuned agent verified before citing; the baseline shipped its citations
                unchecked. Only the trajectory layer sees the difference.
              </span>
            </div>
          )}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 items-start">
            <SideCard side="baseline" data={result.baseline} win={tunedWins} />
            <SideCard side="tuned" data={result.tuned} win={tunedWins} />
          </div>
        </section>
      )}
    </div>
  );
}
