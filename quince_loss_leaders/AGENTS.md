# Python backend package

This directory owns the data pipeline behind Quince Loss Leaders. Read the
root `AGENTS.md` first: it defines the product meaning, identity contract,
publication policy, and unresolved hardening work. This file narrows that
guidance to Python changes.

## Responsibilities by module

- `models.py` defines normalized observations, cost lines, parse issues, money
  values, identity fields, derived metrics, rankability, classifications, and
  parser/calculation versions.
- `parser.py` converts one authorized HTML page or snapshot into one
  `ProductObservation`. It owns source-specific extraction and variant matching;
  it must not contain database or dashboard logic.
- `storage.py` owns SQLite schema, migrations, transactions, append-only
  observation writes, latest/history queries, and conversion to ranking rows.
- `taxonomy.py` provides presentation-only department/category inference. It
  must never alter identity or cost calculations.
- `history.py` serializes observations into per-variant history, manifests,
  rankings, and static JSON. It is the shared export contract for API/static
  consumers, not a place to repair bad parsed data.
- `api.py` provides read-only health, rankings, facets, and product-detail
  endpoints through the ranking service and its cache.
- `crawler.py` handles authorized URL discovery/fetching, robots and origin
  boundaries, bounded concurrency, snapshots, parsing, and crawl statistics.
- `crawler_cli.py` exposes crawler configuration and quality gates.
- `cli.py`, `__main__.py`, and `__init__.py` provide the local snapshot CLI and
  package entry points; keep them thin.

## Invariants that backend code must preserve

- The reported metric is `selling price - normalized disclosed total cost`.
  It is not a claim about Quince’s full business profitability.
- `(product_key, variant_key)` is the historical identity. A parent product,
  display name, color, or price group is not a replacement for that identity.
- Variant matching must be evidence-based. If the selected offer cannot be
  matched uniquely to embedded pricing data, record an issue and keep the
  observation non-rankable; never choose a convenient first or lexicographic
  candidate.
- Observations are append-only. A new capture creates a new timestamped record,
  even when its values are unchanged. Partial or invalid observations must not
  rewrite trusted metadata used by older observations.
- `ProductObservation.is_rankable()` is the semantic source of truth: the
  observation must be complete, have a positive price and complete cost, and
  have a calculated spread. Storage, API, exports, and health must enforce the
  same rule.
- Use `Decimal` during parsing/calculation and integer cents in SQLite/API
  serialization. Preserve currency and source/provenance fields per
  observation.
- If the exorbitant-fee guardrail normalizes a fee to zero, retain the original
  disclosed amount, normalized amount, warning, and rule/version so the result
  remains reproducible.
- Display grouping happens after filtering and only combines compatible,
  same-parent, same-market, same-current-price variants. It must never merge
  their stored histories or hide different price tiers.

## Safe change workflow

1. For parser changes, add a focused fixture and parser regression test first;
   update `PARSER_VERSION` when extraction semantics change.
2. For storage changes, use a temporary database, preserve transaction and
   migration behavior, and test both latest projections and historical rows.
3. For ranking/API changes, test raw variant filtering before grouping,
   deterministic sorting, summaries/facets, cache invalidation, and API/static
   parity.
4. For history changes, test per-variant identity, component-level points,
   partial-crawl merge behavior, provenance, and export validation.
5. For crawler changes, test URL/robots/redirect safety and quality gates
   without contacting the live site. Never add stealth, proxy rotation, or
   access-control evasion.
6. Update `README.md` for user-visible commands or endpoint semantics and the
   root `AGENTS.md` for architectural decisions or hardening policy.

## Local verification

Run these from the repository root:

```text
python3 -m unittest discover -s tests -v
quince-api --help
quince-crawl --help
quince-history --help
```

The snapshot CLI normally uses `data/quince.sqlite3`; the crawler and API
normally use `data/quince-us.sqlite3` or `QUINCE_DATABASE`. Confirm the database
path before comparing results. Local databases and raw pages are artifacts,
not fixtures; use temporary paths for experiments and do not commit them.

The root hardening section lists known gaps that are not automatically fixed by
this documentation. Do not report rankability, durable CI history, atomic
publication, parser ambiguity handling, or API/static parity as complete unless
the relevant code and regression tests have actually been changed.
