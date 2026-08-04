<script setup lang="ts">
import { computed } from 'vue'
import type { ContentItem, ContentType } from '../../types/content'
import { CONTENT_TYPE_OPTIONS } from '../../constants/content-types'

const props = defineProps<{ item: ContentItem }>()

// 板块标签查找表：由集中配置驱动
const boardLabels = new Map<ContentType, string>(
  CONTENT_TYPE_OPTIONS.map((option): [ContentType, string] => [
    option.value,
    option.label,
  ]),
)

const boardLabel = computed(
  () => boardLabels.get(props.item.contentType) ?? props.item.contentType,
)

// ISO 日期格式化为简洁中文日期；解析失败时回退原值
const formatDate = (iso: string): string => {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`
}
</script>

<template>
  <article class="content-card">
    <header class="content-card__meta">
      <span class="content-card__board">{{ boardLabel }}</span>
      <time :datetime="item.publishedAt" class="content-card__date">
        {{ formatDate(item.publishedAt) }}
      </time>
    </header>
    <h2 class="content-card__title">{{ item.title }}</h2>
    <p class="content-card__summary">{{ item.summary }}</p>
    <p v-if="item.sourceName" class="content-card__source">
      来源：{{ item.sourceName }}
    </p>
  </article>
</template>

<style scoped>
.content-card {
  height: 100%;
  padding: var(--space-lg);
  background: var(--content-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  box-shadow: var(--shadow-subtle);
}

.content-card__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-sm);
}

.content-card__board {
  padding: 2px var(--space-sm);
  font-size: var(--font-size-sm);
  color: var(--brand-color);
  background: var(--brand-bg-soft);
  border-radius: var(--radius-sm);
}

.content-card__date {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.content-card__title {
  margin-top: var(--space-sm);
  font-size: var(--font-size-lg);
  font-weight: 600;
  line-height: var(--line-height-tight);
}

.content-card__summary {
  margin-top: var(--space-xs);
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.content-card__source {
  margin-top: var(--space-sm);
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}
</style>
