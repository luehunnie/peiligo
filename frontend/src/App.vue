<script setup lang="ts">
import { onMounted, ref } from 'vue'

type HealthResponse = {
  status: string
}

const health = ref('检查中')

onMounted(async () => {
  try {
    const response = await fetch('/api/health')
    if (!response.ok) throw new Error('健康检查请求失败')
    const data = (await response.json()) as HealthResponse
    health.value = data.status === 'ok' ? '正常' : data.status
  } catch {
    health.value = '后端未连接'
  }
})
</script>

<template>
  <main>
    <section class="card">
      <p class="eyebrow">PEILI SMART SEARCH</p>
      <h1>培黎智寻</h1>
      <p class="description">校园 Web 资源搜索集合网站 · M0 最小运行骨架</p>
      <p class="health">后端状态：<strong>{{ health }}</strong></p>
    </section>
  </main>
</template>

