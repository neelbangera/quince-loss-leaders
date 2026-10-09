# Dashboard pages

`index.vue` is the catalog page. It composes the components and is the
presentation of the backend contracts, not a second ranking engine.
`method.vue` is a static page explaining the disclosure basis and the counting
rules; it renders fixed prose and definitions and must not compute a metric the
backend owns.

## State and data loading

- `view` selects `losses` (shown as Below cost), `profit` (Above cost), or
  `all` (Everything).
- `search`, `department`, and `category` define filters; `scope` says whether
  a search covers the current view or the whole catalog; `sort`, `pageSize`,
  and `currentPage` control local presentation. All but the last two are
  mirrored in the address bar.
- `displayMode` switches Photos and List. The theme lives in
  `components/ThemeSelect.vue`, not in the page.
- `useAsyncData` loads the whole catalog once, from the API (`view=all`) or
  static `rankings.json`. Views, facets, search and ranks are computed in the
  browser with the helpers in `utils/ranking.ts`, identically in both modes.
- A style's rank is its place in the current view, filters and sort before
  searching, so a search never renumbers it.
- `useProductDetail` drives the product sheet. A detail request must identify
  the selected variant, and a stale response must not overwrite a newer
  selection.

The interfaces in `types/ranking.ts` mirror the API/static payload. When a
backend field changes, update the exporter/API contract and its tests before
loosening or duplicating a TypeScript type there.

## Display rules

- Keep `name` free of color/size suffixes when it is a shared product title;
  show variant attributes in secondary text or the variant picker.
- Grouped rows can contain multiple variants. Render ranges for disagreeing
  price, cost, spread, or margin values instead of presenting the representative
  variant as universal.
- Preserve metric meaning: negative spread/margin is below cost, positive is
  above cost, zero is at cost, and mixed is a range that says it varies. Only
  below cost takes colour (see `DESIGN.md`); the others are distinguished by
  their words.
- Mark exorbitant-fee normalization with the restrained asterisk/warning
  treatment and explain it in the detail view.
- Sorting and paging must remain instant after the ranking payload is loaded;
  do not turn a local table interaction into a full API reload.

## History/detail rules

History points are chronological observations and cost lines are component data,
not merely chart labels. Preserve repeated timestamps/lines with unique keys,
use elapsed time for a time series, and provide a readable fallback when a chart
cannot render. The drawer should behave as an accessible dialog with keyboard
close/focus behavior and should restore focus when closed.

The change ledger is derived from the same history points, never from a second
source. It reports only the moves between consecutive captures — price, each
cost line matched by its unique key, and the derived cost and spread — with both
amounts and a signed delta. A line that appeared or disappeared is labelled, not
shown as a move from zero. Captures with no movement are omitted and counted in
the section heading. Colour on a move describes the direction of the change, not
whether the value is good.

Changes to this page usually require `npm run typecheck` and `npm run build`
from `web/`. If a behavior differs between API and static mode, add or update
the backend/static contract test as well as the UI code.
