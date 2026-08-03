<script setup lang="ts">
import { computed } from 'vue'
import type { ContentType } from '../types/content'
import { CONTENT_TYPE_OPTIONS } from '../constants/content-types'
import { MOCK_CONTENTS } from '../data/mock-contents'

// 近期内容预览：仅展示少量已发布内容，按发布时间倒序
const RECENT_LIMIT = 5

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
  MOCK_CONTENTS.filter((item) => item.status === 'published')
    .sort((a, b) => b.publishedAt.localeCompare(a.publishedAt))
    .slice(0, RECENT_LIMIT),
)
</script>

<template>
  <div class="home site-container">
    <section class="hero">
      <p class="hero__eyebrow">校园 Web 资源聚合</p>
      <h1 class="hero__title">培黎智寻</h1>
      <p class="hero__subtitle">
        汇集校园学习、活动、资料、软件与入学指引等内容板块，方便同学集中查找与浏览。
      </p>
      <p class="hero__note">
        当前为 M1 静态原型阶段：页面内容均为示例演示数据，仅用于展示内容结构与板块字段，不代表学校正式信息。
      </p>
    </section>

    <section class="boards" aria-labelledby="boards-title">
      <h2 id="boards-title" class="section-title">内容板块</h2>
      <p class="section-hint">
        五个板块由统一配置驱动；完整的内容列表与按板块筛选将在后续 M1 批次接入。
      </p>
      <ul class="boards__list">
        <li
          v-for="option in CONTENT_TYPE_OPTIONS"
          :key="option.value"
          class="board-card"
        >
          <h3 class="board-card__title">{{ option.label }}</h3>
          <p class="board-card__desc">{{ option.description }}</p>
        </li>
      </ul>
      <p class="boards__footnote">
        各板块的完整浏览与详情将在后续接入，当前卡片仅作展示，暂不可进入。
      </p>
    </section>

    <section class="recent" aria-labelledby="recent-title">
      <h2 id="recent-title" class="section-title">近期内容预览</h2>
      <p class="section-hint">
        搜索与完整内容列表将在后续 M1 批次接入；当前仅展示少量已发布内容的标题、板块与时间。
      </p>
      <ul class="recent__list">
        <li
          v-for="item in recentContents"
          :key="item.id"
          class="recent-item"
        >
          <p class="recent-item__title">{{ item.title }}</p>
          <p class="recent-item__meta">
            <span class="recent-item__board">{{ getBoardLabel(item.contentType) }}</span>
            <span class="recent-item__date">{{ formatDate(item.publishedAt) }}</span>
          </p>
        </li>
      </ul>
    </section>

    <section class="roadmap" aria-labelledby="roadmap-title">
      <h2 id="roadmap-title" class="section-title">后续计划</h2>
      <p class="roadmap__intro">
        以下页面与功能尚未建立，将在后续 M1 批次逐步接入，当前不提供链接：
      </p>
      <ul class="roadmap__list">
        <li>内容列表页与按板块筛选</li>
        <li>内容搜索</li>
        <li>内容详情页</li>
        <li>投稿说明</li>
        <li>关于本站</li>
      </ul>
    </section>
  </div>
</template>

<style scoped>
.home {
  padding-block: var(--space-lg) var(--space-2xl);
}

.home > section + section {
  margin-top: var(--space-2xl);
}

.hero__eyebrow {
  color: var(--brand-color);
  font-size: var(--font-size-sm);
  font-weight: 600;
}

.hero__title {
  margin-top: var(--space-xs);
}

.hero__subtitle {
  margin-top: var(--space-md);
  max-width: 60ch;
  color: var(--text-secondary);
  font-size: var(--font-size-lg);
}

.hero__note {
  margin-top: var(--space-lg);
  max-width: 72ch;
  padding: var(--space-sm) var(--space-md);
  background: var(--notice-bg);
  border: 1px solid var(--notice-border);
  border-radius: var(--radius-sm);
  color: var(--notice-text);
  font-size: var(--font-size-sm);
}

.section-hint {
  margin-top: var(--space-xs);
  max-width: 72ch;
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}

.boards__list {
  margin-top: var(--space-lg);
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--space-md);
}

.board-card {
  padding: var(--space-lg);
  background: var(--content-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
}

.board-card__title {
  color: var(--brand-color);
}

.board-card__desc {
  margin-top: var(--space-xs);
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
  line-height: 1.6;
}

.boards__footnote {
  margin-top: var(--space-md);
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
  padding: var(--space-md) var(--space-lg);
  background: var(--content-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
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

.roadmap__intro {
  margin-top: var(--space-sm);
  color: var(--text-secondary);
}

.roadmap__list {
  margin-top: var(--space-sm);
 display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  color: var(--text-secondary);
  list-style: disc;
  padding-left: var(--space-lg);
}
</style>
