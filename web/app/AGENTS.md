# Nuxt application code

The `app/` directory is the browser-facing application. `pages/index.vue`
holds catalog state and layout, `components/` holds the pieces it renders,
`utils/` and `composables/` hold the logic, and `assets/css/main.css` holds
the presentation rules.
Keep data contracts and business calculations in the Python/export layers.

## Data flow

1. Load the whole catalog once as a `RankingResponse`, from the API
   (`view=all`) or static `rankings.json`.
2. Apply view, search, filter, sort and page behavior locally, with the same
   code in both modes.
3. Render grouped ranking rows. Nested variants remain available for labels,
   classification, price/cost ranges, and selection.
4. On detail selection, request the matching product/variant history only when
   needed. Render current metrics, complete cost lines, component changes, and
   history charts from that response.

The UI must not infer a product identity from a cleaned title or merge histories
because two rows look alike. Use `productKey`, `variantKey`, and the history
reference supplied by the backend/export.

## Interaction rules

- Table sorting, page-size changes, and page navigation are client-side once
  rankings are loaded. Avoid a network request for each click.
- Filters and search must inspect nested variant data when required, while
  visible totals remain display-group totals.
- Protect detail state from late responses when the user changes selection or
  closes the drawer. Keep loading, empty, and error states explicit.
- Treat images as optional product metadata. Use a safe fallback and do not
  substitute recommendation/UI assets for a failed product image.
- Keep theme selection persistent but respect system preference and maintain
  readable contrast. Avoid adding visual effects that compete with the data.

The look is defined in the root `DESIGN.md` and the mockup at
`mockups/session-a/index.html`, and the code here implements it. See "UI
rebuild: current state" in `web/AGENTS.md` for what was decided and what is
still open.

For page-specific behavior read `pages/AGENTS.md`; for visual changes read
`assets/css/AGENTS.md`. Run the frontend checks in `web/AGENTS.md` after any
TypeScript, template, CSS, runtime-config, or payload-shape change.
