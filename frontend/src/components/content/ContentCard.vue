<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import type { ContentItem } from '../../types/content'
import ContentMeta from './ContentMeta.vue'

const props = defineProps<{ item: ContentItem }>()

const route = useRoute()

// 进入详情时携带当前列表的 q 与 type，供详情页"返回列表"复原筛选
const detailTo = computed(() => {
  const query: Record<string, string> = {}
  const q = route.query.q
  const type = route.query.type
  if (typeof q === 'string' && q) query.q = q
  if (typeof type === 'string' && type) query.type = type
  return { name: 'content-detail', params: { id: props.item.id }, query }
})
</script>

<template>
  <router-link :to="detailTo" class="content-card-link">
    <article class="content-card">
      <header class="content-card__meta">
        <ContentMeta
          :content-type="item.contentType"
          :published-at="item.publishedAt"
        />
      </header>
      <h2 class="content-card__title">{{ item.title }}</h2>
      <p class="content-card__summary">{{ item.summary }}</p>
      <p v-if="item.sourceName" class="content-card__source">
        来源：{{ item.sourceName }}
      </p>
    </article>
  </router-link>
</template>

<style scoped>
.content-card-link {
  display: flex;
  width: 100%;
  height: 100%;
  color: inherit;
  text-decoration: none;
}

.content-card {
  width: 100%;
  padding: var(--space-lg);
  background: var(--content-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  box-shadow: var(--shadow-subtle);
  transition: border-color 0.15s ease;
}

.content-card-link:hover .content-card {
  border-color: var(--brand-color);
}

.content-card__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-sm);
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
