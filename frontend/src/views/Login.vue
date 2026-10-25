<template>
  <div class="auth-page">
    <section class="art">
      <div class="art-inner">
        <router-link to="/" class="brand"><SealLogo :size="56" /></router-link>
        <div class="verse kai">
          <span>上医治未病</span>
          <span>中医治欲病</span>
          <span>下医治已病</span>
        </div>
        <p class="art-foot kai">倪海厦 · 经方中医</p>
      </div>
    </section>

    <section class="panel">
      <div class="form-box">
        <h2 class="kai">{{ isRegister ? '注册会员' : '登录' }}</h2>
        <p class="sub">{{ isRegister ? '注册后可查阅医案库、收藏典籍、使用经方问诊' : '欢迎回来，继续研读经方' }}</p>

        <el-form ref="formRef" :model="form" :rules="rules" label-position="top" size="large" @submit.prevent="submit">
          <el-form-item :label="isRegister ? '用户名' : '用户名 / 邮箱'" prop="username">
            <el-input v-model="form.username" :prefix-icon="User" autocomplete="username" :placeholder="isRegister ? '字母开头，3-30 位字母数字下划线' : ''" />
          </el-form-item>
          <el-form-item v-if="isRegister" label="昵称" prop="nickname">
            <el-input v-model="form.nickname" placeholder="选填" />
          </el-form-item>
          <el-form-item v-if="isRegister" label="邮箱" prop="email">
            <el-input v-model="form.email" placeholder="选填，可用于登录" autocomplete="email" />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input v-model="form.password" type="password" show-password :prefix-icon="Lock" :autocomplete="isRegister ? 'new-password' : 'current-password'" :placeholder="isRegister ? '至少 8 位，包含字母和数字' : ''" />
          </el-form-item>
          <el-form-item v-if="isRegister" label="确认密码" prop="confirm">
            <el-input v-model="form.confirm" type="password" show-password autocomplete="new-password" />
          </el-form-item>
          <el-button type="primary" native-type="submit" :loading="loading" class="submit">{{ isRegister ? '注册并登录' : '登录' }}</el-button>
        </el-form>

        <div class="switch">
          <template v-if="isRegister">已有账号？<router-link :to="{ name: 'login', query: $route.query }">去登录</router-link></template>
          <template v-else-if="auth.config.allow_registration">还没有账号？<router-link :to="{ name: 'register', query: $route.query }">免费注册</router-link></template>
          <span class="dot">·</span><router-link to="/">返回首页</router-link>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'
import SealLogo from '@/components/SealLogo.vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const isRegister = computed(() => route.name === 'register')
const formRef = ref<FormInstance>()
const loading = ref(false)
const form = reactive({ username: '', password: '', confirm: '', email: '', nickname: '' })

const rules = computed<FormRules>(() => ({
  username: isRegister.value
    ? [{ required: true, message: '请输入用户名' }, { pattern: /^[A-Za-z][A-Za-z0-9_]{2,29}$/, message: '字母开头，3-30 位字母、数字或下划线' }]
    : [{ required: true, message: '请输入用户名或邮箱' }],
  password: isRegister.value
    ? [{ required: true, message: '请输入密码' }, { pattern: /^(?=.*[A-Za-z])(?=.*\d).{8,72}$/, message: '至少 8 位，需同时包含字母和数字' }]
    : [{ required: true, message: '请输入密码' }],
  confirm: [{ validator: (_r, v, cb) => (v === form.password ? cb() : cb(new Error('两次密码不一致'))) }],
  email: [{ type: 'email', message: '邮箱格式不正确' }],
}))

watch(isRegister, () => formRef.value?.clearValidate())

async function submit() {
  if (!(await formRef.value?.validate().catch(() => false))) return
  loading.value = true
  try {
    if (isRegister.value) {
      await auth.register({ username: form.username, password: form.password, email: form.email || undefined, nickname: form.nickname || undefined })
      ElMessage.success('注册成功，欢迎加入')
    } else {
      await auth.login(form.username, form.password)
      ElMessage.success(`欢迎回来，${auth.user?.nickname || auth.user?.username}`)
    }
    const redirect = typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/') ? route.query.redirect : '/'
    router.replace(redirect)
  } catch {
    /* 错误提示由拦截器处理 */
  } finally {
    loading.value = false
  }
}
</script>

<style scoped lang="scss">
.auth-page { min-height: 100vh; display: flex; }
.art {
  flex: 1;
  position: relative;
  background:
    linear-gradient(160deg, rgba(43, 36, 32, 0.92), rgba(46, 87, 83, 0.88)),
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 600 400'%3E%3Cpath d='M0 300 C100 220 160 260 240 190 S400 120 460 200 S560 260 600 230 V400 H0Z' fill='%23f5eedf' fill-opacity='.06'/%3E%3Cpath d='M0 340 C120 300 220 320 320 280 S520 300 600 290 V400 H0Z' fill='%23f5eedf' fill-opacity='.05'/%3E%3C/svg%3E") bottom/cover no-repeat;
  color: #f1e6d0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.art-inner { display: flex; flex-direction: column; align-items: center; gap: 36px; }
.verse {
  display: flex;
  flex-direction: row-reverse;
  gap: 28px;
  span { writing-mode: vertical-rl; font-size: 30px; letter-spacing: 14px; }
  span:nth-child(2) { margin-top: 40px; color: #e3c08a; }
  span:nth-child(3) { margin-top: 80px; }
}
.art-foot { letter-spacing: 8px; opacity: 0.7; margin: 0; }
.panel { width: 480px; display: flex; align-items: center; justify-content: center; padding: 40px; background: var(--card); border-left: 1px solid var(--line); }
.form-box { width: 100%; max-width: 360px; }
h2 { font-size: 32px; letter-spacing: 8px; margin: 0; }
.sub { color: var(--ink-3); font-size: 14px; margin: 6px 0 24px; }
.submit { width: 100%; margin-top: 8px; height: 44px; font-size: 16px; letter-spacing: 6px; }
.switch { margin-top: 20px; text-align: center; font-size: 14px; color: var(--ink-3); .dot { margin: 0 8px; } }
@media (max-width: 860px) {
  .art { display: none; }
  .panel { width: 100%; border: none; }
}
</style>
