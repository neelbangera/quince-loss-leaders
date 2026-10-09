<script setup lang="ts">
// Resolve the theme before first paint so a saved or system night theme never flashes white.
useHead({
  htmlAttrs: { lang: "en" },
  script: [
    {
      key: "theme-init",
      tagPosition: "head",
      innerHTML:
        "(function(){try{var t=localStorage.getItem('quince-ledger-theme');if(t!=='light'&&t!=='dark'){t=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'}document.documentElement.dataset.theme=t}catch(e){document.documentElement.dataset.theme='light'}})()",
    },
  ],
});
</script>

<template>
  <NuxtPage />
</template>
