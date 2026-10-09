<script setup lang="ts">
type View = "losses" | "profit" | "all";
type SortField = "name" | "department" | "price" | "cost" | "spread" | "margin";
type Sort = `${SortField}_asc` | `${SortField}_desc`;

interface Facet {
  value: string;
  label: string;
  count: number;
}

interface ProductResult {
  productKey: string;
  variantKey: string;
  name: string;
  url: string | null;
  brand: string | null;
  department: string;
  departmentLabel: string;
  category: string;
  categoryLabel: string;
  currency: string;
  sellingPrice: string | null;
  reportedTotalCost: string | null;
  unitSpread: string | null;
  marginPct: number | null;
  classification: "loss" | "profit" | "break_even" | "mixed";
  capturedAt: string;
  hasExorbitantFees: boolean;
  imageUrl?: string | null;
  imageUrls?: string[];
  historyPath?: string;
  parentProductId?: string | null;
  variantLabel?: string | null;
  variantColor?: string | null;
  variantSize?: string | null;
  variantCount?: number;
  isGrouped?: boolean;
  variantLabels?: string[];
  variantColors?: string[];
  variantSizes?: string[];
  variantClassifications?: Array<"loss" | "profit" | "break_even">;
  metricsMixed?: boolean;
  sellingPriceMin?: string | null;
  sellingPriceMax?: string | null;
  reportedTotalCostMin?: string | null;
  reportedTotalCostMax?: string | null;
  unitSpreadMin?: string | null;
  unitSpreadMax?: string | null;
  marginPctMin?: number | null;
  marginPctMax?: number | null;
  variants?: ProductResult[];
}

interface ProductHistoryPoint {
  capturedAt: string;
  sellingPrice: string | null;
  reportedTotalCost: string | null;
  unitSpread: string | null;
  marginPct: number | null;
  parseStatus: string;
  totalCostSource: string;
  costLines: CostLine[];
}

interface CostLine {
  label: string;
  type: string;
  amount: string | null;
}

type ChangeDirection = "up" | "down" | "added" | "removed" | "anchor";

interface ChangeMove {
  label: string;
  from: string | null;
  to: string | null;
  delta: string | null;
  direction: ChangeDirection;
  summary?: boolean;
}

interface ChangeEvent {
  capturedAt: string;
  kind: "anchor" | "update";
  moves: ChangeMove[];
}

interface ProductDetail {
  product: ProductResult;
  current: ProductHistoryPoint;
  analytics: {
    observationCount: number;
    lossObservations: number;
    profitObservations: number;
    lowestPrice: string | null;
    highestPrice: string | null;
    lowestCost: string | null;
    highestCost: string | null;
    averageSpread: string | null;
    firstObservedAt: string;
    lastObservedAt: string;
  };
  history: ProductHistoryPoint[];
}

interface HistoryChartPoint {
  capturedAt: string;
  x: number;
  price: number | null;
  cost: number | null;
  priceY: number | null;
  costY: number | null;
  label: string;
}

interface HistoryChart {
  points: HistoryChartPoint[];
  pricePath: string;
  costPath: string;
  gridLines: { y: number; label: string }[];
  axisLabels: { x: number; label: string; anchor: "start" | "middle" | "end" }[];
}

interface Summary {
  total: number;
  losses: number;
  profitDrivers: number;
  breakEven: number;
  mixed: number;
  filtered: {
    total: number;
    losses: number;
    profitDrivers: number;
    breakEven: number;
    mixed: number;
  };
}

interface RankingResponse {
  generatedAt: string;
  latestCapturedAt: string | null;
  view: View;
  total: number;
  hasMore: boolean;
  summary: Summary;
  facets: {
    departments: Facet[];
    categories: Facet[];
  };
  results: ProductResult[];
}

const emptyResponse = (): RankingResponse => ({
  generatedAt: "",
  latestCapturedAt: null,
  view: "losses",
  total: 0,
  hasMore: false,
  summary: {
    total: 0,
    losses: 0,
    profitDrivers: 0,
    breakEven: 0,
    mixed: 0,
    filtered: { total: 0, losses: 0, profitDrivers: 0, breakEven: 0, mixed: 0 },
  },
  facets: { departments: [], categories: [] },
  results: [],
});

const config = useRuntimeConfig();
const apiBase = String(config.public.apiBase || "http://127.0.0.1:8877").replace(/\/$/, "");
const staticDataBase = String(config.public.staticDataBase || "").replace(/\/$/, "");
const staticMode = Boolean(staticDataBase);
const REQUEST_TIMEOUT_MS = 10_000;

async function fetchJson<T>(url: string, query?: Record<string, string>): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    if (query) {
      return await $fetch<T>(url, { query, signal: controller.signal });
    }
    return await $fetch<T>(url, { signal: controller.signal });
  } finally {
    clearTimeout(timeout);
  }
}

const view = ref<View>("losses");
const search = ref("");
const department = ref("");
const category = ref("");
const sort = ref<Sort>("spread_asc");
type DisplayMode = "table" | "images";
const displayMode = ref<DisplayMode>("table");
const hydrated = ref(false);
const selectedProduct = ref<ProductResult | null>(null);
const selectedGroup = ref<ProductResult | null>(null);
const detail = ref<ProductDetail | null>(null);
const detailPending = ref(false);
const detailError = ref("");

const failedImages = ref<Record<string, boolean>>({});

function markImageFailed(url: string | null | undefined) {
  if (!url) return;
  failedImages.value = { ...failedImages.value, [url]: true };
}

function usableImage(url: string | null | undefined) {
  return url && !failedImages.value[url] ? url : null;
}

const detailImageUrls = computed(() => {
  const product = detail.value?.product;
  if (!product) return [];
  const candidates = product.imageUrls?.length
    ? product.imageUrls
    : product.imageUrl
      ? [product.imageUrl]
      : [];
  return candidates.map((url) => usableImage(url)).filter((url): url is string => Boolean(url));
});

onMounted(() => {
  hydrated.value = true;
});

const requestQuery = computed(() => {
  const query: Record<string, string> = {
    view: view.value,
    limit: "5000",
  };
  if (search.value.trim()) query.search = search.value.trim();
  if (department.value) query.department = department.value;
  if (category.value) query.category = category.value;
  return query;
});

const { data, pending, error, refresh } = useAsyncData<RankingResponse>(
  "rankings",
  () => staticMode
    ? fetchJson<RankingResponse>(`${staticDataBase}/rankings.json`)
    : fetchJson<RankingResponse>(`${apiBase}/api/rankings`, requestQuery.value),
  {
    server: false,
    default: emptyResponse,
    watch: staticMode ? [] : [requestQuery],
  },
);

const sourceResponse = computed(() => data.value || emptyResponse());

function productVariants(product: ProductResult): ProductResult[] {
  return product.variants?.length ? product.variants : [product];
}

function productHasClassification(product: ProductResult, classification: ProductResult["classification"]) {
  if (classification === "mixed") {
    return product.classification === "mixed";
  }
  return productVariants(product).some((variant) => variant.classification === classification)
    || product.classification === classification;
}

function staticProductMatches(
  product: ProductResult,
  options: { includeDepartment?: boolean; includeCategory?: boolean } = {},
) {
  const includeDepartment = options.includeDepartment !== false;
  const includeCategory = options.includeCategory !== false;
  const searchTerm = search.value.trim().toLowerCase();

  return productVariants(product).some((variant) => {
    if (includeDepartment && department.value && variant.department !== department.value) return false;
    if (includeCategory && category.value && variant.category !== category.value) return false;
    if (
      searchTerm
      && ![
        variant.name,
        variant.brand || "",
        variant.departmentLabel,
        variant.categoryLabel,
        variant.variantLabel || "",
        variant.variantColor || "",
        variant.variantSize || "",
      ]
        .join(" ")
        .toLowerCase()
        .includes(searchTerm)
    ) return false;
    return true;
  });
}

function staticFacetValues(items: ProductResult[], field: "department" | "category"): Facet[] {
  const counts = new Map<string, Facet>();
  for (const item of items) {
    const value = field === "department" ? item.department : item.category;
    const label = field === "department" ? item.departmentLabel : item.categoryLabel;
    const current = counts.get(value);
    if (current) {
      current.count += 1;
    } else {
      counts.set(value, { value, label, count: 1 });
    }
  }
  return [...counts.values()].sort((left, right) =>
    right.count - left.count || left.label.localeCompare(right.label),
  );
}

function staticFilteredRows(
  items: ProductResult[],
  options: { includeDepartment?: boolean; includeCategory?: boolean } = {},
) {
  return items.filter((item) => staticProductMatches(item, options));
}

function staticResponse(source: RankingResponse): RankingResponse {
  let viewRows = source.results;

  if (view.value === "losses") {
    viewRows = viewRows.filter((item) => productHasClassification(item, "loss"));
  } else if (view.value === "profit") {
    viewRows = viewRows.filter((item) => productHasClassification(item, "profit"));
  }

  const rows = staticFilteredRows(viewRows);
  const departmentFacetRows = staticFilteredRows(viewRows, { includeDepartment: false });
  const categoryFacetRows = staticFilteredRows(viewRows, { includeCategory: false });

  // Partition on the group-level label so the buckets sum to the group total.
  // Counting by variant membership would put a mixed group in every bucket it
  // touches and the figures would not add up.
  const filtered = {
    total: rows.length,
    losses: rows.filter((item) => item.classification === "loss").length,
    profitDrivers: rows.filter((item) => item.classification === "profit").length,
    breakEven: rows.filter((item) => item.classification === "break_even").length,
    mixed: rows.filter((item) => item.classification === "mixed").length,
  };
  return {
    ...source,
    view: view.value,
    total: rows.length,
    hasMore: false,
    summary: { ...source.summary, filtered },
    facets: {
      departments: staticFacetValues(departmentFacetRows, "department"),
      categories: staticFacetValues(categoryFacetRows, "category"),
    },
    results: rows,
  };
}

const response = computed(() => staticMode ? staticResponse(sourceResponse.value) : sourceResponse.value);
type PageSize = "10" | "100" | "all";
const pageSize = ref<PageSize>("100");
const currentPage = ref(1);
const results = computed(() => sortResults(response.value.results));
const pageSizeValue = computed(() =>
  pageSize.value === "all" ? Math.max(1, results.value.length) : Number(pageSize.value),
);
const pageCount = computed(() => Math.max(1, Math.ceil(results.value.length / pageSizeValue.value)));
const pageStartIndex = computed(() => (currentPage.value - 1) * pageSizeValue.value);
const pageEndIndex = computed(() => Math.min(pageStartIndex.value + pageSizeValue.value, results.value.length));
const visibleResults = computed(() => results.value.slice(pageStartIndex.value, pageEndIndex.value));
const summary = computed(() => response.value.summary);
const rankingsLoading = computed(() => !hydrated.value || pending.value);
const filtersActive = computed(() => Boolean(search.value.trim() || department.value || category.value));
const viewMismatchNote = computed(() => {
  if (filtersActive.value || view.value === "all") return "";
  const shown = response.value.total;
  const bucket = view.value === "losses" ? summary.value.losses : summary.value.profitDrivers;
  if (shown <= bucket) return "";
  const qualifier = view.value === "losses" ? "loss" : "positive";
  return `The tab lists any product with a ${qualifier} variant, so it shows ${formatNumber(shown)} groups while ${formatNumber(bucket)} are ${qualifier} throughout.`;
});
const departments = computed(() => response.value.facets.departments);
const categories = computed(() => response.value.facets.categories);
const sortOrder = computed<"asc" | "desc">(() => sort.value.endsWith("_desc") ? "desc" : "asc");
const sortField = computed<SortField>({
  get: () => sort.value.replace(/_(?:asc|desc)$/, "") as SortField,
  set: (field) => {
    sort.value = `${field}_${sortOrder.value}` as Sort;
  },
});
const sortDirectionLabel = computed(() => {
  if (sortField.value === "name" || sortField.value === "department") {
    return sortOrder.value === "asc" ? "A–Z" : "Z–A";
  }
  return sortOrder.value === "asc" ? "Low to high" : "High to low";
});

watch([view, search, department, category, sort, pageSize], () => {
  currentPage.value = 1;
});

watch(pageCount, (count) => {
  if (currentPage.value > count) currentPage.value = count;
});

const activeViewLabel = computed(() => {
  if (view.value === "profit") return "Positive spread";
  if (view.value === "all") return "All products";
  return "Loss leaders";
});

const viewDescription = computed(() => {
  if (view.value === "profit") return "Products with the largest disclosed spread above cost.";
  if (view.value === "all") return "Every rankable product, ordered by disclosed spread.";
  return "Products where the listed price is below Quince's disclosed cost.";
});

const numberFormat = new Intl.NumberFormat("en-US");

function formatNumber(value: number) {
  return numberFormat.format(value);
}

function normalizeCurrency(currency: string | null | undefined) {
  const code = (currency ?? "").trim().toUpperCase();
  return /^[A-Z]{3}$/.test(code) ? code : "USD";
}

function formatMoney(value: string | null, currency = "USD") {
  if (value === null || value === undefined || value === "") return "—";
  const amount = Number(value);
  if (!Number.isFinite(amount)) return "—";
  const code = normalizeCurrency(currency);
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: code,
    }).format(amount);
  } catch {
    return `${amount.toFixed(2)} ${code}`;
  }
}

function formatMargin(value: number | null) {
  return value === null ? "—" : `${value.toFixed(1)}%`;
}

function formatDate(value: string) {
  if (!value) return "No snapshot";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "Unknown";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(parsed);
}

function numericValue(value: string | number | null) {
  if (value === null) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function compareNumbers(left: number | null, right: number | null, direction: number) {
  if (left === null && right === null) return 0;
  if (left === null) return 1;
  if (right === null) return -1;
  return (left - right) * direction;
}

function formatSpreadValue(
  value: string | null | undefined,
  currency: string,
  classification: ProductResult["classification"],
) {
  const formatted = formatMoney(value ?? null, currency);
  const numeric = numericValue(value ?? null);
  if (formatted === "—" || numeric === null || numeric === 0) return formatted;
  return numeric > 0 ? `+${formatted}` : formatted;
}

function formatMoneyRange(
  minimum: string | null | undefined,
  maximum: string | null | undefined,
  fallback: string | null,
  currency: string,
) {
  const lower = minimum ?? fallback;
  const upper = maximum ?? fallback;
  if (lower === null && upper === null) return "—";
  const lowerNumber = numericValue(lower);
  const upperNumber = numericValue(upper);
  if (lowerNumber === null || upperNumber === null || lowerNumber === upperNumber) {
    return formatMoney(fallback ?? lower ?? upper, currency);
  }
  return `${formatMoney(lower, currency)}–${formatMoney(upper, currency)}`;
}

function formatSpreadRange(product: ProductResult) {
  const minimum = product.unitSpreadMin ?? product.unitSpread;
  const maximum = product.unitSpreadMax ?? product.unitSpread;
  const lowerNumber = numericValue(minimum);
  const upperNumber = numericValue(maximum);
  if (lowerNumber === null || upperNumber === null || lowerNumber === upperNumber) {
    return formatSpreadValue(product.unitSpread, product.currency, product.classification);
  }
  return `${formatSpreadValue(minimum, product.currency, product.classification)}–${formatSpreadValue(maximum, product.currency, product.classification)}`;
}

function formatMarginRange(product: ProductResult) {
  const minimum = product.marginPctMin ?? product.marginPct;
  const maximum = product.marginPctMax ?? product.marginPct;
  const lowerNumber = numericValue(minimum);
  const upperNumber = numericValue(maximum);
  if (lowerNumber === null || upperNumber === null || lowerNumber === upperNumber) {
    return formatMargin(product.marginPct);
  }
  return `${formatMargin(lowerNumber)}–${formatMargin(upperNumber)}`;
}

function formatProductPrice(product: ProductResult) {
  return formatMoneyRange(
    product.sellingPriceMin,
    product.sellingPriceMax,
    product.sellingPrice,
    product.currency,
  );
}

function formatProductCost(product: ProductResult) {
  return formatMoneyRange(
    product.reportedTotalCostMin,
    product.reportedTotalCostMax,
    product.reportedTotalCost,
    product.currency,
  );
}

function formatProductSpread(product: ProductResult) {
  return formatSpreadRange(product);
}

function formatProductMargin(product: ProductResult) {
  return formatMarginRange(product);
}

function productMetricBounds(product: ProductResult, field: SortField): [number | null, number | null] {
  if (field === "price") {
    return [
      numericValue(product.sellingPriceMin ?? product.sellingPrice),
      numericValue(product.sellingPriceMax ?? product.sellingPrice),
    ];
  }
  if (field === "cost") {
    return [
      numericValue(product.reportedTotalCostMin ?? product.reportedTotalCost),
      numericValue(product.reportedTotalCostMax ?? product.reportedTotalCost),
    ];
  }
  if (field === "margin") {
    return [
      numericValue(product.marginPctMin ?? product.marginPct),
      numericValue(product.marginPctMax ?? product.marginPct),
    ];
  }
  return [
    numericValue(product.unitSpreadMin ?? product.unitSpread),
    numericValue(product.unitSpreadMax ?? product.unitSpread),
  ];
}

function productSortValue(product: ProductResult, field: SortField, direction: number) {
  const [minimum, maximum] = productMetricBounds(product, field);
  return direction === -1 ? maximum : minimum;
}

function variantSummary(product: ProductResult) {
  const count = product.variantCount || 1;
  if (count <= 1) return product.variantLabel || "";

  const descriptors: string[] = [];
  const colors = product.variantColors || [];
  const sizes = product.variantSizes || [];
  if (colors.length) descriptors.push(countLabel(colors.length, "color"));
  if (sizes.length) descriptors.push(countLabel(sizes.length, "size"));
  if (product.metricsMixed) descriptors.push(product.classification === "mixed" ? "spread varies" : "cost varies");
  return `${countLabel(count, "variant")}${descriptors.length ? ` · ${descriptors.join(" · ")}` : ""}`;
}

function productSpreadClass(product: ProductResult) {
  return product.classification === "mixed" ? "spread-mixed" : `spread-${product.classification}`;
}

function productMarginClass(product: ProductResult) {
  if (product.classification === "mixed") return "margin-mixed";
  return marginClass(product.marginPctMin ?? product.marginPct);
}

function sortResults(items: ProductResult[]) {
  const rawSort = sort.value as string;
  const normalizedSort = rawSort === "name" ? "name_asc" : rawSort;
  const directionSuffix = normalizedSort.endsWith("_desc") ? "_desc" : "_asc";
  const field = normalizedSort.endsWith(directionSuffix)
    ? normalizedSort.slice(0, -directionSuffix.length)
    : "spread";
  const direction = directionSuffix === "_desc" ? -1 : 1;

  return [...items].sort((left, right) => {
    if (field === "name" || field === "department") {
      const leftText = field === "name" ? left.name : left.departmentLabel;
      const rightText = field === "name" ? right.name : right.departmentLabel;
      return leftText.localeCompare(rightText, undefined, { sensitivity: "base" }) * direction;
    }

    if (["price", "cost", "margin", "spread"].includes(field)) {
      return compareNumbers(
        productSortValue(left, field as SortField, direction),
        productSortValue(right, field as SortField, direction),
        direction,
      );
    }

    return 0;
  });
}

function sortDirection(field: SortField): "asc" | "desc" | null {
  if (sort.value === `${field}_asc`) return "asc";
  if (sort.value === `${field}_desc`) return "desc";
  return null;
}

function sortIndicator(field: SortField) {
  const direction = sortDirection(field);
  return direction === "asc" ? "↑" : direction === "desc" ? "↓" : "↕";
}

function ariaSort(field: SortField) {
  const direction = sortDirection(field);
  return direction === "asc" ? "ascending" : direction === "desc" ? "descending" : "none";
}

function toggleSort(field: SortField) {
  const direction = sortDirection(field);
  sort.value = `${field}_${direction === "asc" ? "desc" : "asc"}` as Sort;
}

function toggleSortDirection() {
  sort.value = `${sortField.value}_${sortOrder.value === "asc" ? "desc" : "asc"}` as Sort;
}

function setView(nextView: View) {
  view.value = nextView;
  sort.value = nextView === "profit" ? "spread_desc" : "spread_asc";
}

function resetFilters() {
  search.value = "";
  department.value = "";
  category.value = "";
  sort.value = view.value === "profit" ? "spread_desc" : "spread_asc";
}

function previousPage() {
  currentPage.value = Math.max(1, currentPage.value - 1);
}

function nextPage() {
  currentPage.value = Math.min(pageCount.value, currentPage.value + 1);
}

function marginClass(value: number | null) {
  if (value === null) return "";
  if (value < 0) return "margin-negative";
  if (value > 0) return "margin-positive";
  return "margin-zero";
}

function retry() {
  void refresh();
}

function sameVariant(left: ProductResult | null | undefined, right: ProductResult | null | undefined) {
  return Boolean(
    left
    && right
    && left.productKey === right.productKey
    && left.variantKey === right.variantKey,
  );
}

let detailRequest = 0;

async function loadProduct(product: ProductResult) {
  const request = ++detailRequest;
  selectedProduct.value = product;
  detail.value = null;
  detailError.value = "";
  detailPending.value = true;
  try {
    const payload = staticMode
      ? await (async () => {
        if (!product.historyPath) throw new Error("History file is not available.");
        return await fetchJson<ProductDetail>(`${staticDataBase}/${product.historyPath}`);
      })()
      : await fetchJson<ProductDetail>(`${apiBase}/api/product`, {
        product_key: product.productKey,
        variant_key: product.variantKey,
      });
    if (request !== detailRequest) return;
    detail.value = payload;
  } catch {
    if (request !== detailRequest) return;
    detailError.value = "Could not load product history.";
  } finally {
    if (request === detailRequest) detailPending.value = false;
  }
}

async function openProduct(product: ProductResult) {
  selectedGroup.value = product.variants?.length ? product : null;
  const initialProduct = product.variants?.find((variant) => sameVariant(variant, product))
    || product.variants?.[0]
    || product;
  await loadProduct(initialProduct);
}

function handleProductClick(event: MouseEvent, product: ProductResult) {
  if ((event.ctrlKey || event.metaKey) && product.url) {
    window.open(product.url, "_blank", "noopener,noreferrer");
    return;
  }
  void openProduct(product);
}

function closeProduct() {
  detailRequest += 1;
  selectedProduct.value = null;
  selectedGroup.value = null;
  detail.value = null;
  detailError.value = "";
  detailPending.value = false;
}

const drawerEl = ref<HTMLElement | null>(null);
let previouslyFocused: HTMLElement | null = null;

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

function trapDrawerFocus(event: KeyboardEvent) {
  if (!selectedProduct.value) return;
  if (event.key === "Escape") {
    event.preventDefault();
    closeProduct();
    return;
  }
  if (event.key !== "Tab" || !drawerEl.value) return;
  const nodes = Array.from(drawerEl.value.querySelectorAll<HTMLElement>(FOCUSABLE))
    .filter((element) => element.offsetParent !== null);
  if (!nodes.length) return;
  const first = nodes[0];
  const last = nodes[nodes.length - 1];
  if (!first || !last) return;
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

watch(selectedProduct, async (open) => {
  if (import.meta.client) {
    document.body.style.overflow = open ? "hidden" : "";
  }
  if (open) {
    previouslyFocused = (document.activeElement as HTMLElement | null) ?? null;
    await nextTick();
    drawerEl.value?.querySelector<HTMLElement>(FOCUSABLE)?.focus();
  } else if (previouslyFocused) {
    previouslyFocused.focus();
    previouslyFocused = null;
  }
});

onMounted(() => document.addEventListener("keydown", trapDrawerFocus, true));
onBeforeUnmount(() => {
  document.removeEventListener("keydown", trapDrawerFocus, true);
  document.body.style.overflow = "";
});

function detailSpread(point: ProductHistoryPoint) {
  const value = formatMoney(point.unitSpread, detail.value?.product.currency || "USD");
  if (value === "—") return value;
  return Number(point.unitSpread) > 0 ? `+${value}` : value;
}

function spreadClass(value: string | null) {
  const numeric = numericValue(value);
  if (numeric === null || numeric === 0) return "spread-zero";
  return numeric < 0 ? "spread-loss" : "spread-profit";
}

function shortDate(value: string) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "Unknown";
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" }).format(parsed);
}

function costComponentKey(line: CostLine) {
  return line.type || line.label.trim().toLowerCase();
}

function uniqueCostLineKeys(lines: CostLine[]) {
  const seen = new Map<string, number>();
  return lines.map((line) => {
    const base = costComponentKey(line);
    const count = seen.get(base) ?? 0;
    seen.set(base, count + 1);
    return { key: count === 0 ? base : `${base}#${count}`, line };
  });
}

function moneyDelta(from: number | null, to: number | null, currency: string) {
  if (from === null || to === null) return null;
  const change = to - from;
  if (Math.abs(change) < 0.005) return null;
  const formatted = formatMoney(change.toFixed(2), currency);
  return change > 0 ? `+${formatted}` : formatted;
}

function changeDirection(from: number | null, to: number | null): ChangeDirection {
  if (from === null && to === null) return "anchor";
  if (from === null) return "added";
  if (to === null) return "removed";
  return to > from ? "up" : "down";
}

function changeMove(
  label: string,
  from: string | null,
  to: string | null,
  fromValue: number | null,
  toValue: number | null,
  currency: string,
  summary = false,
): ChangeMove {
  return {
    label,
    from,
    to,
    delta: moneyDelta(fromValue, toValue, currency),
    direction: changeDirection(fromValue, toValue),
    summary,
  };
}

const changeLog = computed<ChangeEvent[]>(() => {
  const history = detail.value?.history || [];
  const currency = normalizeCurrency(detail.value?.product.currency);
  if (!history.length) return [];

  const anchor = history[0];
  if (!anchor) return [];

  const events: ChangeEvent[] = [
    {
      capturedAt: anchor.capturedAt,
      kind: "anchor",
      moves: [
        { label: "Price", from: null, to: formatMoney(anchor.sellingPrice, currency), delta: null, direction: "anchor" },
        { label: "Reported cost", from: null, to: formatMoney(anchor.reportedTotalCost, currency), delta: null, direction: "anchor" },
        { label: "Spread", from: null, to: detailSpread(anchor), delta: null, direction: "anchor", summary: true },
      ],
    },
  ];

  for (let index = 1; index < history.length; index += 1) {
    const previous = history[index - 1];
    const next = history[index];
    if (!previous || !next) continue;
    const moves: ChangeMove[] = [];

    const previousPrice = numericValue(previous.sellingPrice);
    const nextPrice = numericValue(next.sellingPrice);
    if (previousPrice !== nextPrice) {
      moves.push(
        changeMove(
          "Price",
          formatMoney(previous.sellingPrice, currency),
          formatMoney(next.sellingPrice, currency),
          previousPrice,
          nextPrice,
          currency,
        ),
      );
    }

    const previousLines = new Map(uniqueCostLineKeys(previous.costLines).map((entry) => [entry.key, entry.line]));
    const nextLines = new Map(uniqueCostLineKeys(next.costLines).map((entry) => [entry.key, entry.line]));
    const lineKeys: string[] = [];
    for (const key of previousLines.keys()) lineKeys.push(key);
    for (const key of nextLines.keys()) if (!previousLines.has(key)) lineKeys.push(key);

    for (const key of lineKeys) {
      const previousLine = previousLines.get(key);
      const nextLine = nextLines.get(key);
      const previousAmount = numericValue(previousLine?.amount ?? null);
      const nextAmount = numericValue(nextLine?.amount ?? null);
      if (previousAmount === nextAmount) continue;
      moves.push(
        changeMove(
          (nextLine ?? previousLine)?.label || key,
          previousLine ? formatMoney(previousLine.amount, currency) : null,
          nextLine ? formatMoney(nextLine.amount, currency) : null,
          previousAmount,
          nextAmount,
          currency,
        ),
      );
    }

    const previousCost = numericValue(previous.reportedTotalCost);
    const nextCost = numericValue(next.reportedTotalCost);
    if (previousCost !== nextCost) {
      moves.push(
        changeMove(
          "Reported cost",
          formatMoney(previous.reportedTotalCost, currency),
          formatMoney(next.reportedTotalCost, currency),
          previousCost,
          nextCost,
          currency,
          true,
        ),
      );
    }

    const previousSpread = numericValue(previous.unitSpread);
    const nextSpread = numericValue(next.unitSpread);
    if (previousSpread !== nextSpread) {
      moves.push(
        changeMove(
          "Spread",
          formatMoney(previous.unitSpread, currency),
          formatMoney(next.unitSpread, currency),
          previousSpread,
          nextSpread,
          currency,
          true,
        ),
      );
    }

    if (moves.length) events.push({ capturedAt: next.capturedAt, kind: "update", moves });
  }

  return events;
});

const recordedChanges = computed(() => changeLog.value.filter((event) => event.kind === "update").length);

function countLabel(count: number, singular: string) {
  return `${count} ${singular}${count === 1 ? "" : "s"}`;
}

function changeEventLabel(event: ChangeEvent) {
  if (event.kind === "anchor") return "First capture";
  return countLabel(event.moves.filter((move) => !move.summary).length, "line move");
}

function linePath(points: HistoryChartPoint[], field: "priceY" | "costY") {
  let path = "";
  let connected = false;
  for (const point of points) {
    const y = point[field];
    if (y === null) {
      connected = false;
      continue;
    }
    path += `${connected ? "L" : "M"} ${point.x.toFixed(2)} ${y.toFixed(2)} `;
    connected = true;
  }
  return path.trim();
}

const historyChart = computed<HistoryChart>(() => {
  const history = detail.value?.history || [];
  const values = history.flatMap((point) =>
    [numericValue(point.sellingPrice), numericValue(point.reportedTotalCost)].filter(
      (value): value is number => value !== null,
    ),
  );
  if (!history.length || !values.length) {
    return { points: [], pricePath: "", costPath: "", gridLines: [], axisLabels: [] };
  }

  let minimum = Math.min(...values);
  let maximum = Math.max(...values);
  const padding = minimum === maximum
    ? Math.max(Math.abs(minimum) * 0.08, 1)
    : (maximum - minimum) * 0.12;
  minimum -= padding;
  maximum += padding;

  const width = 640;
  const height = 230;
  const left = 58;
  const right = 16;
  const top = 18;
  const bottom = 30;
  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;
  const yFor = (value: number) => top + ((maximum - value) / (maximum - minimum)) * plotHeight;

  const times = history.map((point) => {
    const parsed = new Date(point.capturedAt).getTime();
    return Number.isFinite(parsed) ? parsed : null;
  });
  const validTimes = times.filter((time): time is number => time !== null);
  const firstTime = validTimes.length ? Math.min(...validTimes) : 0;
  const timeSpan = validTimes.length > 1 ? Math.max(...validTimes) - firstTime : 0;

  const points = history.map((point, index) => {
    const price = numericValue(point.sellingPrice);
    const cost = numericValue(point.reportedTotalCost);
    let x = left + plotWidth / 2;
    if (history.length > 1) {
      const time = times[index] ?? null;
      x = time !== null && timeSpan > 0
        ? left + ((time - firstTime) / timeSpan) * plotWidth
        : left + (index / (history.length - 1)) * plotWidth;
    }
    return {
      capturedAt: point.capturedAt,
      x,
      price,
      cost,
      priceY: price === null ? null : yFor(price),
      costY: cost === null ? null : yFor(cost),
      label: shortDate(point.capturedAt),
    };
  });

  const labelCount = Math.min(points.length, 7);
  const labelIndices = new Set<number>();
  for (let index = 0; index < labelCount; index += 1) {
    labelIndices.add(Math.round((index * (points.length - 1)) / Math.max(1, labelCount - 1)));
  }
  const candidates: HistoryChartPoint[] = [];
  for (const pointIndex of [...labelIndices].sort((left, right) => left - right)) {
    const point = points[pointIndex];
    if (!point) continue;
    // Captures can share a timestamp; keep one label per x so they cannot collide.
    if (candidates.some((placed) => Math.abs(placed.x - point.x) < 1)) continue;
    candidates.push(point);
  }

  // A label is ~48px wide at 11px mono; drop neighbours closer than that and
  // always keep the newest capture labelled.
  const minimumLabelGap = 52;
  const axisPoints: HistoryChartPoint[] = [];
  for (const point of candidates) {
    const previous = axisPoints[axisPoints.length - 1];
    if (previous && point.x - previous.x < minimumLabelGap) continue;
    axisPoints.push(point);
  }
  const newest = candidates[candidates.length - 1];
  if (newest) {
    while (axisPoints.length) {
      const tail = axisPoints[axisPoints.length - 1];
      if (!tail || tail === newest || newest.x - tail.x >= minimumLabelGap) break;
      axisPoints.pop();
    }
    const tail = axisPoints[axisPoints.length - 1];
    if (tail !== newest) axisPoints.push(newest);
  }

  const axisLabels = axisPoints.map((point, index) => ({
    x: point.x,
    label: point.label,
    anchor: (index === 0 ? "start" : index === axisPoints.length - 1 ? "end" : "middle") as
      "start" | "middle" | "end",
  }));

  const currency = detail.value?.product.currency || "USD";
  const gridLines = [0, 1, 2, 3, 4].map((index) => {
    const value = maximum - ((maximum - minimum) * index) / 4;
    return { y: yFor(value), label: formatMoney(value.toFixed(2), currency) };
  });

  return {
    points,
    pricePath: linePath(points, "priceY"),
    costPath: linePath(points, "costY"),
    gridLines,
    axisLabels,
  };
});
</script>

<template>
  <div class="shell">
    <header class="topbar">
      <NuxtLink class="brand" to="/" aria-label="Quince Ledger home">
        <span class="brand-mark">QL</span>
        <span class="brand-copy">
          <strong>Quince Ledger</strong>
          <small>Listed price vs. reported cost</small>
        </span>
      </NuxtLink>
      <div class="topbar-actions">
        <nav class="topbar-nav" aria-label="Ledger sections">
          <NuxtLink class="topbar-link" to="/">Ledger</NuxtLink>
          <NuxtLink class="topbar-link" to="/method">Method</NuxtLink>
        </nav>
        <ThemeSelect />
        <div class="connection-status" :class="{ loading: rankingsLoading }">
          <span class="status-dot" />
          {{ rankingsLoading ? "Updating" : staticMode ? "Published snapshot" : "Local snapshot" }}
        </div>
      </div>
    </header>

    <main>
    <section class="masthead">
      <div class="masthead-claim">
        <h1>Quince products, ranked by price minus reported cost.</h1>
        <p class="hero-text">
          Every number comes from the cost breakdown Quince publishes on its own
          product pages, kept as a dated history.
        </p>
        <p class="capture-stamp">
          <span class="capture-stamp-label">Last capture</span>
          <time v-if="response.latestCapturedAt" :datetime="response.latestCapturedAt">{{ formatDate(response.latestCapturedAt) }}</time>
          <span v-else>No capture recorded</span>
        </p>
      </div>
    </section>

    <section class="summary-strip" aria-label="Ranking summary">
      <div class="summary-grain">
        <strong>{{ formatNumber(summary.total) }}</strong>
        <span>display groups</span>
      </div>
      <div class="summary-item summary-loss">
        <strong>{{ formatNumber(summary.losses) }}</strong><span>loss</span>
      </div>
      <div class="summary-item summary-profit">
        <strong>{{ formatNumber(summary.profitDrivers) }}</strong><span>positive</span>
      </div>
      <div class="summary-item summary-zero">
        <strong>{{ formatNumber(summary.breakEven) }}</strong><span>break-even</span>
      </div>
      <div class="summary-item summary-mixed">
        <strong>{{ formatNumber(summary.mixed) }}</strong><span>mixed</span>
      </div>
    </section>
    <p class="summary-note">
      <span>Catalog totals, counted as display groups — one product at one price. <em>Loss</em> means every variant sits below cost; <em>mixed</em> means they disagree.</span>
      <span v-if="viewMismatchNote" class="summary-note-detail">{{ viewMismatchNote }}</span>
      <NuxtLink class="summary-note-link" to="/method">How counting works →</NuxtLink>
    </p>

    <section class="workspace">
      <aside class="filters-panel">
        <div class="panel-heading">
          <h2>Catalog filters</h2>
          <button class="text-button" type="button" @click="resetFilters">Reset</button>
        </div>

        <div class="view-tabs" role="group" aria-label="Ranking view">
          <button
            v-for="tab in [
              { value: 'losses', label: 'Losses' },
              { value: 'profit', label: 'Positive' },
              { value: 'all', label: 'All' },
            ]"
            :key="tab.value"
            class="view-tab"
            :class="{ active: view === tab.value }"
            type="button"
            :aria-pressed="view === tab.value"
            @click="setView(tab.value as View)"
          >
            {{ tab.label }}
          </button>
        </div>

        <label class="field-label" for="search">Search products</label>
        <div class="search-field">
          <svg class="search-icon" aria-hidden="true" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <circle cx="11" cy="11" r="7" />
            <path d="M20 20l-3.6-3.6" />
          </svg>
          <input id="search" v-model="search" type="search" placeholder="Try pants, tote, rug…" />
        </div>

        <label class="field-label" for="department">Department</label>
        <select id="department" v-model="department" class="select-field">
          <option value="">All departments</option>
          <option v-for="item in departments" :key="item.value" :value="item.value">
            {{ item.label }} ({{ item.count }})
          </option>
        </select>

        <label class="field-label" for="category">Category</label>
        <select id="category" v-model="category" class="select-field">
          <option value="">All categories</option>
          <option v-for="item in categories" :key="item.value" :value="item.value">
            {{ item.label }} ({{ item.count }})
          </option>
        </select>

        <div class="filter-note">
          <span class="note-icon">i</span>
          <p>Categories are inferred from product names and URLs until a stable source taxonomy is added.</p>
        </div>
      </aside>

      <section class="results-panel">
        <div class="results-heading">
          <div>
            <h2>{{ activeViewLabel }}</h2>
            <p class="results-description">{{ viewDescription }}</p>
          </div>
          <div class="table-controls">
            <div class="display-toggle" role="group" aria-label="Result display">
              <button
                class="display-toggle-button"
                :class="{ active: displayMode === 'table' }"
                type="button"
                :aria-pressed="displayMode === 'table'"
                @click="displayMode = 'table'"
              >
                Table
              </button>
              <button
                class="display-toggle-button"
                :class="{ active: displayMode === 'images' }"
                type="button"
                :aria-pressed="displayMode === 'images'"
                @click="displayMode = 'images'"
              >
                Images
              </button>
            </div>
            <div class="sort-control">
              <label for="sort">Sort by</label>
              <select id="sort" v-model="sortField" class="select-field compact-select">
                <option value="name">Product name</option>
                <option value="department">Department</option>
                <option value="price">Price</option>
                <option value="cost">Reported cost</option>
                <option value="spread">Spread</option>
                <option value="margin">Margin</option>
              </select>
            </div>
            <button
              class="sort-direction"
              type="button"
              :aria-label="`Sort ${sortField} ${sortOrder === 'asc' ? 'ascending' : 'descending'}`"
              @click="toggleSortDirection"
            >
              <span class="sort-direction-icon" aria-hidden="true">{{ sortOrder === "asc" ? "↑" : "↓" }}</span>
              <span>{{ sortDirectionLabel }}</span>
            </button>
            <div class="sort-control">
              <label for="page-size">Rows</label>
              <select id="page-size" v-model="pageSize" class="select-field compact-select">
                <option value="10">10</option>
                <option value="100">100</option>
                <option value="all">All</option>
              </select>
            </div>
          </div>
        </div>

        <div v-if="error && !results.length" class="state-card error-state">
          <strong>{{ staticMode ? "Could not load the published snapshot." : "Could not reach the rankings API." }}</strong>
          <p>{{ staticMode ? "The static data files are missing or unavailable." : "Start the Python API on port 8877, then try again." }}</p>
          <button class="action-button" type="button" @click="retry">Retry</button>
        </div>

        <div v-else-if="rankingsLoading && !results.length" class="state-card loading-state">
          <span class="loading-bar" />
          <span class="loading-bar short" />
          <p>Loading the latest stored rankings…</p>
        </div>

        <div v-else-if="!results.length" class="state-card">
          <strong>No matching products.</strong>
          <p>Try another department, category, or search term.</p>
        </div>

        <template v-else>
          <div class="result-meta">
            <span>Showing {{ formatNumber(pageStartIndex + 1) }}–{{ formatNumber(pageEndIndex) }} of {{ formatNumber(response.total) }} matches</span>
            <span v-if="error" class="result-meta-warn">
              Latest refresh failed — showing the last loaded ranking.
              <button class="text-button" type="button" @click="retry">Retry</button>
            </span>
            <span v-if="response.hasMore" class="result-meta-warn">Catalog truncated at 5,000 groups — not the full assortment</span>
          </div>
          <template v-if="displayMode === 'table'">
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th scope="col" :aria-sort="ariaSort('name')">
                    <button class="column-sort" type="button" @click="toggleSort('name')">
                      <span>Product</span><span class="sort-indicator">{{ sortIndicator("name") }}</span>
                    </button>
                  </th>
                  <th scope="col" :aria-sort="ariaSort('department')">
                    <button class="column-sort" type="button" @click="toggleSort('department')">
                      <span>Department</span><span class="sort-indicator">{{ sortIndicator("department") }}</span>
                    </button>
                  </th>
                  <th scope="col" class="numeric" :aria-sort="ariaSort('price')">
                    <button class="column-sort" type="button" @click="toggleSort('price')">
                      <span>Price</span><span class="sort-indicator">{{ sortIndicator("price") }}</span>
                    </button>
                  </th>
                  <th scope="col" class="numeric" :aria-sort="ariaSort('cost')">
                    <button class="column-sort" type="button" @click="toggleSort('cost')">
                      <span>Reported cost</span><span class="sort-indicator">{{ sortIndicator("cost") }}</span>
                    </button>
                  </th>
                  <th scope="col" class="numeric" :aria-sort="ariaSort('spread')">
                    <button class="column-sort" type="button" @click="toggleSort('spread')">
                      <span>Spread</span><span class="sort-indicator">{{ sortIndicator("spread") }}</span>
                    </button>
                  </th>
                  <th scope="col" class="numeric" :aria-sort="ariaSort('margin')">
                    <button class="column-sort" type="button" @click="toggleSort('margin')">
                      <span>Margin</span><span class="sort-indicator">{{ sortIndicator("margin") }}</span>
                    </button>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="product in visibleResults" :key="`${product.productKey}-${product.variantKey}`" class="result-row" @click="handleProductClick($event, product)">
                  <td>
                    <div class="product-cell">
                      <div class="product-name-row">
                        <button class="product-detail-button" type="button" :title="product.name" @click.stop="handleProductClick($event, product)">
                          {{ product.name }}
                        </button>
                        <span
                          v-if="product.hasExorbitantFees"
                          class="fee-asterisk"
                          title="A reported fee was flagged as implausible; see the cost breakdown for details."
                          aria-label="Flagged for an implausible reported fee"
                        >*</span>
                      </div>
                      <span>{{ product.categoryLabel }}<template v-if="product.brand"> · {{ product.brand }}</template></span>
                      <span v-if="variantSummary(product)" class="variant-summary">{{ variantSummary(product) }}</span>
                    </div>
                  </td>
                  <td><span class="department-pill">{{ product.departmentLabel }}</span></td>
                  <td class="numeric">{{ formatProductPrice(product) }}</td>
                  <td class="numeric">{{ formatProductCost(product) }}</td>
                  <td class="numeric" :class="productSpreadClass(product)">
                    {{ formatProductSpread(product) }}
                  </td>
                  <td class="numeric" :class="productMarginClass(product)">
                    {{ formatProductMargin(product) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="pageCount > 1" class="pagination" aria-label="Ranking pages">
            <button class="pagination-button" type="button" :disabled="currentPage === 1" @click="previousPage">Previous</button>
            <span>Page {{ formatNumber(currentPage) }} of {{ formatNumber(pageCount) }}</span>
            <button class="pagination-button" type="button" :disabled="currentPage === pageCount" @click="nextPage">Next</button>
          </div>
          </template>
          <template v-else>
            <div class="image-grid">
              <article v-for="product in visibleResults" :key="`${product.productKey}-${product.variantKey}`" class="image-card">
                <button class="image-card-media" type="button" @click="handleProductClick($event, product)">
                  <img
                    v-if="usableImage(product.imageUrl)"
                    :src="usableImage(product.imageUrl) || undefined"
                    :alt="product.name"
                    loading="lazy"
                    decoding="async"
                    @error="markImageFailed(product.imageUrl)"
                  >
                  <span v-else class="image-placeholder">No image captured</span>
                </button>
                <div class="image-card-body">
                  <div class="image-card-title-row">
                    <button class="image-card-title" type="button" @click="handleProductClick($event, product)">
                      {{ product.name }}
                    </button>
                    <span
                      v-if="product.hasExorbitantFees"
                      class="fee-asterisk"
                      title="A reported fee was flagged as implausible; see the cost breakdown for details."
                      aria-label="Flagged for an implausible reported fee"
                    >*</span>
                  </div>
                  <span class="image-card-meta">{{ product.departmentLabel }} · {{ product.categoryLabel }}</span>
                  <span v-if="variantSummary(product)" class="image-card-variant">{{ variantSummary(product) }}</span>
                  <div class="image-card-metrics">
                    <span>Price <strong>{{ formatProductPrice(product) }}</strong></span>
                    <span :class="productSpreadClass(product)">Spread <strong>{{ formatProductSpread(product) }}</strong></span>
                    <span :class="productMarginClass(product)">Margin <strong>{{ formatProductMargin(product) }}</strong></span>
                  </div>
                </div>
              </article>
            </div>
            <div v-if="pageCount > 1" class="pagination" aria-label="Ranking pages">
              <button class="pagination-button" type="button" :disabled="currentPage === 1" @click="previousPage">Previous</button>
              <span>Page {{ formatNumber(currentPage) }} of {{ formatNumber(pageCount) }}</span>
              <button class="pagination-button" type="button" :disabled="currentPage === pageCount" @click="nextPage">Next</button>
            </div>
          </template>
        </template>

        <footer class="results-footer">
          <span>United States catalog, USD · Source: Quince-reported cost breakdowns</span>
          <span><span class="fee-asterisk" aria-hidden="true">*</span> An implausible reported fee was flagged; duties, taxes, and fees above the rest of the breakdown are excluded from calculated cost.</span>
          <span>These figures are disclosed spread, not verified net profit. <NuxtLink class="footer-link" to="/method">How this is calculated →</NuxtLink></span>
        </footer>
      </section>
    </section>

    </main>

    <div v-if="selectedProduct" class="detail-backdrop" @click.self="closeProduct">
      <aside
        ref="drawerEl"
        class="detail-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="drawer-title"
      >
        <button class="drawer-close" type="button" aria-label="Close product details" @click="closeProduct">×</button>
        <template v-if="detailPending">
          <p class="eyebrow">PRODUCT ANALYTICS</p>
          <h2 id="drawer-title">
            <a v-if="selectedProduct.url" class="drawer-product-link" :href="selectedProduct.url" target="_blank" rel="noreferrer" @click.stop>
              {{ selectedProduct.name }} ↗
            </a>
            <template v-else>{{ selectedProduct.name }}</template>
          </h2>
          <div class="state-card loading-state"><span class="loading-bar" /><span class="loading-bar short" /><p>Loading history…</p></div>
        </template>
        <template v-else-if="detailError">
          <p class="eyebrow">PRODUCT ANALYTICS</p>
          <h2 id="drawer-title">
            <a v-if="selectedProduct.url" class="drawer-product-link" :href="selectedProduct.url" target="_blank" rel="noreferrer" @click.stop>
              {{ selectedProduct.name }} ↗
            </a>
            <template v-else>{{ selectedProduct.name }}</template>
          </h2>
          <div class="state-card error-state">
            <strong>{{ detailError }}</strong>
            <button class="action-button" type="button" @click="void loadProduct(selectedProduct)">Retry</button>
          </div>
        </template>
        <template v-else-if="detail">
          <p class="eyebrow">{{ detail.product.departmentLabel }} / {{ detail.product.categoryLabel }}</p>
          <h2 id="drawer-title">
            <a v-if="detail.product.url" class="drawer-product-link" :href="detail.product.url" target="_blank" rel="noreferrer" @click.stop>
              {{ detail.product.name }} ↗
            </a>
            <template v-else>{{ detail.product.name }}</template>
          </h2>
          <p class="drawer-subtitle">
            {{ detail.product.brand || "Quince catalog" }} · {{ countLabel(detail.analytics.observationCount, "observation") }}
            <template v-if="detail.product.variantLabel"> · {{ detail.product.variantLabel }}</template>
          </p>

          <div v-if="selectedGroup?.variants?.length" class="variant-picker">
            <div class="variant-picker-heading">
              <div>
                <p class="eyebrow">SAME PRICE</p>
                <h3>Available variants</h3>
              </div>
              <span>{{ selectedGroup.variantCount }} tracked</span>
            </div>
            <div class="variant-options" role="group" aria-label="Product variants at this price">
              <button
                v-for="variant in selectedGroup.variants"
                :key="`${variant.productKey}-${variant.variantKey}`"
                class="variant-option"
                :class="{ active: sameVariant(detail.product, variant) }"
                type="button"
                :aria-pressed="sameVariant(detail.product, variant)"
                @click="void loadProduct(variant)"
              >
                <span>{{ variant.variantColor || variant.variantLabel || `Variant ${variant.variantKey}` }}</span>
                <small>{{ variant.variantSize || "Color / size not captured" }}</small>
              </button>
            </div>
            <p v-if="selectedGroup.metricsMixed" class="variant-picker-note">
              Production costs differ across these variants, so the table shows a range and each option keeps its own history.
            </p>
          </div>

          <div v-if="detailImageUrls.length" class="detail-product-images">
            <div v-for="(imageUrl, index) in detailImageUrls" :key="`${imageUrl}-${index}`" class="detail-product-image">
              <img
                :src="imageUrl"
                :alt="`${detail.product.name} image ${index + 1}`"
                loading="lazy"
                decoding="async"
                @error="markImageFailed(imageUrl)"
              >
            </div>
          </div>

          <div class="detail-current-grid">
            <div><span>Current price</span><strong>{{ formatMoney(detail.current.sellingPrice, detail.product.currency) }}</strong></div>
            <div><span>Reported cost</span><strong>{{ formatMoney(detail.current.reportedTotalCost, detail.product.currency) }}</strong></div>
            <div><span>Current spread</span><strong :class="spreadClass(detail.current.unitSpread)">{{ detailSpread(detail.current) }}</strong></div>
          </div>

          <div class="detail-section">
            <div class="section-heading"><div><p class="eyebrow">CURRENT BREAKDOWN</p><h3>Reported cost components</h3></div><span>Stored per observation</span></div>
            <div v-if="detail.current.costLines.length" class="cost-breakdown">
              <div
                v-for="(line, index) in detail.current.costLines"
                :key="`${line.type}-${line.label}-${index}`"
                class="cost-breakdown-row"
              >
                <span>{{ line.label }}</span>
                <strong>{{ formatMoney(line.amount, detail.product.currency) }}</strong>
              </div>
              <div class="cost-breakdown-row total">
                <span>Total reported cost</span>
                <strong>{{ formatMoney(detail.current.reportedTotalCost, detail.product.currency) }}</strong>
              </div>
            </div>
            <p v-else class="history-empty">No component-level cost lines were retained for this observation.</p>
            <p v-if="detail.product.hasExorbitantFees" class="breakdown-note fee-warning"><span class="fee-asterisk" aria-hidden="true">*</span> An implausible reported fee was detected. Duties, taxes, and fees above the rest of the breakdown are shown as $0.00 in calculated cost.</p>
            <p class="breakdown-note">Each observation stores its own component amounts, so the ledger below can attribute a move to materials, crafting, freight, or the line that actually changed.</p>
          </div>

          <div v-if="changeLog.length" class="detail-section">
            <div class="section-heading">
              <div><p class="eyebrow">WHAT CHANGED</p><h3>Change ledger</h3></div>
              <span>{{ recordedChanges === 0 ? "No moves recorded" : `${countLabel(recordedChanges, "move")} recorded` }} · {{ countLabel(detail.analytics.observationCount, "capture") }}</span>
            </div>
            <ol class="change-log">
              <li
                v-for="(event, eventIndex) in changeLog"
                :key="`${event.capturedAt}-${eventIndex}`"
                class="change-event"
                :class="`change-event-${event.kind}`"
              >
                <div class="change-event-head">
                  <time :datetime="event.capturedAt">{{ formatDate(event.capturedAt) }}</time>
                  <span>{{ changeEventLabel(event) }}</span>
                </div>
                <ul class="change-moves">
                  <li
                    v-for="(move, moveIndex) in event.moves"
                    :key="`${move.label}-${moveIndex}`"
                    class="change-move"
                    :class="[`change-move-${move.direction}`, { 'change-move-summary': move.summary }]"
                  >
                    <span class="change-move-label">{{ move.label }}</span>
                    <span class="change-move-values">
                      <template v-if="event.kind === 'update' && move.from && move.to">{{ move.from }} → {{ move.to }}</template>
                      <template v-else-if="move.direction === 'added'">New line at {{ move.to }}</template>
                      <template v-else-if="move.direction === 'removed'">Dropped after {{ move.from }}</template>
                      <template v-else>{{ move.to ?? move.from ?? "—" }}</template>
                    </span>
                    <span v-if="event.kind === 'update'" class="change-move-delta">
                      <template v-if="move.delta">{{ move.delta }}</template>
                      <template v-else-if="move.direction === 'added'">added</template>
                      <template v-else-if="move.direction === 'removed'">removed</template>
                      <template v-else>—</template>
                    </span>
                  </li>
                </ul>
              </li>
            </ol>
            <p v-if="recordedChanges === 0" class="breakdown-note">Nothing moved between captures — the listed price and every reported cost line are unchanged since the first observation.</p>
          </div>

          <div class="detail-section">
            <div class="section-heading"><div><p class="eyebrow">HISTORY</p><h3>Price and cost timeline</h3></div><span>{{ formatDate(detail.analytics.firstObservedAt) }} — {{ formatDate(detail.analytics.lastObservedAt) }}</span></div>
            <div v-if="historyChart.points.length" class="history-chart-card">
              <div class="history-legend" aria-hidden="true">
                <span><i class="legend-swatch price" />Price</span>
                <span><i class="legend-swatch cost" />Reported cost</span>
              </div>
              <svg
                class="history-chart"
                viewBox="0 0 640 230"
                role="img"
                :aria-label="`Price and reported cost history for ${detail.product.name}`"
              >
                <g v-for="line in historyChart.gridLines" :key="line.y">
                  <line class="chart-gridline" x1="58" :y1="line.y" x2="624" :y2="line.y" />
                  <text class="chart-label" x="0" :y="line.y + 4">{{ line.label }}</text>
                </g>
                <path v-if="historyChart.pricePath" class="chart-line price" :d="historyChart.pricePath" />
                <path v-if="historyChart.costPath" class="chart-line cost" :d="historyChart.costPath" />
                <template v-for="(point, index) in historyChart.points" :key="`${point.capturedAt}-${index}`">
                  <circle v-if="point.priceY !== null" class="chart-point price" :cx="point.x" :cy="point.priceY" r="4" />
                  <circle v-if="point.costY !== null" class="chart-point cost" :cx="point.x" :cy="point.costY" r="4" />
                </template>
                <text
                  v-for="(axisLabel, index) in historyChart.axisLabels"
                  :key="`axis-${index}`"
                  class="chart-axis-label"
                  :x="axisLabel.x"
                  y="220"
                  :text-anchor="axisLabel.anchor"
                >{{ axisLabel.label }}</text>
              </svg>
            </div>
            <div v-else class="history-empty">No numeric price or cost observations are available for this product.</div>
            <div class="history-bars">
              <div v-for="(point, index) in detail.history" :key="`${point.capturedAt}-${index}`" class="history-row">
                <time :datetime="point.capturedAt">{{ formatDate(point.capturedAt) }}</time>
                <div class="history-values"><span>Price <strong>{{ formatMoney(point.sellingPrice, detail.product.currency) }}</strong></span><span>Cost <strong>{{ formatMoney(point.reportedTotalCost, detail.product.currency) }}</strong></span><span :class="spreadClass(point.unitSpread)">Spread <strong>{{ detailSpread(point) }}</strong></span></div>
              </div>
            </div>
          </div>

          <div class="detail-section">
            <div class="section-heading"><div><p class="eyebrow">ANALYTICS</p><h3>Observed range</h3></div></div>
            <div class="analytics-grid">
              <div><span>Lowest price</span><strong>{{ formatMoney(detail.analytics.lowestPrice, detail.product.currency) }}</strong></div>
              <div><span>Highest price</span><strong>{{ formatMoney(detail.analytics.highestPrice, detail.product.currency) }}</strong></div>
              <div><span>Average spread</span><strong>{{ formatMoney(detail.analytics.averageSpread, detail.product.currency) }}</strong></div>
              <div><span>Loss observations</span><strong>{{ detail.analytics.lossObservations }}</strong></div>
              <div><span>Profit observations</span><strong>{{ detail.analytics.profitObservations }}</strong></div>
              <div><span>Highest reported cost</span><strong>{{ formatMoney(detail.analytics.highestCost, detail.product.currency) }}</strong></div>
            </div>
          </div>
        </template>
      </aside>
    </div>
  </div>
</template>
