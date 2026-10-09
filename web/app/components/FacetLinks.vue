<script setup lang="ts">
import type { Facet } from "~/types/ranking";

// A row of text filters. The first `limit` choices are shown as words; the
// rest sit behind a "More" menu so a long taxonomy never wraps the toolbar.
const props = withDefaults(defineProps<{
  items: Facet[];
  active: string;
  label: string;
  limit?: number;
  allLabel?: string;
  allCount?: number;
  showCounts?: boolean;
  panels?: boolean;
}>(), { limit: 6, allLabel: "", allCount: 0, showCounts: true, panels: false });

// `peek` reports the choice under the pointer or keyboard focus ("" when it
// leaves for the More menu) and `descend` a Down-arrow press, so a parent can
// show and enter a panel for that choice.
const emit = defineEmits<{ select: [value: string]; peek: [value: string]; descend: [value: string] }>();

function onDown(event: KeyboardEvent, value: string) {
  if (!props.panels) return;
  event.preventDefault();
  emit("descend", value);
}
// One thing open at a time: moving to a plain choice closes the More menu.
const menu = ref<{ hide: () => void } | null>(null);
function peekAt(value: string) {
  if (value) menu.value?.hide();
  emit("peek", value);
}
function onPointer(event: PointerEvent, value: string) {
  if (event.pointerType === "mouse") peekAt(value);
}

const head = computed(() => props.items.slice(0, props.limit));
const tail = computed(() => props.items.slice(props.limit));
const tailActive = computed(() => (tail.value.some((item) => item.value === props.active) ? props.active : ""));
const tailOptions = computed(() => tail.value.map((item) => ({
  value: item.value,
  label: item.label,
  count: props.showCounts ? item.count : undefined,
})));

// Choosing the active filter again clears it.
function choose(value: string) {
  emit("select", value === props.active ? "" : value);
}
</script>

<template>
  <div class="facet-links label" role="group" :aria-label="label">
    <button v-if="allLabel" type="button" :aria-pressed="!active" @click="emit('select', '')">
      {{ allLabel }}<span v-if="showCounts" class="count">{{ formatNumber(allCount) }}</span>
    </button>
    <button
      v-for="item in head"
      :key="item.value"
      type="button"
      :aria-pressed="active === item.value"
      :data-facet="item.value"
      @click="choose(item.value)"
      @pointerenter="onPointer($event, item.value)"
      @focus="peekAt(item.value)"
      @keydown.down="onDown($event, item.value)"
    >
      {{ item.label }}<span v-if="showCounts" class="count">{{ formatNumber(item.count) }}</span>
    </button>
    <TextMenu
      v-if="tail.length"
      ref="menu"
      :hover="panels"
      :options="tailOptions"
      :model-value="tailActive"
      :label="`More ${label.toLowerCase()}`"
      placeholder="More"
      @pointerenter="onPointer($event, '')"
      @focusin="emit('peek', '')"
      @update:model-value="choose"
    />
  </div>
</template>
