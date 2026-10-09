<script setup lang="ts">
import type { ProductResult, Sort, SortField } from "~/types/ranking";

const props = defineProps<{
  products: ProductResult[];
  rankOf: (product: ProductResult) => number | null;
  sort: Sort;
}>();
const emit = defineEmits<{
  open: [event: MouseEvent, product: ProductResult];
  sort: [sort: Sort];
}>();

const { markFailed, usable } = useFailedImages();

const columns: { field: SortField; label: string; numeric: boolean }[] = [
  { field: "name", label: "Style", numeric: false },
  { field: "department", label: "Department", numeric: false },
  { field: "price", label: "Price", numeric: true },
  { field: "cost", label: "Costs Quince", numeric: true },
  { field: "spread", label: "Difference", numeric: true },
  { field: "margin", label: "As % of price", numeric: true },
];

function direction(field: SortField) {
  const current = sortParts(props.sort);
  return current.field === field ? current.direction : null;
}

function ariaSort(field: SortField) {
  const current = direction(field);
  return current === "asc" ? "ascending" : current === "desc" ? "descending" : "none";
}

function toggle(field: SortField) {
  emit("sort", `${field}_${direction(field) === "asc" ? "desc" : "asc"}` as Sort);
}
</script>

<template>
  <div class="list-wrap">
    <table class="list">
      <thead>
        <tr class="label">
          <th scope="col">No.</th>
          <th scope="col"><span class="sr-only">Photograph</span></th>
          <th
            v-for="column in columns"
            :key="column.field"
            scope="col"
            :class="{ num: column.numeric }"
            :aria-sort="ariaSort(column.field)"
          >
            <button type="button" class="column-sort" :class="{ active: direction(column.field) }" @click="toggle(column.field)">
              {{ column.label }}
              <span class="sort-arrow" aria-hidden="true">{{ direction(column.field) === "asc" ? "↑" : direction(column.field) === "desc" ? "↓" : "" }}</span>
            </button>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="product in products" :key="productKey(product)">
          <td class="rank-cell fig">{{ rankOf(product) ?? "" }}</td>
          <td class="thumb-cell">
            <img
              v-if="usable(product.imageUrl)"
              class="thumb"
              :src="photoUrl(product.imageUrl, 160) || undefined"
              alt=""
              loading="lazy"
              decoding="async"
              @error="markFailed(product.imageUrl)"
            >
            <span v-else class="thumb" />
          </td>
          <td>
            <span class="name-row">
              <button class="name" type="button" @click="emit('open', $event, product)">{{ product.name }}</button>
              <FeeFlag v-if="product.hasExorbitantFees" />
            </span>
            <div class="variant">{{ variantLine(product) }}</div>
          </td>
          <td>{{ product.departmentLabel }} · {{ product.categoryLabel }}</td>
          <td class="num fig"><strong>{{ priceText(product) }}</strong></td>
          <td class="num fig quiet">{{ costText(product) }}</td>
          <td class="num fig" :class="{ below: isBelowCost(product) }">{{ differenceText(product) }}</td>
          <td class="num fig" :class="{ below: isBelowCost(product) }">{{ marginText(product) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
