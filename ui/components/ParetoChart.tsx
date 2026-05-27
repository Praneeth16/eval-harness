"use client";

import { useMemo } from "react";
import type { Pareto, ParetoCandidate } from "@/lib/api";

/**
 * Pareto chart — THE CLIMAX VISUAL.
 *
 * Axes are configurable but default to (cost ↑, correctness ↑) — both
 * normalized to [0,1] so the "better" direction is up-and-to-the-right.
 *
 * Baseline candidates render as graphite-stroked hollow rings (instant).
 * Tuned candidates that sit on the Pareto frontier render as mint-filled
 * dots; the connecting frontier curve sweeps in over 400ms with
 * `ease-hero` (slight overshoot) and each frontier dot ring-pulses in.
 *
 * One choreographed animation in the whole app. Do not embellish.
 */
export function ParetoChart({
  pareto,
  xAxis = "cost",
  yAxis = "correctness",
  showAnnotation = true,
}: {
  pareto: Pareto;
  xAxis?: string;
  yAxis?: string;
  showAnnotation?: boolean;
}) {
  const width = 760;
  const height = 460;
  const padding = { top: 32, right: 40, bottom: 56, left: 64 };

  const innerW = width - padding.left - padding.right;
  const innerH = height - padding.top - padding.bottom;

  const baselineId = pareto.baseline_id;
  const winnerId = pareto.winner_id;
  const frontierSet = new Set(pareto.frontier_ids);

  const points = useMemo(() => {
    return pareto.candidates.map((c) => {
      const x = c.objectives?.[xAxis] ?? 0;
      const y = c.objectives?.[yAxis] ?? 0;
      return {
        candidate: c,
        x: padding.left + x * innerW,
        y: padding.top + (1 - y) * innerH,
        onFrontier: frontierSet.has(c.candidate_id),
        isBaseline: c.candidate_id === baselineId,
        isWinner: c.candidate_id === winnerId,
      };
    });
  }, [
    pareto, xAxis, yAxis, innerW, innerH, frontierSet,
    baselineId, winnerId, padding.left, padding.top,
  ]);

  const baselinePt = points.find((p) => p.isBaseline);
  const winnerPt = points.find((p) => p.isWinner);

  // Frontier path — sort by x asc, draw a smooth polyline.
  const frontierPath = useMemo(() => {
    const fr = points
      .filter((p) => p.onFrontier && !p.isBaseline)
      .sort((a, b) => a.x - b.x);
    if (fr.length === 0) return "";
    return fr.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
  }, [points]);

  return (
    <div className="relative w-full">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full h-auto"
        role="img"
        aria-label={`Pareto frontier: ${xAxis} vs ${yAxis}`}
      >
        {/* hairline grid */}
        <g>
          {Array.from({ length: 5 }).map((_, i) => {
            const t = i / 4;
            const yy = padding.top + t * innerH;
            const xx = padding.left + t * innerW;
            return (
              <g key={i}>
                <line
                  x1={padding.left}
                  x2={padding.left + innerW}
                  y1={yy}
                  y2={yy}
                  stroke="rgba(255,255,255,0.05)"
                  strokeWidth="1"
                />
                <line
                  x1={xx}
                  x2={xx}
                  y1={padding.top}
                  y2={padding.top + innerH}
                  stroke="rgba(255,255,255,0.05)"
                  strokeWidth="1"
                />
              </g>
            );
          })}
        </g>

        {/* axes */}
        <g>
          <line
            x1={padding.left}
            x2={padding.left + innerW}
            y1={padding.top + innerH}
            y2={padding.top + innerH}
            stroke="#3F3F46"
          />
          <line
            x1={padding.left}
            x2={padding.left}
            y1={padding.top}
            y2={padding.top + innerH}
            stroke="#3F3F46"
          />
          <text
            x={padding.left + innerW / 2}
            y={height - 16}
            textAnchor="middle"
            className="fill-ink-secondary"
            fontSize="13"
            fontFamily="var(--font-geist-mono)"
          >
            {xAxis} →
          </text>
          <text
            x={-(padding.top + innerH / 2)}
            y={20}
            transform="rotate(-90)"
            textAnchor="middle"
            className="fill-ink-secondary"
            fontSize="13"
            fontFamily="var(--font-geist-mono)"
          >
            ↑ {yAxis}
          </text>
        </g>

        {/* dominated cluster — baseline + dominated candidates as hollow rings */}
        <g>
          {points
            .filter((p) => !p.onFrontier || p.isBaseline)
            .map((p) => (
              <circle
                key={p.candidate.candidate_id}
                cx={p.x}
                cy={p.y}
                r={p.isBaseline ? 5 : 4}
                fill="transparent"
                stroke={p.isBaseline ? "#71717A" : "#52525B"}
                strokeWidth={p.isBaseline ? 1.5 : 1}
              >
                <title>{`${p.candidate.label} — ${p.candidate.candidate_id}`}</title>
              </circle>
            ))}
        </g>

        {/* frontier path — animated sweep */}
        {frontierPath && (
          <path
            d={frontierPath}
            fill="none"
            stroke="#10F09C"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="pareto-frontier"
            style={{ ["--pareto-len" as string]: "1200" } as React.CSSProperties}
          />
        )}

        {/* frontier dots — pulse ring */}
        <g>
          {points
            .filter((p) => p.onFrontier && !p.isBaseline)
            .map((p) => (
              <g key={p.candidate.candidate_id}>
                <circle
                  cx={p.x}
                  cy={p.y}
                  r={p.isWinner ? 8 : 6}
                  fill="#10F09C"
                  stroke="rgba(16,240,156,0.6)"
                  strokeWidth={p.isWinner ? 3 : 2}
                >
                  <title>{`${p.candidate.label} — ${p.candidate.candidate_id}`}</title>
                </circle>
                <circle
                  cx={p.x}
                  cy={p.y}
                  r={p.isWinner ? 8 : 6}
                  fill="none"
                  stroke="#10F09C"
                  strokeWidth="2"
                  className="pareto-dot-ring"
                />
                {p.isWinner && (
                  <g
                    style={{
                      animation:
                        "fade-up 400ms cubic-bezier(0.16, 1, 0.3, 1) 700ms both",
                    }}
                  >
                    <text
                      x={p.x + 14}
                      y={p.y - 6}
                      className="fill-improved"
                      fontFamily="var(--font-geist-mono)"
                      fontSize="12"
                    >
                      ▸ winner
                    </text>
                  </g>
                )}
              </g>
            ))}
        </g>

        {/* annotation — baseline label + GEPA shift arrow */}
        {showAnnotation && baselinePt && winnerPt && (
          <g
            style={{
              animation:
                "fade-up 400ms cubic-bezier(0.16, 1, 0.3, 1) 900ms both",
            }}
          >
            <text
              x={baselinePt.x - 12}
              y={baselinePt.y + 4}
              textAnchor="end"
              className="fill-ink-muted"
              fontFamily="var(--font-geist-mono)"
              fontSize="12"
            >
              baseline ◂
            </text>
          </g>
        )}
      </svg>

      <div className="mt-2 flex gap-6 text-ui-sm text-ink-muted">
        <Legend dotColor="#10F09C" label="GEPA-tuned (frontier)" />
        <Legend dotColor="#71717A" label="baseline" hollow />
        <Legend dotColor="#52525B" label="dominated" hollow />
      </div>
    </div>
  );
}

function Legend({
  dotColor,
  label,
  hollow,
}: {
  dotColor: string;
  label: string;
  hollow?: boolean;
}) {
  return (
    <span className="inline-flex items-center gap-2">
      <span
        className="inline-block h-2.5 w-2.5 rounded-full"
        style={{
          backgroundColor: hollow ? "transparent" : dotColor,
          border: `1.5px solid ${dotColor}`,
        }}
      />
      <span className="font-mono">{label}</span>
    </span>
  );
}
