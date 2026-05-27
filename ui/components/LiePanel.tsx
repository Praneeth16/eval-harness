"use client";

import type { Score } from "@/lib/api";

type Retrieved = {
  chunk_id?: string;
  kind?: string;
  title?: string;
  score?: number;
};

/**
 * "Where did it lie?" panel — surfaces the exact failure shape on a
 * failed trace. Three columns:
 *
 *   1. WHAT THE AGENT CITED   — fabricated IDs, real-but-stale,
 *      marketing overclaims pulled from scorer details.
 *   2. WHAT THE CORPUS SAYS   — retrieved chunks the agent had in
 *      context, their kind + title.
 *   3. WHY IT FAILED          — top failed scorers w/ verdicts.
 *
 * This is the visceral Act 2 moment: open a failed trace, see in 5
 * seconds the exact word/citation that lied.
 */
export function LiePanel({
  scores,
  retrieved,
}: {
  scores: Score[];
  retrieved: Retrieved[];
}) {
  const failed = scores.filter((s) => !s.passed);
  if (failed.length === 0) return null;

  // Pull structured failure data from scorer details where present.
  const phantomPolicies = uniq([
    ...flatList(scores, "policy_exists", "missing"),
    ...flatList(scores, "hallucinated_claim", "phantom_policies"),
  ]);
  const marketingOverclaims = flatList(
    scores,
    "hallucinated_claim",
    "marketing_overclaims",
  );
  const unsupportedClaims = flatList(scores, "groundedness", "unsupported_claims");
  const judgeReason = scores
    .find((s) => s.scorer_name === "judge_accept" && !s.passed)
    ?.details?.["reason"] as string | undefined;
  const verifiedMissing = flatList(
    scores,
    "policy_exists_called_before_cite",
    "missing",
  );

  const failedTop = failed
    .filter(
      (s) =>
        s.scorer_name !== "policy_exists_called_before_cite" &&
        s.scorer_name !== "policy_exists" &&
        s.scorer_name !== "hallucinated_claim" &&
        s.scorer_name !== "groundedness" &&
        s.scorer_name !== "judge_accept",
    )
    .slice(0, 4);

  return (
    <section className="mt-4 rounded-md border border-state-error/30 bg-state-error/5">
      <header className="px-4 py-2 border-b border-state-error/30 bg-state-error/10 flex items-center justify-between">
        <div className="font-mono tnum text-ui-sm uppercase tracking-widest text-state-error">
          ▾ Where did the agent lie?
        </div>
        <div className="font-mono tnum text-ui-sm text-state-error/80">
          {failed.length} failed scorer{failed.length === 1 ? "" : "s"}
        </div>
      </header>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-0 divide-y lg:divide-y-0 lg:divide-x divide-state-error/20">
        <Column title="What the agent cited">
          {phantomPolicies.length > 0 && (
            <Block tone="bad" label="Phantom policy IDs">
              {phantomPolicies.map((p) => (
                <code key={p} className="block">
                  {p}
                </code>
              ))}
            </Block>
          )}
          {marketingOverclaims.length > 0 && (
            <Block tone="bad" label="Marketing → certification overclaims">
              {marketingOverclaims.map((m) => (
                <span key={m} className="block">
                  {m}
                </span>
              ))}
            </Block>
          )}
          {unsupportedClaims.length > 0 && (
            <Block tone="warn" label="Unsupported claims (no chunk grounds them)">
              {unsupportedClaims.slice(0, 3).map((c) => (
                <span key={c} className="block">
                  · {c}
                </span>
              ))}
            </Block>
          )}
          {verifiedMissing.length > 0 && (
            <Block tone="warn" label="Cited without verifying">
              {verifiedMissing.map((v) => (
                <code key={v} className="block">
                  {v}
                </code>
              ))}
            </Block>
          )}
          {phantomPolicies.length === 0 &&
            marketingOverclaims.length === 0 &&
            unsupportedClaims.length === 0 &&
            verifiedMissing.length === 0 && (
              <p className="text-ink-muted text-ui-sm">
                No structured fabrication details. See scorer column on the right.
              </p>
            )}
        </Column>

        <Column title="What the corpus said">
          {retrieved.length === 0 && (
            <p className="text-ink-muted text-ui-sm">No retrieved chunks recorded.</p>
          )}
          {retrieved.slice(0, 5).map((r) => (
            <div key={r.chunk_id} className="text-ui-sm">
              <div className="font-mono tnum text-ink-muted">
                {r.kind}{typeof r.score === "number" ? ` · ${r.score.toFixed(2)}` : ""}
              </div>
              <div className="text-ink-primary">
                {r.title}
              </div>
              {r.chunk_id && (
                <div className="font-mono tnum text-ui-sm text-ink-muted">
                  {r.chunk_id}
                </div>
              )}
            </div>
          ))}
        </Column>

        <Column title="Why it failed">
          {judgeReason && (
            <Block tone="bad" label="Judge verdict">
              <span className="block italic">{judgeReason}</span>
            </Block>
          )}
          {failedTop.map((s) => (
            <div key={s.scorer_name} className="text-ui-sm">
              <div className="font-mono tnum text-state-error">
                ✗ {s.scorer_name}
              </div>
              <div className="text-ink-muted">
                value {s.value.toFixed(2)} · axis {s.clear_axis}
              </div>
            </div>
          ))}
          {failedTop.length === 0 && !judgeReason && (
            <p className="text-ink-muted text-ui-sm">
              All structured failures shown above.
            </p>
          )}
        </Column>
      </div>
    </section>
  );
}

function Column({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="p-4 space-y-3">
      <div className="font-mono tnum text-ui-sm uppercase tracking-widest text-ink-muted">
        {title}
      </div>
      {children}
    </div>
  );
}

function Block({
  tone,
  label,
  children,
}: {
  tone: "bad" | "warn";
  label: string;
  children: React.ReactNode;
}) {
  const cls =
    tone === "bad"
      ? "border-state-error/40 bg-state-error/10 text-state-error"
      : "border-state-warn/40 bg-state-warn/10 text-state-warn";
  return (
    <div className={`rounded-sm border ${cls} p-3 space-y-1`}>
      <div className="font-mono tnum text-ui-sm uppercase tracking-widest opacity-80">
        {label}
      </div>
      <div className="code-pane text-ui-sm leading-relaxed">{children}</div>
    </div>
  );
}

function flatList(scores: Score[], scorerName: string, key: string): string[] {
  const sc = scores.find((s) => s.scorer_name === scorerName);
  if (!sc) return [];
  const val = (sc.details as Record<string, unknown>)?.[key];
  if (Array.isArray(val)) return val.map((x) => String(x));
  return [];
}

function uniq(arr: string[]): string[] {
  return Array.from(new Set(arr));
}
