<script setup lang="ts">
import { RouterView } from 'vue-router'
import SiteHeader from './components/layout/SiteHeader.vue'
import SiteFooter from './components/layout/SiteFooter.vue'
</script>

<template>
  <a href="#main-content" class="skip-link">跳至主要内容</a>
  <SiteHeader />
  <main id="main-content" class="app-main">
    <RouterView />
  </main>
  <SiteFooter />
</template>

<style scoped>
/* 应用壳主区域：撑满剩余高度，承载路由页面 */
.app-main {
  flex: 1 0 auto;
  width: 100%;
}
</style>
