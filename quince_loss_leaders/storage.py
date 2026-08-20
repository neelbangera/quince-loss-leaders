from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from .models import ProductObservation, as_utc_iso, money_to_cents


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS products (
    product_key TEXT PRIMARY KEY,
    canonical_url TEXT,
    name TEXT,
    brand TEXT,
    brand_type TEXT NOT NULL DEFAULT 'unknown',
    category TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS source_snapshots (
    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_ref TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    raw_sha256 TEXT,
    source_kind TEXT NOT NULL DEFAULT 'local_snapshot',
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS observations (
    observation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_key TEXT NOT NULL REFERENCES products(product_key),
    variant_key TEXT NOT NULL DEFAULT '',
    snapshot_id INTEGER REFERENCES source_snapshots(snapshot_id),
    captured_at TEXT NOT NULL,
    region TEXT NOT NULL DEFAULT 'US',
    currency TEXT NOT NULL DEFAULT 'USD',
    selling_price_cents INTEGER,
    regular_price_cents INTEGER,
    store_credit_cents INTEGER,
    traditional_retail_price_cents INTEGER,
    reported_total_cost_cents INTEGER,
    total_cost_source TEXT NOT NULL DEFAULT 'reported',
    unit_spread_cents INTEGER,
    margin_pct REAL,
    markup_pct REAL,
    availability TEXT,
    parse_status TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0,
    parser_version TEXT NOT NULL,
    calculation_version TEXT NOT NULL,
    raw_sha256 TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS cost_lines (
    cost_line_id INTEGER PRIMARY KEY AUTOINCREMENT,
    observation_id INTEGER NOT NULL REFERENCES observations(observation_id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    normalized_type TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    source_text TEXT
);

CREATE TABLE IF NOT EXISTS parse_issues (
    issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    observation_id INTEGER NOT NULL REFERENCES observations(observation_id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_observations_product_variant_time
    ON observations(product_key, variant_key, captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_observations_spread
    ON observations(unit_spread_cents);
CREATE INDEX IF NOT EXISTS idx_observations_status
    ON observations(parse_status);
"""


@dataclass(frozen=True)
class RankingRow:
    product_key: str
    variant_key: str
    name: str | None
    canonical_url: str | None
    brand: str | None
    brand_type: str
    captured_at: str
    currency: str
    selling_price_cents: int | None
    reported_total_cost_cents: int | None
    unit_spread_cents: int
    margin_pct: float | None
    parse_status: str
    confidence: float


class Repository:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.database_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "Repository":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()

    def save_observation(self, observation: ProductObservation) -> int:
        observation.finalize_identity()
        assert observation.product_key is not None
        captured_at = as_utc_iso(observation.captured_at)

        self.connection.execute(
            """
            INSERT INTO products(
                product_key, canonical_url, name, brand, brand_type, category,
                first_seen_at, last_seen_at, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(product_key) DO UPDATE SET
                canonical_url = COALESCE(excluded.canonical_url, products.canonical_url),
                name = COALESCE(excluded.name, products.name),
                brand = COALESCE(excluded.brand, products.brand),
                brand_type = CASE
                    WHEN excluded.brand_type != 'unknown' THEN excluded.brand_type
                    ELSE products.brand_type
                END,
                category = COALESCE(excluded.category, products.category),
                last_seen_at = excluded.last_seen_at,
                metadata_json = excluded.metadata_json
            """,
            (
                observation.product_key,
                observation.canonical_url,
                observation.product_name,
                observation.brand,
                observation.brand_type,
                observation.category,
                captured_at,
                captured_at,
                json.dumps(observation.metadata, sort_keys=True),
            ),
        )

        snapshot_cursor = self.connection.execute(
            """
            INSERT INTO source_snapshots(
                source_ref, captured_at, raw_sha256, source_kind, metadata_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                observation.source_ref,
                captured_at,
                observation.raw_sha256,
                "local_snapshot",
                json.dumps({"parser_version": observation.parser_version}),
            ),
        )
        snapshot_id = snapshot_cursor.lastrowid

        cursor = self.connection.execute(
            """
            INSERT INTO observations(
                product_key, variant_key, snapshot_id, captured_at, region, currency,
                selling_price_cents, regular_price_cents, store_credit_cents,
                traditional_retail_price_cents, reported_total_cost_cents,
                total_cost_source, unit_spread_cents, margin_pct, markup_pct,
                availability, parse_status, confidence, parser_version,
                calculation_version, raw_sha256, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                observation.product_key,
                observation.variant_key,
                snapshot_id,
                captured_at,
                observation.region,
                observation.currency,
                money_to_cents(observation.selling_price),
                money_to_cents(observation.regular_price),
                money_to_cents(observation.store_credit),
                money_to_cents(observation.traditional_retail_price),
                money_to_cents(observation.reported_total_cost),
                observation.total_cost_source,
                money_to_cents(observation.unit_spread),
                float(observation.margin_pct) if observation.margin_pct is not None else None,
                float(observation.markup_pct) if observation.markup_pct is not None else None,
                observation.availability,
                observation.parse_status,
                float(observation.confidence),
                observation.parser_version,
                observation.calculation_version,
                observation.raw_sha256,
                json.dumps(observation.metadata, sort_keys=True),
            ),
        )
        observation_id = int(cursor.lastrowid)

        self.connection.executemany(
            """
            INSERT INTO cost_lines(observation_id, label, normalized_type, amount_cents, source_text)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    observation_id,
                    line.label,
                    line.normalized_type,
                    money_to_cents(line.amount),
                    line.source_text,
                )
                for line in observation.cost_lines
            ],
        )
        self.connection.executemany(
            """
            INSERT INTO parse_issues(observation_id, code, severity, message)
            VALUES (?, ?, ?, ?)
            """,
            [
                (observation_id, issue.code, issue.severity, issue.message)
                for issue in observation.issues
            ],
        )
        self.connection.commit()
        return observation_id

    def latest_observations(self, *, include_partial: bool = False) -> list[sqlite3.Row]:
        statuses = ("complete", "partial") if include_partial else ("complete",)
        placeholders = ",".join("?" for _ in statuses)
        query = f"""
            WITH ranked AS (
                SELECT
                    o.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY o.product_key, o.variant_key
                        ORDER BY o.captured_at DESC, o.observation_id DESC
                    ) AS row_number
                FROM observations o
                WHERE o.parse_status IN ({placeholders})
            )
            SELECT
                r.product_key, r.variant_key, p.name, p.canonical_url, p.brand,
                p.brand_type, r.captured_at, r.currency, r.selling_price_cents,
                r.reported_total_cost_cents, r.unit_spread_cents, r.margin_pct,
                r.parse_status, r.confidence
            FROM ranked r
            JOIN products p ON p.product_key = r.product_key
            WHERE r.row_number = 1
            ORDER BY r.unit_spread_cents ASC
        """
        return list(self.connection.execute(query, statuses).fetchall())

    def loss_leaders(self, *, include_partial: bool = False) -> list[RankingRow]:
        rows = self.latest_observations(include_partial=include_partial)
        result: list[RankingRow] = []
        for row in rows:
            spread = row["unit_spread_cents"]
            if spread is None or spread >= 0:
                continue
            result.append(
                RankingRow(
                    product_key=row["product_key"],
                    variant_key=row["variant_key"],
                    name=row["name"],
                    canonical_url=row["canonical_url"],
                    brand=row["brand"],
                    brand_type=row["brand_type"],
                    captured_at=row["captured_at"],
                    currency=row["currency"],
                    selling_price_cents=row["selling_price_cents"],
                    reported_total_cost_cents=row["reported_total_cost_cents"],
                    unit_spread_cents=spread,
                    margin_pct=row["margin_pct"],
                    parse_status=row["parse_status"],
                    confidence=row["confidence"],
                )
            )
        return result

