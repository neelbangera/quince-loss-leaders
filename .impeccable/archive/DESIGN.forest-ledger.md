---
name: Quince Ledger
description: Forest ink on pale green paper. Editorial claim, monospace evidence.
colors:
  ink: "#18241f"
  muted: "#53635b"
  line: "#d6e0da"
  line-strong: "#b8cec0"
  row-line: "#edf1ee"
  paper: "#f2f6f3"
  surface: "#ffffff"
  soft: "#e4ebe6"
  forest: "#254d3e"
  on-forest: "#ffffff"
  red: "#ad463d"
  gold: "#a47c35"
  gold-text: "#805c18"
  ink-accent: "#a44b2b"
  ink-muted: "#766f67"
  image-surface: "#f7f4ed"
  image-line: "#e2d9cc"
  image-ink: "#6b5a48"
  drawer: "#f8f5ef"
  drawer-fill: "rgba(255, 255, 255, 0.5)"
  drawer-total: "rgba(232, 220, 190, 0.28)"
  focus-ring: "#254d3e"
  focus-soft: "#dceee2"
  status: "#4d9368"
  component-increase: "#a44b2b"
  component-decrease: "#39715c"
typography:
  display:
    fontFamily: "Source Serif 4, Georgia, serif"
    fontSize: "clamp(28px, 2.8vw, 40px)"
    fontWeight: 600
    lineHeight: 1.02
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Public Sans, sans-serif"
    fontSize: "18px"
    fontWeight: 400
    letterSpacing: "-0.02em"
  body:
    fontFamily: "Public Sans, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "IBM Plex Mono, monospace"
    fontSize: "11px"
    fontWeight: 500
    letterSpacing: "0.12em"
  figure:
    fontFamily: "IBM Plex Mono, monospace"
    fontSize: "12px"
    fontWeight: 500
rounded:
  control: "6px"
  card: "10px"
  panel: "16px"
  pill: "99px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
components:
  button-primary:
    backgroundColor: "{colors.forest}"
    textColor: "{colors.on-forest}"
    rounded: "{rounded.control}"
    padding: "9px 16px"
  field:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    height: "38px"
  panel:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
    padding: "22px"
  chip:
    backgroundColor: "{colors.soft}"
    textColor: "{colors.forest}"
    rounded: "{rounded.pill}"
    padding: "5px 8px"
---

# Quince Ledger

## Overview

Forest ink on pale green paper. A serif states the claim, a monospace states the
evidence, and the space between them is where the product lives. The page is
mostly rules and whitespace: containers are defined by hairlines, not by shadow
or fill, and the one material change in the whole interface is the drawer, which
opens on a warmer paper than the catalog it covers.

The tone is that of a ledger kept by hand — measured, warm, a little literary.
Numbers carry their unit ("display groups"), caveats are printed next to the
thing they qualify rather than hidden in a footnote, and colour is reserved for
meaning.

**Key characteristics**
- Source Serif 4 for the masthead claim and the product name; IBM Plex Mono for every
  number and label; Public Sans for prose and controls.
- Three surfaces only — paper, surface, soft — and hairlines do the rest.
- Semantic colour with one job each: green is positive, red is loss, gold is
  uncertain.

## Colors

Three surfaces, one ink, one accent family. The CSS names are the source of
truth; they are listed here with their role.

### Surfaces
- **paper** (#f2f6f3) — the page ground.
- **surface** (#ffffff) — panels, cards, table rows.
- **soft** (#e4ebe6) — table headers, segmented-control tracks, hover, image wells'
  surrounding chrome. One visible step below surface, not a near-white.

### Ink
- **ink** (#18241f) — primary text, a near-black with green in it.
- **muted** (#53635b) — secondary text and labels.
- **ink-muted** (#766f67) — the drawer's warmer secondary text. The neutral
  changes temperature at the drawer boundary on purpose: the drawer is a
  different material.
- **line** (#d6e0da) / **row-line** (#edf1ee) / **line-strong** (#b8cec0) — container
  edges, row dividers, hovered card edges.

### Semantic
- **forest** (#254d3e) — positive spread, eyebrows, links, the primary button, chart
  price line. The one accent.
- **red** (#ad463d) — negative spread and negative margin. Nothing else.
- **gold** (#a47c35) / **gold-text** (#805c18) — fee warnings, mixed and zero values,
  cost-change annotations. Two weights of one voice: the bright value is for
  chart lines and swatches, the dark value for any glyph small enough to need
  4.5:1.
- **component-increase** (#a44b2b) / **component-decrease** (#39715c) — movement in a
  *cost* line. Deliberately the inverse of the spread colours, because here the
  colour describes a change, not a value.

## Typography

**Display:** Source Serif 4 (fallback Georgia, serif) — a plain text serif, no thick/thin drama
**Body:** Public Sans (fallback sans-serif) — a neutral grotesque
**Label / figure:** IBM Plex Mono (fallback monospace) — instrument mono

Five sizes, two trackings. 11px for labels and eyebrows, 12px for secondary text
and figures, 15px for prose and product titles, 18px for section headings, 22px
for panel headings. The masthead and drawer title use `clamp()`.

Labels are IBM Plex Mono, uppercase, tracked 0.12em. Headings are tracked -0.02em.
Nothing else carries tracking.

Source Serif is reserved for a claim: the masthead claim, the Method page's
opening statement, and the product name in the drawer. Every number is
monospace, including the summary figures.

## Layout

A centred shell at `min(1440px, calc(100% - 64px))`. The top of the page is the
claim — display statement, one line of hero text, and a mono capture stamp
("Last capture · Aug 29, 2026") set under the claim like a provenance mark on a
document. Then a summary strip, then the workspace. Nothing else sits beside the
claim: coverage and disclosure caveats live where they qualify the numbers.

The workspace is a two-column row: a 260px sticky filter rail beside a fluid
results panel. Only the table scrolls horizontally; no ancestor of it does.

At 900px the shell narrows, the masthead stacks, and the filter rail becomes a
full-width band above the results. At 560px the display drops to 22px-equivalent,
the topbar wraps, and the summary strip's total takes a leading row.

## Elevation & Depth

No shadows on resting elements. Depth is hairlines and the three-step surface
ladder. Two shadows exist and both are responses to state: a tight 2px lift on an
active segmented control, and a directional shadow on the drawer, which has to
read as a sheet laid over the catalog.

## Shapes

Four radii: 6px for controls and fields, 10px for cards and the brand mark, 16px
for major panels, 99px for pills and loading bars. Focus outlines use 4px;
status dots are circles.

## Components

### Buttons
Flat forest fill, 6px radius, 12px Public Sans. Ghost buttons are forest text with no
border. Segmented controls sit in a soft track with a 6px inner radius; the active
segment takes a surface fill and the 2px lift.

### Fields
Surface fill, 1px line border, 6px radius, 38px tall. Focus shifts the border to
forest and adds a 2px `focus-ring` outline.

### Summary strip
A hairline-ruled tally across the top of the workspace: the total with its unit
("4,083 display groups"), then loss / positive / break-even / mixed, each as a
mono figure over a small uppercase label, separated by 1px rules. It is a
statement about the catalog, not a control — the tabs below do the filtering.
Under the strip runs one quiet 12px legend line: the counting grain, the
loss/mixed definitions, the tab-versus-tally difference in real numbers when it
applies, and a link to the Method page. It is a legend, never a paragraph.

### Method page
A reading page, not a second dashboard. Serif claim at the top, then paired
sections: a mono eyebrow and 18px heading in a 260px rail, prose in a 68ch
column. Definition rows are hairline-ruled with the term in forest mono caps.
The page owns the disclosure basis, the counting and classification rules, the
identity rules, the fee guardrail, the change ledger, and the limits — printed
once, with authority, instead of scattered as caveats.

### Table
Mono figures, Public Sans product cell. Headers on soft; rows ruled with row-line;
hover to soft. Sortable headers carry `aria-sort` and turn forest when active.
Long names truncate with an ellipsis and keep their fee marker outside the
truncating element so a warning is never clipped away.

### Drawer
A warm sheet over the catalog: `drawer` ground, its own warmer secondary ink,
hairline-separated cost rows on translucent fills, and a hand-built SVG timeline
plotted on elapsed time, not index. Below the current breakdown sits the change
ledger — a dated list of moves between captures, each showing the amounts on
either side and the signed delta. Product photography sits in a light well with
`mix-blend-mode: multiply` so white packshots don't punch a hole in the paper.

## Do's and Don'ts

**Do**
- State the unit next to any count. A number without its grain is a guess.
- Let a hairline do the work before reaching for a fill, a shadow, or a new tone.
- Keep colour semantic: green positive, red loss, gold uncertain.
- Print a caveat beside the thing it qualifies.
- Keep every number in monospace.

**Don't**
- Add a fourth surface tone. Three is the whole ladder.
- Add tracking to anything that isn't an uppercase mono label, or use a size
  outside 11 / 12 / 15 / 18 / 22 and the two clamps.
- Use the serif for anything but the claim and the product name.
- Put a shadow on a resting element.
- Present a count without saying what was counted.
