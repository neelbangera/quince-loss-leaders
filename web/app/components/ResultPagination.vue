<script setup lang="ts">
import type { PageSize } from "~/types/ranking";

defineProps<{
  page: number;
  pageCount: number;
  pageSize: PageSize;
  from: number;
  to: number;
  total: number;
}>();
const PAGE_SIZES = [
  { value: "24", label: "24" },
  { value: "96", label: "96" },
  { value: "all", label: "All" },
];
const emit =defineEmits<{ "update:page": [page: number]; "update:pageSize": [size: PageSize] }>();
</script>

<template>
  <nav class="pagination label" aria-label="Pages of results">
    <span class="pagination-range">Showing {{ formatNumber(from) }}–{{ formatNumber(to) }} of {{ countLabel(total, "style") }}</span>
    <span v-if="pageCount > 1" class="pagination-steps">
      <button type="button" :disabled="page === 1" @click="emit('update:page', page - 1)">Previous</button>
      <span>Page {{ formatNumber(page) }} of {{ formatNumber(pageCount) }}</span>
      <button type="button" :disabled="page === pageCount" @click="emit('update:page', page + 1)">Next</button>
    </span>
    <TextMenu
      :model-value="pageSize"
      :options="PAGE_SIZES"
      label="Styles per page"
      prefix="Show"
      align="end"
      direction="up"
      @update:model-value="emit('update:pageSize', $event as PageSize)"
    />
  </nav>
</template>
