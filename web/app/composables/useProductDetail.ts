import type { ProductDetail, ProductResult } from "~/types/ranking";

// Loads one variant's detail and history. A response that arrives after a
// newer selection, or after the sheet closed, is discarded.
export function useProductDetail() {
  const { apiBase, staticDataBase, staticMode, fetchJson } = useDataSource();
  const selectedProduct = ref<ProductResult | null>(null);
  const selectedGroup = ref<ProductResult | null>(null);
  const detail = ref<ProductDetail | null>(null);
  const pending = ref(false);
  const error = ref("");
  let request = 0;

  async function loadVariant(product: ProductResult) {
    const current = ++request;
    selectedProduct.value = product;
    error.value = "";
    pending.value = true;
    try {
      let payload: ProductDetail;
      if (staticMode) {
        if (!product.historyPath) throw new Error("History file is not available.");
        payload = await fetchJson<ProductDetail>(`${staticDataBase}/${product.historyPath}`);
      } else {
        payload = await fetchJson<ProductDetail>(`${apiBase}/api/product`, {
          product_key: product.productKey,
          variant_key: product.variantKey,
        });
      }
      if (current !== request) return;
      detail.value = payload;
    } catch {
      if (current !== request) return;
      detail.value = null;
      error.value = "The history for this item could not be loaded.";
    } finally {
      if (current === request) pending.value = false;
    }
  }

  // A grouped row opens on its representative variant; every variant in the
  // group stays selectable and keeps its own history.
  async function open(product: ProductResult) {
    selectedGroup.value = (product.variants?.length ?? 0) > 1 ? product : null;
    detail.value = null;
    const initial = product.variants?.find((variant) => sameVariant(variant, product))
      || product.variants?.[0]
      || product;
    await loadVariant(initial);
  }

  function close() {
    request += 1;
    selectedProduct.value = null;
    selectedGroup.value = null;
    detail.value = null;
    error.value = "";
    pending.value = false;
  }

  return { selectedProduct, selectedGroup, detail, pending, error, open, loadVariant, close };
}
