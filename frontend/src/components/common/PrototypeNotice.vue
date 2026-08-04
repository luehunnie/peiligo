<script setup lang="ts">
withDefaults(
  defineProps<{
    title?: string
    message: string
  }>(),
  {
    title: '原型说明',
  },
)
</script>

<template>
  <aside class="prototype-notice">
    <p class="prototype-notice__title">{{ title }}</p>
    <p class="prototype-notice__message">{{ message }}</p>
  </aside>
</template>

<style scoped>
.prototype-notice {
  padding: var(--space-sm) var(--space-md);
  background: var(--notice-bg);
  border: 1px solid var(--notice-border);
  border-radius: var(--radius-sm);
  color: var(--notice-text);
}

.prototype-notice__title {
  font-weight: 600;
  font-size: var(--font-size-sm);
}

.prototype-notice__message {
  margin-top: var(--space-xs);
  font-size: var(--font-size-sm);
  line-height: var(--line-height-base);
}
</style>
