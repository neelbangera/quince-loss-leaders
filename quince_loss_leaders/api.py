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
import os
from pathlib import Path
import sqlite3
import sys
from threading import RLock
from typing import Iterable, Mapping
from urllib.parse import parse_qs, urlsplit, urlunsplit

from .history import display_name, history_file_path, product_detail
from .models import cents_to_money
from .storage import RankingRow, Repository
from .taxonomy import Taxonomy, infer_taxonomy


DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)
DEFAULT_DATABASE_PATH = Path("data/quince-us.sqlite3")
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
RowKey = tuple[str, str]
DatabaseSignature = tuple[tuple[int, int, int], ...]
QueryKey = tuple[tuple[str, tuple[str, ...]], ...]
ProductCacheKey = tuple[DatabaseSignature, str, str, bool]


@dataclass(frozen=True)
class _CatalogCache:
    signature: DatabaseSignature
    rows: tuple[RankingRow, ...]
    taxonomies: Mapping[RowKey, Taxonomy]
    latest_captured_at: str | None = None


@dataclass(frozen=True)
class _RankingGroup:
    """Display group for same-price variants of one parent product."""

    rows: tuple[RankingRow, ...]
    taxonomy: Taxonomy

    @property
    def classifications(self) -> frozenset[str]:
        return frozenset(_classification(row) for row in self.rows)

    @property
    def classification(self) -> str:
        values = self.classifications
        return next(iter(values)) if len(values) == 1 else "mixed"

    @property
    def representative(self) -> RankingRow:
        if "loss" in self.classifications:
            return min(self.rows, key=lambda row: (row.unit_spread_cents, row.product_key, row.variant_key))
        if "profit" in self.classifications:
            return max(self.rows, key=lambda row: (row.unit_spread_cents, row.product_key, row.variant_key))
        return self.rows[0]

    def values(self, attribute: str) -> list[int | float]:
        return [
            value
            for row in self.rows
            if (value := getattr(row, attribute)) is not None
        ]


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


def _classification(row: RankingRow) -> str:
    if row.unit_spread_cents < 0:
        return "loss"
    if row.unit_spread_cents > 0:
        return "profit"
    return "break_even"


def _base_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlsplit(url)
    if not parsed.scheme or not parsed.netloc:
        return url
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/") or "/",
            "",
            "",
        )
    )


def _group_identity(row: RankingRow, taxonomy: Taxonomy) -> tuple[object, ...]:
    parent = row.parent_key or _base_url(row.canonical_url) or display_name(row.name or row.product_key).lower()
    return (
        parent,
        row.currency,
        row.selling_price_cents,
        taxonomy.department,
        taxonomy.category,
    )


def _group_rows(
    rows: Iterable[RankingRow],
    taxonomies: Mapping[RowKey, Taxonomy],
) -> tuple[_RankingGroup, ...]:
    grouped: dict[tuple[object, ...], list[RankingRow]] = {}
    for row in rows:
        taxonomy = taxonomies[_row_key(row)]
        grouped.setdefault(_group_identity(row, taxonomy), []).append(row)

    result: list[_RankingGroup] = []
    for group_rows in grouped.values():
        ordered = tuple(
            sorted(
                group_rows,
                key=lambda row: (
                    (row.variant_label or "").lower(),
                    (row.variant_color or "").lower(),
                    (row.variant_size or "").lower(),
                    row.product_key,
                    row.variant_key,
                ),
            )
        )
        result.append(_RankingGroup(rows=ordered, taxonomy=taxonomies[_row_key(ordered[0])]))
    return tuple(result)


def _row_dict(row: RankingRow, taxonomy: Taxonomy | None = None) -> dict[str, object]:
    taxonomy = taxonomy or _row_taxonomy(row)
    return {
        "productKey": row.product_key,
        "variantKey": row.variant_key,
        "name": display_name(row.name or row.product_key),
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
        "imageUrl": row.image_url,
        "historyPath": history_file_path(row.product_key, row.variant_key),
        "parentProductId": row.parent_key,
        "variantLabel": row.variant_label,
        "variantColor": row.variant_color,
        "variantSize": row.variant_size,
        "variantCount": 1,
    }


def _group_dict(
    group: _RankingGroup,
    taxonomies: Mapping[RowKey, Taxonomy],
) -> dict[str, object]:
    representative = group.representative
    payload = _row_dict(representative, group.taxonomy)
    payload["classification"] = group.classification
    payload["capturedAt"] = max(row.captured_at for row in group.rows)
    payload["variantCount"] = len(group.rows)
    payload["isGrouped"] = len(group.rows) > 1

    labels = [row.variant_label for row in group.rows if row.variant_label]
    colors = sorted({row.variant_color for row in group.rows if row.variant_color})
    sizes = sorted({row.variant_size for row in group.rows if row.variant_size})
    payload["variantLabels"] = labels
    payload["variantColors"] = colors
    payload["variantSizes"] = sizes
    payload["variantClassifications"] = sorted(group.classifications)

    for attribute, minimum_key, maximum_key in (
        ("selling_price_cents", "sellingPriceMin", "sellingPriceMax"),
        ("reported_total_cost_cents", "reportedTotalCostMin", "reportedTotalCostMax"),
        ("unit_spread_cents", "unitSpreadMin", "unitSpreadMax"),
        ("margin_pct", "marginPctMin", "marginPctMax"),
    ):
        values = group.values(attribute)
        if not values:
            payload[minimum_key] = None
            payload[maximum_key] = None
            continue
        if attribute == "margin_pct":
            payload[minimum_key] = min(values)
            payload[maximum_key] = max(values)
        else:
            payload[minimum_key] = _money(int(min(values)))
            payload[maximum_key] = _money(int(max(values)))

    payload["metricsMixed"] = any(
        len(set(group.values(attribute))) > 1
        for attribute in ("reported_total_cost_cents", "unit_spread_cents", "margin_pct")
    ) or len(group.classifications) > 1
    if len(group.rows) > 1:
        payload["variants"] = [
            _row_dict(row, taxonomies[_row_key(row)])
            for row in group.rows
        ]
    payload["hasExorbitantFees"] = any(row.has_exorbitant_fees for row in group.rows)
    return payload


def _facet_values(
    groups: Iterable[_RankingGroup],
    attribute: str,
) -> list[dict[str, object]]:
    values: Counter[tuple[str, str]] = Counter()
    for group in groups:
        key = getattr(group.taxonomy, attribute)
        label = getattr(group.taxonomy, f"{attribute}_label")
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

    def health(self) -> dict[str, object]:
        """Return whether the configured database contains usable rankings."""

        status: dict[str, object] = {
            "ok": False,
            "database": str(self.database_path),
        }
        if not self.database_path.is_file():
            status["error"] = f"Database does not exist: {self.database_path}"
            return status

        try:
            with Repository(self.database_path, read_only=True) as repository:
                counts = {
                    row["parse_status"]: int(row["count"])
                    for row in repository.connection.execute(
                        "SELECT parse_status, COUNT(*) AS count FROM observations GROUP BY parse_status"
                    ).fetchall()
                }
                total = sum(counts.values())
                latest = repository.connection.execute(
                    "SELECT MAX(captured_at) FROM observations"
                ).fetchone()[0]
                rankable = len(repository.rankings())
        except (OSError, sqlite3.Error) as error:
            status["error"] = str(error)
            return status

        status.update(
            {
                "ok": rankable > 0,
                "observations": total,
                "completeObservations": counts.get("complete", 0),
                "partialObservations": counts.get("partial", 0),
                "invalidObservations": counts.get("invalid", 0),
                "rankableVariants": rankable,
                "latestCapturedAt": latest,
            }
        )
        if rankable == 0:
            status["error"] = "Database contains no rankable complete observations"
        return status

    def _load_catalog(self, include_partial: bool) -> _CatalogCache:
        """Read a stable catalog snapshot, retrying if a crawl commits mid-read."""

        for _attempt in range(3):
            before = _database_signature(self.database_path)
            with Repository(self.database_path, read_only=True) as repository:
                rows = tuple(repository.rankings(include_partial=include_partial))
            after = _database_signature(self.database_path)
            if before == after:
                taxonomies = {_row_key(row): _row_taxonomy(row) for row in rows}
                capture_times = [row.captured_at for row in rows if row.captured_at]
                return _CatalogCache(
                    signature=after,
                    rows=rows,
                    taxonomies=taxonomies,
                    latest_captured_at=max(capture_times) if capture_times else None,
                )
        raise RuntimeError("Database changed while loading; retry the request")

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

            catalog = self._load_catalog(include_partial)
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
            view_rows = [row for row in all_rows if row.unit_spread_cents < 0]
        elif view == "profit":
            view_rows = [row for row in all_rows if row.unit_spread_cents > 0]
        else:
            view_rows = list(all_rows)

        department = _first(query, "department").lower()
        category = _first(query, "category").lower()
        search = _first(query, "search").lower()
        brand = _first(query, "brand").lower()
        min_spread = _dollars_to_cents(_first(query, "min_spread"))
        max_spread = _dollars_to_cents(_first(query, "max_spread"))
        min_price = _dollars_to_cents(_first(query, "min_price"))
        max_price = _dollars_to_cents(_first(query, "max_price"))

        def matches(
            row: RankingRow,
            *,
            include_department: bool = True,
            include_category: bool = True,
        ) -> bool:
            taxonomy = taxonomies[_row_key(row)]
            if include_department and department and taxonomy.department != department:
                return False
            if include_category and category and taxonomy.category != category:
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

        matched_rows = [row for row in view_rows if matches(row)]
        if not sort:
            sort = "spread_desc" if view == "profit" else "spread_asc"
        if sort == "name":
            sort = "name_asc"

        def sort_groups(groups: Iterable[_RankingGroup]) -> list[_RankingGroup]:
            grouped = list(groups)
            descending = sort.endswith("_desc")
            if sort in {"name_asc", "name_desc"}:
                grouped.sort(
                    key=lambda group: display_name(
                        group.representative.name or group.representative.product_key
                    ).lower(),
                    reverse=descending,
                )
                return grouped
            if sort in {"department_asc", "department_desc"}:
                grouped.sort(
                    key=lambda group: group.taxonomy.department_label.lower(),
                    reverse=descending,
                )
                return grouped

            attribute = {
                "price_asc": "selling_price_cents",
                "price_desc": "selling_price_cents",
                "cost_asc": "reported_total_cost_cents",
                "cost_desc": "reported_total_cost_cents",
                "spread_asc": "unit_spread_cents",
                "spread_desc": "unit_spread_cents",
                "margin_asc": "margin_pct",
                "margin_desc": "margin_pct",
            }.get(sort, "unit_spread_cents")
            grouped.sort(
                key=lambda group: (
                    max(group.values(attribute)) if descending else min(group.values(attribute))
                )
                if group.values(attribute)
                else (float("-inf") if descending else float("inf")),
                reverse=descending,
            )
            return grouped

        matched_groups = sort_groups(_group_rows(matched_rows, taxonomies))

        try:
            offset = max(0, int(_first(query, "offset", "0")))
            limit = int(_first(query, "limit", "100"))
        except ValueError:
            raise ValueError("offset and limit must be integers") from None
        if limit < 1 or limit > 5000:
            raise ValueError("limit must be between 1 and 5000")

        page = matched_groups[offset : offset + limit]
        summary_groups = _group_rows(all_rows, taxonomies)
        filtered_summary_groups = _group_rows(matched_rows, taxonomies)
        def _partition(groups: Iterable[_RankingGroup]) -> dict[str, int]:
            """Count each display group exactly once.

            Groups are partitioned on ``_RankingGroup.classification``, which is a
            total four-way label. Counting by membership in ``classifications``
            instead would double-count mixed groups into every bucket they touch,
            so the buckets would no longer sum to the group total.
            """
            counts = {"loss": 0, "profit": 0, "break_even": 0, "mixed": 0}
            for group in groups:
                counts[group.classification] += 1
            return counts

        filtered_counts = _partition(filtered_summary_groups)
        filtered_summary = {
            "total": len(filtered_summary_groups),
            "losses": filtered_counts["loss"],
            "profitDrivers": filtered_counts["profit"],
            "breakEven": filtered_counts["break_even"],
            "mixed": filtered_counts["mixed"],
        }
        counts = _partition(summary_groups)
        summary = {
            "total": len(summary_groups),
            "losses": counts["loss"],
            "profitDrivers": counts["profit"],
            "breakEven": counts["break_even"],
            "mixed": counts["mixed"],
            "filtered": filtered_summary,
        }

        department_facet_rows = [
            row for row in view_rows
            if matches(row, include_department=False)
        ]
        category_facet_rows = [
            row for row in view_rows
            if matches(row, include_category=False)
        ]
        department_facet_groups = _group_rows(department_facet_rows, taxonomies)
        category_facet_groups = _group_rows(category_facet_rows, taxonomies)
        response = {
            "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "latestCapturedAt": catalog.latest_captured_at,
            "view": view,
            "offset": offset,
            "limit": limit,
            "total": len(matched_groups),
            "hasMore": offset + len(page) < len(matched_groups),
            "summary": summary,
            "facets": {
                "departments": _facet_values(department_facet_groups, "department"),
                "categories": _facet_values(category_facet_groups, "category"),
            },
            "results": [_group_dict(group, taxonomies) for group in page],
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

        for _attempt in range(3):
            before = _database_signature(self.database_path)
            with Repository(self.database_path, read_only=True) as repository:
                observations = repository.historical_observations(
                    product_key=product_key,
                    variant_key=variant_key or None,
                    include_partial=include_partial,
                )
            after = _database_signature(self.database_path)
            if before == after:
                signature = after
                break
        else:
            raise RuntimeError("Database changed while loading; retry the request")
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
                health = self.service.health()
                self._send_json(health, status=200 if health["ok"] else 503)
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
        except (OSError, sqlite3.Error) as error:
            self._send_json({"error": str(error)}, status=503)
        except RuntimeError as error:
            self._send_json({"error": str(error)}, status=500)

    def log_message(self, format: str, *args: object) -> None:
        # Keep the API useful in a terminal without the default noisy date.
        print(f"api: {format % args}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Serve stored Quince rankings as read-only JSON.")
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(os.environ.get("QUINCE_DATABASE", str(DEFAULT_DATABASE_PATH))),
        help="SQLite database path (default: QUINCE_DATABASE or data/quince-us.sqlite3).",
    )
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

    health = service.health()
    if not health["ok"]:
        print(f"Cannot serve rankings: {health.get('error', 'database is not ready')}", file=sys.stderr)
        return 2

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
