<template>
  <svg :width="size" :height="size" viewBox="0 0 200 200" class="taiji" aria-hidden="true">
    <circle cx="100" cy="100" r="98" fill="#fbf7ee" stroke="currentColor" stroke-width="3" />
    <path d="M100 2a98 98 0 0 1 0 196a49 49 0 0 1 0-98a49 49 0 0 0 0-98z" fill="currentColor" />
    <circle cx="100" cy="51" r="14" fill="#fbf7ee" />
    <circle cx="100" cy="149" r="14" fill="currentColor" />
  </svg>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ size?: number }>(), { size: 120 })
</script>
