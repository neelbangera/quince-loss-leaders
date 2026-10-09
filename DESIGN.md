---
name: Quince Ledger
description: A white-shirt retail catalog that prints what each item cost to make beside its price.
colors:
  paper: "#ffffff"
  ink: "#1b1b19"
  soft: "#6b6b66"
  rule: "#d9d9d3"
  rule-soft: "#ecece7"
  well: "#eef1f5"
  hover: "#f6f6f2"
  claret: "#7d1d2f"
  stripe: "#9db4d3"
  night-paper: "#131412"
  night-ink: "#efebe2"
  night-soft: "#a5a49c"
  night-rule: "#3a3b35"
  night-rule-soft: "#262722"
  night-well: "#e9ecf0"
  night-hover: "#1c1d1a"
  night-claret: "#eba0aa"
  night-stripe: "#5d77a0"
typography:
  display:
    fontFamily: "EB Garamond, Garamond, Georgia, serif"
    fontSize: "clamp(40px, 5vw, 68px)"
    fontWeight: 400
    lineHeight: 1.02
    letterSpacing: "-0.01em"
  wordmark:
    fontFamily: "EB Garamond, Garamond, Georgia, serif"
    fontSize: "34px"
    fontWeight: 400
    lineHeight: 1
    letterSpacing: "0.01em"
  headline:
    fontFamily: "EB Garamond, Garamond, Georgia, serif"
    fontSize: "26px"
    fontWeight: 400
    lineHeight: 1.2
  name:
    fontFamily: "EB Garamond, Garamond, Georgia, serif"
    fontSize: "21px"
    fontWeight: 400
    lineHeight: 1.2
  caption:
    fontFamily: "EB Garamond, Garamond, Georgia, serif"
    fontSize: "16px"
    fontStyle: "italic"
    fontWeight: 400
  body:
    fontFamily: "Hanken Grotesk, Helvetica Neue, Arial, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Hanken Grotesk, Helvetica Neue, Arial, sans-serif"
    fontSize: "11px"
    fontWeight: 600
    letterSpacing: "0.09em"
  figure:
    fontFamily: "Hanken Grotesk, Helvetica Neue, Arial, sans-serif"
    fontSize: "16px"
    fontWeight: 500
    fontFeature: "tnum"
rounded:
  none: "0"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "28px"
  2xl: "56px"
  3xl: "72px"
components:
  search-field:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    height: "40px"
    width: "220px"
    padding: "0 12px 0 34px"
  button-outline:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "14px 26px"
  button-outline-hover:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
  photo-well:
    backgroundColor: "{colors.well}"
    rounded: "{rounded.none}"
---

# Design System: Quince Ledger

## Overview

**Creative North Star: "The White Oxford Shirt"**

Quince Ledger looks like the website of a quiet, well-made clothing brand:
white page, near-black ink, a Garamond wordmark centred in the masthead, large
product photographs, and almost nothing else. The photographs carry all the
colour. The one thing this shop prints that a retailer's does not is the cost:
beside every price sits what Quince reports the item cost to make, and the
difference between the two.

The reference implementation is `mockups/session-a/index.html`. Where this
document and that mockup disagree, raise it; do not guess.

It replaces two earlier systems, both archived in `.impeccable/archive/`: the
"forest ledger" and the navy "mail-order catalog". Rules about honesty carry
over from both: every count states its unit, a caveat is printed beside the
thing it qualifies, and a coloured figure always carries a word.

**Key Characteristics:**
- White paper, near-black ink, square corners, hairline rules. No cards, no pills, no shadows at rest, no side rail.
- EB Garamond for the wordmark, headlines, product names and italic captions; Hanken Grotesk for labels, controls and every figure.
- One colour with a meaning: claret marks below cost. Nothing else on the page is coloured.
- A fine blue shirt stripe under the masthead is the only ornament.
- The difference against cost is the figure that matters; Quince's cost is printed in grey beside the price.

## Colors

White paper and near-black ink, with one colour reserved for one meaning.

### Primary
- **Claret** (`claret`): below cost, and nothing else. The difference line on an item, the difference columns in the list, the shortfall strip and the "Below cost by" total on the product sheet.

### Tertiary
- **Oxford Stripe** (`stripe`): the 1px lines of the shirting band under the masthead. Ornament only; used nowhere else.

### Neutral
- **Paper** (`paper`): the page. Pure white, never cream or tinted.
- **Ink** (`ink`): all primary text, the price, the rule that opens the toolbar, outlined buttons, the active underline on tabs and switches.
- **Soft** (`soft`): secondary text, labels, captions, and Quince's reported cost wherever it sits beside a price.
- **Rule** (`rule`, `rule-soft`): section rules and field borders; row rules in the list.
- **Well** (`well`): the ground behind a photograph while it loads or when none was captured. Nothing else.
- **Hover** (`hover`): the tint on a hovered list row.
- **Night theme** (`night-*`): the dark theme is the same page at night. Each token above swaps for its `night-` value. Photo wells stay light in both themes so packshots never sit on black.

### Named Rules
**The One-Colour Rule.** Claret means below cost and nothing else. Above cost
and "varies" are printed in ink with words, not given colours of their own,
because below cost is the exception this product exists to find.
The one place other colour appears is the cost bar in the product sheet, where
blues and tans tell the cost lines apart (see "Cost-line colours"). They label
parts of a cost; they never say whether an item is above or below it.

**The Word-With-Colour Rule.** A claret figure always carries a sign and the
words "below cost". Colour alone never says which side of cost an item is on.

**The Grey-Cost Rule.** Wherever price, reported cost and difference appear
together, the price is ink and bold, the cost is grey and regular, and the
difference is the emphasised line.

## Typography

**Display Font:** EB Garamond (with Garamond, Georgia, serif)
**Body Font:** Hanken Grotesk (with Helvetica Neue, Arial, sans-serif)
**Label/Mono Font:** Hanken Grotesk for labels. There is no monospace in the system.

**Character:** Garamond is the brand's voice: the wordmark, what is being said, what a thing is called. Hanken Grotesk is the price tag: small capitals for finding, tabular figures for comparing.

### Hierarchy
- **Display** (Garamond 400, clamp 40–68px, 1.02): the page headline. One per screen.
- **Wordmark** (Garamond 400, 34px): "Quince Ledger", centred in the masthead.
- **Headline** (Garamond 400, 26px): section headings on the product sheet and Method page. The product name on the sheet is 38px.
- **Name** (Garamond 400, 21px, sentence case as Quince writes it): product names in the grid; 19px in the list.
- **Caption** (Garamond italic, 16px, soft): the colour and size line under a name, and the standfirst under the headline (roman, 21px).
- **Body** (Hanken 400, 15px, 1.5): prose and notes. Maximum line length 60ch.
- **Label** (Hanken 600, 11px, uppercase, 0.09em): navigation, tabs, category links, column heads, rank numbers, buttons.
- **Figure** (Hanken 500, tabular numerals): every price, cost, difference and count. The price is 17px and 600; the grey cost is 14px and 400; the difference is 16px.

### Named Rules
**The Caps-Are-For-Finding Rule.** Uppercase is only for things a shopper scans
for: navigation, tabs, category links, column heads, buttons. Product names and
sentences are never set in capitals.

**The Tabular Rule.** Every number uses tabular numerals and is right-aligned
when it sits in a column.

## Layout

A centred page at `min(1360px, 100% - 64px)`; the notice strip and shirting
band run full width. From the top:

1. **Notice strip.** One centred line where a shop would put a promotion. It states the source and the date last checked, with a link to the Method page.
2. **Masthead.** Departments on the left, the wordmark centred, Method and the theme switch on the right.
3. **Shirting band.** 10px tall, 1px stripes every 5px.
4. **Opening.** Centred headline, one standfirst sentence with the count and its unit, then the three tabs (Below cost, Above cost, Everything) with counts.
5. **Toolbar.** One line ruled in ink above and hairline below: category links on the left; search box, sort, and the Photos/List switch on the right.
6. **Results.** Photos by default.
7. **Colophon.** Three short notes: the source, what a style is, what this is not.

The photo grid is four columns, three below 1000px, two below 640px, with 28px
between columns and 56px between rows so a row reads as a row. Photographs are
4:5. The list is one ruled table and the only element allowed to scroll
sideways. Below 1000px the masthead stacks with the wordmark first. Below 640px
the search box takes the full toolbar width.

## Elevation & Depth

Flat. Nothing floats at rest; separation comes from white space and hairline
rules. The product sheet is the one exception, laid over a dimmed page
(`rgba(20, 20, 18, 0.32)`).

### Shadow Vocabulary
- **Product sheet** (`box-shadow: -24px 0 60px rgba(20, 20, 18, 0.18)`; `rgba(0, 0, 0, 0.5)` in the night theme): the sheet that slides over the page. The only shadow in the system.

### Named Rules
**The Paper-Is-Flat Rule.** No shadow, lift or scale on hover. A hovered name
underlines; a hovered photograph dims slightly.

## Shapes

Square. Every photograph, field, button and bar has a 0 radius. Borders are
1px. The toolbar opens with an ink rule; everything else uses hairlines.

## Components

### Catalog item
A 4:5 photograph, then on paper: the rank as a label ("No. 1"), the name in
Garamond, an italic line for colour and size, a hairline, and the price block.
No outline and no background behind the text. The photograph and the name both
open the product sheet.

### Price block
Two lines. First: the price in bold ink with "costs Quince $479.15" in grey
beside it. Second: the difference, "−$419.25 below cost" in claret, or
"+$0.71 above cost" in ink. When a style's options disagree, the difference is
a range in ink ending "varies by option", and the cost is a range.

### List
One ruled table: rank, 44×55 thumbnail, name with its italic line, department,
price (bold), costs Quince (grey), difference, and difference as a percentage
of price. No zebra stripes. Hover tints the row.

### Tabs, category links and switches
All label type. Tabs and the search-scope switch mark the active item with a
2px ink underline; category links mark it by turning from soft to ink; the
Photos/List switch underlines the active word. Counts sit beside the label.

### Menus
More, Sort and Show open a drawn menu, never the operating system's dropdown.
The trigger is label type with a small drawn chevron that flips when open. The
list is a paper panel with a 1px ink border, square corners and no shadow,
10px below the trigger and at least 220px wide. Each row is label type in soft,
10px by 16px, with its count right-aligned in tabular figures; hover and
keyboard focus fill the row with the hover tone and turn it ink; the current
choice is ink with a 1px ink underline. Arrow keys move, Escape closes, and the
list shifts sideways to stay 16px inside the page.

### Department panel
Pointing at a department in the masthead, or focusing it, opens a full-width
panel under the shirting band: paper, a 1px ink rule along its bottom, no
shadow. On the left, the department in headline serif (30px), an italic caption
with its style count in the current view, and an underlined "All {department}"
label. On the right, its categories in four columns of label type, soft turning
ink on hover, each with its count; the current category is ink and underlined.
Choosing one sets department and category together. It opens after a short
pause and closes when the pointer leaves the masthead and panel; Down-arrow
moves into it and Escape closes it. Touch has no hover: a tap picks the
department and the category row below does the same job.

### Search
One box in the toolbar: a magnifier, placeholder naming the current view
("Search below cost"), square, 40px tall, hairline border that turns ink on
focus. It filters the current view as you type.

While there is a search term, one line appears under the toolbar: "Results for
'linen' in" followed by a two-option switch with counts, **Below cost 2** and
**Whole catalog 309**. Choosing Whole catalog searches every style, moves the
tab to Everything and changes the headline; choosing the other returns. Both
counts are always shown, so an empty local search still shows what exists
elsewhere. There is never a second search box.

### Product sheet
A full-height paper sheet from the right, up to 700px wide, as a modal dialog.
In order: a Close button; up to three photographs in a row of thirds; a label
line with department, category and rank; the name at 38px; the italic variant
line; then sections headed in Garamond.

- **What Quince says it costs.** Two bars on one scale, 48px tall, each with its label and figure in a 9.5em column at its left: "Costs Quince" over "Quince sells it for". Both start at the same left edge and the larger one spans the width, so the shorter is plain to see. The cost bar is split by cost line in the cost-line colours (below), with 2px gaps; a segment prints its name and amount inside when it is wide enough, its amount alone when narrower, nothing when narrower still. The price bar is solid ink. Under a hairline, one line in headline serif: "Sold below its reported cost by" with the amount at the right, in claret when below cost and ink otherwise. Then the cost lines in two columns, one per family, each headed by the family's name, total and share; every line has a 12px swatch, its name, its share and its amount. On a phone the labels sit above their bars and the two columns stack.
- **Cost-line colours.** Used only for cost lines in the product sheet, never for a state. Blues are what goes into the product: Materials `#1f3a5f`, Crafting `#5f7fae`, Packaging `#b5c6de` (night: `#6f93c9`, `#a3bbe0`, `#d3dff0`). Tans are what it takes to reach the buyer: Freight `#8a5a24`, Duties and taxes `#c3965a`, Card fees `#e6cfa8` (night: `#b9853f`, `#d6ae78`, `#ecdcbd`). A line that fits neither family is stone `#a9a79c` (night `#8d8c84`). A line keeps its colour on every item. None is a red, so claret still has one meaning. The two families are this site's grouping, not Quince's.
- **Since we started looking.** The number of checks, one sentence on whether anything moved, and a dated table of price and reported cost.
- An outlined "See it on Quince" button, and a closing note that this compares against disclosed cost only.

Between those sit three parts the mockup does not draw and the app does: an
option picker (square outlined buttons, the active one ruled in ink) when a
style has more than one option at this price; "What changed", a dated list of
moves between checks with the amount on either side and a signed difference
in ink; and a price-and-cost timeline with price as a solid ink line and
reported cost as a dashed grey line.

### Buttons and links
The only button shape is the outline button: 1px ink border, label type,
inverts to ink on hover. Everything else is a text control in label type or an
underlined link. Focus is a 2px ink outline, offset 3px.

### States
- **Loading:** well-coloured blocks in the shape of the content that is coming. No spinner.
- **Empty:** one sentence in Garamond, centred ("Nothing below cost matches that").
- **Error:** one sentence naming what failed and an outline Retry button.

## Do's and Don'ts

### Do:
- **Do** print Quince's cost in grey beside every price, and make the difference the emphasised figure.
- **Do** state the unit beside every count ("38 of 4,083 styles").
- **Do** keep the page white and let the photographs supply the colour.
- **Do** put a sign and the words "below cost" or "above cost" with every difference.
- **Do** keep a fee warning outside any element that truncates.
- **Do** keep the product sheet keyboard-operable and every text pairing at 4.5:1 or better in both themes.

### Don't:
- **Don't** round a corner, add a shadow at rest, or draw a card around an item.
- **Don't** add a side rail, a stat strip, a status dot or a pill.
- **Don't** use monospace anywhere.
- **Don't** use claret for anything except below cost, or add a second meaning colour.
- **Don't** add a second search box.
- **Don't** describe a negative difference as Quince losing money overall; it is the gap against the costs Quince discloses, nothing more.

## Open decisions

Settled during the app rebuild (see `web/AGENTS.md`): the app uses the
mockup's vocabulary; a style whose options disagree shows its range in every
view; a flagged fee is an ink asterisk with an explanation; the product sheet
keeps its option picker, change list and timeline.

Still open, and not to be invented:

- **Vocabulary outside the app.** `README.md` and `PRODUCT.md` still say
  losses, positive spread, display groups and reported cost.
- **Break-even and "varies" emphasis.** Both are ink with words today; confirm
  that is enough.
