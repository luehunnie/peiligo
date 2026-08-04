<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ keyword: string }>()

// 根据是否有关键词给出不同的空状态提示
const hint = computed(() =>
  props.keyword
    ? `没有找到与"${props.keyword}"匹配的内容，请尝试更换关键词或清除筛选条件。`
    : '当前筛选条件下暂无内容，请尝试清除筛选条件。',
)
</script>

<template>
  <div class="empty-state">
    <p class="empty-state__title">暂无内容</p>
    <p class="empty-state__hint">{{ hint }}</p>
  </div>
</template>

<style scoped>
.empty-state {
  margin-top: var(--space-xl);
  padding: var(--space-2xl) var(--space-lg);
  text-align: center;
  background: var(--content-bg);
  border: 1px dashed var(--border-color);
  border-radius: var(--radius);
}

.empty-state__title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--text-primary);
}

.empty-state__hint {
  margin-top: var(--space-xs);
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}
</style>
