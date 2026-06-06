"""Render the data-driven blog figures from the real NIST-run numbers.

Two figures, one house style (white background, thin charcoal rules, a single
muted-teal accent, flat vector look):

  fig1_two_traces.png  — the thesis: the same question, two trajectories. The
                         baseline cites without a verify span; the fixed agent
                         verifies before it cites. Difference is ordering.
  fig2_clears_radar.png — CLEAR-S across the six axes scored on the run,
                          baseline vs the propose/verify/finalize fix.

Numbers come from the Databricks run logged to the `eval_harness_journey_mlflow`
experiment (gemini-2.5-flash, 20 SOC 2 questions over NIST SP 800-53).

    python docs/figures/make_figures.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.patches as mpatches
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent

INK = "#1f2933"        # charcoal text / rules
TEAL = "#10b981"       # single accent, reserved for the verified / fixed path
GRAY = "#9aa5b1"       # neutral, dominated / baseline
LIGHT = "#e4e7eb"      # fills
AMBER = "#d97706"      # the misleading "looks fine" signal

# Prefer a Charter-like serif for body, monospace for numbers; degrade gracefully.
_serif = next((f for f in ("Charter", "Georgia", "DejaVu Serif") if any(
    f.lower() in x.name.lower() for x in fm.fontManager.ttflist)), "serif")
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": [_serif],
    "savefig.dpi": 200,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "svg.fonttype": "none",
})
MONO = {"family": "monospace"}


# ─────────────────────────────────────────────────────────────────────────
# Figure 1 — two traces, one question
# ─────────────────────────────────────────────────────────────────────────

def two_traces() -> None:
    fig, axes = plt.subplots(2, 1, figsize=(16, 9))
    fig.subplots_adjust(left=0.04, right=0.97, top=0.84, bottom=0.06, hspace=0.42)
    fig.suptitle("One question, two trajectories", x=0.04, ha="left",
                 fontsize=26, fontweight="bold", color=INK)
    fig.text(0.04, 0.90,
             "“Reference the internal control governing vendor risk reviews.”  "
             "The final answers read the same. The traces do not.",
             ha="left", fontsize=14, color=INK)

    def box(ax, x, w, label, *, edge=INK, face="white", text=INK, lw=1.4, bold=False):
        b = FancyBboxPatch((x, 0.30), w, 0.40, boxstyle="round,pad=0.01,rounding_size=0.02",
                           linewidth=lw, edgecolor=edge, facecolor=face, mutation_aspect=0.6)
        ax.add_patch(b)
        ax.text(x + w / 2, 0.50, label, ha="center", va="center",
                fontsize=12.5, color=text, fontweight="bold" if bold else "normal")

    def arrow(ax, x0, x1):
        ax.add_patch(FancyArrowPatch((x0, 0.50), (x1, 0.50), arrowstyle="-|>",
                     mutation_scale=14, linewidth=1.2, color=GRAY))

    for ax in axes:
        ax.set_xlim(0, 13.2)
        ax.set_ylim(0, 1)
        ax.axis("off")

    # ── Baseline ──
    ax = axes[0]
    ax.text(0, 0.93, "Baseline  ·  single call", ha="left", fontsize=15,
            fontweight="bold", color=INK, transform=ax.transAxes)
    seq = [("parse", 1.0), ("classify", 1.3), ("retrieve", 1.3), ("draft + cite", 1.8)]
    x = 0.1
    xs = []
    for i, (lab, w) in enumerate(seq):
        box(ax, x, w, lab, edge=GRAY if lab != "draft + cite" else INK,
            face="white", bold=(lab == "draft + cite"))
        xs.append((x, w))
        x += w
        if i < len(seq) - 1:
            arrow(ax, x, x + 0.25)
            x += 0.35
    # citation marker, never verified
    cx = xs[-1][0] + xs[-1][1]
    ax.add_patch(FancyArrowPatch((cx, 0.50), (cx + 0.5, 0.50), arrowstyle="-|>",
                 mutation_scale=14, linewidth=1.2, color=AMBER))
    box(ax, cx + 0.6, 1.9, "cites  SC-7", edge=AMBER, face="#fdf3e7", text=AMBER, bold=True)
    ax.text(cx + 1.55, 0.18, "no verify step ran", ha="center", fontsize=11.5,
            color=AMBER, style="italic")
    ax.text(13.0, 0.50, "verify-before-cite\n0.00", ha="right", va="center",
            fontsize=15, color=AMBER, fontweight="bold", **MONO)

    # ── Fixed ──
    ax = axes[1]
    ax.text(0, 0.93, "Fixed  ·  propose, verify, finalize", ha="left", fontsize=15,
            fontweight="bold", color=INK, transform=ax.transAxes)
    seq = [("parse", 1.0), ("classify", 1.3), ("retrieve", 1.3), ("propose", 1.3)]
    x = 0.1
    for i, (lab, w) in enumerate(seq):
        box(ax, x, w, lab, edge=GRAY, face="white")
        x += w
        arrow(ax, x, x + 0.25)
        x += 0.35
    # verify span, highlighted
    box(ax, x, 1.7, "verify (tool)", edge=TEAL, face="#e7f8f1", text=TEAL, lw=2.0, bold=True)
    ax.text(x + 0.85, 0.24, "tool returns true", ha="center", fontsize=10.5,
            color=TEAL, style="italic")
    vx = x + 1.7
    x = vx
    arrow(ax, x, x + 0.25)
    x += 0.35
    box(ax, x, 1.9, "finalize + cite", edge=INK, face="white", bold=True)
    fx = x
    # ordering bracket
    ax.annotate("", xy=(fx + 0.2, 0.78), xytext=(vx - 1.5, 0.78),
                arrowprops=dict(arrowstyle="-", color=TEAL, lw=1.3))
    ax.text((vx - 1.5 + fx + 0.2) / 2, 0.84, "verify precedes the citation",
            ha="center", fontsize=11.5, color=TEAL, style="italic")
    ax.text(13.0, 0.50, "verify-before-cite\n0.97", ha="right", va="center",
            fontsize=15, color=TEAL, fontweight="bold", **MONO)

    fig.text(0.04, 0.015,
             "Both answers cite a real NIST 800-53 control and pass a string check. "
             "Only the trace shows the baseline never verified it.",
             ha="left", fontsize=11.5, color=GRAY)
    fig.savefig(OUT / "fig1_two_traces.png", facecolor="white")
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────
# Figure 2 — CLEAR-S radar
# ─────────────────────────────────────────────────────────────────────────

def clears_radar() -> None:
    # Six axes scored on the run (relevance/groundedness was not scored here).
    axes_labels = ["Correctness", "Latency", "Execution\n(verify-before-cite)",
                   "Adherence", "Safety", "Cost"]
    baseline = [0.75, 1.00, 0.50, 1.00, 1.00, 1.00]
    fixed = [0.683, 0.90, 0.925, 1.00, 1.00, 1.00]

    n = len(axes_labels)
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    ang += ang[:1]

    def close(v):
        return v + v[:1]

    fig = plt.figure(figsize=(16, 9))
    ax = fig.add_subplot(111, polar=True)
    fig.subplots_adjust(left=0.06, right=0.72, top=0.78, bottom=0.10)

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 1.0)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0.25", "0.50", "0.75", "1.00"], fontsize=9, color=GRAY, **MONO)
    ax.set_rlabel_position(202)  # radial numbers to lower-left, clear of the top label
    ax.set_xticks(ang[:-1])
    ax.set_xticklabels(axes_labels, fontsize=13, color=INK)
    ax.tick_params(pad=14)
    ax.grid(color=LIGHT, linewidth=1)
    ax.spines["polar"].set_color(LIGHT)

    ax.plot(ang, close(baseline), color=GRAY, linewidth=2, label="Baseline (single call)")
    ax.fill(ang, close(baseline), color=GRAY, alpha=0.12)
    ax.plot(ang, close(fixed), color=TEAL, linewidth=2.4, label="Fixed (propose/verify/finalize)")
    ax.fill(ang, close(fixed), color=TEAL, alpha=0.15)

    fig.suptitle("CLEAR-S: you cannot hide a regression in the average", x=0.06, y=0.965,
                 ha="left", fontsize=22, fontweight="bold", color=INK)
    fig.text(0.06, 0.90,
             "Six axes scored on the NIST run. The fix lifts execution from 0.50 to 0.93,\n"
             "while the baseline only looks competitive because the average hides it.",
             ha="left", fontsize=13, color=INK)

    ax.legend(loc="upper left", bbox_to_anchor=(1.12, 1.05), frameon=False, fontsize=13)
    # callout on the execution axis gap
    fig.text(0.74, 0.42,
             "Execution is the\nverify-before-cite axis.\nBaseline 0.50  to  Fixed 0.93\n\n"
             "On the trajectory scorer\nalone, baseline is 0.00.",
             ha="left", fontsize=12, color=INK)
    fig.savefig(OUT / "fig2_clears_radar.png", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    two_traces()
    clears_radar()
    print("wrote", OUT / "fig1_two_traces.png")
    print("wrote", OUT / "fig2_clears_radar.png")
