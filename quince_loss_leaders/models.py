from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import hashlib
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


PARSER_VERSION = "0.2.0"
CALCULATION_VERSION = "0.1.0"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc_iso(value: datetime) -> str:
    """Return a stable ISO-8601 representation for storage."""

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def money_to_cents(value: Decimal | None) -> int | None:
    if value is None:
        return None
    cents = (value * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(cents)


def cents_to_money(value: int | None) -> Decimal | None:
    if value is None:
        return None
    return (Decimal(value) / Decimal("100")).quantize(Decimal("0.01"))


def canonicalize_url(value: str | None) -> str | None:
    """Remove tracking query parameters while retaining meaningful variants."""

    if not value:
        return None
    parsed = urlsplit(value)
    if not parsed.scheme or not parsed.netloc:
        return value

    meaningful_query_keys = {"color", "size", "variant", "sku", "id"}
    query = [
        (key, val)
        for key, val in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() in meaningful_query_keys
    ]
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/") or "/",
            urlencode(sorted(query)),
            "",
        )
    )


def stable_product_key(canonical_url: str | None, source_ref: str, sku: str | None) -> str:
    if sku:
        return f"sku:{sku.strip()}"
    if canonical_url:
        return canonical_url
    # Local fixture paths are stable enough for repeated runs, while avoiding
    # making the full path part of every displayed product name.
    digest = hashlib.sha256(source_ref.encode("utf-8")).hexdigest()[:16]
    return f"local:{digest}"


@dataclass(frozen=True)
class CostLine:
    label: str
    normalized_type: str
    amount: Decimal
    source_text: str | None = None


@dataclass(frozen=True)
class ParseIssue:
    code: str
    message: str
    severity: str = "warning"


@dataclass
class ProductObservation:
    """One immutable observation of one product/variant at one point in time.

    The model intentionally contains both normalized fields and an extensible
    metadata dictionary. New data such as ratings, inventory, benchmark prices,
    or demand signals can be added without changing the parser's core math.
    """

    source_ref: str
    captured_at: datetime = field(default_factory=utc_now)
    canonical_url: str | None = None
    product_key: str | None = None
    variant_key: str = ""
    sku: str | None = None
    product_name: str | None = None
    brand: str | None = None
    brand_type: str = "unknown"
    category: str | None = None
    region: str = "US"
    currency: str = "USD"
    selling_price: Decimal | None = None
    regular_price: Decimal | None = None
    store_credit: Decimal | None = None
    traditional_retail_price: Decimal | None = None
    reported_total_cost: Decimal | None = None
    total_cost_source: str = "reported"
    cost_lines: list[CostLine] = field(default_factory=list)
    availability: str | None = None
    parse_status: str = "unknown"
    issues: list[ParseIssue] = field(default_factory=list)
    raw_sha256: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    parser_version: str = PARSER_VERSION
    calculation_version: str = CALCULATION_VERSION
    unit_spread: Decimal | None = None
    margin_pct: Decimal | None = None
    markup_pct: Decimal | None = None

    def add_issue(self, code: str, message: str, severity: str = "warning") -> None:
        self.issues.append(ParseIssue(code=code, message=message, severity=severity))

    def finalize_identity(self) -> None:
        self.canonical_url = canonicalize_url(self.canonical_url)
        self.product_key = self.product_key or stable_product_key(
            self.canonical_url, self.source_ref, self.sku
        )

    def calculate_metrics(self) -> None:
        if self.selling_price is None or self.reported_total_cost is None:
            self.unit_spread = None
            self.margin_pct = None
            self.markup_pct = None
            return

        self.unit_spread = self.selling_price - self.reported_total_cost
        if self.selling_price > 0:
            self.margin_pct = (self.unit_spread / self.selling_price * Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        else:
            self.margin_pct = None

        if self.reported_total_cost > 0:
            self.markup_pct = (
                self.unit_spread / self.reported_total_cost * Decimal("100")
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            self.markup_pct = None

    @property
    def is_rankable(self) -> bool:
        return (
            self.parse_status == "complete"
            and self.selling_price is not None
            and self.selling_price > 0
            and self.reported_total_cost is not None
            and self.unit_spread is not None
        )

    @property
    def classification(self) -> str:
        if not self.is_rankable or self.unit_spread is None:
            return "unknown"
        if self.unit_spread < 0:
            return "loss"
        if self.unit_spread == 0:
            return "break_even"
        return "positive"

    @property
    def confidence(self) -> Decimal:
        if self.parse_status == "complete":
            return Decimal("1.00")
        if self.parse_status == "partial":
            return Decimal("0.60")
        return Decimal("0.00")

    def to_json_dict(self) -> dict[str, Any]:
        def money(value: Decimal | None) -> str | None:
            return str(value) if value is not None else None

        return {
            "source_ref": self.source_ref,
            "captured_at": as_utc_iso(self.captured_at),
            "canonical_url": self.canonical_url,
            "product_key": self.product_key,
            "variant_key": self.variant_key,
            "sku": self.sku,
            "product_name": self.product_name,
            "brand": self.brand,
            "brand_type": self.brand_type,
            "category": self.category,
            "region": self.region,
            "currency": self.currency,
            "selling_price": money(self.selling_price),
            "regular_price": money(self.regular_price),
            "store_credit": money(self.store_credit),
            "traditional_retail_price": money(self.traditional_retail_price),
            "reported_total_cost": money(self.reported_total_cost),
            "total_cost_source": self.total_cost_source,
            "cost_lines": [
                {
                    "label": line.label,
                    "normalized_type": line.normalized_type,
                    "amount": money(line.amount),
                }
                for line in self.cost_lines
            ],
            "availability": self.availability,
            "parse_status": self.parse_status,
            "classification": self.classification,
            "unit_spread": money(self.unit_spread),
            "margin_pct": money(self.margin_pct),
            "markup_pct": money(self.markup_pct),
            "confidence": str(self.confidence),
            "issues": [issue.__dict__ for issue in self.issues],
            "raw_sha256": self.raw_sha256,
            "metadata": self.metadata,
            "parser_version": self.parser_version,
            "calculation_version": self.calculation_version,
        }
