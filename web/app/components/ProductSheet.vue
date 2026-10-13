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
// price bar as long as the price, and the largest figure drawn spans the width.
// When either has moved, a tick marks where it stood before the last change.
const before = computed(() => captureBeforeLastChange(props.detail?.history ?? []));
const tally = computed(() => {
  const price = numericValue(props.detail?.current.sellingPrice);
  const cost = numericValue(props.detail?.current.reportedTotalCost);
  if (price === null || cost === null || price <= 0 || cost <= 0) return null;
  const earlier = (value: number | null, current: number) => (value !== null && value > 0 && value !== current ? value : null);
  const wasPrice = earlier(numericValue(before.value?.sellingPrice), price);
  const wasCost = earlier(numericValue(before.value?.reportedTotalCost), cost);
  const scale = Math.max(price, cost, wasPrice ?? 0, wasCost ?? 0);
  const share = (value: number) => (value / scale) * 100;
  // The tick sits where the bar used to end; a dashed outline fills the length it has lost.
  const mark = (was: number | null, current: number) => {
    if (was === null) return null;
    const at = share(was);
    return {
      amount: was,
      tick: { left: `${at.toFixed(2)}%` },
      text: at > 60 ? { right: `${(100 - at).toFixed(2)}%` } : { left: `${at.toFixed(2)}%` },
      ghost: was > current ? { left: `${share(current).toFixed(2)}%`, width: `${(at - share(current)).toFixed(2)}%` } : null,
    };
  };
  const gap = price - cost;
  return {
    price,
    cost,
    gap,
    costWidth: `${share(cost).toFixed(2)}%`,
    paidWidth: `${share(price).toFixed(2)}%`,
    wasCost: mark(wasCost, cost),
    wasPrice: mark(wasPrice, price),
    verdict: gap < 0 ? "Sold below its reported cost by" : gap > 0 ? "Sold above its reported cost by" : "Sold at its reported cost",
  };
});
const tallyLabel = computed(() => {
  const now = tally.value;
  if (!now) return "";
  const parts = [`Reported cost ${money(now.cost)}, price ${money(now.price)}.`, `${now.verdict}${now.gap === 0 ? "" : ` ${money(Math.abs(now.gap))}`}.`];
  if (now.wasCost) parts.push(`The reported cost was ${money(now.wasCost.amount)} before the last change.`);
  if (now.wasPrice) parts.push(`The price was ${money(now.wasPrice.amount)} before the last change.`);
  return parts.join(" ");
});

const families = computed(() => groupCostLines(props.detail?.current.costLines ?? []));
const linesTotal = computed(() => families.value.reduce((sum, family) => sum + family.total, 0));
const segments = computed(() => families.value.flatMap((family) => family.lines).filter((line) => line.value > 0));

const changeLog = computed(() => buildChangeLog(props.detail?.history ?? [], currency.value));
// Newest first, so the move the ticks describe leads the list.
const updates = computed(() => changeLog.value.filter((event) => event.kind === "update").reverse());
const checkCount = computed(() => props.detail?.history.length ?? 0);
const everyCheck = computed(() => [...(props.detail?.history ?? [])].reverse());
const showChecks = ref(false);
watch(() => props.selectedProduct, () => {
  showChecks.value = false;
});

const times = (count: number) => (count === 1 ? "once" : count === 2 ? "twice" : `${formatNumber(count)} times`);
const sinceSentence = computed(() => {
  const analytics = props.detail?.analytics;
  if (!analytics || !checkCount.value) return "";
  if (checkCount.value < 2) return `Checked once, on ${formatDate(analytics.lastObservedAt)}. The price hasn’t moved.`;
  const lead = `Checked ${times(checkCount.value)} since ${formatDate(analytics.firstObservedAt)}.`;
  const latest = updates.value[0];
  if (!latest) return `${lead} Nothing has moved.`;
  return `${lead} Something moved ${times(updates.value.length)}, ${updates.value.length === 1 ? "on" : "last on"} ${formatDate(latest.capturedAt)}.`;
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
              :aria-label="tallyLabel"
            >
              <p class="twobars-name"><span class="label">Costs Quince</span><b class="fig">{{ money(tally.cost) }}</b></p>
              <div class="twobars-track">
                <div class="twobars-cost" :style="{ width: tally.costWidth }">
                  <span v-for="line in segments" :key="line.key" class="tone" :class="`tone-${line.tone}`" :style="{ flex: `${line.value} 0 0` }">
                    <span><b>{{ line.label }}</b>{{ money(line.amount) }}</span>
                  </span>
                </div>
                <i v-if="tally.wasCost?.ghost" class="twobars-ghost" :style="tally.wasCost.ghost" />
              </div>
              <p v-if="tally.wasCost" class="twobars-was">
                <i :style="tally.wasCost.tick" /><span class="fig" :style="tally.wasCost.text">was {{ money(tally.wasCost.amount) }}</span>
              </p>
              <p class="twobars-name"><span class="label">Quince sells it for</span><b class="fig">{{ money(tally.price) }}</b></p>
              <div class="twobars-track">
                <span class="twobars-price" :style="{ width: tally.paidWidth }" />
                <i v-if="tally.wasPrice?.ghost" class="twobars-ghost" :style="tally.wasPrice.ghost" />
              </div>
              <p v-if="tally.wasPrice" class="twobars-was">
                <i :style="tally.wasPrice.tick" /><span class="fig" :style="tally.wasPrice.text">was {{ money(tally.wasPrice.amount) }}</span>
              </p>
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

        <section>
          <h3 class="sr-only">Since we started looking</h3>
          <p class="since" :class="{ quiet: !updates.length }">{{ sinceSentence }}</p>
          <ol v-if="updates.length" class="ledger">
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
          <p v-if="checkCount > 1" class="note">
            <button class="text-link" type="button" :aria-expanded="showChecks" @click="showChecks = !showChecks">
              {{ showChecks ? "Hide the checks" : `Show all ${countLabel(checkCount, "check")}` }}
            </button>
          </p>
          <table v-if="showChecks" class="checks">
            <thead>
              <tr class="label"><th scope="col">Checked</th><th scope="col" class="num">Price</th><th scope="col" class="num">Reported cost</th><th scope="col" class="num">Difference</th></tr>
            </thead>
            <tbody>
              <tr v-for="(point, index) in everyCheck" :key="`${point.capturedAt}-${index}`">
                <td><time :datetime="point.capturedAt">{{ formatDate(point.capturedAt) }}</time></td>
                <td class="num fig">{{ money(point.sellingPrice) }}</td>
                <td class="num fig quiet">{{ money(point.reportedTotalCost) }}</td>
                <td class="num fig" :class="{ below: (numericValue(point.unitSpread) ?? 0) < 0 }">{{ formatSignedMoney(point.unitSpread, currency) }}</td>
              </tr>
            </tbody>
          </table>
        </section>

        <a v-if="product.url" class="outline-button label" :href="product.url" target="_blank" rel="noreferrer">See it on Quince</a>
        <p class="note">
          This compares the listed price with the cost breakdown Quince publishes for this item. It says nothing about Quince&rsquo;s profit overall.
        </p>
      </div>
    </aside>
  </div>
</template>
