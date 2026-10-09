<script setup lang="ts">
import type { ProductResult } from "~/types/ranking";

const props = defineProps<{ product: ProductResult; rank: number | null }>();
const emit = defineEmits<{ open: [event: MouseEvent, product: ProductResult] }>();

const { markFailed, usable } = useFailedImages();
const image = computed(() => usable(props.product.imageUrl));
</script>

<template>
  <li class="item">
    <button class="photo" type="button" tabindex="-1" aria-hidden="true" @click="emit('open', $event, product)">
      <img
        v-if="image"
        :src="photoUrl(image, 640) || undefined"
        alt=""
        loading="lazy"
        decoding="async"
        @error="markFailed(product.imageUrl)"
      >
      <span v-else class="photo-missing">No photograph</span>
    </button>
    <span class="rank label">{{ rank ? `No. ${formatNumber(rank)}` : product.departmentLabel }}</span>
    <span class="name-row">
      <button class="name" type="button" @click="emit('open', $event, product)">{{ product.name }}</button>
      <FeeFlag v-if="product.hasExorbitantFees" />
    </span>
    <p class="variant">{{ variantLine(product) }}</p>
    <div class="pricing">
      <p class="paid fig"><strong>{{ priceText(product) }}</strong><span>costs Quince {{ costText(product) }}</span></p>
      <p class="diff fig" :class="{ below: isBelowCost(product) }">{{ differenceText(product) }}</p>
    </div>
  </li>
</template>
