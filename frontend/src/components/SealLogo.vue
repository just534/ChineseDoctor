<template>
  <span class="seal seal-logo" :style="{ width: size + 'px', height: size + 'px', fontSize: size * 0.42 + 'px' }">
    <span class="grid"><i>倪</i><i>師</i><i>經</i><i>方</i></span>
  </span>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ size?: number }>(), { size: 44 })
</script>

<style scoped lang="scss">
.seal-logo {
  transform: rotate(-4deg);
  flex-shrink: 0;
  .grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-auto-flow: column;
    grid-template-rows: 1fr 1fr;
    direction: rtl;
    gap: 0;
    line-height: 1;
    i { font-style: normal; font-size: 0.5em; padding: 1px; }
  }
}
</style>
