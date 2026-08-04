<script setup lang="ts">
// 年份使用简单表达式生成，不建立日期工具文件
const year = new Date().getFullYear()
</script>

<template>
  <footer class="site-footer">
    <div class="site-footer__inner">
      <p class="footer-purpose">
        培黎智寻：面向校园的 Web 资源聚合站点，方便同学集中查找学习、活动、资料、软件与入学指引等信息。
      </p>
      <p class="footer-notice">
        当前为 M1 静态原型阶段：仅用于展示页面结构与内容字段，非正式网站。
      </p>
      <p class="footer-demo">
        页面中的内容均为示例演示数据，不代表学校正式通知、政策或官方信息，准确性请以官方渠道为准。
      </p>
      <p class="footer-meta">© {{ year }} 培黎智寻（M1 原型演示）· 非正式网站</p>
    </div>
  </footer>
</template>

<style scoped>
.site-footer {
  margin-top: var(--space-2xl);
  background: var(--content-bg);
  border-top: 1px solid var(--border-color);
}

.site-footer__inner {
  max-width: var(--content-max-width);
  margin-inline: auto;
  padding: var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.footer-notice {
  padding: var(--space-sm) var(--space-md);
  background: var(--notice-bg);
  border: 1px solid var(--notice-border);
  border-radius: var(--radius-sm);
  color: var(--notice-text);
  font-size: var(--font-size-sm);
}

.footer-demo,
.footer-meta {
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}
</style>
