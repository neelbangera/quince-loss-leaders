<script setup lang="ts">
type Theme = "system" | "light" | "dark";

const theme = ref<Theme>("system");

function applyTheme(nextTheme: Theme) {
  if (!import.meta.client) return;
  document.documentElement.dataset.theme = nextTheme;
  document.documentElement.style.colorScheme = nextTheme === "system" ? "light dark" : nextTheme;
  window.localStorage.setItem("quince-ledger-theme", nextTheme);
}

onMounted(() => {
  const savedTheme = window.localStorage.getItem("quince-ledger-theme");
  if (savedTheme === "system" || savedTheme === "light" || savedTheme === "dark") {
    theme.value = savedTheme;
  }
  applyTheme(theme.value);
});

watch(theme, applyTheme);
</script>

<template>
  <label class="theme-control" for="theme">
    <span>Theme</span>
    <select id="theme" v-model="theme" class="theme-select">
      <option value="system">System</option>
      <option value="light">Light</option>
      <option value="dark">Dark</option>
    </select>
  </label>
</template>
