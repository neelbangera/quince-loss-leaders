# Backend tests

Tests are executable contracts for the pipeline. Read the root `AGENTS.md` and
`quince_loss_leaders/AGENTS.md` before changing a test. A green test suite does
not imply that the production hardening roadmap is complete; add tests when a
new contract is introduced.

## Test-file ownership

- `test_parser.py` covers HTML extraction, source precedence, product/variant
  identity, cost lines, money parsing, images, fee warnings, and rankability
  inputs.
- `test_storage.py` covers schema setup, writes, transactions, latest versus
  historical observations, cost lines/issues, identity, and ranking queries.
- `test_history.py` covers serialized detail/history points, component history,
  manifests, stable file paths, merge behavior, and static ranking output.
- `test_api.py` covers ranking views, filters, facets, summaries, grouping,
  sorting, cache behavior, health, and product-detail responses.
- `test_crawler.py` covers authorization, URL/origin policy, robots, discovery,
  bounded parallel fetching, snapshots, parser coverage, diagnostics, and CLI
  quality gates.

## Rules for reliable tests

- Keep tests deterministic and offline. Do not fetch Quince or depend on the
  local populated SQLite database.
- Use temporary directories and temporary SQLite databases for persistence or
  export tests. Clean up through the test framework rather than deleting broad
  paths.
- Use the small HTML files in `fixtures/` for parser behavior. If a markup
  shape matters, add a minimal fixture and a regression assertion instead of
  embedding a large page in the test.
- Do not assert current production catalog counts, latest capture dates, or
  incidental ordering. Assert documented semantics and explicit stable
  tie-breakers.
- When a bug crosses layers, test it where the value is created and at the
  public boundary that exposed it. For example, an identity mismatch needs a
  parser assertion and a storage/API or export assertion.
- Avoid weakening an assertion merely to preserve an implementation detail.
  If behavior changes intentionally, update the owning contract and README or
  root `AGENTS.md` as appropriate.

## Important regression categories

Keep coverage for ambiguous variant matching, primary-product selection,
conflicting price sources, explicit zero values, unknown/duplicate cost lines,
fee provenance, empty variant keys, metadata immutability, canonical rankability,
partial export retention, corrupt/atomic exports, migration, API/static search
parity, deterministic pagination, cache races, redirect/robots safety, and
quality-gate rollback. These are known risk areas even when older tests pass.

From the repository root, run:

```text
python3 -m unittest discover -s tests -v
```
