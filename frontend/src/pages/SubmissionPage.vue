<script setup lang="ts">
import { CONTENT_TYPE_OPTIONS } from '../constants/content-types'

const prohibitedContents = [
  '违反法律法规或学校规章制度的内容',
  '虚假信息、谣言或未经核实的传闻',
  '侵犯他人隐私或公开他人个人信息的内容',
  '未经许可的商业广告与推广信息',
  '涉及歧视、攻击性或敏感争议的内容',
]

const contactEmail = '待项目方确认'
</script>

<template>
  <div class="submission-page site-container">
    <h1>投稿说明</h1>
    <p class="submission-page__intro">
      欢迎向培黎智寻投稿校园相关内容。本站目前仅提供投稿说明，暂不支持在线投稿表单，请通过文末方式与项目方联系。
    </p>

    <section aria-labelledby="suitable-title">
      <h2 id="suitable-title" class="submission-page__section-title">适合投稿的内容</h2>
      <p>以下五个板块的内容均欢迎投稿：</p>
      <ul class="submission-page__board-list">
        <li v-for="option in CONTENT_TYPE_OPTIONS" :key="option.value">
          <span class="submission-page__board-name">{{ option.label }}</span>
          <span class="submission-page__board-desc">{{ option.description }}</span>
        </li>
      </ul>
    </section>

    <section aria-labelledby="prohibited-title">
      <h2 id="prohibited-title" class="submission-page__section-title">禁止投稿的内容</h2>
      <ul class="submission-page__list">
        <li v-for="(item, index) in prohibitedContents" :key="index">
          {{ item }}
        </li>
      </ul>
    </section>

    <section aria-labelledby="privacy-title">
      <h2 id="privacy-title" class="submission-page__section-title">隐私与真实性要求</h2>
      <ul class="submission-page__list">
        <li>投稿内容应真实准确，不得编造虚假信息或夸大事实。</li>
        <li>涉及他人时请征得当事人同意，不公开他人隐私信息。</li>
        <li>引用资料请标注来源，尊重原创与知识产权。</li>
        <li>项目方有权对投稿内容进行核实与编辑后再决定是否发布。</li>
      </ul>
    </section>

    <section aria-labelledby="method-title">
      <h2 id="method-title" class="submission-page__section-title">投稿方式</h2>
      <p>
        当前暂不提供在线投稿表单。如需投稿或有内容建议，请通过以下方式联系：
      </p>
      <dl class="submission-page__contact">
        <dt>联系邮箱</dt>
        <dd>{{ contactEmail }}</dd>
      </dl>
    </section>
  </div>
</template>

<style scoped>
.submission-page {
  padding-block: var(--space-lg) var(--space-2xl);
}

.submission-page__intro {
  margin-top: var(--space-md);
  max-width: 72ch;
  color: var(--text-secondary);
  font-size: var(--font-size-lg);
  line-height: var(--line-height-base);
}

.submission-page__section-title {
  margin-top: var(--space-xl);
}

.submission-page__board-list {
  margin-top: var(--space-sm);
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: var(--space-md);
}

.submission-page__board-list li {
  padding: var(--space-md);
  background: var(--content-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
}

.submission-page__board-name {
  display: block;
  color: var(--brand-color);
  font-weight: 600;
}

.submission-page__board-desc {
  display: block;
  margin-top: var(--space-xs);
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
  line-height: 1.6;
}

.submission-page__list {
  margin-top: var(--space-sm);
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  padding-left: var(--space-lg);
  list-style: disc;
  color: var(--text-primary);
}

.submission-page__contact {
  margin-top: var(--space-sm);
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: var(--space-xs) var(--space-md);
}

.submission-page__contact dt {
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}

.submission-page__contact dd {
  margin: 0;
}
</style>
