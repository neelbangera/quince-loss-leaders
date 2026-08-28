"""Historical product detail serialization and static export helpers."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterable
import re

from .models import ProductObservation, as_utc_iso
from .storage import Repository
from .taxonomy import infer_taxonomy


COLOR_SUFFIX_RE = re.compile(r"^(?P<title>.+)\s+in\s+(?P<color>[^,]+)$", re.IGNORECASE)
HISTORY_SCHEMA_VERSION = 1


def display_name(value: str) -> str:
    """Remove Quince's trailing color/finish from a product title."""

    match = COLOR_SUFFIX_RE.match(value.strip())
    return match.group("title").strip() if match else value


def history_file_path(product_key: str, variant_key: str) -> str:
    """Return a stable, URL-safe path for one product/variant history."""

    identity = f"{product_key}\0{variant_key}".encode("utf-8")
    digest = hashlib.sha256(identity).hexdigest()[:24]
    return f"history/{digest}.json"


def _money(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _average_money(values: list[Decimal]) -> str | None:
    if not values:
        return None
    average = (sum(values, Decimal("0")) / Decimal(len(values))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return str(average)


def _classification(value: Decimal | None) -> str:
    if value is None:
        return "unknown"
    if value < 0:
        return "loss"
    if value > 0:
        return "profit"
    return "break_even"


def _has_exorbitant_fees(observation: ProductObservation) -> bool:
    if observation.selling_price is None:
        return False
    return any(
        line.normalized_type in {"freight_handling", "credit_card_fees", "duties_taxes_fees"}
        and line.amount >= observation.selling_price
        for line in observation.cost_lines
    )


def observation_point(observation: ProductObservation) -> dict[str, object]:
    """Serialize the chart-friendly fields for one observation."""

    return {
        "capturedAt": as_utc_iso(observation.captured_at),
        "sellingPrice": _money(observation.selling_price),
        "reportedTotalCost": _money(observation.reported_total_cost),
        "unitSpread": _money(observation.unit_spread),
        "marginPct": float(observation.margin_pct) if observation.margin_pct is not None else None,
        "parseStatus": observation.parse_status,
        "totalCostSource": observation.total_cost_source,
        "costLines": [
            {
                "label": line.label,
                "type": line.normalized_type,
                "amount": _money(line.amount),
            }
            for line in observation.cost_lines
        ],
    }


def _product_metadata(observation: ProductObservation) -> dict[str, object]:
    product_key = observation.product_key or ""
    taxonomy = infer_taxonomy(
        observation.canonical_url,
        observation.product_name,
        observation.category,
    )
    return {
        "productKey": product_key,
        "variantKey": observation.variant_key,
        "name": display_name(observation.product_name or product_key),
        "url": observation.canonical_url,
        "brand": observation.brand,
        "department": taxonomy.department,
        "departmentLabel": taxonomy.department_label,
        "category": taxonomy.category,
        "categoryLabel": taxonomy.category_label,
        "currency": observation.currency,
        "hasExorbitantFees": _has_exorbitant_fees(observation),
    }


def _analytics(history: list[dict[str, object]]) -> dict[str, object]:
    spreads = [Decimal(str(point["unitSpread"])) for point in history if point.get("unitSpread") is not None]
    prices = [Decimal(str(point["sellingPrice"])) for point in history if point.get("sellingPrice") is not None]
    costs = [
        Decimal(str(point["reportedTotalCost"]))
        for point in history
        if point.get("reportedTotalCost") is not None
    ]
    return {
        "observationCount": len(history),
        "lossObservations": sum(spread < 0 for spread in spreads),
        "profitObservations": sum(spread > 0 for spread in spreads),
        "lowestPrice": _money(min(prices) if prices else None),
        "highestPrice": _money(max(prices) if prices else None),
        "lowestCost": _money(min(costs) if costs else None),
        "highestCost": _money(max(costs) if costs else None),
        "averageSpread": _average_money(spreads),
        "firstObservedAt": history[0]["capturedAt"] if history else "",
        "lastObservedAt": history[-1]["capturedAt"] if history else "",
    }


def _detail_from_history(
    product: dict[str, object],
    history: Iterable[dict[str, object]],
) -> dict[str, object]:
    points = sorted(
        (dict(point) for point in history),
        key=lambda point: str(point.get("capturedAt", "")),
    )
    if not points:
        raise ValueError("Product history cannot be empty")
    return {
        "schemaVersion": HISTORY_SCHEMA_VERSION,
        "product": product,
        "current": points[-1],
        "analytics": _analytics(points),
        "history": points,
    }


def product_detail(observations: Iterable[ProductObservation]) -> dict[str, object]:
    """Build the API/static payload for one product/variant history."""

    ordered = sorted(observations, key=lambda item: item.captured_at)
    if not ordered:
        raise ValueError("Product history cannot be empty")
    return _detail_from_history(
        _product_metadata(ordered[-1]),
        (observation_point(observation) for observation in ordered),
    )


def _point_identity(point: dict[str, object]) -> tuple[object, ...]:
    """Identify duplicate exports without depending on cost-line ordering."""

    return (
        point.get("capturedAt"),
        point.get("sellingPrice"),
        point.get("reportedTotalCost"),
        point.get("unitSpread"),
        point.get("marginPct"),
    )


def merge_product_detail(
    existing: dict[str, object] | None,
    current: dict[str, object],
) -> dict[str, object]:
    """Merge a new crawl into an existing static product history."""

    if existing is None:
        return current

    existing_history = existing.get("history", [])
    current_history = current.get("history", [])
    points: list[dict[str, object]] = []
    seen: set[tuple[object, ...]] = set()
    for raw_point in [*existing_history, *current_history]:
        if not isinstance(raw_point, dict):
            continue
        point = dict(raw_point)
        identity = _point_identity(point)
        if identity in seen:
            continue
        seen.add(identity)
        points.append(point)

    existing_product = existing.get("product")
    current_product = current.get("product")
    product = current_product if isinstance(current_product, dict) else existing_product
    if not isinstance(product, dict):
        raise ValueError("Static history is missing product metadata")
    return _detail_from_history(dict(product), points)


@dataclass(frozen=True)
class ExportSummary:
    product_count: int
    observation_count: int
    output_dir: Path


def _load_json(path: Path) -> dict[str, object] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _write_json_if_changed(path: Path, payload: dict[str, object]) -> None:
    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    try:
        if path.read_text(encoding="utf-8") == encoded:
            return
    except FileNotFoundError:
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(encoded, encoding="utf-8")


def _manifest_entry(payload: dict[str, object], path: str) -> dict[str, object]:
    product = payload["product"]
    current = payload["current"]
    analytics = payload["analytics"]
    assert isinstance(product, dict)
    assert isinstance(current, dict)
    assert isinstance(analytics, dict)
    return {
        "productKey": product.get("productKey", ""),
        "variantKey": product.get("variantKey", ""),
        "name": product.get("name", ""),
        "url": product.get("url"),
        "brand": product.get("brand"),
        "department": product.get("department"),
        "departmentLabel": product.get("departmentLabel"),
        "category": product.get("category"),
        "categoryLabel": product.get("categoryLabel"),
        "currency": product.get("currency", "USD"),
        "hasExorbitantFees": product.get("hasExorbitantFees", False),
        "historyPath": path,
        "observationCount": analytics.get("observationCount", 0),
        "firstObservedAt": analytics.get("firstObservedAt", ""),
        "lastObservedAt": analytics.get("lastObservedAt", ""),
        "sellingPrice": current.get("sellingPrice"),
        "reportedTotalCost": current.get("reportedTotalCost"),
        "unitSpread": current.get("unitSpread"),
        "marginPct": current.get("marginPct"),
        "classification": _classification(
            Decimal(str(current["unitSpread"]))
            if current.get("unitSpread") is not None
            else None
        ),
    }


def export_history(
    database_path: str | Path,
    output_dir: str | Path,
    *,
    include_partial: bool = False,
    merge: bool = True,
) -> ExportSummary:
    """Export SQLite history into mergeable static JSON files.

    The output is intentionally split by product so a static UI can fetch one
    history file when a user opens a detail drawer. With ``merge=True``, a
    temporary database from a new crawl can be merged into an earlier export;
    products absent from the new crawl remain in the manifest.
    """

    database = Path(database_path)
    destination = Path(output_dir)
    manifest_path = destination / "manifest.json"
    previous_manifest = _load_json(manifest_path) if merge else None

    existing_payloads: dict[tuple[str, str], dict[str, object]] = {}
    if previous_manifest:
        entries = previous_manifest.get("products", [])
        if isinstance(entries, list):
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                product_key = entry.get("productKey")
                variant_key = entry.get("variantKey", "")
                history_path = entry.get("historyPath")
                if not isinstance(product_key, str) or not isinstance(variant_key, str):
                    continue
                if not isinstance(history_path, str):
                    continue
                payload = _load_json(destination / history_path)
                if payload is not None:
                    existing_payloads[(product_key, variant_key)] = payload

    with Repository(database) as repository:
        observations = repository.historical_observations(include_partial=include_partial)

    grouped: dict[tuple[str, str], list[ProductObservation]] = {}
    for observation in observations:
        key = (observation.product_key or "", observation.variant_key)
        grouped.setdefault(key, []).append(observation)

    payloads = dict(existing_payloads)
    for key, product_observations in grouped.items():
        current = product_detail(product_observations)
        payloads[key] = merge_product_detail(payloads.get(key), current)

    entries: list[dict[str, object]] = []
    observation_count = 0
    latest_timestamp = ""
    for (product_key, variant_key), payload in payloads.items():
        path = history_file_path(product_key, variant_key)
        _write_json_if_changed(destination / path, payload)
        entry = _manifest_entry(payload, path)
        entries.append(entry)
        observation_count += int(entry["observationCount"])
        latest_timestamp = max(latest_timestamp, str(entry["lastObservedAt"]))

    entries.sort(key=lambda entry: (str(entry.get("name", "")).lower(), str(entry.get("productKey", ""))))
    manifest = {
        "schemaVersion": HISTORY_SCHEMA_VERSION,
        "generatedAt": latest_timestamp or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "products": entries,
    }
    _write_json_if_changed(manifest_path, manifest)
    return ExportSummary(
        product_count=len(entries),
        observation_count=observation_count,
        output_dir=destination,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export retained Quince price/cost history as static JSON."
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("data/quince.sqlite3"),
        help="SQLite database path (default: data/quince.sqlite3).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/exports/history"),
        help="Directory for manifest.json and per-product files.",
    )
    parser.add_argument(
        "--include-partial",
        action="store_true",
        help="Include observations with parser warnings.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace the export instead of merging with existing JSON.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.database.exists():
        print(f"Database does not exist: {args.database}", file=sys.stderr)
        return 2
    summary = export_history(
        args.database,
        args.output_dir,
        include_partial=args.include_partial,
        merge=not args.replace,
    )
    print(
        json.dumps(
            {
                "outputDir": str(summary.output_dir),
                "products": summary.product_count,
                "observations": summary.observation_count,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
