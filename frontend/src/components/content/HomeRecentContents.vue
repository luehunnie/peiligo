<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import type { ContentItem, ContentType } from '../../types/content'
import { CONTENT_TYPE_OPTIONS } from '../../constants/content-types'
import { ContentsApiError, getPublishedContents } from '../../api/contents'

// 近期内容预览：仅展示少量已发布内容，按发布时间倒序
const RECENT_LIMIT = 5

const data = ref<ContentItem[]>([])
const loading = ref(false)
const error = ref<ContentsApiError | null>(null)
const errorHint = computed(
  () => error.value?.message ?? '加载内容失败，请稍后重试',
)

// API 失败不回退 mock；提供重新加载入口
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

// 板块标签查找表：由集中配置 CONTENT_TYPE_OPTIONS 驱动，键值类型与模型一致
const boardLabels = new Map<ContentType, string>(
  CONTENT_TYPE_OPTIONS.map((option): [ContentType, string] => [
    option.value,
    option.label,
  ]),
)

const getBoardLabel = (type: ContentType): string =>
  boardLabels.get(type) ?? type

// 将 ISO 日期格式化为简洁中文日期；解析失败时回退原值
const formatDate = (iso: string): string => {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`
}

// 仅已发布、按发布时间倒序、截取少量条目
const recentContents = computed(() =>
  [...data.value]
    .sort((a, b) => b.publishedAt.localeCompare(a.publishedAt))
    .slice(0, RECENT_LIMIT),
)
</script>

<template>
  <section class="recent" aria-labelledby="recent-title">
    <h2 id="recent-title" class="section-title">近期内容预览</h2>
    <p class="section-hint">
      以下仅展示少量近期已发布内容；完整列表请在内容浏览页查看。
    </p>

    <p v-if="loading" class="state state--loading">加载中…</p>

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

    <div v-else-if="recentContents.length === 0" class="state state--empty">
      <p class="state__title">暂无已发布内容</p>
      <p class="state__hint">内容还在准备中，请稍后再来看看。</p>
    </div>

    <ul v-else class="recent__list">
      <li v-for="item in recentContents" :key="item.id">
        <RouterLink
          class="recent-item"
          :to="{ name: 'content-detail', params: { id: item.id } }"
          :aria-label="`查看「${item.title}」详情`"
        >
          <p class="recent-item__title">{{ item.title }}</p>
          <p class="recent-item__meta">
            <span class="recent-item__board">{{ getBoardLabel(item.contentType) }}</span>
            <span class="recent-item__date">{{ formatDate(item.publishedAt) }}</span>
          </p>
        </RouterLink>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.section-hint {
  margin-top: var(--space-xs);
  max-width: 72ch;
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}

.recent__list {
  margin-top: var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.recent-item {
  display: block;
  padding: var(--space-md) var(--space-lg);
  color: inherit;
  text-decoration: none;
  background: var(--content-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  transition: border-color 0.15s ease;
}

.recent-item:hover,
.recent-item:focus-visible {
  border-color: var(--brand-color);
}

.recent-item:focus-visible {
  outline: 2px solid var(--brand-color);
  outline-offset: 2px;
}

.recent-item__title {
  font-size: var(--font-size-lg);
  font-weight: 500;
}

.recent-item__meta {
  margin-top: var(--space-xs);
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-md);
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}

.recent-item__board {
  color: var(--brand-color);
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
</style>
