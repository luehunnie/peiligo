<script setup lang="ts">
import { computed } from 'vue'
import type { ContentType } from '../../types/content'
import { CONTENT_TYPE_OPTIONS } from '../../constants/content-types'

const props = defineProps<{
  contentType: ContentType
  publishedAt: string
}>()

// 板块标签查找表：由集中配置驱动，供卡片与详情页共用
const boardLabels = new Map<ContentType, string>(
  CONTENT_TYPE_OPTIONS.map((option): [ContentType, string] => [
    option.value,
    option.label,
  ]),
)

const boardLabel = computed(
  () => boardLabels.get(props.contentType) ?? props.contentType,
)

// ISO 日期格式化为简洁中文日期；解析失败时回退原值
const formatDate = (iso: string): string => {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`
}
</script>

<template>
  <span class="content-meta__board">{{ boardLabel }}</span>
  <time :datetime="publishedAt" class="content-meta__date">
    {{ formatDate(publishedAt) }}
  </time>
</template>

<style scoped>
.content-meta__board {
  padding: 2px var(--space-sm);
  font-size: var(--font-size-sm);
  color: var(--brand-color);
  background: var(--brand-bg-soft);
  border-radius: var(--radius-sm);
}

.content-meta__date {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}
</style>
