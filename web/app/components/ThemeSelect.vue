<script setup lang="ts">
type Theme = "light" | "dark";

const STORAGE_KEY = "quince-ledger-theme";
const theme = ref<Theme>("light");

function applyTheme(next: Theme) {
  document.documentElement.dataset.theme = next;
  document.documentElement.style.colorScheme = next;
}

// The head script in app.vue has already resolved the saved or system theme.
onMounted(() => {
  theme.value = document.documentElement.dataset.theme === "dark" ? "dark" : "light";
  applyTheme(theme.value);
});

function toggle() {
  theme.value = theme.value === "dark" ? "light" : "dark";
  applyTheme(theme.value);
  try {
    window.localStorage.setItem(STORAGE_KEY, theme.value);
  } catch {
    // Storage can be unavailable in private windows; the theme still applies for this visit.
  }
}
</script>

<template>
  <button class="mast-link" type="button" :aria-label="`Switch to the ${theme === 'dark' ? 'light' : 'dark'} theme`" @click="toggle">
    {{ theme === "dark" ? "Light" : "Dark" }}
  </button>
</template>
