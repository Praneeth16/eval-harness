"""Render the data-driven blog figures from the real NIST-run numbers.

Five figures, one house style (white background, thin charcoal rules, a single
muted-teal accent, flat vector look):

  fig1_two_traces.png  — the thesis: the same question, two trajectories. The
                         baseline cites without a verify span; the fixed agent
                         verifies before it cites. Difference is ordering.
  fig2_clears_radar.png — CLEAR-S across the six axes scored on the run,
                          baseline vs the propose/verify/finalize fix.

Figures 3-5 (architecture, scorer funnel, loop) are authored as SVG by Claude
Fable 5 on Databricks FMAPI: see gen_fable_figures.py.

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


# ─────────────────────────────────────────────────────────────────────────
# Table figures — Medium cannot render markdown tables, so each table in the
# article ships as an image in the same house style.
# ─────────────────────────────────────────────────────────────────────────

def _table_fig(fname, title, subtitle, cols, rows, widths, *, accents=None,
               caption="", mono_data=True, align="center", fontsize=13,
               row_h=0.62, header_color=None):
    accents = accents or {}
    n_rows = len(rows)
    fig_h = 1.7 + (n_rows + 1) * row_h + (0.7 if caption else 0.3)
    fig, ax = plt.subplots(figsize=(12, fig_h))
    fig.subplots_adjust(left=0.05, right=0.95, top=0.97, bottom=0.03)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, fig_h)
    ax.axis("off")

    ax.text(0.5, fig_h - 0.45, title, ha="center", fontsize=21,
            fontweight="bold", color=INK)
    ax.text(0.5, fig_h - 0.95, subtitle, ha="center", fontsize=12.5, color=GRAY)

    x_edges = [0.06]
    for w in widths:
        x_edges.append(x_edges[-1] + w)
    top = fig_h - 1.35
    y_edges = [top - i * row_h for i in range(n_rows + 2)]

    for y in y_edges:
        ax.plot([x_edges[0], x_edges[-1]], [y, y], color=LIGHT, lw=1.2, zorder=1)
    ax.plot([x_edges[0], x_edges[-1]], [y_edges[0], y_edges[0]], color=INK, lw=1.4)
    ax.plot([x_edges[0], x_edges[-1]], [y_edges[1], y_edges[1]], color=INK, lw=1.4)
    ax.plot([x_edges[0], x_edges[-1]], [y_edges[-1], y_edges[-1]], color=INK, lw=1.4)
    for x in x_edges:
        ax.plot([x, x], [y_edges[0], y_edges[-1]], color=LIGHT, lw=1.2)

    for c, lab in enumerate(cols):
        cx = (x_edges[c] + x_edges[c + 1]) / 2
        ax.text(cx, (y_edges[0] + y_edges[1]) / 2, lab, ha="center", va="center",
                fontsize=fontsize, fontweight="bold",
                color=(header_color or {}).get(c, INK))

    for r, row in enumerate(rows):
        cy = (y_edges[r + 1] + y_edges[r + 2]) / 2
        for c, cell in enumerate(row):
            color = accents.get((r, c), INK if c == 0 else INK)
            kw = dict(MONO) if (mono_data and c > 0) else {}
            ha = "left" if (align == "left" or c == 0) else "center"
            cx = x_edges[c] + 0.015 if ha == "left" else (x_edges[c] + x_edges[c + 1]) / 2
            ax.text(cx, cy, cell, ha=ha, va="center", fontsize=fontsize - 0.5,
                    color=color, fontweight="bold" if (r, c) in accents else "normal",
                    **kw)

    if caption:
        ax.text(0.5, y_edges[-1] - 0.42, caption, ha="center", fontsize=11,
                color=GRAY, style="italic")
    fig.savefig(OUT / fname, facecolor="white")
    plt.close(fig)


def tables() -> None:
    _table_fig(
        "tbl1_fix.png",
        "CLEAR-S signals, side by side",
        "Baseline single call vs propose/verify/finalize fix · NIST run, 20 questions",
        ["CLEAR-S signal", "Baseline (single call)", "Fixed (propose/verify/finalize)"],
        [["Verify-before-cite (trajectory)", "0.00", "0.97"],
         ["Citation resolves (deterministic)", "1.00", "1.00"],
         ["Reviewer-accept (judge)", "0.58", "0.43"],
         ["Execution axis", "0.50", "0.93"],
         ["Safety axis", "1.00", "1.00"]],
        [0.40, 0.24, 0.24],
        accents={(0, 1): AMBER, (0, 2): TEAL, (3, 1): AMBER, (3, 2): TEAL},
        header_color={2: TEAL},
        caption="Average these signals and the regression fades. Keep them separate and it is obvious.",
    )
    _table_fig(
        "tbl2_transfer.png",
        "CLEAR-S signals across frameworks",
        "SOC 2 in-domain vs ISO 27001 held out · same fixed agent, untouched",
        ["CLEAR-S signal", "SOC 2 (in-domain)", "ISO 27001 (held out)"],
        [["Verify-before-cite", "0.97", "1.00"],
         ["Reviewer-accept (judge)", "0.43", "0.38"]],
        [0.40, 0.24, 0.24],
        accents={(0, 2): TEAL},
        caption="The structural guarantee transfers; semantic quality does not come free on an unseen framework.",
    )
    _table_fig(
        "tbl3_models.png",
        "CLEAR-S signals across models",
        "gemini-2-5-flash vs claude-sonnet-4-6 · same agent, same questions",
        ["CLEAR-S signal", "gemini-2-5-flash", "claude-sonnet-4-6"],
        [["Verify-before-cite", "0.97", "1.00"],
         ["Reviewer-accept (judge)", "0.43", "0.53"]],
        [0.40, 0.24, 0.24],
        accents={(0, 2): TEAL},
        caption="Verify-before-cite holds across model families; the judge moves within noise at this sample size.",
    )
    _table_fig(
        "tbl4_datasets.png",
        "Three datasets, and they never trade places",
        "What each set is for, and what GEPA is allowed to see",
        ["Set", "Job", "Does GEPA see it?"],
        [["SOC 2 development set",
          "Built and tuned the graph and prompts;\nin-domain side of the transfer test",
          "Only indirectly: the seed\nprompt was written against it"],
         ["ISO 27001, re-cited\nto NIST controls",
          "Held-out framework for the transfer test,\nthen reused as GEPA's validation set",
          "Yes, as validation"],
         ["SOC 2 held-out tail",
          "The final gate; the winning candidate\nis checked here once, at the end",
          "Never"]],
        [0.20, 0.38, 0.30],
        accents={(2, 2): TEAL},
        caption="The set that gates the ship decision is the one nothing upstream ever optimized against.",
        mono_data=False, align="left", fontsize=12, row_h=0.95,
    )
    _table_fig(
        "tbl5_services.png",
        "One harness, one governed surface",
        "Each piece of the eval loop maps to a managed Databricks service, and each mapping closes a governance seam",
        ["Harness piece", "Databricks service", "What the mapping buys"],
        [["Corpus + golden sets", "Unity Catalog Delta tables",
          "Eval data carries the same permissions\nand lineage as production data"],
         ["Retrieval", "AI Search (Delta Sync index,\ngte-large-en embeddings)",
          "The index derives from the governed table,\nnot a copy in an outside vector store"],
         ["Drafting + judging", "Foundation Model APIs\n(gemini-2-5-flash drafts; a second judges)",
          "Control text never leaves the platform\nfor an external API key"],
         ["Model choice", "The same gateway: Claude, GPT,\nGemini, Llama, Qwen behind one interface",
          "Swap models per task without rewriting\nthe agent or moving the corpus"],
         ["Traces + scores", "Managed MLflow",
          "Every run records endpoint, dataset, and\nvariant next to its CLEAR-S scores"],
         ["Orchestration", "A Job",
          "The whole run, data load to GEPA,\nreproduces as one notebook"]],
        [0.17, 0.33, 0.36],
        caption="Assembled from separate products instead, every seam is a governance boundary the eval evidence must cross.",
        mono_data=False, align="left", fontsize=11.5, row_h=0.95,
    )


if __name__ == "__main__":
    two_traces()
    clears_radar()
    tables()
    for f in ("fig1_two_traces.png", "fig2_clears_radar.png",
              "tbl1_fix.png", "tbl2_transfer.png", "tbl3_models.png",
              "tbl4_datasets.png", "tbl5_services.png"):
        print("wrote", OUT / f)
