"""Read-only JSON API for the Nuxt dashboard.

The API intentionally sits beside the crawler instead of inside it.  Crawling
and parsing can run on a schedule, while the dashboard only reads the latest
stored observations.
"""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
from threading import RLock
from typing import Iterable, Mapping
from urllib.parse import parse_qs, urlsplit

from .history import product_detail
from .models import cents_to_money
from .storage import RankingRow, Repository
from .taxonomy import Taxonomy, infer_taxonomy


DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)
VALID_VIEWS = {"losses", "profit", "all"}
VALID_SORTS = {
    "name",
    "name_asc",
    "name_desc",
    "department_asc",
    "department_desc",
    "price_asc",
    "price_desc",
    "cost_asc",
    "cost_desc",
    "spread_asc",
    "spread_desc",
    "margin_asc",
    "margin_desc",
}
COLOR_SUFFIX_RE = re.compile(r"^(?P<title>.+)\s+in\s+(?P<color>[^,]+)$", re.IGNORECASE)
RowKey = tuple[str, str]
DatabaseSignature = tuple[tuple[int, int, int], ...]
QueryKey = tuple[tuple[str, tuple[str, ...]], ...]
ProductCacheKey = tuple[DatabaseSignature, str, str, bool]


@dataclass(frozen=True)
class _CatalogCache:
    signature: DatabaseSignature
    rows: tuple[RankingRow, ...]
    taxonomies: Mapping[RowKey, Taxonomy]
    department_facets: tuple[dict[str, object], ...]


def _first(params: Mapping[str, list[str]], key: str, default: str = "") -> str:
    values = params.get(key, [])
    return values[0].strip() if values and values[0] is not None else default


def _bool_param(params: Mapping[str, list[str]], key: str) -> bool:
    return _first(params, key).lower() in {"1", "true", "yes", "on"}


def _money(cents: int | None) -> str | None:
    value = cents_to_money(cents)
    return str(value) if value is not None else None


def _dollars_to_cents(value: str) -> int | None:
    if not value:
        return None
    try:
        amount = Decimal(value.replace("$", "").replace(",", "")).quantize(Decimal("0.01"))
    except InvalidOperation:
        raise ValueError(f"Invalid money filter: {value}") from None
    return int(amount * 100)


def _database_signature(database_path: Path) -> DatabaseSignature:
    """Track the database and SQLite journal files for cache invalidation."""

    signature: list[tuple[int, int, int]] = []
    for candidate in (
        database_path,
        Path(f"{database_path}-wal"),
        Path(f"{database_path}-shm"),
    ):
        try:
            stat = candidate.stat()
        except FileNotFoundError:
            signature.append((0, 0, 0))
        else:
            signature.append((stat.st_mtime_ns, stat.st_size, stat.st_ctime_ns))
    return tuple(signature)


def _row_key(row: RankingRow) -> RowKey:
    return row.product_key, row.variant_key


def _query_cache_key(query: Mapping[str, list[str]]) -> QueryKey:
    return tuple(sorted((key, tuple(values)) for key, values in query.items()))


def _row_taxonomy(row: RankingRow) -> Taxonomy:
    return infer_taxonomy(row.canonical_url, row.name, row.category)


def _display_name(value: str) -> str:
    """Remove Quince's trailing color/finish from the table title."""

    match = COLOR_SUFFIX_RE.match(value.strip())
    return match.group("title").strip() if match else value


def _classification(row: RankingRow) -> str:
    if row.unit_spread_cents < 0:
        return "loss"
    if row.unit_spread_cents > 0:
        return "profit"
    return "break_even"


def _row_dict(row: RankingRow, taxonomy: Taxonomy | None = None) -> dict[str, object]:
    taxonomy = taxonomy or _row_taxonomy(row)
    return {
        "productKey": row.product_key,
        "variantKey": row.variant_key,
        "name": _display_name(row.name or row.product_key),
        "url": row.canonical_url,
        "brand": row.brand,
        "brandType": row.brand_type,
        "department": taxonomy.department,
        "departmentLabel": taxonomy.department_label,
        "category": taxonomy.category,
        "categoryLabel": taxonomy.category_label,
        "taxonomySource": taxonomy.source,
        "capturedAt": row.captured_at,
        "currency": row.currency,
        "sellingPrice": _money(row.selling_price_cents),
        "reportedTotalCost": _money(row.reported_total_cost_cents),
        "unitSpread": _money(row.unit_spread_cents),
        "marginPct": row.margin_pct,
        "classification": _classification(row),
        "parseStatus": row.parse_status,
        "confidence": row.confidence,
        "hasExorbitantFees": row.has_exorbitant_fees,
    }


def _facet_values(
    rows: Iterable[RankingRow],
    attribute: str,
    taxonomies: Mapping[RowKey, Taxonomy],
) -> list[dict[str, object]]:
    values: Counter[tuple[str, str]] = Counter()
    for row in rows:
        taxonomy = taxonomies[_row_key(row)]
        key = getattr(taxonomy, attribute)
        label = getattr(taxonomy, f"{attribute}_label")
        values[(key, label)] += 1
    return [
        {"value": key, "label": label, "count": count}
        for (key, label), count in sorted(values.items(), key=lambda item: (-item[1], item[0][1]))
    ]


class RankingService:
    """Load and filter latest rankable observations from the SQLite database."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self._cache_lock = RLock()
        self._catalog_cache: dict[bool, _CatalogCache] = {}
        self._response_cache: dict[tuple[DatabaseSignature, QueryKey], dict[str, object]] = {}
        self._product_cache: dict[ProductCacheKey, dict[str, object]] = {}

    def _catalog(self, include_partial: bool = False) -> _CatalogCache:
        signature = _database_signature(self.database_path)
        with self._cache_lock:
            cached = self._catalog_cache.get(include_partial)
            if cached is not None and cached.signature == signature:
                return cached

            database_changed = bool(self._catalog_cache) and any(
                item.signature != signature for item in self._catalog_cache.values()
            )
            if database_changed:
                self._catalog_cache.clear()
                self._response_cache.clear()
                self._product_cache.clear()

            with Repository(self.database_path) as repository:
                rows = tuple(repository.rankings(include_partial=include_partial))
            taxonomies = {_row_key(row): _row_taxonomy(row) for row in rows}
            catalog = _CatalogCache(
                signature=_database_signature(self.database_path),
                rows=rows,
                taxonomies=taxonomies,
                department_facets=tuple(_facet_values(rows, "department", taxonomies)),
            )
            self._catalog_cache[include_partial] = catalog
            return catalog

    def get_rankings(self, params: Mapping[str, list[str]] | None = None) -> dict[str, object]:
        query = params or {}
        view = _first(query, "view", "losses").lower()
        if view not in VALID_VIEWS:
            raise ValueError("view must be one of: losses, profit, all")

        sort = _first(query, "sort", "").lower()
        if sort and sort not in VALID_SORTS:
            raise ValueError(
                "sort must be one of: name_asc, name_desc, department_asc, "
                "department_desc, price_asc, price_desc, cost_asc, cost_desc, "
                "spread_asc, spread_desc, margin_asc, margin_desc"
            )

        include_partial = _bool_param(query, "include_partial")
        catalog = self._catalog(include_partial=include_partial)
        cache_key = (catalog.signature, _query_cache_key(query))
        with self._cache_lock:
            cached_response = self._response_cache.get(cache_key)
        if cached_response is not None:
            return deepcopy(cached_response)

        all_rows = catalog.rows
        taxonomies = catalog.taxonomies
        if view == "losses":
            rows = [row for row in all_rows if row.unit_spread_cents < 0]
        elif view == "profit":
            rows = [row for row in all_rows if row.unit_spread_cents > 0]
        else:
            rows = all_rows

        department = _first(query, "department").lower()
        category = _first(query, "category").lower()
        search = _first(query, "search").lower()
        brand = _first(query, "brand").lower()
        min_spread = _dollars_to_cents(_first(query, "min_spread"))
        max_spread = _dollars_to_cents(_first(query, "max_spread"))
        min_price = _dollars_to_cents(_first(query, "min_price"))
        max_price = _dollars_to_cents(_first(query, "max_price"))

        def matches(row: RankingRow) -> bool:
            taxonomy = taxonomies[_row_key(row)]
            if department and taxonomy.department != department:
                return False
            if category and taxonomy.category != category:
                return False
            if brand and (row.brand or "").lower() != brand:
                return False
            if search:
                searchable = " ".join(
                    (
                        row.name or "",
                        row.brand or "",
                        taxonomy.department_label,
                        taxonomy.category_label,
                    )
                ).lower()
                if search not in searchable:
                    return False
            if min_spread is not None and row.unit_spread_cents < min_spread:
                return False
            if max_spread is not None and row.unit_spread_cents > max_spread:
                return False
            if min_price is not None and (
                row.selling_price_cents is None or row.selling_price_cents < min_price
            ):
                return False
            if max_price is not None and (
                row.selling_price_cents is None or row.selling_price_cents > max_price
            ):
                return False
            return True

        rows = [row for row in rows if matches(row)]
        if not sort:
            sort = "spread_desc" if view == "profit" else "spread_asc"
        if sort == "name":
            sort = "name_asc"

        if sort == "spread_desc":
            rows.sort(key=lambda row: row.unit_spread_cents, reverse=True)
        elif sort == "spread_asc":
            rows.sort(key=lambda row: row.unit_spread_cents)
        elif sort == "price_desc":
            rows.sort(key=lambda row: row.selling_price_cents or 0, reverse=True)
        elif sort == "price_asc":
            rows.sort(key=lambda row: row.selling_price_cents or 0)
        elif sort == "cost_desc":
            rows.sort(key=lambda row: row.reported_total_cost_cents or 0, reverse=True)
        elif sort == "cost_asc":
            rows.sort(key=lambda row: row.reported_total_cost_cents or 0)
        elif sort == "margin_desc":
            rows.sort(key=lambda row: row.margin_pct if row.margin_pct is not None else float("-inf"), reverse=True)
        elif sort == "margin_asc":
            rows.sort(key=lambda row: row.margin_pct if row.margin_pct is not None else float("inf"))
        elif sort == "department_desc":
            rows.sort(key=lambda row: taxonomies[_row_key(row)].department_label.lower(), reverse=True)
        elif sort == "name_desc":
            rows.sort(key=lambda row: _display_name(row.name or row.product_key).lower(), reverse=True)
        else:
            # Includes name_asc and department_asc.
            key = (
                (lambda row: taxonomies[_row_key(row)].department_label.lower())
                if sort == "department_asc"
                else lambda row: _display_name(row.name or row.product_key).lower()
            )
            rows.sort(key=key)

        try:
            offset = max(0, int(_first(query, "offset", "0")))
            limit = int(_first(query, "limit", "100"))
        except ValueError:
            raise ValueError("offset and limit must be integers") from None
        if limit < 1 or limit > 5000:
            raise ValueError("limit must be between 1 and 5000")

        filtered_rows = rows
        page = filtered_rows[offset : offset + limit]
        summary_rows = all_rows
        filtered_summary = {
            "total": len(filtered_rows),
            "losses": sum(row.unit_spread_cents < 0 for row in filtered_rows),
            "profitDrivers": sum(row.unit_spread_cents > 0 for row in filtered_rows),
            "breakEven": sum(row.unit_spread_cents == 0 for row in filtered_rows),
        }
        summary = {
            "total": len(summary_rows),
            "losses": sum(row.unit_spread_cents < 0 for row in summary_rows),
            "profitDrivers": sum(row.unit_spread_cents > 0 for row in summary_rows),
            "breakEven": sum(row.unit_spread_cents == 0 for row in summary_rows),
            "filtered": filtered_summary,
        }

        facet_rows = [
            row for row in all_rows
            if not department or taxonomies[_row_key(row)].department == department
        ]
        response = {
            "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "view": view,
            "offset": offset,
            "limit": limit,
            "total": len(filtered_rows),
            "hasMore": offset + len(page) < len(filtered_rows),
            "summary": summary,
            "facets": {
                "departments": list(catalog.department_facets),
                "categories": _facet_values(facet_rows, "category", taxonomies),
            },
            "results": [_row_dict(row, taxonomies[_row_key(row)]) for row in page],
        }
        with self._cache_lock:
            self._response_cache[cache_key] = response
            if len(self._response_cache) > 16:
                self._response_cache.pop(next(iter(self._response_cache)))
        return deepcopy(response)

    def get_product(self, params: Mapping[str, list[str]]) -> dict[str, object]:
        product_key = _first(params, "product_key")
        if not product_key:
            raise ValueError("product_key is required")
        variant_key = _first(params, "variant_key")
        include_partial = _bool_param(params, "include_partial")

        signature = _database_signature(self.database_path)
        cache_key = (signature, product_key, variant_key, include_partial)
        with self._cache_lock:
            cached = self._product_cache.get(cache_key)
        if cached is not None:
            return deepcopy(cached)

        with Repository(self.database_path) as repository:
            observations = repository.historical_observations(
                product_key=product_key,
                variant_key=variant_key or None,
                include_partial=include_partial,
            )
        if not observations:
            raise ValueError("Product history not found")

        response = product_detail(observations)
        with self._cache_lock:
            self._product_cache[cache_key] = response
            if len(self._product_cache) > 32:
                self._product_cache.pop(next(iter(self._product_cache)))
        return deepcopy(response)


class ApiHandler(BaseHTTPRequestHandler):
    service: RankingService
    cors_origins: tuple[str, ...]

    def _origin_allowed(self) -> str | None:
        origin = self.headers.get("Origin")
        if origin and ("*" in self.cors_origins or origin in self.cors_origins):
            return "*" if "*" in self.cors_origins else origin
        return self.cors_origins[0] if self.cors_origins else None

    def _send_json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        origin = self._origin_allowed()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        self.send_response(204)
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        origin = self._origin_allowed()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        parsed = urlsplit(self.path)
        try:
            if parsed.path == "/api/health":
                self._send_json({"ok": True})
                return
            if parsed.path == "/api/product":
                self._send_json(self.service.get_product(parse_qs(parsed.query)))
                return
            if parsed.path in {"/api/rankings", "/api/facets"}:
                payload = self.service.get_rankings(parse_qs(parsed.query))
                if parsed.path == "/api/facets":
                    payload = {"facets": payload["facets"]}
                self._send_json(payload)
                return
            self._send_json({"error": "Not found"}, status=404)
        except ValueError as error:
            self._send_json({"error": str(error)}, status=400)
        except (OSError, RuntimeError) as error:
            self._send_json({"error": str(error)}, status=500)

    def log_message(self, format: str, *args: object) -> None:
        # Keep the API useful in a terminal without the default noisy date.
        print(f"api: {format % args}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Serve stored Quince rankings as read-only JSON.")
    parser.add_argument("--database", type=Path, default=Path("data/quince.sqlite3"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8877)
    parser.add_argument(
        "--cors-origin",
        action="append",
        default=None,
        help="Allowed browser origin; repeat for multiple origins (default: localhost:3000 and 127.0.0.1:3000).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    service = RankingService(args.database)
    origins = tuple(args.cors_origin) if args.cors_origin is not None else DEFAULT_CORS_ORIGINS

    handler = type(
        "ConfiguredApiHandler",
        (ApiHandler,),
        {"service": service, "cors_origins": origins},
    )
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Serving rankings from {args.database} at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping API server.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
