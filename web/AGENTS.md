# Nuxt frontend

This directory contains the Nuxt 4 presentation layer for the Quince Loss
Leaders research dashboard. Read the root `AGENTS.md` for the data model and
the backend instructions for payload semantics before changing the UI.

## Visual design

The look is defined in two places, and both must be read before changing any
template or style:

- `DESIGN.md` (repository root) is the written system: colours, type, layout,
  components, named rules, and a list of open decisions.
- `mockups/session-a/index.html` is the reference implementation. Open it in a
  browser; it runs from the file system with no server. Append `#dark`,
  `#list`, `#open=7`, `#q=linen` or `#everything` (comma-separated) to see each
  state.

Match the mockup's markup structure, spacing and CSS values rather than
reinterpreting the description. Where an instruction file under `web/` and
`DESIGN.md` disagree about appearance, `DESIGN.md` wins. Do not resolve an item
under "Open decisions" in `DESIGN.md` without asking; do not build from the
archived systems in `.impeccable/archive/`.

## UI rebuild: current state

As of October 8, 2026 the app has been rebuilt to `DESIGN.md`. The catalog
page, the product sheet and the Method page use the new system; the previous
"forest ledger" versions of `index.vue`, `method.vue`, `main.css` and
`ThemeSelect.vue` are kept in `.impeccable/archive/forest-ledger-app/` for
reference only.

Verified at the time of the rebuild: `npm run typecheck` and `npm run build`
pass, the Python suite passes (52 tests), and the page was checked in a
browser against the local API in both themes at desktop and phone width.
**Static mode was not exercised** because no generated `public/data` existed;
check it before a deploy.

Decisions taken during the rebuild that `DESIGN.md` had listed as open:

- The catalog loads once (`view=all`) in both modes and every view, filter,
  search and sort is local. A style whose options disagree therefore shows its
  range under both Below cost and Above cost.
- The app uses the mockup's words: below cost, above cost, styles, costs
  Quince, difference. `README.md` and `PRODUCT.md` still use the older terms.
- A flagged fee is an ink asterisk beside the name, explained in the colophon
  and on the product sheet. No second colour.
- The product sheet keeps the option picker, the change list ("What changed")
  and the price-and-cost timeline, drawn in the new system.

Known gaps:

- The product sheet's variant line comes from `/api/product`, which can
  disagree with the ranking row for the same identity (Lennox Wool Rug reads
  "Green" in the ranking and "Brown" in the detail). That is a backend
  inconsistency; do not paper over it in the UI.
- Page number and page size are not kept in the address bar; view, department,
  category, search, scope, sort and Photos/List are.
- There are still no browser tests. Pure logic now lives in `app/utils/` and
  can be unit-tested without a browser; no test runner is set up for it yet.

## Runtime modes

- API mode is the default for local development. `NUXT_PUBLIC_API_BASE`
  selects the Python read API and defaults to `http://127.0.0.1:8877`.
- Static mode is enabled when `NUXT_PUBLIC_STATIC_DATA_BASE` is non-empty. It
  loads generated `rankings.json` and requests only the selected variant’s
  history JSON. GitHub Pages uses this mode and must not need Python or SQLite.
- Both modes must expose the same view, filter, grouping, search, summary,
  classification, pagination, and detail semantics. Do not fix a mismatch in
  only one mode.

## File ownership

- `app/pages/index.vue` owns catalog state (view, filters, search and its
  scope, sort, paging, Photos/List), address-bar sync, and the page layout. It
  holds no formatting or ranking logic of its own.
- `app/pages/method.vue` is the static method page: disclosure basis, counting
  and classification rules, identity rules, the fee guardrail, and the limits of
  the analysis. It owns no data loading and must not restate a calculation the
  backend owns.
- `app/types/ranking.ts` mirrors the API/static payload. Change the exporter
  and its tests before loosening a type here.
- `app/utils/` holds pure logic: `format.ts` (money, dates, counts),
  `ranking.ts` (views, filters, facets, sorting, the price/cost/difference
  text), `changeLedger.ts` (moves between captures) and `historyChart.ts`
  (chart geometry), and `costFamilies.ts` (which cost lines count as making
  it, getting it to you, or other, and the shade each one takes).
- `app/composables/` holds stateful pieces: `useDataSource` (API or static
  JSON), `useProductDetail` (detail loading with the stale-response guard),
  `useDialogFocus` (modal focus and Escape), `useFailedImages`.
- `app/components/`: `SiteMasthead` (notice strip, masthead, shirting band, and the
  department panel that lists a department's categories on hover or focus),
  `FacetLinks` (text filters with a "More" menu), `TextMenu` (the drawn menu
  behind More, Sort and Show; never a native `<select>`), `CatalogItem`, `RankingList`,
  `ResultPagination`, `ProductSheet`, `FeeFlag`, and `ThemeSelect` (the
  Dark/Light switch and its persistence).
- `app/assets/css/main.css` owns the visual system, layout, contrast, themes,
  responsive behavior and focus states. Tokens are declared once per theme.
- `app/app.vue` is the global shell; it also resolves the theme before first
  paint.
- `nuxt.config.ts` owns runtime configuration and global CSS registration.
- `package.json` owns scripts and intentional dependencies; keep the lockfile
  synchronized when dependencies change.

## Frontend contracts

- Load the catalog once per visit (`/api/rankings?view=all&limit=5000`, or
  `rankings.json` in static mode). Views, filters, search, sort, page size and
  page are all local operations and must not refetch it.
- Keep display groups separate from variant identity. A grouped row may show
  ranges and labels, but detail/history requests must carry the selected
  `productKey` and `variantKey`, never just a display name.
- Treat external data as optional/untrusted: handle missing images, invalid
  currency, absent history, fee warnings, stale responses, and API errors.
- Follow the colour rules in `DESIGN.md`: claret marks below cost and nothing
  else; above cost, exact zero and mixed are printed in ink with words. Every
  coloured figure carries a sign and words. Preserve readability in both
  themes.
- Maintain dialog, keyboard, focus, reduced-motion, responsive, and chart
  accessibility while changing layout or interaction.

## Verification

From `web/`, run:

```text
npm run typecheck
npm run build
```

Use `npm run dev` for local interaction and verify API mode against the
currently running Python API. To test static mode, first generate valid data
with `quince-history`/`quince-static-data` and set
`NUXT_PUBLIC_STATIC_DATA_BASE`. Do not commit `.nuxt/`, `.output/`,
`node_modules/`, or other generated build artifacts.
