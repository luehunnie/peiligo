<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { CONTENT_TYPE_OPTIONS } from '../constants/content-types'
import HomeRecentContents from '../components/content/HomeRecentContents.vue'

const router = useRouter()
const searchKeyword = ref('')

const submitSearch = () => {
  const trimmed = searchKeyword.value.trim()
  router.push({
    name: 'contents',
    query: trimmed ? { q: trimmed } : {},
  })
}
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
        近期内容来自内容系统已发布条目；正式上线前内容仍在完善，部分信息仅供校内同学参考，不代表学校正式通知或政策。
      </p>
    </section>

    <section class="search" aria-labelledby="search-title">
      <h2 id="search-title" class="section-title">搜索内容</h2>
      <form class="search-form" @submit.prevent="submitSearch">
        <label for="home-search" class="search-form__label">关键词</label>
        <div class="search-form__controls">
          <input
            id="home-search"
            v-model="searchKeyword"
            type="search"
            placeholder="搜索标题、摘要或正文"
          />
          <button type="submit" class="btn btn--primary">搜索</button>
        </div>
        <p class="search-form__hint">
          输入关键词后点击搜索，可进入内容浏览页查看完整结果并按板块筛选。
        </p>
      </form>
    </section>

    <section class="boards" aria-labelledby="boards-title">
      <h2 id="boards-title" class="section-title">内容板块</h2>
      <p class="section-hint">
        五个板块由统一配置驱动；可在内容浏览页按板块筛选与搜索。
      </p>
      <ul class="boards__list">
        <li v-for="option in CONTENT_TYPE_OPTIONS" :key="option.value">
          <RouterLink
            class="board-card"
            :to="{ name: 'contents', query: { type: option.value } }"
            :aria-label="`进入「${option.label}」板块浏览内容`"
          >
            <h3 class="board-card__title">{{ option.label }}</h3>
            <p class="board-card__desc">{{ option.description }}</p>
          </RouterLink>
        </li>
      </ul>
      <p class="boards__footnote">
        可在内容浏览页查看各板块内容，点击任意条目即可进入内容详情页。
      </p>
    </section>

    <HomeRecentContents />

    <section class="roadmap" aria-labelledby="roadmap-title">
      <h2 id="roadmap-title" class="section-title">更多页面</h2>
      <p class="roadmap__intro">
        内容详情页、投稿说明与关于本站均已接入：内容详情可在内容浏览页点击条目进入，投稿说明与关于本站可直接访问。
      </p>
      <ul class="roadmap__list">
        <li>
          <RouterLink class="roadmap__link" :to="{ name: 'submission' }">投稿说明</RouterLink>
        </li>
        <li>
          <RouterLink class="roadmap__link" :to="{ name: 'about' }">关于本站</RouterLink>
        </li>
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

.search-form__hint {
  margin-top: var(--space-xs);
  color: var(--text-secondary);
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
  display: block;
  height: 100%;
  padding: var(--space-lg);
  color: inherit;
  text-decoration: none;
  background: var(--content-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  transition: border-color 0.15s ease;
}

.board-card:hover,
.board-card:focus-visible {
  border-color: var(--brand-color);
}

.board-card:focus-visible {
  outline: 2px solid var(--brand-color);
  outline-offset: 2px;
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

.roadmap__link {
  color: var(--brand-color);
  text-decoration: none;
}

.roadmap__link:hover {
  text-decoration: underline;
}
</style>
