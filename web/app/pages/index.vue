<script setup lang="ts">
type View = "losses" | "profit" | "all";

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

const view = ref<View>("losses");
const search = ref("");
const department = ref("");
const category = ref("");
const sort = ref("spread_asc");
const hydrated = ref(false);

onMounted(() => {
  hydrated.value = true;
});

const requestQuery = computed(() => {
  const query: Record<string, string> = {
    view: view.value,
    sort: sort.value,
    limit: "5000",
  };
  if (search.value.trim()) query.search = search.value.trim();
  if (department.value) query.department = department.value;
  if (category.value) query.category = category.value;
  return query;
});

const { data, pending, error, refresh } = await useAsyncData<RankingResponse>(
  "rankings",
  () => $fetch<RankingResponse>(`${apiBase}/api/rankings`, { query: requestQuery.value }),
  {
    server: false,
    default: emptyResponse,
    watch: [requestQuery],
  },
);

const response = computed(() => data.value || emptyResponse());
const results = computed(() => response.value.results);
const summary = computed(() => response.value.summary);
const departments = computed(() => response.value.facets.departments);
const categories = computed(() => response.value.facets.categories);

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

function retry() {
  void refresh();
}
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
        {{ hydrated && pending ? "Updating" : "Local snapshot" }}
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
          <div class="sort-control">
            <label for="sort">Sort by</label>
            <select id="sort" v-model="sort" class="select-field compact-select">
              <option value="spread_asc">Lowest spread</option>
              <option value="spread_desc">Highest spread</option>
              <option value="price_desc">Highest price</option>
              <option value="price_asc">Lowest price</option>
              <option value="name">Product name</option>
            </select>
          </div>
        </div>

        <div v-if="error" class="state-card error-state">
          <strong>Could not reach the rankings API.</strong>
          <p>Start the Python API on port 8877, then try again.</p>
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
            <span>Showing {{ formatNumber(results.length) }} of {{ formatNumber(response.total) }} matches</span>
            <span>Updated {{ formatDate(response.generatedAt) }}</span>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th scope="col">Product</th>
                  <th scope="col">Department</th>
                  <th scope="col" class="numeric">Price</th>
                  <th scope="col" class="numeric">Reported cost</th>
                  <th scope="col" class="numeric">Spread</th>
                  <th scope="col" class="numeric">Margin</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="product in results" :key="`${product.productKey}-${product.variantKey}`">
                  <td>
                    <div class="product-cell">
                      <a v-if="product.url" :href="product.url" target="_blank" rel="noreferrer">
                        {{ product.name }} <span aria-hidden="true">↗</span>
                      </a>
                      <strong v-else>{{ product.name }}</strong>
                      <span>{{ product.categoryLabel }}<template v-if="product.brand"> · {{ product.brand }}</template></span>
                    </div>
                  </td>
                  <td><span class="department-pill">{{ product.departmentLabel }}</span></td>
                  <td class="numeric">{{ formatMoney(product.sellingPrice, product.currency) }}</td>
                  <td class="numeric">{{ formatMoney(product.reportedTotalCost, product.currency) }}</td>
                  <td class="numeric" :class="`spread-${product.classification}`">
                    {{ formatSpread(product) }}
                  </td>
                  <td class="numeric">{{ formatMargin(product.marginPct) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>

        <footer class="results-footer">
          <span>Source: Quince-reported cost breakdowns</span>
          <span>These figures are disclosed spread, not verified net profit.</span>
        </footer>
      </section>
    </section>
  </main>
</template>
