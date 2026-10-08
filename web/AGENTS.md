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
