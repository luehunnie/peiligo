<script setup lang="ts">
import { CONTENT_TYPE_OPTIONS } from '../constants/content-types'

const boardLabels = CONTENT_TYPE_OPTIONS.map((option) => option.label)
</script>

<template>
  <div class="about-page site-container">
    <h1>关于本站</h1>
    <p class="about-page__intro">
      培黎智寻是一个面向校园的 Web 资源聚合站点，方便同学集中查找学习、活动、资料、软件与入学指引等信息。
    </p>

    <section aria-labelledby="purpose-title">
      <h2 id="purpose-title" class="about-page__section-title">网站用途</h2>
      <p>
        本站将校园中分散的各类信息整合为统一的内容板块，提供浏览与搜索入口，帮助同学更便捷地获取所需内容。
      </p>
    </section>

    <section aria-labelledby="scope-title">
      <h2 id="scope-title" class="about-page__section-title">内容边界</h2>
      <p>当前提供以下板块的内容：</p>
      <p class="about-page__boards">{{ boardLabels.join('、') }}</p>
      <p>
        本站聚焦于校园学习与生活相关的资源聚合，不替代学校行政系统、教务系统或其他官方信息系统。
      </p>
    </section>

    <section aria-labelledby="demo-title">
      <h2 id="demo-title" class="about-page__section-title">示例内容性质</h2>
      <p>
        当前处于 M1 静态原型阶段，站内所有内容均为示例演示数据，仅用于展示页面结构与板块字段，不代表真实信息。
      </p>
    </section>

    <section aria-labelledby="disclaimer-title">
      <h2 id="disclaimer-title" class="about-page__section-title">免责声明</h2>
      <ul class="about-page__list">
        <li>本站为非正式项目，不是学校官方网站，不代表学校立场。</li>
        <li>示例内容中的名称、日期、地点等均为虚构，如有雷同纯属巧合。</li>
        <li>任何信息的准确性、时效性请以学校官方渠道发布的内容为准。</li>
      </ul>
    </section>
  </div>
</template>

<style scoped>
.about-page {
  padding-block: var(--space-lg) var(--space-2xl);
}

.about-page__intro {
  margin-top: var(--space-md);
  max-width: 72ch;
  color: var(--text-secondary);
  font-size: var(--font-size-lg);
  line-height: var(--line-height-base);
}

.about-page__section-title {
  margin-top: var(--space-xl);
}

.about-page section > p {
  max-width: 72ch;
  line-height: var(--line-height-base);
}

.about-page__boards {
  margin-top: var(--space-sm);
  color: var(--brand-color);
  font-weight: 500;
}

.about-page__list {
  margin-top: var(--space-sm);
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  padding-left: var(--space-lg);
  list-style: disc;
}

.about-page__list li {
  max-width: 72ch;
  line-height: var(--line-height-base);
}
</style>
