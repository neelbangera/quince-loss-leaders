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
  classification: "loss" | "profit" | "break_even";
  capturedAt: string;
  hasExorbitantFees: boolean;
  historyPath?: string;
}

interface ProductHistoryPoint {
  capturedAt: string;
  sellingPrice: string | null;
  reportedTotalCost: string | null;
  unitSpread: string | null;
  marginPct: number | null;
  parseStatus: string;
  totalCostSource: string;
  costLines: { label: string; type: string; amount: string | null }[];
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
}

interface Summary {
  total: number;
  losses: number;
  profitDrivers: number;
  breakEven: number;
  filtered: {
    total: number;
    losses: number;
    profitDrivers: number;
    breakEven: number;
  };
}

interface RankingResponse {
  generatedAt: string;
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
  view: "losses",
  total: 0,
  hasMore: false,
  summary: {
    total: 0,
    losses: 0,
    profitDrivers: 0,
    breakEven: 0,
    filtered: { total: 0, losses: 0, profitDrivers: 0, breakEven: 0 },
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
const hydrated = ref(false);
const selectedProduct = ref<ProductResult | null>(null);
const detail = ref<ProductDetail | null>(null);
const detailPending = ref(false);
const detailError = ref("");

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

const { data, pending, error, refresh } = await useAsyncData<RankingResponse>(
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

function staticResponse(source: RankingResponse): RankingResponse {
  const facetRows = department.value
    ? source.results.filter((item) => item.department === department.value)
    : source.results;
  let rows = source.results;

  if (view.value === "losses") {
    rows = rows.filter((item) => numericValue(item.unitSpread) !== null && numericValue(item.unitSpread)! < 0);
  } else if (view.value === "profit") {
    rows = rows.filter((item) => numericValue(item.unitSpread) !== null && numericValue(item.unitSpread)! > 0);
  }

  if (department.value) rows = rows.filter((item) => item.department === department.value);
  if (category.value) rows = rows.filter((item) => item.category === category.value);
  const searchTerm = search.value.trim().toLowerCase();
  if (searchTerm) {
    rows = rows.filter((item) =>
      [item.name, item.brand || "", item.departmentLabel, item.categoryLabel]
        .join(" ")
        .toLowerCase()
        .includes(searchTerm),
    );
  }

  const filtered = {
    total: rows.length,
    losses: rows.filter((item) => numericValue(item.unitSpread) !== null && numericValue(item.unitSpread)! < 0).length,
    profitDrivers: rows.filter((item) => numericValue(item.unitSpread) !== null && numericValue(item.unitSpread)! > 0).length,
    breakEven: rows.filter((item) => numericValue(item.unitSpread) === 0).length,
  };
  return {
    ...source,
    view: view.value,
    total: rows.length,
    hasMore: false,
    summary: { ...source.summary, filtered },
    facets: {
      departments: source.facets.departments.length
        ? source.facets.departments
        : staticFacetValues(source.results, "department"),
      categories: staticFacetValues(facetRows, "category"),
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
const departments = computed(() => response.value.facets.departments);
const categories = computed(() => response.value.facets.categories);

watch([view, search, department, category, sort, pageSize], () => {
  currentPage.value = 1;
});

watch(pageCount, (count) => {
  if (currentPage.value > count) currentPage.value = count;
});

const activeViewLabel = computed(() => {
  if (view.value === "profit") return "Positive spread drivers";
  if (view.value === "all") return "Full spread ranking";
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

function formatMoney(value: string | null, currency = "USD") {
  if (value === null) return "—";
  const amount = Number(value);
  if (!Number.isFinite(amount)) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
  }).format(amount);
}

function formatSpread(product: ProductResult) {
  const value = formatMoney(product.unitSpread, product.currency);
  if (value === "—" || product.classification === "break_even") return value;
  return product.classification === "profit" ? `+${value}` : value;
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

    if (field === "price") {
      return compareNumbers(numericValue(left.sellingPrice), numericValue(right.sellingPrice), direction);
    }
    if (field === "cost") {
      return compareNumbers(numericValue(left.reportedTotalCost), numericValue(right.reportedTotalCost), direction);
    }
    if (field === "margin") {
      return compareNumbers(numericValue(left.marginPct), numericValue(right.marginPct), direction);
    }
    if (field === "spread") {
      return compareNumbers(numericValue(left.unitSpread), numericValue(right.unitSpread), direction);
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

async function openProduct(product: ProductResult) {
  selectedProduct.value = product;
  detail.value = null;
  detailError.value = "";
  detailPending.value = true;
  try {
    if (staticMode) {
      if (!product.historyPath) throw new Error("History file is not available.");
      detail.value = await fetchJson<ProductDetail>(`${staticDataBase}/${product.historyPath}`);
    } else {
      detail.value = await fetchJson<ProductDetail>(`${apiBase}/api/product`, {
        product_key: product.productKey,
        variant_key: product.variantKey,
      });
    }
  } catch {
    detailError.value = "Could not load product history.";
  } finally {
    detailPending.value = false;
  }
}

function handleProductClick(event: MouseEvent, product: ProductResult) {
  if ((event.ctrlKey || event.metaKey) && product.url) {
    window.open(product.url, "_blank", "noopener,noreferrer");
    return;
  }
  void openProduct(product);
}

function closeProduct() {
  selectedProduct.value = null;
  detail.value = null;
}

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
    return { points: [], pricePath: "", costPath: "", gridLines: [] };
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
  const points = history.map((point, index) => {
    const price = numericValue(point.sellingPrice);
    const cost = numericValue(point.reportedTotalCost);
    return {
      capturedAt: point.capturedAt,
      x: history.length === 1 ? left + plotWidth / 2 : left + (index / (history.length - 1)) * plotWidth,
      price,
      cost,
      priceY: price === null ? null : yFor(price),
      costY: cost === null ? null : yFor(cost),
      label: shortDate(point.capturedAt),
    };
  });
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
  };
});
</script>

<template>
  <main class="shell">
    <header class="topbar">
      <NuxtLink class="brand" to="/" aria-label="Quince Ledger home">
        <span class="brand-mark">QL</span>
        <span class="brand-copy">
          <strong>Quince Ledger</strong>
          <small>Disclosed cost intelligence</small>
        </span>
      </NuxtLink>
      <div class="connection-status" :class="{ loading: pending }">
        <span class="status-dot" />
        {{ hydrated && pending ? "Updating" : staticMode ? "Published snapshot" : "Local snapshot" }}
      </div>
    </header>

    <section class="hero">
      <div class="hero-copy">
        <p class="eyebrow">US CATALOG / REPORTED COSTS</p>
        <h1>Where the price tells a different story.</h1>
        <p class="hero-text">
          A living view of Quince products ranked against the cost breakdowns
          published on their product pages.
        </p>
      </div>
      <div class="snapshot-card">
        <span>Latest data refresh</span>
        <strong>{{ formatDate(response.generatedAt) }}</strong>
        <small>Complete observations only</small>
      </div>
    </section>

    <section class="metrics" aria-label="Ranking summary">
      <article class="metric-card">
        <span>Ranked items</span>
        <strong>{{ formatNumber(summary.total) }}</strong>
        <small>Latest complete observations</small>
      </article>
      <article class="metric-card metric-loss">
        <span>Loss leaders</span>
        <strong>{{ formatNumber(summary.losses) }}</strong>
        <small>Negative disclosed spread</small>
      </article>
      <article class="metric-card metric-profit">
        <span>Positive spread</span>
        <strong>{{ formatNumber(summary.profitDrivers) }}</strong>
        <small>Price above disclosed cost</small>
      </article>
      <article class="metric-card">
        <span>Break-even</span>
        <strong>{{ formatNumber(summary.breakEven) }}</strong>
        <small>Reported price equals cost</small>
      </article>
    </section>

    <section class="workspace">
      <aside class="filters-panel">
        <div class="panel-heading">
          <div>
            <p class="eyebrow">EXPLORE</p>
            <h2>Catalog filters</h2>
          </div>
          <button class="text-button" type="button" @click="resetFilters">Reset</button>
        </div>

        <div class="view-tabs" role="tablist" aria-label="Ranking view">
          <button
            v-for="tab in [
              { value: 'losses', label: 'Losses' },
              { value: 'profit', label: 'Drivers' },
              { value: 'all', label: 'All' },
            ]"
            :key="tab.value"
            class="view-tab"
            :class="{ active: view === tab.value }"
            type="button"
            role="tab"
            :aria-selected="view === tab.value"
            @click="setView(tab.value as View)"
          >
            {{ tab.label }}
          </button>
        </div>

        <label class="field-label" for="search">Search products</label>
        <div class="search-field">
          <span aria-hidden="true">⌕</span>
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
            <p class="eyebrow">RANKING / {{ view.toUpperCase() }}</p>
            <h2>{{ activeViewLabel }}</h2>
            <p class="results-description">{{ viewDescription }}</p>
          </div>
          <div class="table-controls">
            <div class="sort-control">
              <label for="sort">Sort by</label>
              <select id="sort" v-model="sort" class="select-field compact-select">
                <option value="spread_asc">Lowest spread</option>
                <option value="spread_desc">Highest spread</option>
                <option value="price_desc">Highest price</option>
                <option value="price_asc">Lowest price</option>
                <option value="cost_desc">Highest reported cost</option>
                <option value="cost_asc">Lowest reported cost</option>
                <option value="margin_desc">Highest margin</option>
                <option value="margin_asc">Lowest margin</option>
                <option value="name_asc">Product name</option>
              </select>
            </div>
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

        <div v-if="error" class="state-card error-state">
          <strong>{{ staticMode ? "Could not load the published snapshot." : "Could not reach the rankings API." }}</strong>
          <p>{{ staticMode ? "The static data files are missing or unavailable." : "Start the Python API on port 8877, then try again." }}</p>
          <button class="action-button" type="button" @click="retry">Retry</button>
        </div>

        <div v-else-if="pending" class="state-card loading-state">
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
            <span>Updated {{ formatDate(response.generatedAt) }}</span>
          </div>
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
                      <button class="product-detail-button" type="button" @click.stop="handleProductClick($event, product)">
                        {{ product.name }}<span
                          v-if="product.hasExorbitantFees"
                          class="fee-asterisk"
                          title="A reported freight, card, or duties fee is at least as large as the listed price."
                          aria-label="Flagged for an exorbitant reported fee"
                        >*</span>
                      </button>
                      <span>{{ product.categoryLabel }}<template v-if="product.brand"> · {{ product.brand }}</template></span>
                    </div>
                  </td>
                  <td><span class="department-pill">{{ product.departmentLabel }}</span></td>
                  <td class="numeric">{{ formatMoney(product.sellingPrice, product.currency) }}</td>
                  <td class="numeric">{{ formatMoney(product.reportedTotalCost, product.currency) }}</td>
                  <td class="numeric" :class="`spread-${product.classification}`">
                    {{ formatSpread(product) }}
                  </td>
                  <td class="numeric" :class="marginClass(product.marginPct)">
                    {{ formatMargin(product.marginPct) }}
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

        <footer class="results-footer">
          <span>Source: Quince-reported cost breakdowns</span>
          <span><span class="fee-asterisk" aria-hidden="true">*</span> A reported fee is at least as large as the listed price.</span>
          <span>These figures are disclosed spread, not verified net profit.</span>
        </footer>
      </section>
    </section>

    <div v-if="selectedProduct" class="detail-backdrop" @click.self="closeProduct">
      <aside class="detail-drawer" aria-label="Product analytics">
        <button class="drawer-close" type="button" aria-label="Close product details" @click="closeProduct">×</button>
        <template v-if="detailPending">
          <p class="eyebrow">PRODUCT ANALYTICS</p>
          <h2>
            <a v-if="selectedProduct.url" class="drawer-product-link" :href="selectedProduct.url" target="_blank" rel="noreferrer" @click.stop>
              {{ selectedProduct.name }} ↗
            </a>
            <template v-else>{{ selectedProduct.name }}</template>
          </h2>
          <div class="state-card loading-state"><span class="loading-bar" /><span class="loading-bar short" /><p>Loading history…</p></div>
        </template>
        <template v-else-if="detailError">
          <p class="eyebrow">PRODUCT ANALYTICS</p>
          <h2>
            <a v-if="selectedProduct.url" class="drawer-product-link" :href="selectedProduct.url" target="_blank" rel="noreferrer" @click.stop>
              {{ selectedProduct.name }} ↗
            </a>
            <template v-else>{{ selectedProduct.name }}</template>
          </h2>
          <div class="state-card error-state"><strong>{{ detailError }}</strong></div>
        </template>
        <template v-else-if="detail">
          <p class="eyebrow">{{ detail.product.departmentLabel }} / {{ detail.product.categoryLabel }}</p>
          <h2>
            <a v-if="detail.product.url" class="drawer-product-link" :href="detail.product.url" target="_blank" rel="noreferrer" @click.stop>
              {{ detail.product.name }} ↗
            </a>
            <template v-else>{{ detail.product.name }}</template>
          </h2>
          <p class="drawer-subtitle">{{ detail.product.brand || "Quince catalog" }} · {{ detail.analytics.observationCount }} observations</p>

          <div class="detail-current-grid">
            <div><span>Current price</span><strong>{{ formatMoney(detail.current.sellingPrice, detail.product.currency) }}</strong></div>
            <div><span>Reported cost</span><strong>{{ formatMoney(detail.current.reportedTotalCost, detail.product.currency) }}</strong></div>
            <div><span>Current spread</span><strong :class="spreadClass(detail.current.unitSpread)">{{ detailSpread(detail.current) }}</strong></div>
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
              </svg>
              <div class="history-axis" aria-hidden="true">
                <span v-for="(point, index) in historyChart.points" :key="`${point.capturedAt}-label-${index}`">{{ point.label }}</span>
              </div>
            </div>
            <div v-else class="history-empty">No numeric price or cost observations are available for this product.</div>
            <div class="history-bars">
              <div v-for="(point, index) in detail.history" :key="`${point.capturedAt}-${index}`" class="history-row">
                <time>{{ formatDate(point.capturedAt) }}</time>
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
  </main>
</template>
