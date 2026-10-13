# Repository automation

This directory contains GitHub automation for the static catalog/dashboard.
Read the root `AGENTS.md` and the more specific `workflows/AGENTS.md` before
editing a workflow.

The intended publication target is GitHub Pages. The workflow performs an
authorized scheduled/manual crawl, creates static ranking/history JSON, builds
Nuxt, and deploys the generated site. It must not make the public site depend
on a live Python API, local SQLite file, or raw snapshots on the runner.

Current operational facts:

- `.github/workflows/update-site.yml` runs from a daily cron and supports
  `workflow_dispatch`.
- The workflow currently requests write permissions for repository contents and
  Pages deployment; keep permissions minimal if the workflow changes.
- Workflow runs share a `github-pages` concurrency group so overlapping
  publications do not race each other.
- The current job still has known publication-order, artifact-validation,
  partial-crawl, and source-boundary gaps. The root hardening section is the
  policy; do not infer completion from a successful YAML run.

Changes to crawl policy, generated-data layout, or deployment ordering should
be documented in `README.md` and root `AGENTS.md`, and should preserve the rule
that failed or suspicious crawls must not replace the last known-good public
catalog.
