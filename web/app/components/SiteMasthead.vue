<script setup lang="ts">
import type { Facet } from "~/types/ranking";

// The notice strip, the masthead and the shirting band. The catalog page
// passes its departments; other pages get a plain link back to the catalog.
// Pointing at a department, or focusing it, opens a panel of its categories.
const props = withDefaults(defineProps<{
  lastChecked?: string | null;
  departments?: Facet[];
  activeDepartment?: string;
  activeCategory?: string;
  categoriesByDepartment?: Record<string, Facet[]>;
  context?: string;
}>(), {
  lastChecked: null,
  departments: () => [],
  activeDepartment: "",
  activeCategory: "",
  categoriesByDepartment: () => ({}),
  context: "",
});

const emit = defineEmits<{ department: [value: string]; category: [department: string, category: string] }>();

const wrap = ref<HTMLElement | null>(null);
const panel = ref<HTMLElement | null>(null);
const peeked = ref("");
let timer: ReturnType<typeof setTimeout> | undefined;
let muted = false;

const shown = computed(() => props.departments.find((item) => item.value === peeked.value));
const shownCategories = computed(() => (shown.value ? props.categoriesByDepartment[shown.value.value] ?? [] : []));

// A short delay each way, so crossing the row does not flash panels and a
// diagonal move toward the panel does not close it.
function schedule(value: string, delay: number) {
  clearTimeout(timer);
  timer = setTimeout(() => {
    peeked.value = value;
  }, delay);
}
function hold() {
  clearTimeout(timer);
}
function peek(value: string) {
  if (muted) return;
  schedule(value, peeked.value ? 60 : 140);
}
function closeNow(returnFocus = false) {
  clearTimeout(timer);
  // Handing focus back must not reopen the panel it just closed.
  muted = true;
  if (returnFocus && peeked.value) wrap.value?.querySelector<HTMLElement>(`[data-facet="${CSS.escape(peeked.value)}"]`)?.focus();
  muted = false;
  peeked.value = "";
}
function onFocusOut(event: FocusEvent) {
  if (!wrap.value?.contains(event.relatedTarget as Node | null)) closeNow();
}
async function descend(value: string) {
  clearTimeout(timer);
  peeked.value = value;
  await nextTick();
  panel.value?.querySelector<HTMLElement>("button")?.focus();
}
function pickDepartment(value: string) {
  closeNow();
  emit("department", value);
}
function pickCategory(category: string) {
  const target = peeked.value;
  closeNow();
  if (category) emit("category", target, category);
  else if (target !== props.activeDepartment || props.activeCategory) emit("category", target, "");
}

onBeforeUnmount(() => clearTimeout(timer));
</script>

<template>
  <p class="notice">
    Every figure is Quince&rsquo;s own reported cost, read from its product pages.
    <template v-if="lastChecked">Last checked <time :datetime="lastChecked">{{ formatDate(lastChecked) }}</time>.</template>
    <NuxtLink to="/method">How this works</NuxtLink>
  </p>
  <div
    ref="wrap"
    class="mast-wrap"
    @pointerleave="schedule('', 180)"
    @pointerenter="hold"
    @focusout="onFocusOut"
    @keydown.esc="closeNow(true)"
  >
    <div class="page">
      <header class="masthead">
        <FacetLinks
          v-if="departments.length"
          class="mast-departments"
          :items="departments"
          :active="activeDepartment"
          :limit="4"
          :show-counts="false"
          label="Departments"
          panels
          @select="pickDepartment"
          @peek="peek"
          @descend="descend"
        />
        <nav v-else class="mast-departments label" aria-label="Sections">
          <NuxtLink class="mast-link" to="/">The catalog</NuxtLink>
        </nav>
        <NuxtLink class="wordmark" to="/" aria-label="Quince Ledger home" @pointerenter="peek('')">Quince Ledger</NuxtLink>
        <div class="mast-utility label" @pointerenter="peek('')">
          <NuxtLink class="mast-link" to="/method">Method</NuxtLink>
          <ThemeSelect />
        </div>
      </header>
    </div>
    <div class="shirting" aria-hidden="true" />
    <div v-if="shown && shownCategories.length" ref="panel" class="mast-panel" role="group" :aria-label="`${shown.label} categories`">
      <div class="page mast-panel-inner">
        <div class="mast-panel-lead">
          <p class="mast-panel-name">{{ shown.label }}</p>
          <p class="mast-panel-note">{{ countLabel(shown.count, "style") }} {{ context }}</p>
          <button type="button" class="label mast-panel-all" @click="pickCategory('')">All {{ shown.label }}</button>
        </div>
        <ul class="mast-panel-list label">
          <li v-for="item in shownCategories" :key="item.value">
            <button
              type="button"
              :aria-pressed="shown.value === activeDepartment && item.value === activeCategory"
              @click="pickCategory(item.value)"
            >
              <span>{{ item.label }}</span><span class="count">{{ formatNumber(item.count) }}</span>
            </button>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>
