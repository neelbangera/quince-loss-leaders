// Product photographs are hot-linked and can fail. A failed URL is remembered
// for the session so every place that shows it falls back to the empty well.
const failed = ref<Record<string, boolean>>({});

export function useFailedImages() {
  function markFailed(url: string | null | undefined) {
    if (url) failed.value = { ...failed.value, [url]: true };
  }
  function usable(url: string | null | undefined) {
    return url && !failed.value[url] ? url : null;
  }
  return { markFailed, usable };
}
