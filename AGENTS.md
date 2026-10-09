# Quince Loss Leaders

Quince Loss Leaders is a research and shopping tool that makes Quince’s pricing and cost transparency easier to explore. It highlights products that appear to be sold for less than their disclosed costs—sometimes called loss leaders—while also showing profitable and break-even products for context. The goal is to help people understand how Quince prices different products, materials, categories, colors, and sizes, identify unusual pricing patterns, and see how those prices and disclosed costs change over time. It can be used both to investigate Quince’s assortment and to make more informed shopping decisions. Because the analysis is based only on the costs Quince discloses, a loss leader is an indication of a negative reported spread, not proof of Quince’s complete business-level profitability or loss.

## High-level technical plan

The project is organized as a pipeline with a clear separation between collecting data, interpreting it, storing it, and presenting it:

```text
Authorized pages or saved snapshots
        ↓
Crawler / input layer
        ↓
Parser and normalized product observations
        ↓
SQLite historical data store
        ↓
Rankings and history exports
        ↓
Python API or static JSON
        ↓
Nuxt dashboard and deployed site
```

The crawler and local snapshot workflow provide the input while respecting the project’s authorization and collection boundaries. The parser turns product pages into consistent product and variant records, including prices and disclosed cost components. The retained local SQLite database is the historical source of truth for development and reprocessing; scheduled CI currently uses a temporary SQLite database, while static JSON is the durable public artifact. Each crawl records a timestamped observation so changes can be analyzed later. The analysis layer derives loss, profit, and all-product rankings, applies taxonomy and filters, and keeps variant identity and price history intact. The Nuxt application uses the Python API during development or for a live installation, and can use compact generated JSON when deployed as a static site. The repository’s GitHub Actions workflow runs the collection and export pipeline on a schedule or by manual dispatch, builds the static dashboard, and publishes it to GitHub Pages; the large working database remains outside the deployed site.

## Scoped repository instructions

The root document defines the shared architecture and guardrails. When working
inside a subdirectory, also read the nearest more-specific instruction file:

- `quince_loss_leaders/AGENTS.md` — Python models, parser, storage, API,
  history/export, taxonomy, and crawler boundaries.
- `tests/AGENTS.md` — test ownership, isolation, fixtures, and regression
  coverage expectations.
- `fixtures/AGENTS.md` — source-shaped parser fixture rules.
- `data/AGENTS.md` — local databases, snapshots, and generated artifacts; do
  not treat them as source code.
- `.github/AGENTS.md` and `.github/workflows/AGENTS.md` — automation and
  GitHub Pages publication rules.
- `web/AGENTS.md`, `web/app/AGENTS.md`, `web/app/pages/AGENTS.md`, and
  `web/app/assets/css/AGENTS.md` — Nuxt runtime, dashboard behavior, page
  state, and visual-system guidance.

Design and product context live beside these instruction files:

- `PRODUCT.md` — who the product is for, what it claims, and the brand
  commitments any copy must keep.
- `DESIGN.md` — the visual system ("The White Oxford Shirt"): tokens, type,
  layout, components, named rules, and a list of open decisions that must be
  asked about, not guessed.
- `mockups/session-a/index.html` — the approved reference mockup, runnable
  from the file system. The app was built to match it.
- `.impeccable/design.json` — a machine-readable companion to `DESIGN.md`;
  `.impeccable/archive/` holds two superseded systems that must not be built.

As of October 8, 2026 the Nuxt app in `web/app` has been rebuilt to this
design. `web/AGENTS.md` records what was decided during the rebuild, what was
verified, and the gaps that remain.

More-specific files add context; they do not waive the root identity,
provenance, authorization, data-retention, or publication guardrails.

## Core data model and vocabulary

The most important design distinction is between a sellable variant, a
historical observation, and a display group. They are related, but they are not
interchangeable:

```text
Selected product page / snapshot
        ↓
One ProductObservation for one captured SKU/variant
        ↓
Latest complete variant row for current rankings
        ↓
Optional same-price display group for the dashboard
```

- A **source page** is the product page or saved HTML snapshot being analyzed.
  One page can contain options for many colors and sizes, but its selected
  JSON-LD offer represents the option shown by that page’s URL/state.
- A **parent product** is the broader style or product family, usually found
  in Quince’s embedded transparent-pricing data. It is useful for explaining
  that several colors or sizes belong together, but it is not sufficient to
  identify a sellable record.
- A **product key** identifies the stable SKU/page-level record. A **variant
  key** identifies the selected embedded option when the source provides one.
  The `(product_key, variant_key)` pair is the storage and history identity.
  A color-free product title is never a substitute for that pair.
- An **observation** is one immutable capture at one point in time. It contains
  the selected price, complete disclosed cost lines, derived metrics, parser
  versions, source reference, and any parse issues. A later crawl creates a new
  observation, even when every value is unchanged.
- A **latest variant row** is a read-time projection: the latest complete
  observation for each identity pair. It powers current rankings but does not
  replace historical observations.
- A **display group** is an API/UI convenience, not a database entity. It may
  combine variants only when they share the same parent, currency, taxonomy,
  and current selling price. Different price tiers remain separate. If costs or
  spreads differ inside a group, the group exposes ranges and retains nested
  variant rows so each history remains inspectable.
- A **static export** is a generated presentation artifact derived from SQLite.
  `rankings.json` contains current grouped rankings, while `history/*.json`
  remains variant-specific. Static files can be regenerated; they are not a
  replacement for the retained source data.

Classification vocabulary also changes slightly at layer boundaries. The
Python model calls a positive spread `positive`; the API and dashboard call it
`profit`; zero is `break_even`; and `mixed` is reserved for a display group
whose nested variants do not all have the same classification. `unknown` or
non-rankable observations are diagnostics, not normal ranking results.

## Current implementation and operational context

The source tree contains an implemented MVP pipeline with known production
hardening gaps, but local data artifacts are intentionally not required to be
present in a fresh checkout:

- `data/quince-us.sqlite3`, raw snapshots, and other local crawl data are
  working/source artifacts and are ignored by Git. Runtime counts and latest
  capture dates therefore come from the local database, not from this document;
  use `/api/health` or a database query when exact counts matter.
- `web/public/data/` is generated static output and may be absent locally. The
  API mode can work from the local SQLite database without it. Static mode
  requires running `quince-history`/`quince-static-data` first and pointing
  `NUXT_PUBLIC_STATIC_DATA_BASE` at the generated data directory.
- The Python API is a separate long-running read-only process. After changing
  Python code, restart that process; Nuxt development mode can reload frontend
  changes independently.
- The repository has two intentional database defaults: the general snapshot
  CLI uses `data/quince.sqlite3`, while the crawler and API use
  `data/quince-us.sqlite3` (or `QUINCE_DATABASE` when configured). Always
  confirm which database a command or process is using before comparing results.
- The dashboard’s `Losses`, `Drivers`, and `All` tabs correspond to API views
  `losses`, `profit`, and `all`. “Drivers” is the product-facing name for
  positive disclosed spread; it is not a separate data source or calculation.
- A process that was started before a backend change continues serving the old
  code. If `/api/rankings` lacks fields such as `variantCount` or `isGrouped`,
  the API has not been restarted and its response cannot be used to validate
  the current working tree. Check `/api/health`, stop/restart the API, and then
  recheck a representative grouped product.
- The identity-matching fix applies to observations parsed after the fix. Old
  observations are intentionally immutable and may retain legacy mismatches.
  Correcting those records requires an explicit, reviewed reparse or migration;
  changing display labels at read time is only a compatibility fallback.
- The scheduled workflow creates a temporary database, validates crawl quality,
  merges the resulting export into committed static JSON, and deploys the Nuxt
  site. This is the intended pipeline, but the workflow still has known
  ordering, artifact-validation, and partial-crawl publication gaps described
  below; do not describe the scheduled job as an audited atomic publication
  until those gaps are fixed. It currently runs daily through its cron trigger
  and can also be manually dispatched. It does not publish the working database
  or raw snapshots.

### Quick onboarding facts

There are two distinct local input paths:

- The snapshot CLI reads already-authorized HTML files from `data/pages/` and
  normally writes `data/quince.sqlite3`. It is useful for deterministic parser
  development and does not fetch Quince.
- The authorized crawler starts from an approved sitemap or explicit seeds,
  saves immutable snapshots, and normally writes `data/quince-us.sqlite3`.
  It is the path used for a real refresh and is subject to the collection
  guardrails in the crawler section below.

The local read API exposes four application routes: `/api/health` for process and
database diagnostics, `/api/rankings` for filtered current rankings,
`/api/facets` for filter choices/counts, and `/api/product` for one
product/variant’s detail and history. The Nuxt `Drivers` tab maps to the API’s
`profit` view. A live API process and a Nuxt process are separate processes, so
restarting Nuxt does not load changed Python code; restart the API after backend
changes.

The last verified local baseline is informational rather than a promise about
future data. On September 1, 2026, the populated `data/quince-us.sqlite3`
contained 7,870 observations: 6,724 complete, 1,010 partial, and 136 invalid;
the latest capture was August 29, 2026, and the latest projection contained
4,711 rankable variant records and approximately 4,083 grouped display rows.
The Python suite had 46 passing tests and the Nuxt typecheck/build passed at
that point. Recheck the database, API, and build locally before relying on any
of these counts; they are not generated configuration or acceptance criteria.

## Production hardening gaps and explicit policies

The current implementation is useful for research, but passing the existing
tests does not mean that every production data contract is protected. The items
below are deliberately recorded so a new agent does not mistake a plausible
dashboard result for an audited, fully durable dataset.

### Data durability and publication

- The durability policy is split by environment. A retained local SQLite
  database is the canonical structured source for reprocessing and detailed
  investigation. In GitHub Actions, the SQLite database and raw snapshots are
  currently temporary; the committed static JSON is the durable public history
  produced by the workflow. Therefore CI cannot currently reparse an old raw
  page or independently recover from corrupted JSON. Do not claim that the
  deployed workflow retains a durable raw source until a database or snapshot
  archive is added.
- History merging and ranking merging are separate concerns. `history.py`
  currently merges per-variant history files but rebuilds `rankings.json` from
  the current crawl database. A partial crawl can therefore retain product B’s
  history while removing B from the current catalog. Until ranking merge or an
  equivalent stale-product policy exists, a partial or incomplete crawl is not
  publishable and the last known-good ranking catalog must be preserved.
- Crawl quality checks currently run after observations have been written. A
  failed run must never become authoritative merely because it wrote rows. The
  target behavior is a staging database or transaction that is promoted only
  after all gates pass; a failed local run must be clearly disposable.
- The `products` table contains mutable catalog metadata, while historical
  queries join old observations to that current row. A newer partial or invalid
  observation can therefore change the name or other metadata shown for an old
  point. Historical metadata must either be snapshotted on each observation or
  low-quality observations must be prevented from overwriting trusted metadata.
- `ProductObservation.is_rankable` is the canonical semantic rule. Storage,
  API, export, and health code must enforce an equivalent rule, including the
  positive-price requirement; checking only for a non-null spread is not enough.
- Repeated ingestion needs a defined crawl-run identity. Until a run ID/source
  hash policy exists, do not silently treat duplicate `(product_key,
  variant_key, captured_at)` rows as either corrections or harmless repeats.

### Parser and source-fidelity policies

- Variant selection must be evidence-based. If no selected offer ID or exact
  attribute match identifies one embedded variant, and multiple candidates are
  possible, the observation must be flagged or rejected. A deterministic
  lexicographic winner is still wrong data.
- Source precedence must be explicit and conflicts must be visible. The
  selected structured offer should outrank incidental meta tags, but a conflict
  should create a parse issue and provenance record rather than silently
  discarding the lower-priority value.
- The primary JSON-LD product must be selected by page identity, canonical URL,
  SKU, or offer URL. `products[0]` is not a reliable primary-product rule when
  recommendations or multiple product graphs are present.
- Price, selected variant, and cost breakdown must come from the same source
  container and identity. Never construct a hybrid observation from the price
  of one variant, the costs of another, and a generic page total.
- Cost extraction must preserve unknown and duplicate source labels, reversed
  layouts, source text, and whether a total was reported or inferred. Combining
  fields such as materials and hardware is acceptable only when that mapping is
  documented and intentional.
- Use explicit presence checks for zero values. A source price of zero may be
  invalid for ranking, but it is still source data that should be preserved and
  flagged rather than replaced by a fallback value through truthiness logic.
- The currency contract is currently effectively USD. If non-USD data is
  supported, define symbols/codes, decimal separators, negative formats,
  precision, conversion policy, and rounding in one place. Preserve the source
  currency per observation; do not let a malformed currency reach frontend
  `Intl.NumberFormat`.
- Fee normalization must retain both the original disclosed amount and the
  normalized analytical amount, identify the exact threshold and version of the
  rule, and expose the distinction in history. A fee warning must remain
  reproducible from exported data.
- An empty `variant_key` is valid only when the page is provably single-variant.
  If multiple sellable options exist and the selected option cannot be proven,
  the observation is ambiguous and must not be ranked as though it were a
  unique variant.
- URL canonicalization is part of identity, not cosmetic cleanup. Define and
  test source-specific rules for scheme, host, ports, credentials, encoding,
  query ordering, meaningful variant parameters, locale, and trailing paths.
- Preserve the raw source title separately from the cleaned display name.
  Removing a final `in <color>` or audience suffix must be conservative and
  must not damage legitimate product names.

### History, schema, and export integrity

- User-facing history may exclude invalid observations from charts, but invalid,
  partial, blocked, and failed events still need an audit/run record if the
  product is meant to support parser investigation. Document that distinction
  instead of calling the filtered export lossless.
- Historical points should carry enough provenance to interpret them later:
  parse status, confidence, availability, region, source reference/hash,
  parser and calculation versions, parse issues, original versus normalized
  totals, and relevant source metadata.
- Export deduplication must distinguish identical values from meaningful
  corrections. Include source hash, run identity, parser/calculation versions,
  status, or an explicit replacement policy in the event identity.
- History files, manifests, and rankings must be written atomically as a
  coherent export. Malformed existing JSON must fail or require review, not be
  silently treated as empty. Replacement mode must define whether unreferenced
  old history files are removed or quarantined.
- SQLite needs an explicit schema version and ordered migrations with tests and
  backup behavior. `CREATE TABLE IF NOT EXISTS` is initialization, not a
  migration strategy. Add indexes for child-table lookups and measure query
  performance on the real catalog, not just fixtures.

### API, grouping, and frontend contracts

- Display grouping is not storage identity. The group key must include market
  identity such as region/locale in addition to parent, currency, taxonomy, and
  current price. A missing variant in `/api/product` must not silently combine
  multiple variant histories; require a variant or return a clearly separated
  product-level choice.
- API and static mode must implement the same search, view, filter, summary,
  grouping, and classification semantics. Shared fixtures should exercise both
  paths, including nested variant search.
- The result cap must be visible. If the API or static export returns at most
  5,000 groups, expose returned/total/`hasMore` state and warn when the catalog
  is truncated. “All” must not imply complete coverage when it is capped.
- Ranking order must be deterministic. Add a stable secondary key after every
  sortable metric so equal values do not move between pages or create noisy
  generated diffs. Document whether summaries count groups or variants and how
  mixed groups are counted.
- Validate query ranges, bounds, repeated parameters, and unknown parameters.
  Health should be a cheap liveness/database check rather than a full ranking
  scan, and cached reads must be discarded if the database changes during the
  read.
- The built-in HTTP server is a local/trusted-network development service, not
  a hardened public API. If it is exposed beyond that boundary, add
  authentication or network controls, rate limiting, security headers, request
  limits, structured logging, graceful shutdown, and explicit TLS assumptions.
- The dashboard must ignore stale product-detail responses after a newer
  selection, use actual timestamps for a time-scaled history chart, avoid
  duplicate Vue keys, and provide an accessible dialog/focus/keyboard model.
  Image failures, invalid currencies, and missing data need explicit fallback
  behavior rather than relying on the happy path.

### Crawler and workflow contracts

- Host allowlists and URL patterns must describe one boundary. The workflow
  currently allowlists both `www.quince.com` and `quince.com` while its URL
  pattern only matches the former. Use full matching and apply the intended
  policy consistently to seeds, sitemap locations, discovered links, and final
  redirects.
- Validate the complete final origin, port, credentials, redirect chain, URL
  pattern, and robots policy. Do not allow a trusted initial URL to redirect to
  an unvalidated origin or bypass a crawl boundary.
- Snapshot writes and metadata writes must be atomic and sufficiently
  descriptive to reproduce a crawl: requested/final URL, status, content type,
  headers as appropriate, redirect context, depth, discovery source, run ID,
  parser version, and content hash.
- Product acceptance must prove that structured identity belongs to the page,
  and crawl statistics must distinguish discovered, skipped, blocked, failed,
  non-product, duplicate, parsed, and rankable URLs. Unexpected exceptions need
  structured per-URL errors and a usable final report.
- Authorization is more than a boolean CLI flag. The operator must know what
  permission, terms review, request policy, and retention/deletion policy make
  the crawl authorized. Never solve a blocked request with evasion techniques.
- The workflow must validate the complete static artifact before committing
  generated data. Require rankings and manifest files, validate every history
  reference and schema, build the site, and only then publish/commit. A
  frontend build failure must not leave newly committed data paired with an old
  deployment.
- Generated history needs a retention and lifecycle policy. Daily immutable
  points, raw snapshots, and Git history grow without bound; define archival or
  compaction rules, and distinguish sold out, temporarily absent, parser-failed,
  URL-changed, and discontinued products before using absence as evidence.

Priority order for hardening is: enforce rankability; prevent partial catalog
publication; define durable history and staging; fix parser source precedence,
primary-product selection, and ambiguous variants; prevent metadata mutation;
add schema/index/transaction support; align crawler boundaries; make API and
static semantics identical; validate complete exports before publication; then
address retention, lifecycle, and deeper frontend accessibility hardening.

### Regression coverage required for hardening

The existing suite is a useful baseline, but a passing suite is not evidence
that the contracts above are complete. Add focused tests before marking the
corresponding hardening work finished:

- Parser tests must cover ambiguous and missing variant matches, a
  recommendation Product appearing before the page Product, conflicting price
  sources, explicit zero values, non-USD/malformed money, duplicate or unknown
  cost lines, reversed label/value layouts, fee-normalization provenance,
  empty variant identity, and URL-canonicalization edge cases.
- Model/storage tests must cover the canonical rankability predicate, partial
  metadata not rewriting trusted history, transaction rollback, duplicate
  crawl events, out-of-order observations, schema migration, child-table
  indexes, and the distinction between latest rankable data and audit events.
- History/export tests must cover partial-crawl ranking retention, invalid or
  corrupt input JSON, atomic publication, replacement cleanup, stable
  tie-breaking, provenance preservation, and meaningful corrections that have
  the same numeric values as an earlier point.
- API/static contract tests must cover nested-variant search parity, missing
  variant detail requests, market-aware grouping, invalid query ranges,
  result caps and `hasMore`, summary/mixed-group semantics, cache races, and
  deterministic pagination.
- Crawler/workflow tests must cover every URL boundary, redirects, robots
  failures, response truncation, snapshot collisions, structured unexpected
  errors, quality-gate rollback, partial-run publication, and complete
  artifact validation before a generated-data commit.
- Frontend validation must cover stale detail responses, repeated timestamps
  and component lines in charts, image/currency fallbacks, and dialog and
  keyboard accessibility. Until browser tests exist, keep these behaviors
  small and testable in isolated helpers where possible, and always run the
  Nuxt typecheck and production build.

## How to trace a result

When a product, price, cost, category, or ranking looks wrong, follow the data
forward from the earliest layer instead of patching the final display:

1. Inspect the HTML snapshot and its capture metadata. Confirm which product
   URL/state was selected and whether the page contains structured JSON-LD and
   transparent-pricing data.
2. Run `parse_html()` against that snapshot and inspect the resulting
   `ProductObservation`: SKU, variant key, parent ID, selected price, cost
   lines, parse status, issues, and calculated spread.
3. Inspect the SQLite observation and its child cost lines. Confirm that the
   stored `(product_key, variant_key)` identity and timestamp match the parsed
   result, and that a newer observation has not intentionally superseded it.
4. Check `Repository.rankings()` for the latest complete variant row. If this
   layer is wrong, fix parsing or persistence; do not compensate in the API or
   UI.
5. Check `RankingService.get_rankings()` for filtering, taxonomy, grouping,
   ranges, summaries, facets, and cache behavior. Remember that visible group
   counts can be lower than raw variant counts.
6. Compare `/api/rankings` with `web/public/data/rankings.json` when live and
   static modes disagree. If both ranking payloads are correct, inspect the
   corresponding per-variant history API response or `history/*.json` file.
7. Only then inspect `web/app/pages/index.vue` and
   `web/app/assets/css/main.css` for formatting, local sorting, state, or
   rendering errors.

This order matters for identity problems. For example, if a Maple page has an
Oak cost breakdown, changing the displayed color or grouping in the dashboard
would conceal the defect. The parser must select the correct embedded variant,
the database must preserve that identity, and the presentation layers should
then simply expose it.

## Ideas intentionally outside the current plan

Several possible approaches were considered but are not part of the current product direction:

- Real-time or continuous crawling is deferred. The project uses scheduled batch updates, which are sufficient for the expected pace of price changes and easier to operate responsibly.
- A live production database is not needed for the public site. SQLite remains the working historical source, while the deployed site receives compact static data.
- The deployed dashboard should not depend exclusively on the Python API. Static JSON mode allows the site to run on GitHub Pages, with the API retained for local development and richer live access.
- Vercel is not the current deployment target. GitHub Actions and GitHub Pages were chosen for the scheduled crawl, static export, and publication workflow.
- Proxy rotation, stealth behavior, CAPTCHA bypass, and access-control evasion are explicitly out of scope. Collection is limited to authorized pages and normal, rate-limited requests.
- Variants are not blindly merged by product name or collapsed into one row across every price. Same-parent variants may be grouped when their current selling price matches; different price tiers remain separate, and each variant keeps its own identity and history.
- The results are not presented as a complete statement of Quince’s profitability. They describe only the costs disclosed on the analyzed product pages.

## Detailed implementation guide

This section is the implementation map for a new agent. Changes should move
through the layers in the order below: establish the data contract first,
preserve it in storage, derive rankings and exports from that stored data, and
then update the API, dashboard, automation, and documentation. A feature that
changes a value’s meaning must be tested at the first layer where that value is
created and at every public boundary where it is exposed.

### 1. Define the product observation and identity contract

Files involved:

- `quince_loss_leaders/models.py` owns the normalized `ProductObservation`,
  `CostLine`, and `ParseIssue` structures. It also owns money conversion,
  canonical URL handling, identity fallback, spread/margin/markup calculation,
  rankability, classification, and parser/calculation version constants.
- `quince_loss_leaders/parser.py` is responsible for turning one HTML page
  into one normalized observation. It should contain source-specific extraction
  logic, not database queries or dashboard-specific formatting.
- `fixtures/*.html` provide small, deterministic examples of the source
  layouts. Add or modify a fixture when a parser behavior depends on a new
  markup shape, variant layout, fee case, or image source.
- `tests/test_parser.py` verifies the extraction contract before the data can
  reach storage. This is the first and most important place to test identity
  mismatches.
- `quince_loss_leaders/__init__.py` should only be changed if a new public
  model or parser entry point is intentionally exposed to package users.

Implementation sequence:

1. Identify the most authoritative source field for each value. Prefer
   structured product data and the selected sellable variant over incidental
   page text. Keep the source reference and raw hash so a result can be
   investigated later.
2. Parse all monetary values into `Decimal` values rounded to cents. Do not
   perform the core calculation with binary floating point. The database layer
   converts these values to integer cents for stable storage.
3. Resolve identity before calculating metrics. A product-level display name is
   not a unique identity: colors and sizes may have separate SKUs, variant IDs,
   prices, and costs. The selected JSON-LD offer identifies the selected
   variant; the matching embedded transparent-pricing variant supplies its
   corresponding cost lines. Store the parent product ID, variant key, color,
   size, and label as metadata when available. If the match is absent or
   ambiguous, record that state and do not select an arbitrary candidate just to
   make the row rankable.
4. Extract the complete disclosed cost breakdown and retain each component as a
   `CostLine`. The reported total must be consistent with the retained lines,
   subject to an explicitly recorded normalization such as the exorbitant-fee
   rule.
5. Apply the fee guardrail explicitly. When duties, taxes, and fees exceed the
   sum of the other disclosed costs, set that fee component to zero for the
   calculated total, mark the observation with `fee_warning`, retain the
   original disclosed amount and normalization rule, and add a parse issue
   explaining what happened. Never silently discard a source value.
6. Call `finalize_identity()` and `calculate_metrics()` after extraction. A row
   is rankable only when it is complete, has a positive selling price, has a
   complete reported cost, and has a calculated spread. Missing or placeholder
   values must remain non-rankable rather than being guessed.
7. If extraction semantics change, update `PARSER_VERSION` and add a fixture
   that demonstrates the old failure and the corrected result. The calculation
   version should change only when the meaning or formula of a derived metric
   changes.

Identity invariants:

- `product_key` identifies the stable SKU/page-level record, normally based on
  the SKU, then the canonical URL, then a deterministic local-source fallback.
- `variant_key` distinguishes the selected embedded variant when the source
  provides one. The `(product_key, variant_key)` pair is the identity used for
  latest rankings and historical detail, and it must not be replaced by a
  color-free display name.
- `parent_product_id` is a grouping hint, not a replacement for variant
  identity. Storage and historical exports remain variant-level.
- Removing a color from a title is presentation cleanup only. It must never
  alter the key used to store observations or history.
- A parser must not choose the first embedded pricing variant merely because
  it is convenient. It must match the selected offer’s variant attributes or
  fail/flag the observation when the match is ambiguous.

### 2. Persist observations without losing history

Files involved:

- `quince_loss_leaders/storage.py` owns the SQLite schema, write transaction,
  latest-observation queries, historical reconstruction, and conversion to
  ranking rows.
- `quince_loss_leaders/models.py` changes only when a persisted domain field or
  invariant is added; keep storage representation concerns out of the model
  where possible.
- `quince_loss_leaders/history.py` serializes retained observations into
  detail payloads, cost-component histories, manifests, and static ranking
  data. It is the bridge between the database and a database-free deployment.
- `quince_loss_leaders/cli.py` is the local snapshot/database-only entry point.
  Update it only when a new field or view should be visible in the command-line
  table, CSV, or JSON output.
- `tests/test_storage.py` covers latest-versus-historical behavior and storage
  identity; `tests/test_history.py` covers detail payloads, cost lines, merge
  behavior, and stable export paths.
- `README.md` documents database commands, export commands, and the distinction
  between latest rankings and retained history.

Implementation sequence:

1. Keep the schema separated into `products`, `source_snapshots`,
   `observations`, `cost_lines`, and `parse_issues`. Products hold relatively
   stable catalog metadata; observations hold a timestamped measurement;
   cost lines and issues belong to that exact observation.
2. When saving an observation, create or attach a source snapshot, insert a new
   observation, then insert its cost lines and issues in one transaction. Any
   product metadata upsert must be limited to trusted current metadata; it must
   not let a partial or invalid observation overwrite fields needed to interpret
   historical points. Store the metadata used by the observation alongside that
   observation, store monetary fields as integer cents, and keep the original
   metadata JSON for forward-compatible fields.
3. Treat observations as append-only. A new crawl must add a new timestamped
   observation even if nothing changed. Do not update an old observation to
   correct a parser result; use a reparse/migration with an explicit audit
   trail if historical data must be repaired.
4. Make `latest_observations()` select the latest complete row per
   `(product_key, variant_key)`. This is the input for current rankings and is
   intentionally different from `historical_observations()`, which returns all
   retained observations in chronological order.
5. Reconstruct cost lines and parse issues when reading history. A historical
   point without its component lines cannot support the component-change view
   and is an incomplete export.
6. Build one history payload per `(product_key, variant_key)` using the stable
   hash from `history_file_path()`. `export_history()` must merge a temporary
   crawl database into existing JSON by default, retain products absent from a
   partial crawl, and deduplicate reruns without throwing away component-level
   changes. Use replacement only when intentionally rebuilding from a complete
   database.
7. If the schema needs a new required column, add a schema version, ordered
   migration, compatibility test, and backup/recovery path before using it.
   `CREATE TABLE IF NOT EXISTS` does not migrate an existing database. Never
   make a production workflow depend on deleting the historical database.

### 3. Infer taxonomy and produce current rankings

Files involved:

- `quince_loss_leaders/taxonomy.py` owns the presentation taxonomy: department
  and category slugs, labels, stored-category precedence, and conservative URL
  or product-name fallback rules.
- `quince_loss_leaders/storage.py` supplies the latest complete variant rows
  that the ranking service consumes.
- `quince_loss_leaders/api.py` owns query validation, filtering, classification
  views, same-price grouping, sorting, facets, summaries, read-only database
  access, and in-process caching.
- `tests/test_api.py` verifies endpoint semantics, filters, facets, fee flags,
  cache invalidation, grouping, price-tier separation, and mixed metrics.
- `README.md` must be updated when ranking fields, query parameters, grouping
  rules, or endpoints change.

Implementation sequence:

1. Keep taxonomy presentation-only. It may affect filters and labels, but it
   must not change product identity, cost math, or classification. Prefer a
   trusted stored category; use URL/name inference only as a documented
   fallback. Add a regression test whenever a rule could capture a broad or
   ambiguous term.
2. Load the catalog from SQLite in read-only mode. Reject a missing database or
   a database with no rankable observations in health checks rather than
   creating an empty database that looks healthy.
3. Apply the requested view (`losses`, `profit`, or `all`) and explicit filters
   to raw latest variant rows before display grouping. This ordering keeps
   category counts, view counts, and search behavior correct.
4. Group only after filtering. The display-group key is the parent product (or
   a safe canonical fallback), currency, current selling price, and taxonomy.
   Classification and production cost are deliberately not in the key: two
   same-price variants can have different costs and therefore different
   spreads, but they still belong to the same price group. If regional or
   locale-specific catalogs are supported, carry region/locale through the
   model, storage row, and API before adding those fields to the group key;
   currency alone is not a sufficient market identity.
5. Keep different price tiers separate. A product with small and large sizes at
   different prices must produce separate ranking groups, even when the name,
   parent ID, and colors match.
6. For each group, expose a representative row plus variant count, labels,
   colors, sizes, classifications, and min/max ranges for price, cost, spread,
   and margin. If classifications differ, label the group `mixed` instead of
   hiding one variant or assigning the whole group an arbitrary result.
7. Sort numeric groups using the minimum value for ascending order and maximum
   value for descending order. This makes a range have a predictable position
   and keeps the API’s sorting semantics aligned with the dashboard.
8. Count groups, not raw variants, in public totals and facets. The nested
   variants remain available for detail views, but one same-price product group
   should not inflate the visible result count by the number of colors.
9. Cache the immutable catalog in `RankingService` using the database and
   SQLite journal file signature. Cache filtered responses and product details
   by query/identity, and clear all caches when the signature changes. Use a
   read snapshot or retry-and-discard rule so a database change during a read
   cannot populate a cache with a mixed-version response. Return deep copies so
   one caller cannot mutate a cached response for another.
10. Keep API reads separate from crawling and writing. The service opens SQLite
    read-only, tolerates short writer-lock windows, validates query parameters,
    and exposes health information suitable for local troubleshooting.

### 4. Expose history and static data without duplicating business logic

Files involved:

- `quince_loss_leaders/history.py` is the canonical serializer for observation
  points, current detail, analytics, component histories, manifests, and
  `rankings.json`.
- `quince_loss_leaders/api.py` exposes the same detail model through
  `/api/product` and reuses the history serializer so live and static modes do
  not drift.
- `web/app/pages/index.vue` loads a ranking snapshot, requests one product’s
  history only when its drawer opens, and renders cost components, charts,
  variant choices, and image metadata.
- `web/nuxt.config.ts` defines the public API base and static-data base without
  hard-coding a deployment environment into the page.
- `web/package.json` owns `dev`, `typecheck`, `build`, `generate`, and `preview`;
  change `web/package-lock.json` only when dependencies change.
- `tests/test_history.py` and `tests/test_api.py` protect the live/static
  payload contract.
- `README.md` documents the export command, merge behavior, file layout, and
  static-mode configuration.

Implementation sequence:

1. Serialize each observation with timestamp, price, total reported cost,
   spread, margin, parse status, total-cost source, and every cost line. Keep
   component amounts at every point so the UI can distinguish a price change
   from a materials, crafting, packaging, freight, fee, or duties change. For
   auditability, also preserve confidence, availability, region, source
   reference/hash, parser and calculation versions, parse issues, and original
   versus normalized totals.
2. Add product metadata separately from points: display name, URL, brand,
   taxonomy, images, parent identity, variant label, and fee-warning state.
   The display name may omit color, but the variant metadata and history path
   must remain specific.
3. Sort history chronologically and derive analytics from the points rather
   than from a second source. Use the latest point as `current`.
4. Keep one stable history file per variant. The ranking export may group
   same-price variants for display, but opening a variant must still request its
   own history file or API identity. Decide separately whether invalid and
   partial observations belong in the user-facing history; if they are
   excluded, retain their audit events somewhere durable.
5. Export `rankings.json`, `manifest.json`, and `history/*.json` into
   `web/public/data`. Write a complete export atomically, fail on corrupt
   existing JSON, and define cleanup/quarantine behavior for unreferenced files
   in replacement mode. Treat these as generated artifacts; do not hand-edit
   them to fix a parser or ranking problem.
6. In static mode, load the ranking file once, perform filtering/sorting/paging
   in the browser, and fetch only the selected history file. In API mode, use
   the same response shape and request only the data needed for the current
   view or opened product.

### 5. Implement the dashboard as a presentation of the contracts

Files involved:

- `web/app/pages/index.vue` owns dashboard state and behavior: view tabs,
  search, taxonomy filters, local sort, page size, table/image display,
  theme selection, detail loading, variant selection, history charts, and
  component-change rendering.
- `web/app/assets/css/main.css` owns the visual system, responsive layout,
  readable contrast, light/dark profiles, table states, image cards, metric
  colors, and detail-drawer styling. It should not contain data-fetching or
  ranking rules.
- `web/app/app.vue` is the minimal Nuxt page shell. Change it only for global
  application structure, not for product-specific ranking behavior.
- `web/nuxt.config.ts` changes when runtime configuration or the generated
  base path changes.
- `web/package.json` changes only for scripts or intentional frontend
  dependencies; run the lockfile update with the package manager when needed.
- The Python API/static export tests cover the data contract; use Nuxt
  `typecheck` and `build` as the frontend validation gates because there is no
  separate browser test suite yet.

Implementation sequence:

1. Define TypeScript interfaces for the API/static payload before rendering a
   new field. Optional fields must remain optional for older exports.
2. Keep ranking interactions cheap. The dashboard requests a bounded ranking
   payload when using the API; changing sort direction, page size, or the
   visible table page should be local computation, not a fresh database request.
   Static mode loads the full ranking snapshot once and applies the same local
   operations.
3. Apply view and taxonomy filters consistently in both API and static modes.
   For grouped rows, search and classification checks must inspect nested
   variants when necessary, while visible counts remain group counts.
4. Render grouped values as ranges when variants disagree. Do not display the
   representative variant’s cost as if it applied to every color or size.
   Provide a variant picker that loads the selected variant’s own history.
5. Keep visual signals restrained and semantic: negative spread/margin uses the
   loss color, positive values use the profit color, zero is neutral, and mixed
   values use a muted warning treatment. Fee warnings receive an asterisk and
   an explanatory note rather than a loud banner.
6. Keep product titles presentation-clean. Color and size belong in the
   secondary variant text or picker, not in the shared product name used for
   comparison.
7. For images, trust the parser’s filtered image list and lazy-load captured
   images. If no reliable image exists, show the placeholder; do not substitute
   arbitrary recommendation or UI assets.
8. After a UI change, run `npm run typecheck` and `npm run build` from `web/`.
   Test API mode against the local service and static mode against generated
   `web/public/data` when the change touches either data path.

### 6. Crawl, validate, and automate the data refresh

Files involved:

- `quince_loss_leaders/crawler.py` owns URL normalization, host allowlisting,
  robots policy, rate limiting, bounded parallel fetches, response checks,
  immutable snapshots, parsing, product acceptance, and crawl statistics.
- `quince_loss_leaders/crawler_cli.py` exposes those controls and the quality
  gates used by local and scheduled crawls.
- `tests/test_crawler.py` verifies authorization, robots handling, sitemap and
  link discovery, URL safety, parallelism, truncation, parse coverage, and CLI
  validation.
- `.github/workflows/update-site.yml` defines the scheduled/manual crawl,
  temporary database, coverage checks, export, generated-data commit, Nuxt
  build, and GitHub Pages deployment.
- `README.md` documents authorized invocation, performance controls, safety
  boundaries, and expected crawl reports.

Implementation sequence:

1. Require explicit authorization, an exact allowed-host list, and at least one
   seed or approved sitemap. Normalize URLs, remove fragments, preserve only
   meaningful variant query parameters, reject non-HTML assets, and block
   redirects outside the allowlist.
2. Read `robots.txt` and fail closed when it cannot be read. Use a descriptive
   user agent and bounded response size/timeouts. Record blocked and failed URLs
   in the crawl result instead of silently treating them as missing products.
3. Permit bounded concurrency for independent requests, but keep one shared
   minimum interval between request starts. Increasing workers must not
   accidentally multiply the request rate beyond the configured delay.
4. Save immutable content-addressed HTML snapshots before parsing. Parse each
   page through `parse_html()`, attach crawl/run metadata, and persist only
   pages with structured product identity. Keep recognized but incomplete pages
   in diagnostics, not rankings. Snapshot and metadata writes must be atomic.
5. Require scheduled quality gates: minimum rankable observations, minimum
   rankable ratio, no sitemap truncation, and a complete static-artifact
   validation. A crawl that produces suspiciously little usable data must fail
   before it overwrites or publishes the catalog.
6. Run the crawl against a staging database or otherwise make all writes
   disposable until validation succeeds. Promote/publish only the validated
   result; do not allow a failed local or scheduled run to become the next
   historical source by accident.
7. Use a temporary SQLite database in automation. Export it into the existing
   static data set with merge behavior, so a partial crawl cannot erase
   previously retained products or history.
8. Do not add proxy rotation, stealth behavior, CAPTCHA bypass, or access
   control evasion when improving crawler reliability. A blocked crawl is a
   signal to investigate authorization or source changes, not a reason to
   circumvent the source.

### 7. Publish the static site through the scheduled workflow

The safe target sequence in `.github/workflows/update-site.yml` is:

1. Check out the repository and install the Python package.
2. Crawl the authorized Quince sitemap with the configured host allowlist,
   concurrency, delay, response limits, and quality gates.
3. Export rankings and per-variant history into a staging data directory,
   merging with existing generated data according to the partial-crawl policy.
4. Validate the complete candidate artifact: required files exist, JSON parses,
   schema versions are supported, every ranking history reference resolves, and
   counts/timestamps are internally consistent.
5. Install the pinned Node dependency graph with `npm ci` and run Nuxt
   generation with the GitHub Pages base path and
   `NUXT_PUBLIC_STATIC_DATA_BASE=./data`.
6. Only after data validation and the frontend build succeed, atomically promote
   the candidate data, commit changed catalog JSON through the workflow bot, and
   deploy the generated artifact. The working SQLite database and raw snapshots
   stay in the runner and are not published.
7. Keep the workflow manually dispatchable so a maintainer can run a controlled
   refresh without waiting for the schedule. Change the cron only after
   considering source load, expected price-change frequency, and history value.

The current workflow commits generated data before the Nuxt build, so that
ordering remains a known hardening gap until the workflow is changed. A build
failure must not leave newly committed catalog data paired with an older
deployed site.

When modifying deployment behavior, change the workflow and its corresponding
README instructions together. When modifying the payload, change the exporter,
API/static consumer, tests, and generated-data validation together. Do not make
GitHub Pages depend on a live Python process or a SQLite file that is not part
of the static artifact.

### 8. Completion checklist for any feature

Before considering a feature complete:

1. Update the owning Python or Nuxt layer and keep responsibilities separated.
2. Add a focused regression test at the source of the behavior and update any
   downstream contract tests.
3. Run `python3 -m unittest discover -s tests -v`.
4. Run `npm run typecheck` and `npm run build` in `web/` for frontend or
   payload changes.
5. Run `git diff --check` and inspect generated JSON shape/counts when export
   behavior changed.
6. Check `/api/health` and a representative ranking/detail request against a
   local database when the API or storage changed.
7. Document user-visible semantics in `README.md` and architectural decisions
   or guardrails in this file.
8. Preserve existing user changes, historical observations, and generated
   history unless a deliberate, reviewed migration explicitly says otherwise.
