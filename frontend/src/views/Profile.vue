<template>
  <div class="container profile" v-if="auth.user">
    <el-alert v-if="auth.user.must_change_password" type="warning" show-icon :closable="false" class="force"
      title="为了账号安全，请先修改初始密码后再继续使用。" />

    <div class="layout">
      <aside class="card paper-card framed">
        <div class="avatar kai">{{ (auth.user.nickname || auth.user.username).slice(0, 1) }}</div>
        <h3 class="kai">{{ auth.user.nickname || auth.user.username }}</h3>
        <p class="uname">@{{ auth.user.username }}</p>
        <div class="roles">
          <el-tag v-for="r in auth.user.roles" :key="r.id" size="small" effect="plain">{{ r.name }}</el-tag>
        </div>
        <dl>
          <dt>注册时间</dt><dd>{{ fmtTime(auth.user.created_at) }}</dd>
          <dt>上次登录</dt><dd>{{ fmtTime(auth.user.last_login_at) }}</dd>
        </dl>
      </aside>

      <div class="main paper-card">
        <el-tabs v-model="tab">
          <el-tab-pane label="我的收藏" name="favorites" :disabled="auth.user.must_change_password">
            <el-empty v-if="!favorites.length" description="还没有收藏，去书阁看看吧" />
            <ul class="favs">
              <li v-for="f in favorites" :key="f.id">
                <span class="fav-type" :class="f.target_type">{{ f.target_type === 'document' ? '典籍' : '医案' }}</span>
                <router-link :to="favLink(f)" class="kai">{{ f.title }}</router-link>
                <span class="fav-time">{{ fmtTime(f.created_at) }}</span>
                <el-button text size="small" @click="removeFav(f)">取消</el-button>
              </li>
            </ul>
          </el-tab-pane>
          <el-tab-pane label="基本资料" name="info" :disabled="auth.user.must_change_password">
            <el-form :model="info" label-width="80px" class="form">
              <el-form-item label="用户名"><el-input :model-value="auth.user.username" disabled /></el-form-item>
              <el-form-item label="昵称"><el-input v-model="info.nickname" maxlength="50" /></el-form-item>
              <el-form-item label="邮箱"><el-input v-model="info.email" /></el-form-item>
              <el-form-item label="手机"><el-input v-model="info.phone" maxlength="30" /></el-form-item>
              <el-form-item><el-button type="primary" :loading="saving" @click="saveInfo">保存</el-button></el-form-item>
            </el-form>
          </el-tab-pane>
          <el-tab-pane label="账号安全" name="password">
            <el-form ref="pwdRef" :model="pwd" :rules="pwdRules" label-width="100px" class="form">
              <el-form-item label="原密码" prop="old"><el-input v-model="pwd.old" type="password" show-password autocomplete="current-password" /></el-form-item>
              <el-form-item label="新密码" prop="new"><el-input v-model="pwd.new" type="password" show-password autocomplete="new-password" placeholder="至少 8 位，包含字母和数字" /></el-form-item>
              <el-form-item label="确认新密码" prop="confirm"><el-input v-model="pwd.confirm" type="password" show-password autocomplete="new-password" /></el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="saving" @click="changePwd">修改密码</el-button>
                <el-button @click="logoutAll">退出所有设备</el-button>
              </el-form-item>
            </el-form>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'
import { authApi, miscApi, type Favorite } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { fmtTime } from '@/utils/format'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const tab = ref(auth.user?.must_change_password ? 'password' : (route.query.tab as string) || 'favorites')
const favorites = ref<Favorite[]>([])
const saving = ref(false)
const info = reactive({ nickname: auth.user?.nickname ?? '', email: auth.user?.email ?? '', phone: auth.user?.phone ?? '' })
const pwdRef = ref<FormInstance>()
const pwd = reactive({ old: '', new: '', confirm: '' })
const pwdRules: FormRules = {
  old: [{ required: true, message: '请输入原密码' }],
  new: [{ required: true, message: '请输入新密码' }, { pattern: /^(?=.*[A-Za-z])(?=.*\d).{8,72}$/, message: '至少 8 位，需同时包含字母和数字' }],
  confirm: [{ validator: (_r, v, cb) => (v === pwd.new ? cb() : cb(new Error('两次密码不一致'))) }],
}

const favLink = (f: Favorite) => (f.target_type === 'document' ? `/library/${f.subtitle}` : { path: '/cases', query: { id: f.target_id } })

async function loadFavs() {
  favorites.value = await miscApi.favorites()
}

async function removeFav(f: Favorite) {
  await miscApi.removeFavorite(f.target_type, f.target_id)
  favorites.value = favorites.value.filter((x) => x.id !== f.id)
}

async function saveInfo() {
  saving.value = true
  try {
    auth.user = await authApi.updateProfile({ nickname: info.nickname, email: info.email || null, phone: info.phone || null })
    ElMessage.success('资料已保存')
  } finally {
    saving.value = false
  }
}

async function changePwd() {
  if (!(await pwdRef.value?.validate().catch(() => false))) return
  saving.value = true
  try {
    const wasForced = auth.user?.must_change_password
    await auth.applyTokens(await authApi.changePassword(pwd.old, pwd.new))
    ElMessage.success('密码已修改')
    pwdRef.value?.resetFields()
    if (wasForced) router.replace((route.query.redirect as string) || '/')
  } finally {
    saving.value = false
  }
}

async function logoutAll() {
  await ElMessageBox.confirm('将使所有设备上的登录失效（包括当前设备），确定继续？', '退出所有设备', { type: 'warning' })
  await authApi.logoutAll()
  auth.logout()
  router.replace('/login')
}

onMounted(() => {
  if (!auth.user?.must_change_password) loadFavs()
})
</script>

<style scoped lang="scss">
.profile { padding-top: 36px; }
.force { margin-bottom: 20px; }
.layout { display: flex; gap: 24px; align-items: flex-start; }
.card {
  width: 280px;
  flex-shrink: 0;
  padding: 32px 24px;
  text-align: center;
  h3 { margin: 14px 0 0; font-size: 22px; letter-spacing: 2px; }
  .uname { color: var(--ink-3); margin: 0 0 10px; font-size: 13px; }
  dl { text-align: left; font-size: 13px; margin: 20px 0 0; display: grid; grid-template-columns: auto 1fr; gap: 6px 12px; }
  dt { color: var(--ink-3); }
  dd { margin: 0; }
}
.avatar {
  width: 84px;
  height: 84px;
  margin: 0 auto;
  border-radius: 50%;
  background: var(--indigo);
  color: #f5eedf;
  font-size: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 0 4px var(--card), 0 0 0 5px var(--gold);
}
.roles { display: flex; gap: 6px; justify-content: center; flex-wrap: wrap; }
.main { flex: 1; padding: 10px 28px 28px; min-height: 360px; }
.form { max-width: 460px; margin-top: 10px; }
.favs {
  list-style: none;
  padding: 0;
  margin: 0;
  li { display: flex; align-items: center; gap: 12px; padding: 12px 0; border-bottom: 1px dashed var(--line); }
  a { flex: 1; color: var(--ink); font-size: 16px; &:hover { color: var(--cinnabar); } }
}
.fav-type { font-size: 12px; padding: 0 6px; color: #fff; border-radius: 2px; &.document { background: var(--indigo); } &.case { background: var(--cinnabar); } }
.fav-time { font-size: 12px; color: var(--ink-3); }
@media (max-width: 800px) {
  .layout { flex-direction: column; }
  .card { width: 100%; }
  .main { width: 100%; padding: 10px 16px 20px; }
}
</style>
