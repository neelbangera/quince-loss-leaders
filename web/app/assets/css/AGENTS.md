# Dashboard styles

`main.css` is the visual system for the dashboard. It should make the data feel
polished and legible—quietly elegant rather than flashy—without owning data
fetching, ranking decisions, or product identity.

## Styling rules

- The visual system is defined in the root `DESIGN.md` and demonstrated in
  `mockups/session-a/index.html`. Take token names and values from there; do
  not invent a colour, radius, shadow or type size it does not list.
- Keep light mode as the visual baseline: a pure white page, near-black ink.
  The night theme swaps each token for its `night-` value and keeps photo
  wells light.
- Claret is the only colour with a meaning (below cost). Above cost, break-even
  and mixed states are ink with words, not colours. Check text contrast in both
  themes.
- Product images often have white backgrounds. Show them square-cornered with
  no outline or card, and do not use blend modes that can erase or distort
  product details.
- Keep focus-visible states, reduced-motion behavior, mobile layout, table
  overflow, drawer layering, and readable small text intact.
- Prefer existing classes/tokens and small scoped additions over one-off style
  overrides. Do not encode a new classification or filter rule in CSS.

After style changes, run the Nuxt typecheck/build from `web/` and inspect both
theme profiles at desktop and narrow widths. Generated `.nuxt`/`.output`
artifacts are not source files.
