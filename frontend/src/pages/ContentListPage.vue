<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { ContentItem, ContentType } from '../types/content'
import { CONTENT_TYPE_OPTIONS } from '../constants/content-types'
import { MOCK_CONTENTS } from '../data/mock-contents'
import ContentCard from '../components/content/ContentCard.vue'
import ContentEmptyState from '../components/content/ContentEmptyState.vue'

type BoardFilterValue = ContentType | 'all'

// 合法板块类型集合，用于校验查询参数中的 type
const VALID_TYPE_SET: Set<string> = new Set(
  CONTENT_TYPE_OPTIONS.map((option) => option.value),
)

const isContentType = (value: unknown): value is ContentType =>
  typeof value === 'string' && VALID_TYPE_SET.has(value)

// 板块筛选选项："全部" + 五个板块，由集中配置驱动
interface BoardFilterOption {
  value: BoardFilterValue
  label: string
}

const boardFilterOptions: readonly BoardFilterOption[] = [
  { value: 'all', label: '全部' },
  ...CONTENT_TYPE_OPTIONS.map((option): BoardFilterOption => ({
    value: option.value,
    label: option.label,
  })),
]

const route = useRoute()
const router = useRouter()

// 关键词输入草稿：路由变化时同步为已应用值
const keyword = ref('')
watch(
  () => route.query.q,
  (q) => {
    keyword.value = typeof q === 'string' ? q : ''
  },
  { immediate: true },
)

// 已应用的关键词：去除首尾空格
const currentKeyword = computed(() => {
  const q = route.query.q
  return typeof q === 'string' ? q.trim() : ''
})

// 已应用的板块筛选：非法值按"全部"处理
const currentType = computed<BoardFilterValue>(() => {
  const t = route.query.type
  return isContentType(t) ? t : 'all'
})

const hasFilters = computed(
  () => currentKeyword.value !== '' || currentType.value !== 'all',
)

// 关键词同时匹配标题、摘要和正文，大小写不敏感
const matchesKeyword = (item: ContentItem, kw: string): boolean => {
  const haystack = `${item.title} ${item.summary} ${item.body.join(' ')}`
  return haystack.toLowerCase().includes(kw.toLowerCase())
}

// 筛选结果：仅已发布、关键词 + 板块同时生效、按发布时间倒序
const filteredContents = computed(() => {
  const kw = currentKeyword.value
  const type = currentType.value

  let result = MOCK_CONTENTS.filter((item) => item.status === 'published')

  if (kw !== '') {
    result = result.filter((item) => matchesKeyword(item, kw))
  }

  if (type !== 'all') {
    result = result.filter((item) => item.contentType === type)
  }

  return result.sort((a, b) => b.publishedAt.localeCompare(a.publishedAt))
})

const buildQuery = (q: string, type: BoardFilterValue) => {
  const query: { q?: string; type?: ContentType } = {}
  if (q) query.q = q
  if (type !== 'all') query.type = type
  return query
}

const submitSearch = () => {
  router.push({
    name: 'contents',
    query: buildQuery(keyword.value.trim(), currentType.value),
  })
}

const selectBoard = (value: BoardFilterValue) => {
  router.push({
    name: 'contents',
    query: buildQuery(keyword.value.trim(), value),
  })
}

const clearFilters = () => {
  router.push({ name: 'contents' })
}
</script>

<template>
  <div class="content-list site-container">
    <h1 class="content-list__title">内容浏览</h1>

    <form class="search-form" @submit.prevent="submitSearch">
      <label for="content-search" class="search-form__label">关键词</label>
      <div class="search-form__controls">
        <input
          id="content-search"
          v-model="keyword"
          type="search"
          placeholder="搜索标题、摘要或正文"
        />
        <button type="submit" class="btn btn--primary">搜索</button>
      </div>
    </form>

    <div class="board-filter" role="group" aria-label="板块筛选">
      <button
        v-for="option in boardFilterOptions"
        :key="option.value"
        type="button"
        class="board-filter__chip"
        :class="{ 'is-active': currentType === option.value }"
        :aria-pressed="currentType === option.value"
        @click="selectBoard(option.value)"
      >
        {{ option.label }}
      </button>
    </div>

    <div class="result-bar">
      <p class="result-bar__count">共 {{ filteredContents.length }} 条结果</p>
      <button
        v-if="hasFilters"
        type="button"
        class="btn btn--ghost"
        @click="clearFilters"
      >
        清空条件
      </button>
    </div>

    <ul v-if="filteredContents.length > 0" class="content-grid">
      <li
        v-for="item in filteredContents"
        :key="item.id"
        class="content-grid__item"
      >
        <ContentCard :item="item" />
      </li>
    </ul>

    <ContentEmptyState v-else :keyword="currentKeyword" />
  </div>
</template>

<style scoped>
.content-list {
  padding-block: var(--space-lg) var(--space-2xl);
}

.search-form {
  margin-top: var(--space-lg);
}

.search-form__label {
  display: block;
  margin-bottom: var(--space-xs);
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.search-form__controls {
  display: flex;
  gap: var(--space-sm);
}

.board-filter {
  margin-top: var(--space-lg);
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-xs);
}

.board-filter__chip {
  padding: var(--space-xs) var(--space-md);
  font: inherit;
  font-size: var(--font-size-sm);
  color: var(--text-primary);
  background: var(--content-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: border-color 0.15s ease, color 0.15s ease;
}

.board-filter__chip:hover {
  border-color: var(--brand-color);
  color: var(--brand-color);
}

.board-filter__chip.is-active {
  color: #ffffff;
  background: var(--brand-color);
  border-color: var(--brand-color);
}

.result-bar {
  margin-top: var(--space-lg);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
}

.result-bar__count {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.content-grid {
  margin-top: var(--space-lg);
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--space-md);
}

.content-grid__item {
  display: flex;
}

@media (max-width: 600px) {
  .search-form__controls {
    flex-direction: column;
  }
}
</style>
