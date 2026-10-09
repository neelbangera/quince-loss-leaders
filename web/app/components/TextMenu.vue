<script setup lang="ts">
// A label-text trigger that opens a ruled list of choices, drawn in the page's
// own type instead of the operating system's dropdown.
export interface MenuOption {
  value: string;
  label: string;
  count?: number;
}

const props = withDefaults(defineProps<{
  options: MenuOption[];
  modelValue: string;
  label: string;
  prefix?: string;
  placeholder?: string;
  align?: "start" | "end";
  direction?: "down" | "up";
  hover?: boolean;
}>(), { prefix: "", placeholder: "", align: "start", direction: "down", hover: false });

const emit = defineEmits<{ "update:modelValue": [value: string] }>();

const root = ref<HTMLElement | null>(null);
const trigger = ref<HTMLButtonElement | null>(null);
const list = ref<HTMLElement | null>(null);
const open = ref(false);
const shift = ref(0);

const current = computed(() => props.options.find((option) => option.value === props.modelValue));
const triggerText = computed(() => (props.placeholder && !props.modelValue ? props.placeholder : current.value?.label ?? props.placeholder));

function items() {
  return Array.from(list.value?.querySelectorAll<HTMLButtonElement>("button") ?? []);
}

async function show(focus: "current" | "last" | "none" = "current") {
  shift.value = 0;
  open.value = true;
  await nextTick();
  // Keep the list inside the page when its trigger sits near an edge.
  const box = list.value?.getBoundingClientRect();
  if (box) {
    const edge = 16;
    const width = document.documentElement.clientWidth;
    if (box.right > width - edge) shift.value = width - edge - box.right;
    else if (box.left < edge) shift.value = edge - box.left;
  }
  if (focus === "none") return;
  const all = items();
  const chosen = all.find((item) => item.getAttribute("aria-checked") === "true");
  (focus === "last" ? all[all.length - 1] : chosen ?? all[0])?.focus();
}

function hide(returnFocus = false) {
  clearTimeout(leaveTimer);
  if (!open.value) return;
  open.value = false;
  if (returnFocus) trigger.value?.focus();
}

function pick(value: string) {
  emit("update:modelValue", value);
  hide(true);
}

function onTriggerKey(event: KeyboardEvent) {
  if (event.key === "ArrowDown" || event.key === "ArrowUp") {
    event.preventDefault();
    show(event.key === "ArrowUp" ? "last" : "current");
  }
}

function onListKey(event: KeyboardEvent) {
  const all = items();
  const index = all.indexOf(document.activeElement as HTMLButtonElement);
  let next = -1;
  if (event.key === "ArrowDown") next = (index + 1) % all.length;
  else if (event.key === "ArrowUp") next = (index - 1 + all.length) % all.length;
  else if (event.key === "Home") next = 0;
  else if (event.key === "End") next = all.length - 1;
  else if (event.key === "Escape") {
    event.preventDefault();
    event.stopPropagation();
    hide(true);
    return;
  } else if (event.key === "Tab") {
    hide();
    return;
  } else return;
  event.preventDefault();
  all[next]?.focus();
}

// With `hover`, the menu opens under the pointer and closes shortly after it
// leaves, the way the department panels beside it do.
let leaveTimer: ReturnType<typeof setTimeout> | undefined;
function onEnter(event: PointerEvent) {
  if (!props.hover || event.pointerType !== "mouse") return;
  clearTimeout(leaveTimer);
  if (!open.value) void show("none");
}
function onLeave(event: PointerEvent) {
  if (!props.hover || event.pointerType !== "mouse") return;
  clearTimeout(leaveTimer);
  leaveTimer = setTimeout(() => hide(), 180);
}
defineExpose({ hide });

function onOutside(event: PointerEvent) {
  if (open.value && !root.value?.contains(event.target as Node)) hide();
}

onMounted(() => document.addEventListener("pointerdown", onOutside));
onBeforeUnmount(() => {
  clearTimeout(leaveTimer);
  document.removeEventListener("pointerdown", onOutside);
});
</script>

<template>
  <div ref="root" class="text-menu" @pointerenter="onEnter" @pointerleave="onLeave" :class="[`align-${align}`, `opens-${direction}`, { open, chosen: !placeholder || modelValue }]">
    <span v-if="prefix" class="text-menu-prefix" aria-hidden="true">{{ prefix }}</span>
    <button
      ref="trigger"
      type="button"
      class="text-menu-trigger"
      aria-haspopup="menu"
      :aria-expanded="open"
      :aria-label="`${label}: ${triggerText}`"
      @click="open ? hide() : show()"
      @keydown="onTriggerKey"
    >
      {{ triggerText }}
    </button>
    <div v-if="open" ref="list" class="text-menu-list" :style="{ '--menu-shift': `${shift}px` }" role="menu" :aria-label="label" @keydown="onListKey">
      <button
        v-for="option in options"
        :key="option.value"
        type="button"
        role="menuitemradio"
        :aria-checked="option.value === modelValue"
        @click="pick(option.value)"
      >
        <span>{{ option.label }}</span>
        <span v-if="option.count !== undefined" class="count">{{ formatNumber(option.count) }}</span>
      </button>
    </div>
  </div>
</template>
