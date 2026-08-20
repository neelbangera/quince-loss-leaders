from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Iterable

from .models import ProductObservation, cents_to_money
from .parser import parse_html
from .storage import RankingRow, Repository


def _money(cents: int | None, currency: str = "USD") -> str:
    value = cents_to_money(cents)
    if value is None:
        return "—"
    symbol = "$" if currency == "USD" else f"{currency} "
    return f"{symbol}{value:,.2f}"


def _read_observations(input_dir: Path) -> Iterable[ProductObservation]:
    for path in sorted(input_dir.rglob("*.html")):
        html = path.read_text(encoding="utf-8", errors="replace")
        try:
            captured_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        except OSError:
            captured_at = datetime.now(timezone.utc)
        yield parse_html(html, source_ref=str(path.resolve()), captured_at=captured_at)


def _print_table(rows: list[RankingRow]) -> None:
    if not rows:
        print("No complete loss-making observations found.")
        return

    headers = ["Product", "Price", "Reported cost", "Spread", "Margin", "Captured"]
    values: list[list[str]] = []
    for row in rows:
        values.append(
            [
                row.name or row.product_key,
                _money(row.selling_price_cents, row.currency),
                _money(row.reported_total_cost_cents, row.currency),
                _money(row.unit_spread_cents, row.currency),
                f"{row.margin_pct:.2f}%" if row.margin_pct is not None else "—",
                row.captured_at,
            ]
        )

    widths = [
        max(len(headers[index]), *(len(row[index]) for row in values))
        for index in range(len(headers))
    ]
    print("  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print("  ".join("-" * width for width in widths))
    for row in values:
        print("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)))


def _row_dict(row: RankingRow) -> dict[str, object]:
    return {
        "product_key": row.product_key,
        "variant_key": row.variant_key,
        "name": row.name,
        "url": row.canonical_url,
        "brand": row.brand,
        "brand_type": row.brand_type,
        "captured_at": row.captured_at,
        "currency": row.currency,
        "selling_price": str(cents_to_money(row.selling_price_cents)),
        "reported_total_cost": str(cents_to_money(row.reported_total_cost_cents)),
        "unit_spread": str(cents_to_money(row.unit_spread_cents)),
        "margin_pct": row.margin_pct,
        "parse_status": row.parse_status,
        "confidence": row.confidence,
    }


def _print_rows(rows: list[RankingRow], output_format: str) -> None:
    if output_format == "table":
        _print_table(rows)
    elif output_format == "json":
        print(json.dumps([_row_dict(row) for row in rows], indent=2))
    else:
        writer = csv.DictWriter(
            sys.stdout,
            fieldnames=list(_row_dict(rows[0]).keys()) if rows else [
                "product_key", "variant_key", "name", "url", "brand", "brand_type",
                "captured_at", "currency", "selling_price", "reported_total_cost",
                "unit_spread", "margin_pct", "parse_status", "confidence",
            ],
        )
        writer.writeheader()
        writer.writerows(_row_dict(row) for row in rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Parse authorized local Quince product-page HTML snapshots and list "
            "products whose disclosed unit spread is negative."
        )
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/pages"),
        help="Directory containing saved .html pages (default: data/pages).",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("data/quince.sqlite3"),
        help="SQLite database path (default: data/quince.sqlite3).",
    )
    parser.add_argument(
        "--format",
        choices=("table", "csv", "json"),
        default="table",
        help="Output format (default: table).",
    )
    parser.add_argument(
        "--include-partial",
        action="store_true",
        help="Include observations with parser warnings; excluded by default.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.input_dir.exists():
        print(
            f"Input directory does not exist: {args.input_dir}. "
            "Add authorized HTML snapshots there first.",
            file=sys.stderr,
        )
        return 2

    observations = list(_read_observations(args.input_dir))
    if not observations:
        print(f"No .html files found under {args.input_dir}.", file=sys.stderr)
        return 2

    with Repository(args.database) as repository:
        for observation in observations:
            repository.save_observation(observation)
        rows = repository.loss_leaders(include_partial=args.include_partial)

    _print_rows(rows, args.format)
    return 0

