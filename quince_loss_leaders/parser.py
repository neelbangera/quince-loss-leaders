from __future__ import annotations

from datetime import datetime
from html.parser import HTMLParser
import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from .models import CostLine, ProductObservation


MONEY_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:USD\s*)?\$\s*"
    r"([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)"
)


COST_LABELS: dict[str, tuple[str, ...]] = {
    "materials": ("materials", "material"),
    "crafting_cost": ("crafting cost", "crafting costs", "craft cost"),
    "packaging": ("packaging", "packaging cost"),
    "freight_handling": (
        "freight & handling",
        "freight and handling",
        "freight handling",
        "freight & shipping",
    ),
    "credit_card_fees": (
        "credit card fees",
        "credit card fee",
        "credit-card fees",
        "credit card processing fees",
    ),
    "duties_taxes_fees": (
        "duties, taxes, and fees",
        "duties taxes and fees",
        "duties, taxes & fees",
        "duties taxes fees",
    ),
}


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


def normalize_label(value: str) -> str:
    value = normalize_space(value).lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return normalize_space(value)


def parse_money(value: str | None) -> Decimal | None:
    if not value:
        return None
    match = MONEY_RE.search(value)
    if not match:
        # Structured metadata commonly stores amounts as bare numeric strings
        # such as `29.99`, while visible page text normally includes `$`.
        bare_number = re.fullmatch(
            r"\s*[0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?\s*|\s*[0-9]+(?:\.[0-9]{1,2})?\s*",
            value,
        )
        if not bare_number:
            return None
        numeric_text = value.strip().replace(",", "")
    else:
        numeric_text = match.group(1).replace(",", "")
    try:
        return Decimal(numeric_text).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def _first_money(values: Iterable[str]) -> Decimal | None:
    for value in values:
        parsed = parse_money(value)
        if parsed is not None:
            return parsed
    return None


class _HTMLCollector(HTMLParser):
    """Collects semantic page fragments without depending on CSS class names."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.canonical: str | None = None
        self.rows: list[list[str]] = []
        self.headings: list[str] = []
        self.text_parts: list[str] = []
        self.jsonld_parts: list[str] = []
        self.price_attribute_values: list[str] = []

        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._heading: list[str] | None = None
        self._script_parts: list[str] | None = None
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.lower(): value or "" for key, value in attrs}
        tag = tag.lower()

        if tag == "meta":
            key = (
                attributes.get("property")
                or attributes.get("name")
                or attributes.get("itemprop")
            )
            content = attributes.get("content")
            if key and content:
                self.meta[key.lower()] = normalize_space(content)

        if tag == "link" and attributes.get("rel", "").lower() == "canonical":
            self.canonical = attributes.get("href") or None

        for attr_name in ("data-price", "data-product-price", "data-selling-price"):
            if attributes.get(attr_name):
                self.price_attribute_values.append(attributes[attr_name])

        if tag == "script":
            script_type = attributes.get("type", "").lower()
            if script_type == "application/ld+json":
                self._script_parts = []
            else:
                self._script_parts = None

        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1

        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []
        elif tag in {"h1", "h2"}:
            self._heading = []

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()

        if tag == "td" or tag == "th":
            if self._row is not None and self._cell is not None:
                value = normalize_space(" ".join(self._cell))
                self._row.append(value)
            self._cell = None
        elif tag == "tr":
            if self._row:
                self.rows.append(self._row)
            self._row = None
            self._cell = None
        elif tag in {"h1", "h2"}:
            if self._heading:
                self.headings.append(normalize_space(" ".join(self._heading)))
            self._heading = None

        if tag == "script" and self._script_parts is not None:
            self.jsonld_parts.append("".join(self._script_parts))
            self._script_parts = None

        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._script_parts is not None:
            self._script_parts.append(data)
            return
        if self._skip_depth:
            return

        if self._cell is not None:
            self._cell.append(data)
        if self._heading is not None:
            self._heading.append(data)
        self.text_parts.append(data)

    @property
    def text(self) -> str:
        return normalize_space(" ".join(self.text_parts))


def _walk_json(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from _walk_json(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_json(nested)


def _jsonld_products(parts: Iterable[str]) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    for part in parts:
        try:
            value = json.loads(part)
        except json.JSONDecodeError:
            continue
        for candidate in _walk_json(value):
            kind = candidate.get("@type")
            kinds = kind if isinstance(kind, list) else [kind]
            if any(str(item).lower() == "product" for item in kinds if item):
                products.append(candidate)
    return products


def _jsonld_offer(product: dict[str, Any]) -> dict[str, Any] | None:
    offers = product.get("offers")
    if isinstance(offers, list):
        return offers[0] if offers and isinstance(offers[0], dict) else None
    return offers if isinstance(offers, dict) else None


def _jsonld_brand(product: dict[str, Any]) -> str | None:
    brand = product.get("brand")
    if isinstance(brand, dict):
        value = brand.get("name")
        return str(value).strip() if value else None
    return str(brand).strip() if brand else None


def _jsonld_price(product: dict[str, Any]) -> Decimal | None:
    offer = _jsonld_offer(product)
    if not offer:
        return None
    value = offer.get("price") or offer.get("lowPrice")
    if value is None:
        return None
    return parse_money(f"${value}")


def _match_cost_label(label: str) -> tuple[str, str] | None:
    normalized = normalize_label(label)
    for normalized_type, aliases in COST_LABELS.items():
        if normalized in {normalize_label(alias) for alias in aliases}:
            return normalized_type, normalize_space(label)
    return None


def _extract_costs(collector: _HTMLCollector) -> tuple[list[CostLine], Decimal | None, str]:
    lines: list[CostLine] = []
    total: Decimal | None = None
    total_source = "reported"
    found_types: set[str] = set()

    for row in collector.rows:
        if not row:
            continue
        label = row[0]
        normalized_label = normalize_label(label)
        amount = _first_money(reversed(row))
        if amount is None:
            continue
        match = _match_cost_label(label)
        if match and match[0] not in found_types:
            normalized_type, source_label = match
            lines.append(
                CostLine(
                    label=source_label,
                    normalized_type=normalized_type,
                    amount=amount,
                    source_text=" | ".join(row),
                )
            )
            found_types.add(normalized_type)
        elif "total cost" in normalized_label and total is None:
            total = amount

    # Fallback for layouts where the cost block is rendered as adjacent divs
    # instead of table rows. The bounded search avoids scanning arbitrary page
    # text indefinitely and deliberately treats this as lower-confidence data.
    flat_text = collector.text
    for normalized_type, aliases in COST_LABELS.items():
        if normalized_type in found_types:
            continue
        for alias in aliases:
            pattern = re.compile(
                rf"\b{re.escape(alias)}\b(?P<tail>.{{0,80}}?)(?P<money>{MONEY_RE.pattern})",
                re.IGNORECASE,
            )
            match = pattern.search(flat_text)
            if match:
                amount = parse_money(match.group("money"))
                if amount is not None:
                    lines.append(
                        CostLine(
                            label=alias,
                            normalized_type=normalized_type,
                            amount=amount,
                            source_text=match.group(0),
                        )
                    )
                    found_types.add(normalized_type)
                    break

    if total is None:
        match = re.search(
            rf"\btotal\s+cost\b(?P<tail>.{{0,80}}?)(?P<money>{MONEY_RE.pattern})",
            flat_text,
            flags=re.IGNORECASE,
        )
        if match:
            total = parse_money(match.group("money"))

    if total is None and lines:
        total = sum((line.amount for line in lines), Decimal("0.00")).quantize(Decimal("0.01"))
        total_source = "inferred"

    return lines, total, total_source


def _extract_store_credit(text: str) -> Decimal | None:
    match = re.search(
        rf"earn\s+(?P<money>{MONEY_RE.pattern})\s+credit",
        text,
        flags=re.IGNORECASE,
    )
    return parse_money(match.group("money")) if match else None


def _extract_price(collector: _HTMLCollector, products: list[dict[str, Any]]) -> Decimal | None:
    meta_keys = (
        "product:price:amount",
        "og:price:amount",
        "price",
    )
    for key in meta_keys:
        value = parse_money(collector.meta.get(key))
        if value is not None:
            return value

    for value in collector.price_attribute_values:
        parsed = parse_money(value)
        if parsed is not None:
            return parsed

    for product in products:
        parsed = _jsonld_price(product)
        if parsed is not None:
            return parsed
    return None


def parse_html(
    html: str,
    source_ref: str,
    *,
    captured_at: datetime | None = None,
    canonical_url: str | None = None,
) -> ProductObservation:
    """Parse a saved product page into one observation.

    This function intentionally does not fetch URLs. Keeping ingestion local
    makes it useful for authorized page exports and parser tests, and leaves a
    future approved API/feed adapter independent from the parsing logic.
    """

    collector = _HTMLCollector()
    collector.feed(html)
    products = _jsonld_products(collector.jsonld_parts)
    product = products[0] if products else {}

    canonical = canonical_url or collector.canonical
    name = (
        str(product.get("name")).strip()
        if product.get("name")
        else (collector.headings[0] if collector.headings else collector.meta.get("og:title"))
    )
    brand = _jsonld_brand(product)
    sku = str(product.get("sku")).strip() if product.get("sku") else None
    currency = (
        str((_jsonld_offer(product) or {}).get("priceCurrency") or "USD").upper()
    )
    selling_price = _extract_price(collector, products)
    cost_lines, total_cost, total_source = _extract_costs(collector)

    observation = ProductObservation(
        source_ref=source_ref,
        captured_at=captured_at or datetime.now().astimezone(),
        canonical_url=canonical,
        sku=sku,
        product_name=name,
        brand=brand,
        brand_type="quince" if brand and brand.lower() == "quince" else "unknown",
        currency=currency,
        selling_price=selling_price,
        store_credit=_extract_store_credit(collector.text),
        reported_total_cost=total_cost,
        total_cost_source=total_source,
        cost_lines=cost_lines,
        raw_sha256=hashlib.sha256(html.encode("utf-8")).hexdigest(),
        metadata={
            "headings": collector.headings,
            "jsonld_product_count": len(products),
        },
    )
    observation.finalize_identity()

    if selling_price is None:
        observation.add_issue("missing_price", "Could not find the product selling price.", "error")
    if total_cost is None:
        observation.add_issue(
            "missing_total_cost", "Could not find a reported or inferable total cost.", "error"
        )
    if not cost_lines:
        observation.add_issue(
            "missing_cost_lines", "Could not find any recognized cost components.", "error"
        )

    if cost_lines:
        line_sum = sum((line.amount for line in cost_lines), Decimal("0.00")).quantize(
            Decimal("0.01")
        )
        if total_cost is not None and line_sum != total_cost:
            observation.add_issue(
                "cost_total_mismatch",
                f"Cost lines sum to {line_sum}, but reported total is {total_cost}.",
                "error",
            )

        if all(line.amount == 0 for line in cost_lines) and total_cost == 0:
            observation.add_issue(
                "zero_cost_placeholder",
                "All cost values are zero; treating this as missing data rather than free inventory.",
                "error",
            )

    observation.calculate_metrics()
    errors = [issue for issue in observation.issues if issue.severity == "error"]
    if errors:
        observation.parse_status = "invalid" if any(
            issue.code == "zero_cost_placeholder" for issue in errors
        ) else "partial"
    elif selling_price is not None and total_cost is not None and cost_lines:
        observation.parse_status = "complete"
    else:
        observation.parse_status = "missing"

    return observation
