# GitHub Pages workflow

`update-site.yml` is the scheduled/manual automation for refreshing the static
catalog. It is an orchestration file, not a place for parser, ranking, or UI
business logic.

## Current flow

The job checks out the repository, installs the Python package, crawls the
authorized Quince sitemap into runner-temporary snapshot/database paths,
performs crawl checks, exports `web/public/data`, commits generated data, then
installs Node dependencies, generates Nuxt, uploads the Pages artifact, and
deploys it. The configured crawl currently uses both `www.quince.com` and
`quince.com`, four workers, a 0.25-second delay, a 10,000-page cap, and minimum
rankable/truncation gates.

## Required workflow contracts

- Keep authorization, exact host/origin validation, robots compliance, bounded
  concurrency, response limits, and immutable snapshots. Never add stealth,
  proxy rotation, CAPTCHA bypass, or access-control evasion.
- Treat the runner database and raw snapshots as disposable unless a durable
  archive is deliberately added. The public artifact is the generated static
  JSON plus the Nuxt site.
- Validate the candidate data before publication: required rankings/manifest
  files, supported schemas, resolved history references, coherent counts and
  timestamps, and a successful Nuxt generation.
- The safe target order is crawl → export to a staging directory → validate
  artifact → build Nuxt → atomically promote/commit/deploy. The current file
  commits generated data before the Nuxt build; that is a known gap, not a
  pattern to copy.
- A partial or suspicious crawl must not silently erase the prior catalog.
  Ranking merge/stale-product policy must be explicit before publishing one.
- Keep concurrency protection and handle push conflicts or failed builds so a
  new catalog cannot be committed while an older site remains deployed without
  an explicit recovery path.

When changing the workflow, inspect the corresponding crawler CLI and history
export contracts rather than duplicating their logic in shell. Keep generated
data commits short and machine-owned, and update README instructions whenever
the schedule, permissions, environment variables, or deployment behavior
changes.
