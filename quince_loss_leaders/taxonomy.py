"""Small, explainable taxonomy helpers for the first dashboard slice.

Quince's product pages do not expose one stable category field in every
snapshot, so the dashboard needs a useful fallback.  The rules here are
deliberately conservative and are presentation metadata: they never alter the
cost calculation or ranking itself.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Taxonomy:
    department: str
    department_label: str
    category: str
    category_label: str
    source: str


DEPARTMENT_LABELS: dict[str, str] = {
    "women": "Women",
    "men": "Men",
    "home": "Home",
    "unisex": "Unisex",
    "beauty-and-wellness": "Beauty & Wellness",
    "beauty-wellness": "Beauty & Wellness",
    "baby-and-kids": "Baby & Kids",
    "baby-kids": "Baby & Kids",
    "health-and-wellness": "Health & Wellness",
    "health-wellness": "Health & Wellness",
    "food-and-wine": "Food & Wine",
}


# Ordered from specific to broad so, for example, a jewelry gift box is not
# classified as a generic box before its jewelry term is considered.
CATEGORY_RULES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("jewelry", "Jewelry", ("jewelry", "ring", "necklace", "earring", "huggies", "charm")),
    ("pants", "Pants", ("pants", "pant", "trouser", "jeans", "legging", "jogger")),
    ("dresses", "Dresses", ("dress",)),
    ("skirts", "Skirts", ("skirt",)),
    (
        "tops",
        "Tops",
        (
            "shirt",
            "blouse",
            "top",
            "tee",
            "sweater",
            "sweatshirt",
            "hoodie",
            "cardigan",
            "pullover",
            "tank",
            "camisole",
            "bodysuit",
        ),
    ),
    (
        "outerwear",
        "Outerwear",
        ("jacket", "coat", "blazer", "vest", "parka", "trench", "puffer"),
    ),
    (
        "shoes",
        "Shoes",
        ("shoe", "sneaker", "boot", "loafer", "flat", "sandal", "heel", "mule", "slipper"),
    ),
    (
        "bags",
        "Bags",
        ("bag", "tote", "purse", "backpack", "crossbody", "clutch", "wallet"),
    ),
    (
        "accessories",
        "Accessories",
        ("hat", "cap", "scarf", "belt", "glove", "sunglasses", "sock", "tie"),
    ),
    (
        "bedding",
        "Bedding",
        ("sheet", "duvet", "comforter", "pillow", "blanket", "quilt", "mattress"),
    ),
    (
        "furniture",
        "Furniture",
        (
            "sofa",
            "chair",
            "table",
            "desk",
            "bed",
            "dresser",
            "ottoman",
            "bench",
            "nightstand",
            "shelf",
            "cabinet",
            "stool",
        ),
    ),
    (
        "home-decor",
        "Home Decor",
        ("rug", "curtain", "mirror", "vase", "candle", "art", "lamp", "lighting"),
    ),
    ("bath", "Bath", ("towel", "robe", "bath", "shower")),
    (
        "beauty",
        "Beauty",
        ("serum", "cream", "cleanser", "shampoo", "conditioner", "makeup", "fragrance", "perfume"),
    ),
    ("kids", "Kids", ("baby", "kid", "toddler", "child")),
    ("pet", "Pet", ("dog", "cat", "pet")),
    ("travel", "Travel", ("luggage", "suitcase", "carry-on", "packing")),
    ("food", "Food", ("olive oil", "coffee", "tea", "honey", "wine", "snack")),
)


def _slug(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.lower())).strip("-")


def _token_text(*values: str | None) -> str:
    text = " ".join(value or "" for value in values).lower()
    return f" {re.sub(r'[^a-z0-9]+', ' ', text)} "


def _contains_term(text: str, term: str) -> bool:
    normalized_term = re.sub(r"[^a-z0-9]+", " ", term.lower()).strip()
    return f" {normalized_term} " in text


def infer_taxonomy(
    canonical_url: str | None,
    product_name: str | None,
    stored_category: str | None = None,
) -> Taxonomy:
    """Return stable filter values, using stored data before URL/name rules."""

    path_parts = [part for part in urlsplit(canonical_url or "").path.split("/") if part]
    department_slug = _slug(path_parts[0]) if path_parts else "other"
    if department_slug.startswith("mens"):
        department_slug = "men"
    elif department_slug.startswith("womens"):
        department_slug = "women"

    department_label = DEPARTMENT_LABELS.get(department_slug)
    if department_label is None:
        department_slug = "other"
        department_label = "Other"

    if stored_category:
        category_slug = _slug(stored_category)
        category_label = stored_category.replace("_", " ").replace("-", " ").title()
        return Taxonomy(
            department=department_slug,
            department_label=department_label,
            category=category_slug or "other",
            category_label=category_label or "Other",
            source="stored",
        )

    page_slug = path_parts[-1] if path_parts else ""
    text = _token_text(product_name, page_slug)
    for category_slug, category_label, terms in CATEGORY_RULES:
        if any(_contains_term(text, term) for term in terms):
            return Taxonomy(
                department=department_slug,
                department_label=department_label,
                category=category_slug,
                category_label=category_label,
                source="inferred",
            )

    return Taxonomy(
        department=department_slug,
        department_label=department_label,
        category="other",
        category_label="Other",
        source="inferred",
    )
