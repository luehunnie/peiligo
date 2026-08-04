<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import type { ContentType } from '../../types/content'
import { CONTENT_TYPE_OPTIONS } from '../../constants/content-types'
import { CONTENT_EXTRA_FIELDS } from '../../constants/content-extra-fields'
import PrototypeNotice from '../../components/common/PrototypeNotice.vue'

// 统一字段
const title = ref('')
const summary = ref('')
const body = ref('')

// 内容类型选择，默认第一个板块
const currentType = ref<ContentType>(CONTENT_TYPE_OPTIONS[0].value)

// 专属字段值：键随当前板块配置变化
const extraValues = reactive<Record<string, string>>({})

// 当前板块的三个专属字段配置
const extraFields = computed(() => CONTENT_EXTRA_FIELDS[currentType.value])

// 类型切换时清空专属字段，因为字段集合随配置变化
watch(currentType, () => {
  for (const key of Object.keys(extraValues)) {
    delete extraValues[key]
  }
})

const saveNotice = ref('')

// 静态原型：不保存数据、不使用 localStorage、不显示虚假成功
const handleSave = () => {
  saveNotice.value =
    '当前为 M1 静态原型，尚未接入保存功能。内容不会被保存，也不会写入本地存储。'
}
</script>

<template>
  <div class="admin-editor site-container">
    <h1>新建内容</h1>

    <PrototypeNotice
      class="admin-editor__notice"
      message="当前为 M1 静态原型，编辑器仅用于展示字段结构。点击保存不会写入任何数据，也不会使用本地存储。"
    />

    <form class="admin-editor__form" @submit.prevent="handleSave">
      <div class="form-field">
        <label for="content-title" class="form-field__label">标题</label>
        <input id="content-title" v-model="title" type="text" />
      </div>

      <div class="form-field">
        <label for="content-type" class="form-field__label">内容板块</label>
        <select id="content-type" v-model="currentType">
          <option
            v-for="option in CONTENT_TYPE_OPTIONS"
            :key="option.value"
            :value="option.value"
          >
            {{ option.label }}
          </option>
        </select>
      </div>

      <div class="form-field">
        <label for="content-summary" class="form-field__label">摘要</label>
        <textarea id="content-summary" v-model="summary" rows="3" />
      </div>

      <div class="form-field">
        <label for="content-body" class="form-field__label">正文</label>
        <textarea id="content-body" v-model="body" rows="8" />
      </div>

      <fieldset class="admin-editor__extra">
        <legend class="admin-editor__legend">专属字段</legend>
        <div
          v-for="field in extraFields"
          :key="field.key"
          class="form-field"
        >
          <label :for="`extra-${field.key}`" class="form-field__label">
            {{ field.label }}
          </label>
          <input
            :id="`extra-${field.key}`"
            v-model="extraValues[field.key]"
            type="text"
            :placeholder="field.placeholder"
          />
          <p
            v-if="field.valueType === 'string-list'"
            class="form-field__hint"
          >
            多个值请用顿号分隔。
          </p>
        </div>
      </fieldset>

      <button type="submit" class="btn btn--primary">保存</button>
    </form>

    <p v-if="saveNotice" class="form-notice" role="status">{{ saveNotice }}</p>
  </div>
</template>

<style scoped>
.admin-editor {
  padding-block: var(--space-lg) var(--space-2xl);
}

.admin-editor__notice {
  margin-top: var(--space-lg);
}

.admin-editor__form {
  margin-top: var(--space-lg);
  max-width: 720px;
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.admin-editor__extra {
  margin: 0;
  padding: var(--space-md);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.admin-editor__legend {
  padding: 0 var(--space-sm);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--text-secondary);
}
</style>
