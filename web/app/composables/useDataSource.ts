const REQUEST_TIMEOUT_MS = 15_000;

// Where the dashboard reads from: the local Python API, or generated static
// JSON when NUXT_PUBLIC_STATIC_DATA_BASE is set (the deployed site).
export function useDataSource() {
  const config = useRuntimeConfig();
  const apiBase = String(config.public.apiBase || "http://127.0.0.1:8877").replace(/\/$/, "");
  const staticDataBase = String(config.public.staticDataBase || "").replace(/\/$/, "");
  const staticMode = Boolean(staticDataBase);

  async function fetchJson<T>(url: string, query?: Record<string, string>): Promise<T> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    try {
      return query
        ? await $fetch<T>(url, { query, signal: controller.signal })
        : await $fetch<T>(url, { signal: controller.signal });
    } finally {
      clearTimeout(timeout);
    }
  }

  return { apiBase, staticDataBase, staticMode, fetchJson };
}
