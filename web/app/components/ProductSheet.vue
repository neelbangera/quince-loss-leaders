<script setup lang="ts">
import type { ProductDetail, ProductResult } from "~/types/ranking";

const props = defineProps<{
  selectedProduct: ProductResult | null;
  selectedGroup: ProductResult | null;
  detail: ProductDetail | null;
  pending: boolean;
  error: string;
}>();
const emit = defineEmits<{ close: []; variant: [variant: ProductResult]; retry: [] }>();

const sheet = ref<HTMLElement | null>(null);
const isOpen = computed(() => Boolean(props.selectedProduct));
useDialogFocus(sheet, isOpen, () => emit("close"));

const { markFailed, usable } = useFailedImages();

const RECENT_CHECKS = 10;

const product = computed(() => props.detail?.product ?? null);
const currency = computed(() => normalizeCurrency(product.value?.currency));
const money = (value: string | number | null | undefined) => formatMoney(value, currency.value);

const images = computed(() => {
  const source = product.value;
  if (!source) return [];
  const candidates = source.imageUrls?.length ? source.imageUrls : source.imageUrl ? [source.imageUrl] : [];
  return candidates.filter((url) => usable(url)).slice(0, 3);
});

// Two bars on one scale: the cost bar is as long as the reported cost, the
// price bar as long as the price, and whichever is larger spans the width.
const tally = computed(() => {
  const price = numericValue(props.detail?.current.sellingPrice);
  const cost = numericValue(props.detail?.current.reportedTotalCost);
  if (price === null || cost === null || price <= 0 || cost <= 0) return null;
  const scale = Math.max(price, cost);
  const gap = price - cost;
  return {
    price,
    cost,
    gap,
    costWidth: `${((cost / scale) * 100).toFixed(2)}%`,
    paidWidth: `${((price / scale) * 100).toFixed(2)}%`,
    verdict: gap < 0 ? "Sold below its reported cost by" : gap > 0 ? "Sold above its reported cost by" : "Sold at its reported cost",
  };
});

const families = computed(() => groupCostLines(props.detail?.current.costLines ?? []));
const linesTotal = computed(() => families.value.reduce((sum, family) => sum + family.total, 0));
const segments = computed(() => families.value.flatMap((family) => family.lines).filter((line) => line.value > 0));

const changeLog = computed(() => buildChangeLog(props.detail?.history ?? [], currency.value));
const updates = computed(() => changeLog.value.filter((event) => event.kind === "update"));
const chart = computed(() => buildHistoryChart(props.detail?.history ?? [], currency.value));
const checkCount = computed(() => props.detail?.history.length ?? 0);
const allChecks = ref(false);
const listedChecks = computed(() => {
  const newestFirst = [...(props.detail?.history ?? [])].reverse();
  return allChecks.value ? newestFirst : newestFirst.slice(0, RECENT_CHECKS);
});
watch(() => props.selectedProduct, () => {
  allChecks.value = false;
});

const movementSentence = computed(() => {
  if (checkCount.value < 2) return "Too early to say whether anything moves.";
  return updates.value.length
    ? `The price or a cost line moved on ${countLabel(updates.value.length, "check")}.`
    : "Nothing has moved between checks.";
});
</script>

<template>
  <div v-if="selectedProduct" class="backdrop" @click.self="emit('close')">
    <aside ref="sheet" class="sheet" role="dialog" aria-modal="true" aria-labelledby="sheet-title">
      <button class="sheet-close label" type="button" @click="emit('close')">Close</button>

      <template v-if="error || !detail || !product">
        <h2 id="sheet-title" class="sheet-title sheet-title-early">{{ selectedProduct.name }}</h2>
        <div v-if="error" class="state">
          <p>{{ error }}</p>
          <button class="outline-button label" type="button" @click="emit('retry')">Retry</button>
        </div>
        <div v-else class="sheet-loading" aria-busy="true">
          <span class="sr-only">Loading the cost breakdown and history</span>
          <span class="block block-photos" /><span class="block block-line" /><span class="block block-bar" /><span class="block block-line short" />
        </div>
      </template>

      <div v-else class="sheet-body" :class="{ 'sheet-busy': pending }" :aria-busy="pending">
        <div v-if="images.length" class="sheet-photos">
          <img
            v-for="(url, index) in images"
            :key="url"
            :src="photoUrl(url, 520) || undefined"
            :alt="index === 0 ? product.name : ''"
            loading="lazy"
            decoding="async"
            @error="markFailed(url)"
          >
        </div>
        <p class="sheet-where label">{{ product.departmentLabel }} · {{ product.categoryLabel }}</p>
        <h2 id="sheet-title" class="sheet-title">
          <a v-if="product.url" class="sheet-title-link" :href="product.url" target="_blank" rel="noreferrer" title="See it on Quince">{{ product.name }}</a>
          <template v-else>{{ product.name }}</template><FeeFlag v-if="product.hasExorbitantFees" />
        </h2>
        <p class="sheet-variant">{{ variantLine(product) || "Quince" }}</p>

        <div v-if="selectedGroup?.variants?.length" class="options">
          <p class="label options-label">{{ countLabel(selectedGroup.variants.length, "option") }} at this price</p>
          <div class="options-list" role="group" aria-label="Options at this price">
            <button
              v-for="variant in selectedGroup.variants"
              :key="productKey(variant)"
              type="button"
              class="option"
              :aria-pressed="sameVariant(product, variant)"
              @click="emit('variant', variant)"
            >
              {{ variantOptionLabel(variant) }}
            </button>
          </div>
          <p v-if="selectedGroup.metricsMixed" class="note">
            Quince reports different costs for these options, so each one keeps its own breakdown and history.
          </p>
        </div>

        <section>
          <h3>What Quince says it costs</h3>
          <template v-if="tally">
            <div
              class="twobars"
              role="img"
              :aria-label="`Reported cost ${money(tally.cost)}, price ${money(tally.price)}. ${tally.verdict}${tally.gap === 0 ? '' : ` ${money(Math.abs(tally.gap))}`}.`"
            >
              <p class="twobars-name"><span class="label">Costs Quince</span><b class="fig">{{ money(tally.cost) }}</b></p>
              <div class="twobars-track">
                <div class="twobars-cost" :style="{ width: tally.costWidth }">
                  <span v-for="line in segments" :key="line.key" class="tone" :class="`tone-${line.tone}`" :style="{ flex: `${line.value} 0 0` }">
                    <span><b>{{ line.label }}</b>{{ money(line.amount) }}</span>
                  </span>
                </div>
              </div>
              <p class="twobars-name"><span class="label">Quince sells it for</span><b class="fig">{{ money(tally.price) }}</b></p>
              <div class="twobars-track"><span class="twobars-price" :style="{ width: tally.paidWidth }" /></div>
            </div>
            <p class="verdict" :class="{ below: tally.gap < 0 }">
              <span>{{ tally.verdict }}</span><span v-if="tally.gap !== 0" class="fig">{{ money(Math.abs(tally.gap)) }}</span>
            </p>
          </template>
          <div v-if="families.length" class="costkey">
            <div v-for="family in families" :key="family.key">
              <p class="label costkey-head">
                <span>{{ family.name }}</span>
                <span class="fig">{{ money(family.total) }}<template v-if="linesTotal > 0"> · {{ costShare(family.total, linesTotal) }}</template></span>
              </p>
              <ul>
                <li v-for="line in family.lines" :key="line.key">
                  <i class="tone" :class="`tone-${line.tone}`" /><span>{{ line.label }}</span>
                  <span class="costkey-share fig">{{ costShare(line.value, linesTotal) }}</span>
                  <span class="costkey-amount fig">{{ money(line.amount) }}</span>
                </li>
              </ul>
            </div>
          </div>
          <p v-else class="note">Quince&rsquo;s page did not list individual cost lines at the last check.</p>
          <p v-if="product.hasExorbitantFees" class="note">
            <FeeFlag /> Quince&rsquo;s page listed duties, taxes and fees larger than the rest of its own breakdown. They are counted as {{ money(0) }} here, and the listed amount is kept on record.
          </p>
        </section>

        <section v-if="updates.length">
          <h3>What changed</h3>
          <p class="lede">Moves between one check and the next, with the amount on either side.</p>
          <ol class="ledger">
            <li v-for="(event, eventIndex) in updates" :key="`${event.capturedAt}-${eventIndex}`">
              <time class="label" :datetime="event.capturedAt">{{ formatDate(event.capturedAt) }}</time>
              <ul>
                <li v-for="(move, moveIndex) in event.moves" :key="`${move.label}-${moveIndex}`" :class="{ 'ledger-sum': move.summary }">
                  <span>{{ move.label }}</span>
                  <span class="fig quiet">
                    <template v-if="move.from && move.to">{{ move.from }} to {{ move.to }}</template>
                    <template v-else-if="move.direction === 'added'">New line at {{ move.to }}</template>
                    <template v-else-if="move.direction === 'removed'">Dropped after {{ move.from }}</template>
                    <template v-else>{{ move.to ?? move.from ?? "—" }}</template>
                  </span>
                  <span class="fig ledger-delta">
                    <template v-if="move.delta">{{ move.delta }}</template>
                    <template v-else-if="move.direction === 'added'">added</template>
                    <template v-else-if="move.direction === 'removed'">removed</template>
                  </span>
                </li>
              </ul>
            </li>
          </ol>
        </section>

        <section>
          <h3>Since we started looking</h3>
          <p class="lede">
            {{ countLabel(checkCount, "check") }}, the latest on <time :datetime="detail.analytics.lastObservedAt">{{ formatDate(detail.analytics.lastObservedAt) }}</time>. {{ movementSentence }}
          </p>
          <figure v-if="chart.points.length > 1" class="chart">
            <figcaption class="chart-key">
              <span><i class="key-price" />Price</span>
              <span><i class="key-cost" />Reported cost</span>
            </figcaption>
            <svg :viewBox="`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`" role="img" :aria-label="`Price and reported cost over time for ${product.name}`">
              <g v-for="line in chart.gridLines" :key="line.y">
                <line class="chart-grid" :x1="CHART_LEFT" :y1="line.y" :x2="CHART_WIDTH - CHART_RIGHT" :y2="line.y" />
                <text class="chart-text" x="0" :y="line.y + 4">{{ line.label }}</text>
              </g>
              <path v-if="chart.costPath" class="chart-line chart-cost" :d="chart.costPath" />
              <path v-if="chart.pricePath" class="chart-line chart-price" :d="chart.pricePath" />
              <template v-for="(point, index) in chart.points" :key="`${point.capturedAt}-${index}`">
                <circle v-if="point.costY !== null" class="chart-dot chart-cost" :cx="point.x" :cy="point.costY" r="3" />
                <circle v-if="point.priceY !== null" class="chart-dot chart-price" :cx="point.x" :cy="point.priceY" r="3" />
              </template>
              <text
                v-for="(axisLabel, index) in chart.axisLabels"
                :key="`axis-${index}`"
                class="chart-text"
                :x="axisLabel.x"
                :y="CHART_HEIGHT - 8"
                :text-anchor="axisLabel.anchor"
              >{{ axisLabel.label }}</text>
            </svg>
          </figure>
          <table class="checks">
            <thead>
              <tr class="label"><th scope="col">Checked</th><th scope="col" class="num">Price</th><th scope="col" class="num">Reported cost</th><th scope="col" class="num">Difference</th></tr>
            </thead>
            <tbody>
              <tr v-for="(point, index) in listedChecks" :key="`${point.capturedAt}-${index}`">
                <td><time :datetime="point.capturedAt">{{ formatDate(point.capturedAt) }}</time></td>
                <td class="num fig">{{ money(point.sellingPrice) }}</td>
                <td class="num fig quiet">{{ money(point.reportedTotalCost) }}</td>
                <td class="num fig" :class="{ below: (numericValue(point.unitSpread) ?? 0) < 0 }">{{ formatSignedMoney(point.unitSpread, currency) }}</td>
              </tr>
            </tbody>
          </table>
          <p v-if="checkCount > RECENT_CHECKS" class="note">
            {{ allChecks ? `All ${countLabel(checkCount, "check")} are listed.` : `The latest ${RECENT_CHECKS} of ${countLabel(checkCount, "check")} are listed.` }}
            <button class="text-link" type="button" :aria-expanded="allChecks" @click="allChecks = !allChecks">{{ allChecks ? "Show fewer" : "Show all" }}</button>
          </p>
          <dl class="observed">
            <div><dt class="label">Lowest price seen</dt><dd class="fig">{{ money(detail.analytics.lowestPrice) }}</dd></div>
            <div><dt class="label">Highest price seen</dt><dd class="fig">{{ money(detail.analytics.highestPrice) }}</dd></div>
            <div><dt class="label">Highest reported cost</dt><dd class="fig">{{ money(detail.analytics.highestCost) }}</dd></div>
            <div><dt class="label">Checks below cost</dt><dd class="fig">{{ formatNumber(detail.analytics.lossObservations) }} of {{ formatNumber(detail.analytics.observationCount) }}</dd></div>
          </dl>
        </section>

        <a v-if="product.url" class="outline-button label" :href="product.url" target="_blank" rel="noreferrer">See it on Quince</a>
        <p class="note">
          This compares the listed price with the cost breakdown Quince publishes for this item. It says nothing about Quince&rsquo;s profit overall.
        </p>
      </div>
    </aside>
  </div>
</template>
