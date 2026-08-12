<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import type { ContentExtraValue, ContentItem } from '../types/content'
import { CONTENT_EXTRA_FIELDS } from '../constants/content-extra-fields'
import { ContentsApiError, getPublishedContentById } from '../api/contents'
import ContentMeta from '../components/content/ContentMeta.vue'

const route = useRoute()

const contentId = computed(() => {
  const id = route.params.id
  return typeof id === 'string' ? id : ''
})

// ---- 详情加载：按 route id 请求 /api/contents/{id}，route 变化时重新加载 ----
const content = ref<ContentItem | null>(null)
const loading = ref(false)
const error = ref<ContentsApiError | null>(null)

// 404（不存在 / 草稿 / 已下线）与网络 / 服务器错误需区分恢复入口
const isNotFound = computed(() => error.value?.status === 404)
const isLoadError = computed(
  () => error.value !== null && error.value.status !== 404,
)
const errorHint = computed(
  () => error.value?.message ?? '内容加载失败，请稍后重试',
)

// route id 变化（含首次进入）触发重新加载；API 失败不回退 mock
async function loadContent(): Promise<void> {
  const id = contentId.value
  loading.value = true
  error.value = null
  content.value = null
  if (!id) {
    error.value = new ContentsApiError('内容不存在或已下线', 404)
    loading.value = false
    return
  }
  try {
    content.value = await getPublishedContentById(id)
  } catch (err) {
    error.value =
      err instanceof ContentsApiError
        ? err
        : new ContentsApiError('内容加载失败，请稍后重试', 0)
  } finally {
    loading.value = false
  }
}

watch(contentId, loadContent, { immediate: true })

// 专属字段：由 CONTENT_EXTRA_FIELDS 驱动，缺失值跳过
interface ExtraEntry {
  label: string
  value: ContentExtraValue
}

const extraEntries = computed<ExtraEntry[]>(() => {
  const item = content.value
  const data = item?.extraData
  if (!item || !data) return []
  return CONTENT_EXTRA_FIELDS[item.contentType]
    .map((field): ExtraEntry | null => {
      const value = data[field.key]
      return value === undefined ? null : { label: field.label, value }
    })
    .filter((entry): entry is ExtraEntry => entry !== null)
})

// 数组值以顿号连接，标量转为字符串
const formatValue = (value: ContentExtraValue): string =>
  Array.isArray(value) ? value.join('、') : String(value)

// 返回列表：尽量保留来源页的 q 与 type 查询参数
const backToContents = computed(() => {
  const query: Record<string, string> = {}
  const q = route.query.q
  const type = route.query.type
  if (typeof q === 'string' && q) query.q = q
  if (typeof type === 'string' && type) query.type = type
  return { name: 'contents', query }
})
</script>

<template>
  <div class="content-detail site-container">
    <nav class="breadcrumb" aria-label="面包屑">
      <ol>
        <li>
          <router-link :to="{ name: 'home' }">首页</router-link>
        </li>
        <li>
          <router-link :to="backToContents">内容浏览</router-link>
        </li>
        <li aria-current="page">
          {{ content ? content.title : '内容详情' }}
        </li>
      </ol>
    </nav>

    <p v-if="loading" class="state state--loading">加载中…</p>

    <div v-else-if="isNotFound" class="content-detail__error">
      <p class="content-detail__error-title">未找到该内容</p>
      <p class="content-detail__error-hint">
        该内容可能尚未发布或已被移除。
      </p>
      <router-link :to="backToContents" class="btn btn--primary">
        返回内容浏览
      </router-link>
    </div>

    <div v-else-if="isLoadError" class="content-detail__error">
      <p class="content-detail__error-title">内容加载失败</p>
      <p class="content-detail__error-hint">{{ errorHint }}</p>
      <div class="content-detail__error-actions">
        <button
          type="button"
          class="btn btn--primary"
          @click="loadContent"
        >
          重新加载
        </button>
        <router-link :to="backToContents" class="btn btn--ghost">
          返回内容浏览
        </router-link>
      </div>
    </div>

    <template v-else-if="content">
      <h1 class="content-detail__title">{{ content.title }}</h1>

      <div class="content-detail__meta">
        <ContentMeta
          :content-type="content.contentType"
          :published-at="content.publishedAt"
        />
      </div>

      <p class="content-detail__summary">{{ content.summary }}</p>

      <section v-if="content.body.length > 0" class="content-detail__body">
        <p
          v-for="(paragraph, index) in content.body"
          :key="index"
          class="content-detail__paragraph"
        >
          {{ paragraph }}
        </p>
      </section>

      <section v-if="extraEntries.length > 0" class="content-detail__extra">
        <h2 class="content-detail__section-title">补充信息</h2>
        <dl class="extra-list">
          <template v-for="entry in extraEntries" :key="entry.label">
            <dt class="extra-list__term">{{ entry.label }}</dt>
            <dd class="extra-list__value">{{ formatValue(entry.value) }}</dd>
          </template>
        </dl>
      </section>

      <section class="content-detail__source">
        <h2 class="content-detail__section-title">来源</h2>
        <p v-if="content.sourceUrl" class="source">
          <a
            :href="content.sourceUrl"
            target="_blank"
            rel="noopener noreferrer"
          >
            {{ content.sourceName || content.sourceUrl }}
          </a>
        </p>
        <p v-else-if="content.sourceName" class="source">
          {{ content.sourceName }}
        </p>
        <p v-else class="source source--empty">未提供来源链接</p>
      </section>

      <router-link
        :to="backToContents"
        class="btn btn--ghost content-detail__back"
      >
        返回内容浏览
      </router-link>
    </template>
  </div>
</template>

<style scoped>
.content-detail {
  padding-block: var(--space-lg) var(--space-2xl);
}

.state {
  margin-top: var(--space-xl);
  padding: var(--space-2xl) var(--space-lg);
  text-align: center;
  background: var(--content-bg);
  border: 1px dashed var(--border-color);
  border-radius: var(--radius);
}

.state--loading {
  border-style: solid;
}

.breadcrumb ol {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-xs);
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.breadcrumb li {
  display: flex;
  align-items: center;
}

.breadcrumb li:not(:last-child)::after {
  content: '/';
  margin-left: var(--space-xs);
}

.breadcrumb [aria-current='page'] {
  color: var(--text-primary);
}

.content-detail__title {
  margin-top: var(--space-md);
}

.content-detail__meta {
  margin-top: var(--space-sm);
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-sm);
}

.content-detail__summary {
  margin-top: var(--space-md);
  max-width: 72ch;
  font-size: var(--font-size-lg);
  color: var(--text-secondary);
  line-height: var(--line-height-base);
}

.content-detail__body {
  margin-top: var(--space-lg);
  max-width: 72ch;
}

.content-detail__paragraph {
  margin-top: var(--space-sm);
  line-height: var(--line-height-base);
}

.content-detail__section-title {
  font-size: var(--font-size-h3);
}

.content-detail__extra {
  margin-top: var(--space-lg);
}

.extra-list {
  margin-top: var(--space-sm);
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: var(--space-xs) var(--space-md);
}

.extra-list__term {
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}

.extra-list__value {
  margin: 0;
  font-size: var(--font-size-sm);
}

.content-detail__source {
  margin-top: var(--space-lg);
}

.source {
  margin-top: var(--space-sm);
  font-size: var(--font-size-sm);
}

.source--empty {
  color: var(--text-secondary);
}

.content-detail__back {
  margin-top: var(--space-xl);
}

.content-detail__error {
  margin-top: var(--space-xl);
  padding: var(--space-2xl) var(--space-lg);
  text-align: center;
  background: var(--content-bg);
  border: 1px dashed var(--border-color);
  border-radius: var(--radius);
}

.content-detail__error-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
}

.content-detail__error-hint {
  margin-top: var(--space-xs);
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}

.content-detail__error > .btn {
  margin-top: var(--space-lg);
}

.content-detail__error-actions {
  margin-top: var(--space-lg);
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
  justify-content: center;
}
</style>
