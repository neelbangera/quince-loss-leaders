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


# Each category lists the nouns that name a product of that kind, singular.
# A name is read from its end, because the last noun is what the thing is:
# a "Dress Shirt" is a shirt, a "Flat Sheet" is a sheet, a "Towel Polo" is a
# polo. Multi-word terms win over the single word they end with, so a
# "Bed Skirt" is bedding and a "Table Runner" is not a table.
CATEGORY_RULES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("pet", "Pet", ("dog collar", "dog leash", "dog bed", "dog harness", "dog toy", "pet bed", "dog bowl")),
    (
        "jewelry",
        "Jewelry",
        (
            "jewelry", "ring", "necklace", "earring", "huggie", "charm", "band", "stud", "hoop",
            "bracelet", "bangle", "pendant", "chain", "anklet", "choker", "ctw", "carat", "cuff",
            "solitaire", "lariat",
        ),
    ),
    (
        "dresses",
        "Dresses & Jumpsuits",
        ("dress", "gown", "jumpsuit", "romper", "overall", "shortall", "caftan", "kaftan"),
    ),
    (
        "sweaters",
        "Sweaters",
        (
            "sweater", "cardigan", "pullover", "sweatshirt", "hoodie", "crew", "crewneck",
            "turtleneck", "quarter zip", "half zip", "full zip", "mockneck", "v neck", "fleece",
        ),
    ),
    (
        "tops",
        "Tops",
        (
            "shirt", "blouse", "top", "tee", "tank", "camisole", "cami", "bodysuit", "polo",
            "henley", "tunic", "undershirt", "t shirt", "popover", "onesie", "button down",
            "base layer", "one piece",
        ),
    ),
    (
        "pants",
        "Pants",
        (
            "pant", "trouser", "jean", "legging", "jogger", "sweatpant", "chino", "capri",
            "tight", "culotte", "flare", "wide leg", "straight leg", "jegging", "cargo",
            "base layer bottom",
        ),
    ),
    ("shorts", "Shorts", ("short", "skort", "sweatshort")),
    ("skirts", "Skirts", ("skirt",)),
    (
        "outerwear",
        "Outerwear",
        (
            "jacket", "coat", "blazer", "vest", "parka", "trench", "puffer", "overcoat",
            "peacoat", "topcoat", "anorak", "shacket", "bomber", "cape", "poncho", "ruana",
            "overshirt", "windbreaker", "gilet",
        ),
    ),
    (
        "swim",
        "Swimwear",
        (
            "swimsuit", "swim trunk", "swim short", "boardshort", "rash guard",
            "bikini top", "bikini bottom", "swim top", "swim bottom", "one piece swimsuit",
            "cover up", "coverup", "swim brief", "tankini",
        ),
    ),
    (
        "sleep-underwear",
        "Sleep & Underwear",
        (
            "bra", "bralette", "thong", "brief", "boyshort", "hipster", "boxer", "trunk", "bikini",
            "pajama", "pj", "nightgown", "sleepshirt", "chemise", "underwear",
            "sleep bag", "sleeping bag", "sleep sack", "swaddle", "footie", "sleeper",
            "sleep set", "lounge set", "pajama set", "sleep mask", "eye mask",
        ),
    ),
    (
        "shoes",
        "Shoes",
        (
            "shoe", "sneaker", "boot", "bootie", "loafer", "flat", "sandal", "heel", "mule",
            "slipper", "slide", "pump", "derby", "oxford", "clog", "espadrille", "moccasin",
            "flip flop", "trainer", "slip on", "runner",
        ),
    ),
    (
        "bags",
        "Bags & Wallets",
        (
            "bag", "tote", "purse", "backpack", "crossbody", "clutch", "wallet", "satchel",
            "wristlet", "sling", "briefcase", "weekender", "duffle", "duffel", "pouch",
            "card holder", "card case", "folio", "portfolio", "laptop sleeve",
            "laptop case", "belt bag", "lunch box", "case",
        ),
    ),
    (
        "travel",
        "Travel",
        (
            "luggage", "suitcase", "carry on", "packing cube", "luggage tag", "passport holder",
            "passport case", "toiletry bag", "toiletry case", "dopp kit", "garment bag",
            "travel case", "travel pouch",
        ),
    ),
    (
        "accessories",
        "Accessories",
        (
            "hat", "cap", "scarf", "belt", "glove", "sunglasses", "sock", "tie", "beanie",
            "mitten", "headband", "scrunchie", "beret", "snood", "balaclava", "shawl", "wrap",
            "earmuff", "fedora", "bandana", "umbrella", "strap", "key ring", "keychain",
            "key chain", "bib", "watch band", "smartwatch band", "hair clip", "visor",
            "iphone case", "magsafe case", "phone case", "multi use cover",
        ),
    ),
    (
        "bedding",
        "Bedding",
        (
            "sheet", "duvet", "comforter", "pillow", "pillowcase", "blanket", "quilt",
            "mattress", "sham", "coverlet", "bed skirt", "duvet cover", "topper", "protector",
            "throw", "bedspread", "pillow case", "bedding bundle", "bedding set",
        ),
    ),
    (
        "bath",
        "Bath",
        (
            "towel", "washcloth", "bath mat", "bath rug", "bath sheet", "shower curtain",
            "bath bundle", "hamper", "bath", "shower", "bathroom", "dryer ball",
        ),
    ),
    (
        "furniture",
        "Furniture",
        (
            "sofa", "sectional", "chair", "armchair", "table", "desk", "bed", "dresser",
            "ottoman", "bench", "nightstand", "shelf", "bookshelf", "bookcase", "cabinet",
            "stool", "sideboard", "loveseat", "credenza", "console", "chest", "headboard",
            "daybed", "dining set", "recliner", "pouf",
        ),
    ),
    (
        "kitchen-dining",
        "Kitchen & Dining",
        (
            "knife", "pan", "pot", "saucepan", "stockpot", "skillet", "bowl", "plate", "glass",
            "mug", "cup", "fork", "spoon", "flatware", "dinnerware", "cookware", "napkin",
            "placemat", "tablecloth", "table runner", "cutting board", "board", "block",
            "grinder", "mill", "shears", "lid", "dutch oven", "apron", "tea towel",
            "kitchen towel", "dish towel", "tumbler", "carafe", "pitcher", "decanter",
            "coaster", "utensil", "spatula", "colander", "kettle", "platter", "glassware",
            "wok", "griddle", "braiser", "fryer", "steamer", "ladle", "whisk", "tong",
            "oven mitt", "pot holder", "serving tray", "salad server", "flute", "coupe",
        ),
    ),
    (
        "home-decor",
        "Home Decor",
        (
            "rug", "curtain", "mirror", "vase", "candle", "art", "lamp", "lighting", "sconce",
            "frame", "wreath", "garland", "tree", "stocking", "basket", "planter", "book",
            "print", "diffuser", "room spray", "spray", "tray", "box", "drape", "ornament",
            "bookend", "clock", "throw pillow", "pillow cover", "lumbar pillow", "candle holder",
            "chandelier", "pendant light", "doormat", "mat", "refill", "sculpture",
            "candlestick", "tree skirt", "tree collar",
        ),
    ),
    (
        "supplements",
        "Vitamins & Supplements",
        (
            "creatine", "monohydrate", "multivitamin", "vitamin", "capsule", "gummy", "powder",
            "protein", "isolate", "collagen", "probiotic", "synbiotic", "colostrum",
            "supplement", "greens", "pre workout", "drink mix", "electrolyte", "magnesium",
            "omega", "focus blend", "stress support", "support",
        ),
    ),
    (
        "beauty",
        "Beauty",
        (
            "serum", "cream", "cleanser", "shampoo", "conditioner", "makeup", "fragrance",
            "perfume", "parfum", "lotion", "moisturizer", "mask", "body oil", "face oil",
            "hair oil", "balm", "toner", "sunscreen", "discovery set", "mascara", "lipstick",
            "comb", "brush", "essence", "body wash", "hand wash", "soap", "exfoliant", "peel",
            "eau de parfum", "eau de toilette",
        ),
    ),
    ("food", "Food", ("olive oil", "coffee", "tea", "honey", "wine", "snack", "caviar", "chocolate", "vinegar")),
)

# A robe is sleepwear on a clothing page and bath linen on a home page; a
# pendant is jewelry on a person and a light in a room.
DEPARTMENT_CATEGORY_OVERRIDES: dict[tuple[str, str], str] = {
    ("home", "jewelry"): "home-decor",
    ("home", "sleep-underwear"): "bedding",
    ("beauty-wellness", "home-decor"): "beauty",
}
ROBE_TERM = "robe"

# These words describe a pet product wherever they fall in the name.
PET_WORDS = frozenset({"dog", "pet", "puppy"})

KID_SEGMENTS = frozenset({"baby-and-kids", "baby-kids", "kids", "baby"})
KID_WORDS = frozenset({"baby", "babies", "kid", "kids", "toddler", "toddlers", "girl", "girls", "boy", "boys", "infant", "newborn", "crib"})

IRREGULAR_SINGULARS: dict[str, str] = {
    "knives": "knife",
    "shelves": "shelf",
    "scarves": "scarf",
    "gummies": "gummy",
    "booties": "bootie",
    "huggies": "huggie",
    "scrunchies": "scrunchie",
    "footies": "footie",
    "onesies": "onesie",
    "hoodies": "hoodie",
    "beanies": "beanie",
}

# A trailing "in Olive" names a colour. Colours such as Wine, Cream, Honey and
# Camel would otherwise be read as the product.
COLOR_SUFFIX_RE = re.compile(r"\s+in\s+(?:[^\s()]+\s*){1,5}$", re.IGNORECASE)
# "Dining Chair with Powder Coated Iron Legs" is a chair; what follows "with"
# describes it.
WITH_CLAUSE_RE = re.compile(r"\s+with\s+.*$", re.IGNORECASE)
# Framed prints are titled like artworks: "Blue Plant by Marco Marella".
ARTIST_CREDIT_RE = re.compile(r"\sby\s+[A-Z][\w'.-]+\s+[A-Z][\w'.-]+(?:\s*\(.*\))?$")

CATEGORY_LABELS: dict[str, str] = {slug: label for slug, label, _ in CATEGORY_RULES}
CATEGORY_LABELS["pet"] = "Pet"


def _build_terms() -> dict[int, dict[tuple[str, ...], str]]:
    by_length: dict[int, dict[tuple[str, ...], str]] = {}
    for category_slug, _label, terms in CATEGORY_RULES:
        for term in terms:
            words = tuple(re.findall(r"[a-z0-9]+", term.lower()))
            by_length.setdefault(len(words), {}).setdefault(words, category_slug)
    return by_length


TERMS_BY_LENGTH = _build_terms()
MAX_TERM_LENGTH = max(TERMS_BY_LENGTH)


def _slug(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.lower())).strip("-")


def _word_forms(word: str) -> frozenset[str]:
    """A word and its likely singular, so "shorts" matches "short"."""

    forms = {word}
    if word in IRREGULAR_SINGULARS:
        forms.add(IRREGULAR_SINGULARS[word])
    elif len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        forms.add(word[:-1])
        if word.endswith("es"):
            forms.add(word[:-2])
    return frozenset(forms)


def _words(value: str | None) -> list[frozenset[str]]:
    return [_word_forms(word) for word in re.findall(r"[a-z0-9]+", (value or "").lower())]


def _category_from_words(words: list[frozenset[str]]) -> str | None:
    """Return the category of the last product noun in the words."""

    for end in range(len(words), 0, -1):
        for length in range(min(MAX_TERM_LENGTH, end), 0, -1):
            window = words[end - length:end]
            for term, category_slug in TERMS_BY_LENGTH.get(length, {}).items():
                if all(part in forms for part, forms in zip(term, window)):
                    return category_slug
    return None


def _infer_category(product_name: str | None, page_slug: str, department_slug: str) -> str:
    name = COLOR_SUFFIX_RE.sub("", (product_name or "").strip())
    if department_slug == "home" and ARTIST_CREDIT_RE.search(name):
        return "home-decor"
    name = WITH_CLAUSE_RE.sub("", name)
    for words in (_words(name), _words(page_slug)):
        if not words:
            continue
        flat = frozenset().union(*words)
        if flat & PET_WORDS:
            return "pet"
        if ROBE_TERM in flat:
            return "bath" if department_slug == "home" else "sleep-underwear"
        category_slug = _category_from_words(words)
        if category_slug:
            return DEPARTMENT_CATEGORY_OVERRIDES.get((department_slug, category_slug), category_slug)
    return "other"


def _names_a_child(words: list[str]) -> bool:
    for index, word in enumerate(words):
        following = words[index + 1] if index + 1 < len(words) else ""
        # "Baby Alpaca" is a fibre, not an age.
        if word in KID_WORDS and following != "alpaca":
            return True
    return False


def _infer_department(path_parts: list[str], product_name: str | None = None) -> str:
    department_slug = _slug(path_parts[0]) if path_parts else "other"
    if department_slug.startswith("mens"):
        department_slug = "men"
    elif department_slug.startswith("womens"):
        department_slug = "women"
    elif department_slug == "beauty":
        department_slug = "beauty-wellness"
    if department_slug not in DEPARTMENT_LABELS:
        department_slug = "other"

    # Quince files many children's items under /unisex or /home/baby-and-kids,
    # and a few products under no department at all. The page slug says who
    # the item is for.
    middle = {_slug(part).replace("and-", "") for part in path_parts[1:-1]} | {_slug(part) for part in path_parts[1:-1]}
    page_words = re.findall(r"[a-z0-9]+", path_parts[-1].lower()) if path_parts else []
    if middle & KID_SEGMENTS:
        return "baby-kids"
    if department_slug in {"unisex", "other"}:
        name_words = re.findall(r"[a-z0-9]+", (product_name or "").lower())
        if _names_a_child(page_words) or _names_a_child(name_words):
            return "baby-kids"
    if department_slug == "other" and page_words:
        if page_words[0] in {"mens", "men"}:
            return "men"
        if page_words[0] in {"womens", "women"}:
            return "women"
    return department_slug


def infer_taxonomy(
    canonical_url: str | None,
    product_name: str | None,
    stored_category: str | None = None,
) -> Taxonomy:
    """Return stable filter values, using stored data before URL/name rules."""

    path_parts = [part for part in urlsplit(canonical_url or "").path.split("/") if part]
    department_slug = _infer_department(path_parts, product_name)
    department_label = DEPARTMENT_LABELS.get(department_slug, "Other")

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

    category_slug = _infer_category(product_name, path_parts[-1] if path_parts else "", department_slug)
    return Taxonomy(
        department=department_slug,
        department_label=department_label,
        category=category_slug,
        category_label=CATEGORY_LABELS.get(category_slug, "Other"),
        source="inferred",
    )
