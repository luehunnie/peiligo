<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { ContentItem, ContentType } from '../types/content'
import { CONTENT_TYPE_OPTIONS } from '../constants/content-types'
import { ContentsApiError, getPublishedContents } from '../api/contents'
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

// ---- 数据加载：请求 /api/contents 已发布内容，不再依赖本地 mock ----
const data = ref<ContentItem[]>([])
const loading = ref(false)
const error = ref<ContentsApiError | null>(null)

// API 成功但无任何已发布内容：与"搜索/筛选无匹配"区分
const isDataEmpty = computed(() => data.value.length === 0)
const errorHint = computed(
  () => error.value?.message ?? '加载内容失败，请稍后重试',
)

async function loadContents(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    data.value = await getPublishedContents()
  } catch (err) {
    error.value =
      err instanceof ContentsApiError
        ? err
        : new ContentsApiError('加载内容失败，请稍后重试', 0)
  } finally {
    loading.value = false
  }
}

onMounted(loadContents)

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

  // 数据源已为 API 返回的已发布内容，无需再次按 status 过滤
  let result = data.value

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

    <!-- 加载中 -->
    <p v-if="loading" class="state state--loading">加载中…</p>

    <!-- 加载失败：不回退 mock，提供重新加载入口 -->
    <div v-else-if="error" class="state state--error">
      <p class="state__title">内容加载失败</p>
      <p class="state__hint">{{ errorHint }}</p>
      <button
        type="button"
        class="btn btn--primary state__action"
        @click="loadContents"
      >
        重新加载
      </button>
    </div>

    <template v-else>
      <div v-if="!isDataEmpty" class="result-bar">
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

      <!-- API 成功但无任何已发布内容 -->
      <div v-else-if="isDataEmpty" class="state state--empty">
        <p class="state__title">暂无已发布内容</p>
        <p class="state__hint">内容还在准备中，请稍后再来看看。</p>
      </div>

      <!-- 有数据但当前搜索 / 筛选无匹配：保持 M1 无匹配语义 -->
      <ContentEmptyState v-else :keyword="currentKeyword" />
    </template>
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

.state {
  margin-top: var(--space-lg);
  padding: var(--space-2xl) var(--space-lg);
  text-align: center;
  background: var(--content-bg);
  border: 1px dashed var(--border-color);
  border-radius: var(--radius);
}

.state--loading {
  border-style: solid;
}

.state__title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--text-primary);
}

.state__hint {
  margin-top: var(--space-xs);
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}

.state__action {
  margin-top: var(--space-md);
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
