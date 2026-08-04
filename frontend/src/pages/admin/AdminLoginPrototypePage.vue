<script setup lang="ts">
import { ref } from 'vue'
import PrototypeNotice from '../../components/common/PrototypeNotice.vue'

const username = ref('')
const password = ref('')
const formNotice = ref('')

// 静态原型：不保存密码、不生成 Token、不执行真实登录
const handleSubmit = () => {
  formNotice.value =
    '当前为 M1 静态原型，尚未接入真实认证。表单不会保存密码、不会生成登录凭证，也无法完成登录。'
}
</script>

<template>
  <div class="admin-login site-container">
    <h1>管理员登录</h1>

    <PrototypeNotice
      class="admin-login__notice"
      message="当前为 M1 静态原型，尚未接入真实认证。下方表单仅用于展示界面结构，不会保存密码，也不会生成任何登录凭证。"
    />

    <form class="admin-login__form" @submit.prevent="handleSubmit">
      <div class="form-field">
        <label for="login-username" class="form-field__label">用户名</label>
        <input
          id="login-username"
          v-model="username"
          type="text"
          autocomplete="username"
        />
      </div>

      <div class="form-field">
        <label for="login-password" class="form-field__label">密码</label>
        <input
          id="login-password"
          v-model="password"
          type="password"
          autocomplete="current-password"
        />
      </div>

      <button type="submit" class="btn btn--primary">登录</button>
    </form>

    <p v-if="formNotice" class="form-notice" role="status">{{ formNotice }}</p>
  </div>
</template>

<style scoped>
.admin-login {
  padding-block: var(--space-lg) var(--space-2xl);
}

.admin-login__notice {
  margin-top: var(--space-lg);
}

.admin-login__form {
  margin-top: var(--space-lg);
  max-width: 400px;
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}
</style>
