<script setup lang="ts">
import type { DisplayMode, Facet, PageSize, ProductResult, RankingResponse, SearchScope, Sort, SortField, View } from "~/types/ranking";

const emptyResponse = (): RankingResponse => ({
  generatedAt: "",
  latestCapturedAt: null,
  view: "all",
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

const VIEWS: { value: View; label: string }[] = [
  { value: "losses", label: "Below cost" },
  { value: "profit", label: "Above cost" },
  { value: "all", label: "Everything" },
];
const SORTS: { value: Sort; label: string }[] = [
  { value: "spread_asc", label: "Furthest below cost" },
  { value: "spread_desc", label: "Furthest above cost" },
  { value: "price_asc", label: "Price, low to high" },
  { value: "price_desc", label: "Price, high to low" },
  { value: "name_asc", label: "Name, A to Z" },
];
const defaultSort = (view: View): Sort => (view === "profit" ? "spread_desc" : "spread_asc");

// ---- State, restored from the address bar so a view can be linked and survives a refresh
const route = useRoute();
const router = useRouter();
const queryValue = (key: string) => {
  const value = route.query[key];
  return typeof value === "string" ? value : "";
};
const oneOf = <T extends string>(value: string, allowed: readonly T[], fallback: T): T =>
  (allowed as readonly string[]).includes(value) ? (value as T) : fallback;

const view = ref<View>(oneOf(queryValue("view"), ["losses", "profit", "all"], "losses"));
const department = ref(queryValue("department"));
const category = ref(queryValue("category"));
const search = ref(queryValue("q"));
const scope = ref<SearchScope>(oneOf(queryValue("scope"), ["local", "global"], "local"));
const sort = ref<Sort>(/^(name|department|price|cost|spread|margin)_(asc|desc)$/.test(queryValue("sort")) ? (queryValue("sort") as Sort) : defaultSort(view.value));
const displayMode = ref<DisplayMode>(oneOf(queryValue("show"), ["photos", "list"], "photos"));
const pageSize = ref<PageSize>(oneOf(queryValue("per"), ["24", "96", "all"], "24"));
const currentPage = ref(Math.max(1, Math.floor(Number(queryValue("page"))) || 1));

watch([view, department, category, search, scope, sort, displayMode, pageSize, currentPage], () => {
  const query: Record<string, string> = {};
  if (view.value !== "losses") query.view = view.value;
  if (department.value) query.department = department.value;
  if (category.value) query.category = category.value;
  if (search.value.trim()) query.q = search.value.trim();
  if (scope.value === "global" && search.value.trim()) query.scope = "global";
  if (sort.value !== defaultSort(view.value)) query.sort = sort.value;
  if (displayMode.value !== "photos") query.show = displayMode.value;
  if (pageSize.value !== "24") query.per = pageSize.value;
  if (currentPage.value > 1) query.page = String(currentPage.value);
  void router.replace({ query });
});

// ---- Data: the whole catalog is loaded once, in either mode. Every view,
// filter, search and sort after that is local, so API and static mode share
// one set of semantics and nothing refetches on a keystroke.
const { apiBase, staticDataBase, staticMode, fetchJson } = useDataSource();
const { data, pending, error, refresh } = useAsyncData<RankingResponse>(
  "catalog",
  () => staticMode
    ? fetchJson<RankingResponse>(`${staticDataBase}/rankings.json`)
    : fetchJson<RankingResponse>(`${apiBase}/api/rankings`, { view: "all", limit: "5000" }),
  { server: false, default: emptyResponse },
);

const hydrated = ref(false);
onMounted(() => {
  hydrated.value = true;
});
const loading = computed(() => !hydrated.value || pending.value);
const catalog = computed(() => data.value?.results ?? []);
const catalogTotal = computed(() => catalog.value.length);
const term = computed(() => search.value.trim());

// Searching the whole catalog steps outside the current view and filters without discarding them.
const searchingEverything = computed(() => scope.value === "global" && Boolean(term.value));
const activeView = computed<View>(() => (searchingEverything.value ? "all" : view.value));
const activeDepartment = computed(() => (searchingEverything.value ? "" : department.value));
const activeCategory = computed(() => (searchingEverything.value ? "" : category.value));

const tabCounts = computed<Record<View, number>>(() => ({
  losses: catalog.value.filter((item) => inView(item, "losses")).length,
  profit: catalog.value.filter((item) => inView(item, "profit")).length,
  all: catalogTotal.value,
}));

const viewRows = computed(() => catalog.value.filter((item) => inView(item, activeView.value)));
// "Other" is the taxonomy's catch-all, so it never leads a row of choices.
const otherLast = (facets: Facet[]) => [...facets.filter((item) => item.value !== "other"), ...facets.filter((item) => item.value === "other")];
const departments = computed(() => orderDepartments(facetValues(viewRows.value, "department")));
// Each department's categories in the current view, for the masthead panel.
const categoriesByDepartment = computed(() => {
  const rows = new Map<string, ProductResult[]>();
  for (const item of viewRows.value) {
    const group = rows.get(item.department);
    if (group) group.push(item);
    else rows.set(item.department, [item]);
  }
  return Object.fromEntries([...rows].map(([value, items]) => [value, otherLast(facetValues(items, "category"))]));
});
const departmentRows = computed(() => viewRows.value.filter((item) => matchesFilter(item, { department: activeDepartment.value })));
const categories = computed(() => otherLast(facetValues(departmentRows.value, "category")));

// Rank is a style's place in the current view and sort before searching, so a search never renumbers it.
const ranked = computed(() =>
  sortResults(departmentRows.value.filter((item) => matchesFilter(item, { category: activeCategory.value })), sort.value),
);
const rankByKey = computed(() => new Map(ranked.value.map((item, index) => [productKey(item), index + 1])));
const rankOf = (product: ProductResult) => rankByKey.value.get(productKey(product)) ?? null;

const results = computed(() => (term.value ? ranked.value.filter((item) => matchesFilter(item, { search: term.value })) : ranked.value));

// Both scope counts are always computed, so an empty local search still shows what exists elsewhere.
const localMatches = computed(() => {
  if (!term.value) return 0;
  if (!searchingEverything.value) return results.value.length;
  return catalog.value.filter((item) =>
    inView(item, view.value)
    && matchesFilter(item, { department: department.value, category: category.value, search: term.value })).length;
});
const globalMatches = computed(() => (term.value ? catalog.value.filter((item) => matchesFilter(item, { search: term.value })).length : 0));
const alreadyEverything = computed(() => view.value === "all" && !department.value && !category.value);

const pageSizeValue = computed(() => (pageSize.value === "all" ? Math.max(1, results.value.length) : Number(pageSize.value)));
const pageCount = computed(() => Math.max(1, Math.ceil(results.value.length / pageSizeValue.value)));
const pageStart = computed(() => (currentPage.value - 1) * pageSizeValue.value);
const pageEnd = computed(() => Math.min(pageStart.value + pageSizeValue.value, results.value.length));
const visibleResults = computed(() => results.value.slice(pageStart.value, pageEnd.value));

watch([view, department, category, search, scope, sort, pageSize], () => {
  currentPage.value = 1;
});
watch(pageCount, (count) => {
  // Until the catalog has loaded there is one empty page; keep the page the address bar asked for.
  if (catalogTotal.value && currentPage.value > count) currentPage.value = count;
});
watch(term, (value) => {
  if (!value) scope.value = "local";
});

// ---- Words
const viewLabel = computed(() => VIEWS.find((item) => item.value === view.value)?.label ?? "Everything");
const headline = computed(() => {
  if (activeView.value === "losses") return "Priced below cost";
  if (activeView.value === "profit") return "Priced above cost";
  return "The whole catalog";
});
const standfirst = computed(() => {
  const total = formatNumber(catalogTotal.value);
  if (activeView.value === "losses") {
    return { count: formatNumber(tabCounts.value.losses), rest: ` of ${total} styles have a colour or size listed for less than Quince says it costs to make.` };
  }
  if (activeView.value === "profit") {
    return { count: formatNumber(tabCounts.value.profit), rest: ` of ${total} styles have a colour or size listed for more than Quince says it costs to make.` };
  }
  return { count: total, rest: " styles, each one product at one price, set against the cost Quince reports for it." };
});
const searchPlaceholder = computed(() => (view.value === "all" ? "Search the catalog" : `Search ${viewLabel.value.toLowerCase()}`));
// A sort picked from a list column head is named in the menu like the others.
const COLUMN_NAMES: Record<SortField, string> = {
  name: "Name",
  department: "Department",
  price: "Price",
  cost: "Cost",
  spread: "Difference",
  margin: "% of price",
};
const columnSortLabel = (value: Sort) => {
  const { field, direction } = sortParts(value);
  const text = field === "name" || field === "department";
  return `${COLUMN_NAMES[field]}, ${direction === "asc" ? (text ? "A to Z" : "low to high") : (text ? "Z to A" : "high to low")}`;
};
const sortOptions = computed(() => (SORTS.some((item) => item.value === sort.value) ? SORTS : [...SORTS, { value: sort.value, label: columnSortLabel(sort.value) }]));

// ---- Actions
function setView(next: View) {
  view.value = next;
  scope.value = "local";
  category.value = "";
  sort.value = defaultSort(next);
}
function setDepartment(next: string) {
  department.value = next;
  category.value = "";
  scope.value = "local";
}
function setDepartmentCategory(nextDepartment: string, nextCategory: string) {
  department.value = nextDepartment;
  category.value = nextCategory;
  scope.value = "local";
}
function setCategory(next: string) {
  category.value = next;
  scope.value = "local";
}
function resetFilters() {
  search.value = "";
  department.value = "";
  category.value = "";
  scope.value = "local";
}

const sheet = useProductDetail();
function openProduct(event: MouseEvent, product: ProductResult) {
  // Ctrl or Cmd click goes straight to the item on Quince.
  if ((event.ctrlKey || event.metaKey) && product.url) {
    window.open(product.url, "_blank", "noopener,noreferrer");
    return;
  }
  void sheet.open(product);
}
function retrySheet() {
  if (sheet.selectedProduct.value) void sheet.loadVariant(sheet.selectedProduct.value);
}
</script>

<template>
  <div>
    <SiteMasthead
      :last-checked="data?.latestCapturedAt"
      :departments="departments"
      :active-department="activeDepartment"
      :active-category="activeCategory"
      :categories-by-department="categoriesByDepartment"
      :context="activeView === 'all' ? 'in the catalog' : viewLabel.toLowerCase()"
      @department="setDepartment"
      @category="setDepartmentCategory"
    />

    <main class="page">
      <section class="opening">
        <h1>{{ headline }}</h1>
        <p v-if="!loading && catalogTotal"><strong>{{ standfirst.count }}</strong>{{ standfirst.rest }}</p>
        <p v-else>&nbsp;</p>
        <div class="tabs label" role="group" aria-label="Which styles to show">
          <button
            v-for="tab in VIEWS"
            :key="tab.value"
            type="button"
            :aria-pressed="activeView === tab.value"
            @click="setView(tab.value)"
          >
            {{ tab.label }}<span v-if="!loading" class="count">{{ formatNumber(tabCounts[tab.value]) }}</span>
          </button>
        </div>
      </section>

      <div class="toolbar">
        <FacetLinks
          :items="categories"
          :active="activeCategory"
          :limit="5"
          all-label="All"
          :all-count="departmentRows.length"
          label="Categories"
          @select="setCategory"
        />
        <div class="tools label">
          <label class="search">
            <svg aria-hidden="true" viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="square"><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.8-3.8" /></svg>
            <input v-model="search" type="search" :placeholder="searchPlaceholder" :aria-label="searchPlaceholder">
          </label>
          <TextMenu :model-value="sort" @update:model-value="sort = $event as Sort" :options="sortOptions" label="Sort" prefix="Sort" align="end" />
          <div class="view-switch" role="group" aria-label="View">
            <button type="button" :aria-pressed="displayMode === 'photos'" @click="displayMode = 'photos'">Photos</button>
            <button type="button" :aria-pressed="displayMode === 'list'" @click="displayMode = 'list'">List</button>
          </div>
        </div>
      </div>

      <p v-if="term && !loading" class="scope" role="status">
        <template v-if="alreadyEverything">
          <span><strong>{{ formatNumber(globalMatches) }}</strong> of {{ countLabel(catalogTotal, "style") }} match &ldquo;{{ term }}&rdquo;</span>
        </template>
        <template v-else>
          <span>Results for &ldquo;{{ term }}&rdquo; in</span>
          <span class="scope-switch label" role="group" aria-label="Where to search">
            <button type="button" :aria-pressed="!searchingEverything" @click="scope = 'local'">
              {{ viewLabel }}<span class="count">{{ formatNumber(localMatches) }}</span>
            </button>
            <button type="button" :aria-pressed="searchingEverything" @click="scope = 'global'">
              Whole catalog<span class="count">{{ formatNumber(globalMatches) }}</span>
            </button>
          </span>
        </template>
      </p>

      <div v-if="error && !catalogTotal" class="state">
        <p>{{ staticMode ? "The published catalog could not be loaded." : "The catalog could not be reached." }}</p>
        <p class="note">{{ staticMode ? "The data files are missing or unavailable." : "Start the Python API on port 8877, then try again." }}</p>
        <button class="outline-button label" type="button" @click="refresh()">Retry</button>
      </div>

      <div v-else-if="loading && !catalogTotal && displayMode === 'list'" class="list-loading" aria-busy="true" aria-label="Loading the catalog">
        <span v-for="index in 8" :key="index" class="block" />
      </div>

      <ol v-else-if="loading && !catalogTotal" class="grid" aria-busy="true" aria-label="Loading the catalog">
        <li v-for="index in 8" :key="index" class="item item-loading">
          <span class="photo" /><span class="block block-line short" /><span class="block block-line" /><span class="block block-line short" />
        </li>
      </ol>

      <div v-else-if="!results.length" class="state">
        <p>{{ term ? `Nothing ${searchingEverything || alreadyEverything ? "in the catalog" : viewLabel.toLowerCase()} matches “${term}”.` : "Nothing here matches those filters." }}</p>
        <button class="text-link" type="button" @click="resetFilters">Clear search and filters</button>
      </div>

      <template v-else>
        <ol v-if="displayMode === 'photos'" class="grid">
          <CatalogItem
            v-for="product in visibleResults"
            :key="productKey(product)"
            :product="product"
            :rank="rankOf(product)"
            @open="openProduct"
          />
        </ol>
        <RankingList v-else :products="visibleResults" :rank-of="rankOf" :sort="sort" @open="openProduct" @sort="sort = $event" />
        <ResultPagination
          v-model:page="currentPage"
          v-model:page-size="pageSize"
          :page-count="pageCount"
          :from="pageStart + 1"
          :to="pageEnd"
          :total="results.length"
        />
        <p v-if="data?.hasMore" class="note">The catalog was cut off at 5,000 styles, so this is not the full assortment.</p>
        <p v-if="error" class="note">The latest refresh failed, so this is the last catalog that loaded. <button class="text-link" type="button" @click="refresh()">Retry</button></p>
      </template>

      <footer class="colophon">
        <div>
          <h2 class="label">The source</h2>
          <p>United States catalog, in US dollars. Costs are the breakdowns Quince publishes on its own product pages.</p>
        </div>
        <div>
          <h2 class="label">What a style is</h2>
          <p>One product at one price. Colours and sizes that share a price are counted together; when they disagree, the range is shown.</p>
        </div>
        <div>
          <h2 class="label">What this is not</h2>
          <p>A difference against disclosed cost, not Quince&rsquo;s profit or loss. Marketing, returns and overhead are not in it. <NuxtLink to="/method">How this works</NuxtLink></p>
        </div>
        <p class="colophon-fee"><FeeFlag /> Quince&rsquo;s page listed fees larger than the rest of its own breakdown; those fees are left out of the cost shown.</p>
      </footer>
    </main>

    <ProductSheet
      :selected-product="sheet.selectedProduct.value"
      :selected-group="sheet.selectedGroup.value"
      :detail="sheet.detail.value"
      :pending="sheet.pending.value"
      :error="sheet.error.value"
      @close="sheet.close"
      @variant="sheet.loadVariant"
      @retry="retrySheet"
    />
  </div>
</template>
