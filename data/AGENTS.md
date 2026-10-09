# Local data artifacts

This directory contains local inputs and processing artifacts, not application
source. Read the root and backend `AGENTS.md` files before operating here.

- `pages/` contains authorized HTML snapshots for the deterministic snapshot
  CLI; it normally feeds `data/quince.sqlite3`.
- `quince-us-pages/` contains crawler snapshots and sidecar metadata; it is
  local crawl output and normally feeds `data/quince-us.sqlite3`.
- `*.sqlite3`/`*.db` files are local databases. The general snapshot CLI uses
  `data/quince.sqlite3`; crawler/API workflows use `data/quince-us.sqlite3` or
  `QUINCE_DATABASE`.
- `exports/` and similar directories contain generated static/history output.

Child page, database, and export artifacts are ignored because they may contain
copied site content and can be large. Do not hand-edit, commit, or delete them
to solve a parser or ranking problem. Inspect them read-only, use a temporary
directory for experiments, and use an explicit reviewed migration or reparse
when historical records need correction. A fresh checkout may have no local
data at all; that is normal.

The CI workflow uses disposable database and snapshot paths. Do not describe
those runner artifacts as a durable raw archive unless an explicit archive and
retention policy has been implemented.
