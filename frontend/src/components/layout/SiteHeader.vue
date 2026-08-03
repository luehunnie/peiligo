<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

// 当前是否处于首页：用于导航高亮（同时用 aria-current 提供语义标记，不只依赖颜色）
const route = useRoute()
const isHome = computed(() => route.name === 'home')
</script>

<template>
  <header class="site-header">
    <div class="site-header__inner">
      <RouterLink to="/" class="site-logo">培黎智寻</RouterLink>
      <p class="site-tagline">校园 Web 资源聚合 · M1 静态原型</p>
      <nav class="site-nav" aria-label="主导航">
        <RouterLink
          to="/"
          class="nav-link"
          :aria-current="isHome ? 'page' : undefined"
        >
          首页
        </RouterLink>
      </nav>
    </div>
  </header>
</template>

<style scoped>
.site-header {
  background: var(--content-bg);
  border-bottom: 1px solid var(--border-color);
}

.site-header__inner {
  max-width: var(--content-max-width);
  margin-inline: auto;
  padding-inline: var(--space-lg);
  height: var(--header-height);
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.site-logo {
  font-size: 20px;
  font-weight: 700;
  color: var(--brand-color);
  white-space: nowrap;
}

.site-logo:hover {
  text-decoration: none;
}

.site-tagline {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.site-nav {
  margin-left: auto;
}

.nav-link {
  padding: var(--space-xs) var(--space-md);
  font-size: var(--font-size-base);
  color: var(--text-primary);
  border-radius: var(--radius-sm);
}

.nav-link:hover {
  text-decoration: none;
  background: var(--brand-bg-soft);
}

/* 当前页：颜色加粗 + aria-current 语义，双重标记 */
.site-nav a[aria-current='page'] {
  color: var(--brand-color);
  font-weight: 600;
}

@media (max-width: 600px) {
  .site-tagline {
    display: none;
  }
}
</style>
