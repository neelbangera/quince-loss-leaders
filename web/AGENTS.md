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

As of October 8, 2026:

- The design is approved as a mockup and written up in `DESIGN.md`. The app
  code has not been rebuilt: `app/pages/index.vue` and `app/assets/css/main.css`
  still implement the earlier "forest ledger" look (green-tinted paper,
  monospace figures, rounded panels, a filter rail).
- Baseline before the rebuild: `python3 -m unittest discover -s tests` passes
  (52 tests) and `npm run typecheck` passes.
- The mockup is static HTML with a data snapshot. Its tabs, category links,
  department links and sort are drawn but inert; search, the Photos/List
  switch, the theme switch and the product sheet work.

### Clean up before changing the look

Do this as a behaviour-preserving refactor first, verified with typecheck and
build, so the visual rebuild is a change of templates and styles only.

1. **Move pure logic out of `index.vue`** (about 1,100 lines of script) into
   typed modules that can be tested without a browser:
   - payload interfaces (`ProductResult`, `ProductDetail`, `RankingResponse`…) to `app/types/`;
   - money, margin, date and range formatters to `app/utils/`;
   - sorting and metric-bound helpers to `app/utils/`;
   - the static-mode filter, facet and summary logic to a composable, since it must stay identical to the API's semantics;
   - product-detail loading with its stale-response guard to a composable;
   - the change-ledger computation and the history-chart geometry to `app/utils/`;
   - the dialog focus trap and focus restore to a composable.
2. **Extract repeated markup into components:** the masthead (copied into
   `index.vue` and `method.vue`), pagination (twice), the fee flag (twice),
   and the drawer header (three times across loading, error and loaded).
   Then split the page into a catalog item, the list table and the product
   sheet, matching the component names in `DESIGN.md`.
3. **Remove small leftovers:** the unused `classification` parameter of
   `formatSpreadValue`, the four one-line `formatProduct*` wrappers, and the
   legacy bare `"name"` sort branch in `sortResults`.
4. **Do not tidy `main.css`.** The rebuild replaces it. When rewriting, declare
   the night-theme tokens once; today they are duplicated under
   `[data-theme="dark"]` and the system media query, and the 560px media block
   appears twice.

### Gaps the rebuild must close

- **Search scope.** The design has one search box with a Below cost / Whole
  catalog switch. In API mode the page refetches on every keystroke with no
  debounce and only for the current view; whole-catalog search needs a second
  query or the full snapshot. Static mode already holds every style.
- **Mixed styles in the Below cost view.** The `losses` view filters variants
  before grouping, so a style whose options disagree reads as uniformly below
  cost there and as "varies" in `all`. This is an open decision in `DESIGN.md`.
- **No URL state.** View, filters, search, sort and view mode are lost on
  refresh.
- **First-paint hydration mismatch.** The server renders the empty state and
  the client hydrates the loading state.
- **Sheet content not yet designed:** the variant picker, change ledger and
  timeline exist in the app and are not drawn in the mockup. Keep their
  behaviour; ask before inventing their look.
- **Wording.** The mockup's vocabulary ("below cost", "styles", "costs
  Quince") is not yet approved for the app, Method page or README.

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

- `app/pages/index.vue` owns dashboard state, data loading, local filtering and
  sorting, table/image views, pagination, detail drawers, variants, charts,
  and theme selection.
- `app/pages/method.vue` is the static method page: disclosure basis, counting
  and classification rules, identity rules, the fee guardrail, and the limits of
  the analysis. It owns no data loading and must not restate a calculation the
  backend owns.
- `app/components/ThemeSelect.vue` owns the theme control and its persistence.
  Both pages use it so the chrome and the saved preference stay identical.
- `app/assets/css/main.css` owns the visual system, layout, contrast, themes,
  responsive behavior, focus states, and restrained metric colors.
- `app/app.vue` is only the global Nuxt shell.
- `nuxt.config.ts` owns runtime configuration and global CSS registration.
- `package.json` owns scripts and intentional dependencies; keep the lockfile
  synchronized when dependencies change.

## Frontend contracts

- Load the bounded/current ranking snapshot once per needed API query. Sort
  direction, page size, and visible page should be local operations and should
  not refetch the catalog.
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
