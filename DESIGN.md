# Design System — eval-harness

> **Memorable thing:** "Agents learn from their own failures here."
> Every typography, color, motion, and layout decision compounds toward the
> self-evolving payoff (Pareto frontier as the hero moment).

---

## Product Context

- **What this is:** Self-evolving eval harness for production AI agents. Pre-baked
  hero example = **Quill**, an RFP / security-questionnaire response agent.
- **Who it's for:** AI engineers, founders, eng leaders building or operating
  agentic systems. Both startups (selling upmarket) and enterprises (procurement).
- **Space:** Agent observability + evaluation + automated improvement.
  Peers: Phoenix, Arize, Langfuse, MLflow native UI, Datadog APM, Linear (visual).
- **Project type:** Web app with editorial moments. Next.js 15 (app router, RSC).
- **Trace inspection:** delegated to MLflow native UI — we link out from our run
  views to `http://mlflow-host/#/traces/{trace_id}`. We do **not** rebuild a
  trace tree.

## Aesthetic Direction

**"Compounding Instrument."** Graphite base + electric-mint signal. Editorial
seriousness, instrument-panel density, terminal-quiet authority.

- **Direction:** Phoenix/Arize density meets Linear discipline meets a faint
  Stripe-Atlas / Vercel-docs literary tone.
- **Decoration level:** intentional. Subtle 1px hairline grid background on
  hero canvases; sparkline ornaments on numeric headers; no decorative blobs;
  no gradients; no purple.
- **Mood:** A serious instrument that lights up when something improves.
  Calm by default. Visibly compounding over time.
- **Dark mode primary**, light mode secondary. True black canvas amplifies
  mint accent so improvement moments feel like instruments firing.
- **Reference visual language:**
  - Linear (sidebar nav + 12-col discipline + tabular legibility)
  - Vercel docs (serif display + mono data, restrained accent)
  - Phoenix / Arize / Langfuse (density patterns for trace + eval data)
  - Stripe Atlas / Pinecone docs (literary serif headlines in dev tooling)

## Typography

| Role | Font | Notes |
|---|---|---|
| Display / Hero | **Fraunces** (variable serif) | The literary risk. Optical-size + soft slant. Signals "thinks about agents like an editor thinks about prose." |
| Body / UI | **Geist Sans** (variable) | Dev-tool native. Variable axis for weight. |
| Data / Tables | **Geist Mono** | `font-variant-numeric: tabular-nums` on every score / latency / cost cell. |
| Code | **JetBrains Mono** | Trace payloads, prompts, GEPA diffs. |

**Loading:** Google Fonts via `next/font/google` for Fraunces, Geist Sans, Geist
Mono, JetBrains Mono. All self-hosted at build time (no runtime CDN dependency).

**Modular scale (px):** 12 · 14 · 16 · 18 · 20 · 24 · 32 · 48 · 64

**Default weights:**
- Fraunces: 400 (body display), 600 (h1/h2), wght-axis tween for hero moments
- Geist Sans: 400 (body), 500 (label), 600 (button), 700 (callout)
- Mono: 400 only

**Numeric rule:** all numbers in tables, badges, scores, costs, latencies,
percentages → `font-feature-settings: 'tnum' 1; font-variant-numeric: tabular-nums`.
Non-negotiable for column alignment.

## Color

**Approach:** restrained. Neutral graphite base + **one** signal accent
(electric mint) + categorical CLEAR-axis palette + semantic states.

### Dark mode (primary)

```
bg-canvas         #0A0A0A     true black, OLED-friendly
bg-surface        #18181B
bg-elevated       #27272A
text-primary      #FAFAF9
text-secondary    #D4D4D8
text-muted        #71717A
border            #27272A
border-strong     #3F3F46
```

### Light mode (secondary)

```
bg-canvas         #FAFAF9     warm white
bg-surface        #FFFFFF
bg-elevated       #F4F4F3
text-primary      #0A0A0A
text-secondary    #44403C
text-muted        #78716C
border            #E7E5E4
border-strong     #D6D3D1
```

### Signal accent (the self-evolving fingerprint)

```
accent-improved        #10F09C     electric mint
accent-improved-soft   rgba(16, 240, 156, 0.10)
accent-improved-ring   rgba(16, 240, 156, 0.35)
```

**Usage rule:** mint fires **only** when something improved — Pareto frontier
dots, GEPA-tuned column headers, score-lift indicators, regression-passed
badges, "+X%" deltas. Never on default UI chrome. Scarcity is the point.

### CLEAR axes (categorical, dark-mode hex)

```
correctness   #60A5FA      sky
latency       #A78BFA      violet
execution     #FBBF24      amber
adherence     #34D399      mint-leaf  (distinct from accent-improved)
relevance     #F472B6      rose
safety        #F87171      coral
cost          #FB923C      pumpkin
```

Each axis paired with a soft background variant at 12% alpha for chip fills.

### Semantic states

```
success   #10B981
warn      #F59E0B
error     #EF4444
info      #3B82F6
```

**Dark mode strategy:** redesign surfaces (not just invert). Reduce saturation
~15% on CLEAR axes and semantic states for dark backgrounds. Mint accent stays
at full saturation to preserve signal.

## Spacing

**Base unit:** 4px. **Density:** comfortable (not compact, not spacious).

```
xs    2px      hairlines, tight inline
sm    4px      icon-text gap
md    8px      chip padding y
lg    16px     standard component gap
xl    24px     section internal padding
2xl   32px     between subsections
3xl   48px     between major blocks
4xl   64px     page-section separation
5xl   96px     hero verticals only
```

## Layout

**Two modes, used deliberately:**

1. **Grid-disciplined** (app surfaces — `/eval`, `/results`, `/clusters`,
   `/optimize`, `/portability`):
   - Sidebar nav 240px fixed + 12-col content grid
   - Max content width 1440px
   - Page padding 24px (mobile) / 32px (≥1024)
2. **Editorial-asymmetric** (landing + `/pareto` + `/prompt-diff`):
   - Oversized chart with top-bleed
   - Captions hug the curve (Fraunces, 18px)
   - Annotated callouts pull-quote style
   - The Pareto page exists to be screenshot-able

**Sidebar nav order:** Examples · Runs · Clusters · Optimize · Pareto · Portability · Prompts · Settings.

**Border radius scale:**
```
xs    2px      badges
sm    4px      inputs, score chips
md    6px      buttons, cards
lg    8px      sections, panels
xl    12px     modals, hero cards, Pareto chart container
full  9999px   pill badges, avatar (rare)
```

## Motion

**Approach:** minimal-functional + **one** expressive moment.

```
duration-instant   50ms     instant routing, no page transitions
duration-micro     150ms    hover, focus, chip swap (DEFAULT)
duration-short     300ms    score-delta number tweens
duration-hero      400ms    Pareto frontier sweep ★
```

**Easing:**
```
ease-out    cubic-bezier(0.16, 1, 0.3, 1)     enter
ease-in     cubic-bezier(0.4, 0, 1, 1)        exit
ease-both   cubic-bezier(0.4, 0, 0.2, 1)      move
ease-hero   cubic-bezier(0.34, 1.56, 0.64, 1) Pareto sweep (slight overshoot)
```

**The expressive moment:** When `/pareto/[id]` loads, baseline cluster dots
appear instantly; then over 400ms the GEPA frontier curve sweeps from origin
outward with `ease-hero`, mint-colored, ending with a 200ms ring-pulse on
each frontier dot. This is the **only** choreographed animation in the app.
Reserved for the climax.

**No page transitions.** Instant routing. The instrument feels responsive,
not theatrical.

## Component conventions

- **Score chip:** mono numeric + 1px border in CLEAR-axis color + 12% bg fill.
  Tabular-nums. Delta variant: prefix `▲`/`▼` in mint (improved) or red (regressed).
- **Run badge:** rounded-sm pill, status colors (running=info, passed=success,
  failed=error, optimizing=accent-improved with subtle pulse).
- **Pareto dot:** filled circle for non-dominated, hollow ring for dominated,
  mint stroke for GEPA-tuned, graphite stroke for baseline.
- **Cluster card:** elevated surface, CLEAR axis as left rule (4px), count + sample.
- **Prompt diff:** Geist Mono, side-by-side, mint for additions, red for removals,
  neutral for context. Inline annotations in Fraunces 14px.

## Safe choices (category baseline)

1. **Sidebar nav + 12-col grid.** Linear/Phoenix/Arize convention. Orients
   new users in seconds. Don't reinvent navigation.
2. **Tabular-nums monospace in score/cost/latency cells.** Every observability
   tool does this. Non-negotiable for column legibility.

## Risks (where eval-harness gets its face)

1. **Serif display (Fraunces).** Observability tools are uniformly sans-serif.
   Serif headlines signal an editorial seriousness. Pairs with the talk's
   literary framing ("Journey of an Agent").
2. **Electric mint (#10F09C) as singular accent.** Phoenix=purple, Arize=orange,
   Langfuse=neutral, Datadog=purple. Mint reads as "growing/learning" and
   points at the self-evolving thesis. Used scarcely so it always means
   "improvement."
3. **True black (#0A0A0A) dark mode.** Not zinc-950. OLED-friendly, terminal-like,
   amplifies mint signal. Trades soft contrast for stage-projector punch.

## Coherence

Serif display + dev-mono data is the Stripe/Vercel-docs literary pattern.
True-black canvas amplifies the mint accent so improvement moments feel like
instruments lighting up. Editorial layout on Pareto page makes the climax feel
earned vs algorithmic. Grid-disciplined app surfaces keep daily use legible.

## Anti-patterns (never ship)

- Purple/violet anywhere (reserved exclusively for `latency` axis chip, never UI chrome)
- Gradient backgrounds, gradient buttons, gradient text
- 3-column SaaS-feature grid with icons in colored circles
- Centered hero with uniform spacing
- Bubble-radius (`9999px`) on cards or buttons
- Inter, Roboto, Space Grotesk, system-ui as primary fonts
- "Built for X / Designed for Y" marketing copy
- Decorative blobs, mesh gradients, abstract 3D renders
- Stock-photo-style hero illustrations
- Sans-serif headlines on landing page
- Mint accent on anything that isn't an improvement signal

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-05-26 | Initial design system | Created by /design-consultation. Memorable thing: "agents learn from their own failures here." Trace UI delegated to MLflow. |
