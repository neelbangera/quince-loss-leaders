---
name: Quince Ledger
description: A prep mail-order catalog whose order form prints what each item cost to make.
colors:
  paper: "#ffffff"
  chino: "#f3eee4"
  chino-deep: "#e4dccb"
  navy: "#12213f"
  navy-deep: "#0b1730"
  on-navy: "#ffffff"
  slate: "#566079"
  rule: "#d5d9e2"
  rule-soft: "#e9ebf0"
  crimson: "#9b1b30"
  crimson-wash: "#f8e9eb"
  hunter: "#1d5a3c"
  hunter-wash: "#e6f0ea"
  gold: "#b48a2c"
  gold-ink: "#76570f"
  gold-wash: "#f6efdc"
  blazer-paper: "#0d1730"
  blazer-surface: "#142142"
  blazer-ink: "#f2efe8"
  blazer-slate: "#aab3c8"
  blazer-rule: "#2c3a5e"
  blazer-crimson: "#f2909c"
  blazer-hunter: "#86cba2"
  blazer-gold: "#e2c476"
typography:
  display:
    fontFamily: "Libre Caslon Display, Libre Caslon Text, Georgia, serif"
    fontSize: "clamp(36px, 4.2vw, 60px)"
    fontWeight: 400
    lineHeight: 1.02
    letterSpacing: "-0.01em"
  headline:
    fontFamily: "Libre Caslon Text, Georgia, serif"
    fontSize: "26px"
    fontWeight: 400
    lineHeight: 1.2
  caption:
    fontFamily: "Libre Caslon Text, Georgia, serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.45
  title:
    fontFamily: "Jost, Futura, Century Gothic, sans-serif"
    fontSize: "14px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "0.04em"
  body:
    fontFamily: "Jost, Futura, Century Gothic, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Jost, Futura, Century Gothic, sans-serif"
    fontSize: "11px"
    fontWeight: 600
    letterSpacing: "0.1em"
  figure:
    fontFamily: "Jost, Futura, Century Gothic, sans-serif"
    fontSize: "14px"
    fontWeight: 500
    fontFeature: "tnum"
rounded:
  none: "0"
  swatch: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  2xl: "40px"
  3xl: "64px"
components:
  masthead:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.navy}"
    height: "76px"
  button-primary:
    backgroundColor: "{colors.navy}"
    textColor: "{colors.on-navy}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    height: "44px"
    padding: "0 24px"
  button-primary-hover:
    backgroundColor: "{colors.navy-deep}"
  button-secondary:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.navy}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    height: "44px"
    padding: "0 24px"
  field:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.navy}"
    rounded: "{rounded.none}"
    height: "44px"
    padding: "0 12px"
  flag-below:
    backgroundColor: "{colors.crimson}"
    textColor: "{colors.on-navy}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "3px 7px"
  flag-above:
    backgroundColor: "{colors.hunter-wash}"
    textColor: "{colors.hunter}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "3px 7px"
  flag-varies:
    backgroundColor: "{colors.gold-wash}"
    textColor: "{colors.gold-ink}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "3px 7px"
  catalog-item-well:
    backgroundColor: "{colors.chino}"
    rounded: "{rounded.none}"
---

# Design System: Quince Ledger

## Overview

**Creative North Star: "The Mail-Order Catalog"**

Quince Ledger looks like a prep clothier's mail-order catalog from the late
1980s: white uncoated paper, navy ink, tall product photographs, a Caslon
headline, and Futura-style capitals for everything a shopper has to find fast.
The ranking is a catalog spread. The table view is the catalog's order form.
The one thing this catalog prints that no retailer's does is the cost: beside
every price sits what Quince reports the item cost to make, and the gap.

The page is a shop first and an analysis second. Product photography is the
only decoration, and the page stays quiet so the photographs and three
school colours can do the work: crimson for below cost, hunter green for above,
old gold for anything uncertain. Navy is the ink, never a meaning.

It replaces the earlier "forest ledger" system (archived in
`.impeccable/archive/`). Several of that system's rules were about honesty
rather than looks and carry over unchanged: every count states its unit, a
caveat is printed beside the thing it qualifies, each colour has one job, and
a fee warning is never clipped away by truncation.

**Key Characteristics:**
- White paper, navy ink, square corners, hairline rules. No cards, no shadows at rest.
- Caslon for headlines and italic captions; Jost for names, labels, controls and figures.
- Photographs sit in a chino well; nothing else on the page is tinted.
- Three school colours, one meaning each: crimson below cost, hunter above, gold uncertain.
- A plain white header with a centred Caslon wordmark, like a shop. No coloured bar, no stripes.

## Colors

White paper and navy ink, with three school colours reserved for meaning.

### Primary
- **Blazer Navy** (`navy`): all text, the wordmark, primary buttons, table head rules, the price line in charts. It is ink, so it carries no meaning.
- **Deep Navy** (`navy-deep`): hover and pressed state of navy fills only.

### Secondary
- **Varsity Crimson** (`crimson`, `crimson-wash`): below cost. The "Below cost" flag, a negative gap, the overhang in the price-and-cost tally. The wash is the row tint when a flagged row is hovered or selected.
- **Hunter Green** (`hunter`, `hunter-wash`): above cost. Positive gap and its flag.

### Tertiary
- **Old Gold** (`gold`, `gold-ink`, `gold-wash`): uncertain. Mixed groups, break-even, flagged fees, and the reported-cost line in charts. `gold` is for graphics; `gold-ink` is the only gold allowed on text.

### Neutral
- **Paper** (`paper`): the page. Pure white, not cream.
- **Chino** (`chino`, `chino-deep`): the well behind every product photograph, loading placeholders, and the reported-cost bar in the tally. Nothing else.
- **Slate** (`slate`): secondary text, a navy-tinted grey.
- **Rule** (`rule`, `rule-soft`): field borders and section rules; row rules in the order form.
- **Blazer theme** (`blazer-*`): the dark theme is a navy blazer, not a black screen. Paper becomes `blazer-paper`, raised surfaces `blazer-surface`, ink `blazer-ink`, and the three school colours lift to their `blazer-` values. Photo wells stay chino in both themes so packshots never sit on navy.

### Named Rules
**The School Colours Rule.** Crimson means below cost, hunter means above cost, gold means uncertain. None of the three is ever used for decoration, links, or emphasis.

**The Word-With-Colour Rule.** A coloured figure always carries a sign or a word ("−$5.99 below cost"). Colour alone never says which side of cost an item is on.

**The Cost-Moves-In-Ink Rule.** Movement in a cost line (materials up, freight down) is shown with a signed amount and an arrow in navy, not in crimson or hunter. Those colours describe the gap, not a change.

## Typography

**Display Font:** Libre Caslon Display (with Libre Caslon Text, Georgia, serif)
**Body Font:** Jost (with Futura, Century Gothic, sans-serif)
**Label/Mono Font:** none. There is no monospace in the system.

**Character:** Caslon is the university press and the catalog cover; Jost is the geometric sans that prep catalogs set product names and prices in. Serif for what is said, sans for what is found.

### Hierarchy
- **Display** (400, clamp 36–60px, 1.02): the wordmark, the page headline, the product name on the product page. One per screen.
- **Headline** (Caslon Text 400, 26px, 1.2): section headings and the Method page's headings.
- **Caption** (Caslon Text italic, 14px, 1.45): colour and size lines under a product ("In Big Sur Green · XS"), provenance notes, definitions. Italic is its only form.
- **Title** (Jost 600, 14px, uppercase, 0.04em): product names in the grid and the order form.
- **Body** (Jost 400, 15px, 1.55): prose and control text. Maximum line length 68ch.
- **Label** (Jost 600, 11px, uppercase, 0.1em): department navigation, column heads, flags, button text.
- **Figure** (Jost 500, 14px, tabular numerals): every price, cost, gap and count. Right-aligned in columns.

### Named Rules
**The No-Label-Above-A-Heading Rule.** A heading is never preceded by a small capitalised kicker. If a section needs a name, the heading is the name.

**The Caps-Are-For-Finding Rule.** Uppercase is used only for things a shopper scans for: navigation, product names, column heads, flags, buttons. Sentences are never set in capitals.

## Layout

A plain white header, then a centred page at
`min(1360px, 100% - 64px)`. Under the header runs the department row, centred, which
is the shop's main navigation (All, Women, Men, Home, Baby & Kids). Below it:
the page headline with the catalog's tally in one sentence, then a 220px
category rail beside the results.

Results default to the catalog grid: four items per row, five at 1500px and
wider, three at 900px, two on phones. Photographs are 4:5. The order-form view
uses the same width as a single ruled table and is the only element allowed to
scroll sideways. Spacing follows one scale (4, 8, 12, 16, 24, 40, 64); gaps
between grid items are 24px across and 40px down, so a row reads as a row.

At 900px the category rail folds into a "Filter" control above the results.
At 620px the department row scrolls horizontally and the header keeps only
the wordmark and its two links.

## Elevation & Depth

Flat. Paper has no shadow and nothing floats at rest; separation comes from
white space, hairline rules and the chino photo well.

### Shadow Vocabulary
- **Product page sheet** (`box-shadow: -24px 0 60px rgba(11, 23, 48, 0.22)`): the product page that slides over the catalog. The only shadow in the system.

### Named Rules
**The Paper-Is-Flat Rule.** No shadow, lift, or scale on hover. A hovered catalog item swaps to its second photograph and underlines its name.

## Shapes

Square. Every box, button, field, flag and photograph has a 0 radius, like
trimmed paper. The only round shapes are colour swatches and radio dots.
Borders are 1px; the order form's head is ruled 2px navy above and 1px below.
There is no ornament: no stripe, ribbon, crest or coloured band.

## Components

### Masthead
White, 76px. The wordmark sits centred in navy Caslon Display, the last-capture
date on the left in slate, and text links (Method, theme) on the right in label
type. No coloured bar, no stripes, no logo box, no status dot. (A navy band
with a rep-stripe ribbon was tried and rejected on 2026-10-08.)

### Department row and view tabs
Label type, navy, in a single ruled row. The active item has a 2px navy
underline and nothing else. View tabs (Below cost / Above cost / Everything)
use the same treatment one size up, with their counts in slate.

### Buttons
- **Shape:** square, 44px tall.
- **Primary:** navy fill, white label type. Hover is deep navy.
- **Secondary:** paper fill, 1px navy border, navy label type. Hover fills chino.
- **Text link:** body type, navy, underlined with a 3px offset. Used for Reset, Retry, and "How this is calculated".
- **Focus:** 2px navy outline, 2px offset.

### Inputs / Fields
Paper fill, 1px rule border, square, 44px. The label sits above in label type.
Focus turns the border navy and adds the focus outline. Category filters are a
plain list of links with counts, not a dropdown.

### Flags
Small square labels that say which side of cost an item is on: "Below cost"
(white on crimson), "Above cost" (hunter on hunter wash), "Varies" and "Fee
flagged" (gold ink on gold wash). They sit on the photograph's top-left corner
in the grid and beside the name in the order form.

### Catalog item
A 4:5 photograph in a chino well with no border, then, on paper: the product
name in title type, an italic Caslon line for colours and sizes, and a price
line: the selling price in navy figures, "costs Quince $47.99" in slate, and
the gap in its school colour. No card outline and no background behind the
text.

### Order form (table)
One ruled table. Column heads in label type, sortable, with a drawn arrow on
the active column. Rows are 1px soft rules with a 40×50 thumbnail, the name in
title type, and right-aligned tabular figures. No zebra stripes, no pills.
Hover tints the row chino.

### Price-and-cost tally
The signature component, on the product page. Two horizontal bars on one
scale: "You pay" in navy and "Quince reports it costs" in chino-deep. When the
cost is longer, the overhang is crimson and labelled with the gap. Below it
the reported cost lines are an itemised list ending in a ruled total.

### Product page (drawer)
A full-height paper sheet from the right, 720px wide: photographs first, then
the name in display type, the tally, the cost lines, the change ledger (dated
moves with both amounts and a signed difference), and the price and cost
timeline plotted on elapsed time.

### Method page
The catalog's back pages. Caslon headlines, body prose at 68ch, definitions as
a ruled two-column list with the term in title type.

### States
- **Loading:** chino blocks in the shape of the content that is coming. No spinner.
- **Empty:** one sentence in headline type and a text link to reset.
- **Error:** one sentence naming what failed and a secondary Retry button.

## Do's and Don'ts

### Do:
- **Do** print the reported cost beside every price, and the unit beside every count ("4,083 styles at one price").
- **Do** keep the page white. Chino belongs behind photographs only.
- **Do** put a sign or a word with every coloured figure.
- **Do** keep a fee warning outside any element that truncates.
- **Do** set every number in Jost with tabular numerals, right-aligned in columns.
- **Do** keep the product-page dialog keyboard-operable and every text pairing at 4.5:1 or better in both themes.

### Don't:
- **Don't** round a corner, add a shadow at rest, or draw a card around a group.
- **Don't** put a small capitalised label above a heading.
- **Don't** use monospace, a status dot, a pill, or a letter-in-a-box logo.
- **Don't** put a coloured band or stripes across the top of the page.
- **Don't** use crimson, hunter or gold for anything except their meaning.
- **Don't** use a cream or tinted page ground in the light theme.
- **Don't** describe a negative gap as Quince losing money overall; it is the gap against the costs Quince discloses, nothing more.
