# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary: shoppers deciding what to buy on Quince. They want value — products priced below what Quince's own disclosed costs imply — and use the ranking to decide what to look at or buy.

Secondary: researchers and analysts investigating Quince's pricing across products, materials, categories, colors, and sizes, and how those prices and disclosed costs change over time. Research depth serves the shopping job, not the reverse.

## Product Purpose

Quince Ledger makes Quince's pricing and cost transparency explorable. It ranks Quince products by the spread between the selling price and the cost breakdown Quince itself discloses, highlighting loss leaders — products whose reported spread is negative — while showing profitable and break-even products for context. Each product keeps a per-variant history of prices and disclosed cost components so changes are visible over time.

Success means a shopper can quickly find which Quince items are underpriced relative to the costs Quince discloses, see why (materials, crafting, packaging, freight, fees, and their history), and trust that every number is traceable to Quince's own disclosures.

## Positioning

Coupon sites, price trackers, and margin estimators work from inferred or third-party data. Quince Ledger ranks products against cost data Quince publishes on its own product pages, retains the full disclosed breakdown per variant, and keeps a dated observation history. A neighboring product could copy the table, but not the claim: every row traces to a captured page, a parsed cost breakdown, and a timestamped observation.

## Operating Context

- Acquisition: authorized saved HTML snapshots in `data/pages/`, or an authorized, rate-limited crawler run against an explicit host allowlist and approved sitemap, saving immutable content-addressed snapshots with crawl metadata.
- Analysis: a Python pipeline parsing pages into normalized observations in a local SQLite store — append-only, timestamped, with cost lines and parse issues per observation. Two intentional database defaults: `data/quince.sqlite3` for the snapshot CLI, `data/quince-us.sqlite3` for the crawler and API (`QUINCE_DATABASE` overrides).
- Presentation: the Nuxt dashboard in `web/`, reading a read-only Python API in development, or compact generated static JSON (`web/public/data`) when deployed.
- Refresh: a scheduled GitHub Actions workflow crawls, validates crawl quality, merges exports into committed static JSON, builds the site, and deploys it to GitHub Pages. The working SQLite database and raw snapshots are local working artifacts and are not published.

## Capabilities and Constraints

Capabilities:

- Three ranking views: loss leaders (negative spread), profit drivers (positive spread), and all products.
- Search, department/category filters, sorting, pagination, and table or image-card display.
- Display grouping of same-parent variants only when their current selling price matches; different price tiers stay separate. Groups show metric ranges, and each color/size keeps its own identity and history.
- Per-variant price and cost-component history with charts and change attribution (price moves vs. materials, crafting, packaging, freight, fee, or duties moves). The drawer's change ledger is the change-attribution surface: dated moves between captures with both amounts and a signed delta, so change is read rather than inferred from a chart.
- A Method page that states the disclosure basis, the display-group counting and classification rules, the identity rules, the fee guardrail, and the limits of the analysis in one place.
- Fee guardrail: implausible disclosed fees are flagged and normalized transparently, with the original disclosed amount retained.
- Static JSON export so the deployed site needs no Python process or database.

Constraints and terminology:

- The core metric is the disclosed unit spread: selling price minus Quince-reported total cost. A loss leader is a negative reported spread — an indication, not proof of Quince's business-level profitability. Marketing, returns, support, overhead, and inventory losses are not covered. Results must never be presented as a complete statement of Quince's profitability.
- Only complete, internally consistent price and cost breakdowns are rankable. Partial and invalid observations are diagnostics, not results. All-zero cost blocks are missing data.
- Identity is the `(product_key, variant_key)` pair — a color-free display title is never identity. Variant selection must be evidence-based; ambiguous or unprovable observations are flagged, never guessed.
- Collection is limited to authorized pages and normal, rate-limited requests. Proxy rotation, stealth behavior, CAPTCHA bypass, and access-control evasion are out of scope. A blocked crawl is a signal to investigate, not a wall to climb.
- The currency contract is effectively USD today.

Explicitly undecided: monetization; any benchmark or claim beyond disclosed-cost analysis; non-USD market support; whether invalid and partial observations appear in user-facing history (durable audit retention is required either way).

## Brand Commitments

- Product name: **Quince Ledger** — the user-facing identity, as branded in the dashboard. Repository and project name: Quince Loss Leaders.
- The disclosed-cost attribution is binding: always state the basis as Quince's own reported cost breakdowns, and never imply complete profitability.
- No logo, visual identity system, or customer-facing brand assets exist yet beyond the name.

## Evidence on Hand

- `data/quince-us.sqlite3` — populated working database: 7,870 observations at last local check, latest capture 2026-08-29. Local, gitignored, not guaranteed in a fresh checkout.
- `data/quince-us-pages/` — ~7.8k immutable snapshot/metadata pairs (15,578 files); `data/pages/` — small authorized snapshot input set. Local only.
- `fixtures/*.html` — three synthetic parser fixtures (loss example, positive example, zero-placeholder).
- `tests/` — five Python test modules (parser, storage, history, api, crawler).
- `README.md` and `AGENTS.md` — pipeline, contract, and guardrail documentation.
- No testimonials, customers, press, case studies, or benchmarks exist. Future work must not fabricate them.

## Product Principles

1. Shopper value first. The default view answers "what is underpriced right now?" before it explains how the pricing works.
2. Evidence over implication. Every number traces to a captured page and a Quince-disclosed cost line; unknowns stay unknown and flagged.
3. Identity is sacred. Variants, price tiers, and histories are never merged for convenience; a display group is presentation, not truth.
4. History is the asset. Observations are append-only and timestamped; repairing a past value requires an explicit, reviewed migration.
5. Honest boundaries. Authorized collection only, disclosed costs only, and never a claim the data cannot support.

## Accessibility & Inclusion

WCAG 2.2 AA is required for the dashboard and deployed site: full keyboard operability (including the product-detail dialog and its focus management), sufficient contrast in all supported themes, screen-reader semantics for tables, charts, and filters, and respect for reduced-motion preferences. The current dialog/focus/keyboard gaps are known hardening work, not an acceptable steady state.
