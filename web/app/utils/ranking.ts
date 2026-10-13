import type { Classification, Facet, ProductResult, Sort, SortField, View } from "~/types/ranking";

export function productVariants(product: ProductResult): ProductResult[] {
  return product.variants?.length ? product.variants : [product];
}

export function productKey(product: ProductResult) {
  return `${product.productKey}::${product.variantKey}`;
}

export function sameVariant(left: ProductResult | null | undefined, right: ProductResult | null | undefined) {
  return Boolean(left && right && left.productKey === right.productKey && left.variantKey === right.variantKey);
}

export function productHasClassification(product: ProductResult, classification: Classification) {
  if (classification === "mixed") return product.classification === "mixed";
  return productVariants(product).some((variant) => variant.classification === classification)
    || product.classification === classification;
}

// A view lists any style with at least one option on that side of cost, so a
// style whose options disagree appears in both Below cost and Above cost.
export function inView(product: ProductResult, view: View) {
  if (view === "losses") return productHasClassification(product, "loss");
  if (view === "profit") return productHasClassification(product, "profit");
  return true;
}

export interface RankingFilter {
  department?: string;
  category?: string;
  search?: string;
}

export function matchesFilter(product: ProductResult, filter: RankingFilter) {
  const term = (filter.search ?? "").trim().toLowerCase();
  return productVariants(product).some((variant) => {
    if (filter.department && variant.department !== filter.department) return false;
    if (filter.category && variant.category !== filter.category) return false;
    if (!term) return true;
    return [
      variant.name,
      variant.brand || "",
      variant.departmentLabel,
      variant.categoryLabel,
      variant.variantLabel || "",
      variant.variantColor || "",
      variant.variantSize || "",
    ].join(" ").toLowerCase().includes(term);
  });
}

export function facetValues(items: ProductResult[], field: "department" | "category"): Facet[] {
  const counts = new Map<string, Facet>();
  for (const item of items) {
    const value = field === "department" ? item.department : item.category;
    const label = field === "department" ? item.departmentLabel : item.categoryLabel;
    const current = counts.get(value);
    if (current) current.count += 1;
    else counts.set(value, { value, label, count: 1 });
  }
  return [...counts.values()].sort((left, right) => right.count - left.count || left.label.localeCompare(right.label));
}

// Departments keep one shop-floor order in every view, instead of reshuffling
// by count each time the tab changes. Unlisted ones follow, and "Other" is last.
const DEPARTMENT_ORDER = [
  "women",
  "men",
  "baby-kids",
  "baby-and-kids",
  "home",
  "beauty-wellness",
  "beauty-and-wellness",
  "health-wellness",
  "health-and-wellness",
  "food-and-wine",
  "unisex",
];

export function orderDepartments(facets: Facet[]): Facet[] {
  const place = (facet: Facet) => {
    if (facet.value === "other") return DEPARTMENT_ORDER.length + 1;
    const index = DEPARTMENT_ORDER.indexOf(facet.value);
    return index === -1 ? DEPARTMENT_ORDER.length : index;
  };
  return [...facets].sort((left, right) => place(left) - place(right) || left.label.localeCompare(right.label));
}

function metricBounds(product: ProductResult, field: SortField): [number | null, number | null] {
  if (field === "price") {
    return [numericValue(product.sellingPriceMin ?? product.sellingPrice), numericValue(product.sellingPriceMax ?? product.sellingPrice)];
  }
  if (field === "cost") {
    return [numericValue(product.reportedTotalCostMin ?? product.reportedTotalCost), numericValue(product.reportedTotalCostMax ?? product.reportedTotalCost)];
  }
  if (field === "margin") {
    return [numericValue(product.marginPctMin ?? product.marginPct), numericValue(product.marginPctMax ?? product.marginPct)];
  }
  return [numericValue(product.unitSpreadMin ?? product.unitSpread), numericValue(product.unitSpreadMax ?? product.unitSpread)];
}

function compareNumbers(left: number | null, right: number | null, direction: number) {
  if (left === null && right === null) return 0;
  if (left === null) return 1;
  if (right === null) return -1;
  return (left - right) * direction;
}

export function sortParts(sort: Sort): { field: SortField; direction: "asc" | "desc" } {
  const direction = sort.endsWith("_desc") ? "desc" : "asc";
  return { field: sort.replace(/_(?:asc|desc)$/, "") as SortField, direction };
}

// A range sorts by its minimum when ascending and its maximum when descending.
// Ties fall back to name, then identity, so equal values never trade places.
export function sortResults(items: ProductResult[], sort: Sort) {
  const { field, direction: order } = sortParts(sort);
  const direction = order === "desc" ? -1 : 1;
  const tieBreak = (left: ProductResult, right: ProductResult) =>
    left.name.localeCompare(right.name, undefined, { sensitivity: "base" })
    || productKey(left).localeCompare(productKey(right));

  return [...items].sort((left, right) => {
    if (field === "name" || field === "department") {
      const leftText = field === "name" ? left.name : left.departmentLabel;
      const rightText = field === "name" ? right.name : right.departmentLabel;
      return leftText.localeCompare(rightText, undefined, { sensitivity: "base" }) * direction || tieBreak(left, right);
    }
    const leftBounds = metricBounds(left, field);
    const rightBounds = metricBounds(right, field);
    return compareNumbers(
      direction === -1 ? leftBounds[1] : leftBounds[0],
      direction === -1 ? rightBounds[1] : rightBounds[0],
      direction,
    ) || tieBreak(left, right);
  });
}

function range(
  minimum: string | number | null | undefined,
  maximum: string | number | null | undefined,
  fallback: string | number | null | undefined,
  format: (value: string | number | null | undefined) => string,
) {
  const lower = numericValue(minimum ?? fallback);
  const upper = numericValue(maximum ?? fallback);
  if (lower === null || upper === null || lower === upper) return format(fallback ?? minimum ?? maximum);
  return `${format(lower)} to ${format(upper)}`;
}

export function priceText(product: ProductResult) {
  return range(product.sellingPriceMin, product.sellingPriceMax, product.sellingPrice, (value) => formatMoney(value, product.currency));
}

export function costText(product: ProductResult) {
  return range(product.reportedTotalCostMin, product.reportedTotalCostMax, product.reportedTotalCost, (value) => formatMoney(value, product.currency));
}

// The difference always carries a sign and words. A style whose options
// disagree shows its range and says so; it never borrows one option's figure.
export function differenceText(product: ProductResult) {
  const signed = (value: string | number | null | undefined) => formatSignedMoney(value, product.currency);
  const figures = range(product.unitSpreadMin, product.unitSpreadMax, product.unitSpread, signed);
  if (product.classification === "mixed") return `${figures}, varies by option`;
  if (product.classification === "break_even") return "Priced at reported cost";
  return `${figures} ${product.classification === "loss" ? "below cost" : "above cost"}`;
}

export function marginText(product: ProductResult) {
  return range(product.marginPctMin, product.marginPctMax, product.marginPct, (value) => formatMargin(numericValue(value)));
}

export function isBelowCost(product: ProductResult) {
  return product.classification === "loss";
}

export function variantLine(product: ProductResult) {
  const count = product.variantCount || 1;
  if (count <= 1) {
    const parts = [product.variantColor ? `In ${product.variantColor}` : "", product.variantSize || ""].filter(Boolean);
    return parts.length ? parts.join(" · ") : product.variantLabel || "";
  }
  const colors = product.variantColors?.length ?? 0;
  const sizes = product.variantSizes?.length ?? 0;
  const parts: string[] = [];
  if (colors > 1) parts.push(countLabel(colors, "colour"));
  if (sizes > 1) parts.push(countLabel(sizes, "size"));
  return parts.length ? `In ${parts.join(", ")}` : `${countLabel(count, "option")} at this price`;
}

export function variantOptionLabel(variant: ProductResult) {
  return [variant.variantColor, variant.variantSize].filter(Boolean).join(" · ")
    || variant.variantLabel
    || `Option ${variant.variantKey}`;
}
