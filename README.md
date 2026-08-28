# Quince Loss Leaders

Script-first tooling for parsing authorized local snapshots of Quince product
pages and ranking products whose reported unit spread is negative.

The project deliberately separates acquisition from parsing. It does not fetch
Quince URLs. Put pages that you are authorized to analyze in `data/pages/`, or
use the included synthetic fixtures while developing the parser.

## What the first version measures

The primary metric is a disclosed unit spread:

```text
unit spread = Quince selling price - Quince-reported total cost
```

This is not a claim of net profit. The site-level cost breakdown may not cover
every expense such as marketing, returns, support, overhead, or inventory
losses. The CLI only ranks observations with a complete, internally consistent
price and cost breakdown. All-zero cost blocks are treated as missing data.

## Run the example

No third-party packages are required:

```bash
python3 -m unittest discover -s tests -v
python3 -m quince_loss_leaders --input-dir fixtures --database /tmp/quince-example.sqlite3
```

The example prints the synthetic product with a negative reported spread. The
database stores both the current observation and its component cost lines.

## Analyze local page snapshots

```bash
mkdir -p data/pages
# Place authorized .html snapshots in data/pages/
python3 -m quince_loss_leaders \
  --input-dir data/pages \
  --database data/quince.sqlite3
```

Other output formats:

```bash
python3 -m quince_loss_leaders --input-dir data/pages --format json
python3 -m quince_loss_leaders --input-dir data/pages --format csv > losses.csv
```

`--include-partial` is available for parser debugging, but should not be used
for a public ranking until the warnings have been reviewed.

## Read stored crawl results

Use `--database-only` to report from an existing crawl database without
re-parsing snapshots:

```bash
python3 -m quince_loss_leaders \
  --database-only \
  --database data/quince-us.sqlite3 \
  --view losses \
  --limit 25
```

The other views are `--view profit` for positive disclosed spreads and
`--view all` for the complete ranking. Use `--format json` or `--format csv`
for data destined for a UI; use `--limit 0` to export every row.

## Authorized crawler

The crawler is a separate acquisition layer. It requires an explicit
`--authorized` flag, an exact host allowlist, and either seed pages or an
approved sitemap. It follows same-host HTML links, saves immutable HTML
snapshots, and sends product pages through the existing parser and database.

Example with an authorized source:

```bash
python3 -m quince_loss_leaders.crawler_cli \
  --authorized \
  --allowed-host www.example.com \
  --seed https://www.example.com/catalog \
  --sitemap https://www.example.com/approved-sitemap.xml \
  --snapshot-dir data/pages \
  --database data/quince.sqlite3 \
  --max-pages 500 \
  --max-depth 2 \
  --delay-seconds 1.5
```

The crawler respects `robots.txt`, uses a descriptive user agent, limits
response size and page count, and records 401/403/429/503 responses as blocked.
It stops when a challenge/CAPTCHA page is detected. It intentionally has no
proxy rotation, stealth behavior, CAPTCHA bypass, or access-control evasion.

The installed console command is also available after packaging:

```bash
quince-crawl --help
```

## Dashboard (Vue + Nuxt)

The first website UI lives in `web/`. It reads the stored rankings through a
small read-only Python API, so the crawler and the browser remain separate
processes.

Start the API from the repository root in one terminal:

```bash
python3 -m quince_loss_leaders.api \
  --database data/quince-us.sqlite3 \
  --host 127.0.0.1 \
  --port 8877
```

Then start Nuxt in a second terminal:

```bash
cd web
npm install
npm run dev
```

Open `http://localhost:3000`. The dashboard supports loss leaders, positive
spread drivers, the full ranking, search, inferred department/category
filters, sorting, and product-level price/cost history charts. Click a product
name or row to open its history. Set `NUXT_PUBLIC_API_BASE` if the API is
running at a different address.

The current Nuxt release recommends Node 22.19 or newer. The app builds on the
local Node 22.16 installation with an engine warning, but upgrading Node is
recommended before deploying it.

The API endpoints currently include:

- `GET /api/health`
- `GET /api/rankings?view=losses|profit|all`
- `GET /api/facets`
- `GET /api/product?product_key=...&variant_key=...` for chronological observations and summary analytics

Ranking filters are query parameters so they can later be shared in URLs or
connected to saved searches without changing the storage model.

## Export historical data for a static site

The dashboard can also consume an export generated from the retained SQLite
observations. The exporter writes a small manifest and one history file per
product/variant, so a static UI can load only the history for the product a
user opens:

```bash
python3 -m quince_loss_leaders.history \
  --database data/quince-us.sqlite3 \
  --output-dir web/public/data
```

Run it with the default merge behavior after each crawl. A new temporary crawl
database can be merged into an existing export; products not present in that
run remain in the manifest. Use `--replace` when rebuilding the export from a
complete database. The installed console command is also available:

```bash
quince-history --help
```

## Storage design

SQLite keeps the MVP simple, but the schema already separates:

- products and variants
- immutable source snapshots
- time-stamped observations
- normalized cost lines
- derived metrics and calculation versions
- parser issues and confidence

That makes later additions such as ratings, availability, benchmark prices,
returns, demand signals, historical charts, and category-level aggregation
additive rather than a rewrite of the core model.

Every accepted crawl is appended to `observations` with its capture time;
existing observations are not overwritten. `Repository.rankings()` intentionally
returns only the latest complete row for the current ranking screens, while
`Repository.historical_observations()` returns the retained observations in
chronological order. `quince-history` turns that time series into mergeable
static JSON, allowing GitHub Pages to serve history without a production
database.
