"""Generate the diagram figures as SVG via Claude Fable 5 on Databricks FMAPI.

Fable 5 is a text model: it authors SVG markup, which we render to PNG with
rsvg-convert. Table figures stay in make_figures.py (exact digits must come
from code, not a model). House style is enforced through the prompt.

    python docs/figures/gen_fable_figures.py [fig3|fig4|fig5 ...]

Auth: Databricks CLI profile `e2-demo-west` (the lakebase workspace lists the
endpoint but its invocation route is not provisioned); endpoint
`databricks-claude-fable-5`.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import requests

OUT = Path(__file__).resolve().parent
PROFILE = "e2-demo-west"
HOST = "https://e2-demo-west.cloud.databricks.com"
ENDPOINT = "databricks-claude-fable-5"

STYLE = """\
House style, follow it exactly:
- Canvas: 1600x900, viewBox="0 0 1600 900", plain white background.
- Palette: charcoal #1f2933 for text and rules; ONE accent, muted teal #10b981,
  reserved strictly for the signal named below; neutral gray #9aa5b1 for
  secondary elements; amber #d97706 only where the brief says; light #e4e7eb
  for faint grid/fills. No other colors, no gradients, no shadows, no 3D.
- Type: body text font-family="Charter, Georgia, serif"; identifiers and
  technical labels font-family="SF Mono, Menlo, monospace". Title 34px bold,
  top-left. One-line gray footnote 17px at the bottom-left.
- Lines 1.5-2px. Rounded rects (rx 10). Arrowheads via a single <marker> def
  per color used. Flat, publication-quality, generous whitespace.
- Output ONLY the SVG markup, nothing else. No external images, no scripts.
- Every text element must fit inside its container: keep labels short, size
  boxes generously, never let text overlap a line or another box."""

BRIEFS = {
    "fig3": (
        "fig3_architecture",
        f"""Draw a flat vector architecture diagram titled "One governed system, not a stitch-job".
{STYLE}

Content brief:
- Subtitle line under the title (17px, charcoal): "Every component of the eval
  loop, and every piece of eval evidence, sits inside the same Unity Catalog
  permission boundary."
- A large dashed TEAL rounded rectangle encloses everything below; label its
  top-left edge "Unity Catalog · governance + lineage" (teal, bold, 19px) and
  its bottom-right inside edge with monospace teal 14px:
  "one permission model, one governed boundary".
- Main left-to-right pipeline of five boxes connected by gray arrows, centered
  vertically inside the boundary. Each box: bold 19px serif title, 13px gray
  monospace sublabel below it.
  1. "NIST SP 800-53 Rev5" / "public catalog" (gray outline)
  2. "Delta tables" / "corpus · golden"
  3. "AI Search" / "Delta Sync · gte-large-en"
  4. "LangGraph agent" / "parse · classify · retrieve | propose · verify · finalize" (two mono lines, slightly heavier outline)
  5. "Managed MLflow" / "traces + CLEAR-S"
- Above box 4: a gray-outlined box "Foundation Model APIs" / "Claude · GPT · Gemini · Llama · Qwen",
  connected to box 4 with a vertical double-headed gray arrow.
- Below box 5: a gray-outlined box "DSPy + GEPA" / "optimizer · runs as a Job",
  connected from box 5 with a downward gray arrow.
- One TEAL curved arrow (2px) from the DSPy + GEPA box sweeping left and up to
  the bottom of the "Delta tables" box, routed through the empty space below
  the main pipeline. Italic teal label near its midpoint:
  "production failures become regression cases".
- Footnote: "Assembled from separate products, every seam between two of these
  boxes is a governance boundary the eval evidence has to cross." """,
    ),
    "fig4": (
        "fig4_scorer_funnel",
        f"""Draw a flat vector pipeline diagram titled "Each scorer layer is blind to a different failure".
{STYLE}

Content brief:
- Subtitle line under the title (17px, charcoal): "The layers run cheapest
  first. The unverified citation looks perfect to the cheapest layer; only the
  trace catches it."
- Four wide stacked boxes, centered, top to bottom with small gaps, each with a
  bold 20px serif title and a 13px gray monospace sublabel:
  1. "1 · Deterministic checks" / "milliseconds · format, budget, ID resolves" (gray outline)
  2. "2 · Trajectory checks" / "the trace · was every citation verified?" (TEAL outline 2.5px, very light teal #e7f8f1 fill)
  3. "3 · LLM judge" / "does the control support the claim?" (light #e4e7eb outline, light gray text: never reached)
  4. "4 · Safety" / "injection, PII, refusal" (light outline, light text)
- On the left, an AMBER monospace token label "cites SC-7, never verified"
  above an amber path: arrow down, arrow right into box 1, then down, then
  arrow right into box 2, where it stops at a bold TEAL multiplication sign ×.
- Right of box 1, amber italic 15px note: "passes · well-formed, control resolves".
- Right of box 2, teal bold italic 15px note: "stopped · the verifier never ran".
- Right of boxes 3-4, light gray italic 15px: "never reached".
- Footnote: "On the NIST run both agents scored 1.00 on layer 1: every cited
  control is real. Only layer 2 separates verified from guessed." """,
    ),
    "fig5": (
        "fig5_loop",
        f"""Draw a flat vector cycle diagram titled "CI for agent behavior".
{STYLE}

Content brief:
- Subtitle line under the title (17px, charcoal): "Seven stages, one governed
  surface. The arrow back from monitor is the point: a production failure
  re-enters as a regression case."
- Seven boxes arranged clockwise on an ellipse (start at top, leave the center
  empty), each with a bold 19px serif title and a 12.5px gray monospace
  sublabel:
  1. "trace" / "managed MLflow tracing" (top)
  2. "score" / "genai.evaluate · CLEAR-S"
  3. "cluster failures" / "judge feedback · MLflow"
  4. "optimize" / "DSPy + GEPA on a Job"
  5. "gate" / "held-out, never tuned on"
  6. "ship" / "Model Serving"
  7. "monitor" / "inference tables" (TEAL outline, teal title)
- Curved gray arrows connect each box to the next (1→2→...→7), clearly not
  touching the boxes.
- One thicker TEAL curved arrow from "monitor" back to "trace", with a
  two-line italic teal label above it: "production failures become" /
  "tomorrow's regression cases".
- No footnote needed; keep the center of the ellipse empty.""",
    ),
}


def token() -> str:
    out = subprocess.run(["databricks", "auth", "token", "-p", PROFILE],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)["access_token"]


def generate(key: str, tok: str) -> Path:
    fname, brief = BRIEFS[key]
    r = requests.post(
        f"{HOST}/serving-endpoints/{ENDPOINT}/invocations",
        headers={"Authorization": f"Bearer {tok}"},
        json={"messages": [{"role": "user", "content": brief}],
              "max_tokens": 16000},
        timeout=600,
    )
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    if isinstance(content, list):  # Fable 5 returns reasoning + text blocks
        text = "".join(b.get("text", "") for b in content if b.get("type") == "text")
    else:
        text = content
    m = re.search(r"<svg.*</svg>", text, re.S)
    if not m:
        raise RuntimeError(f"{key}: no SVG in response:\n{text[:400]}")
    svg = OUT / f"{fname}.svg"
    svg.write_text(m.group(0))
    png = OUT / f"{fname}.png"
    subprocess.run(["rsvg-convert", "-w", "1600", "-h", "900",
                    "-b", "white", "-o", str(png), str(svg)], check=True)
    print("wrote", png)
    return png


if __name__ == "__main__":
    keys = sys.argv[1:] or list(BRIEFS)
    tok = token()
    for k in keys:
        generate(k, tok)
