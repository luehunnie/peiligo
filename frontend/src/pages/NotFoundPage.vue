<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ElButton } from 'element-plus'

const router = useRouter()
const goHome = (): void => {
  router.push('/')
}
</script>

<template>
  <div class="not-found site-container">
    <h1 class="not-found__title">页面未找到</h1>
    <p class="not-found__desc">
      您访问的页面不存在，或尚未在当前 M1 原型中建立。
    </p>
    <ElButton type="primary" size="large" @click="goHome">返回首页</ElButton>
  </div>
</template>

<style scoped>
.not-found {
  padding-block: var(--space-2xl);
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-md);
}

.not-found__desc {
  max-width: 60ch;
  color: var(--text-secondary);
  font-size: var(--font-size-lg);
}
</style>
