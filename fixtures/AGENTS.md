# Parser fixtures

The files in this directory are small, deterministic HTML examples for parser
tests. They model source markup; they are not production catalog data and must
not require network access.

- `loss-example.html` represents a negative reported spread.
- `positive-example.html` represents a positive reported spread.
- `zero-placeholder.html` represents a zero/placeholder case that should not
  silently become a valid rankable observation.

When a parser bug is fixed, add the smallest fixture that reproduces the source
shape and a test in `tests/test_parser.py`. Keep the meaningful JSON-LD,
embedded pricing, variant, cost, and image markup needed to explain the case;
do not simplify away the ambiguity the test is meant to protect.

Use descriptive names tied to behavior, not product names. Do not add copied
full-site pages, credentials, personal data, or downloaded images. Expected
ranking/history payloads belong in tests or temporary export directories, not
as hand-maintained fixture output.
